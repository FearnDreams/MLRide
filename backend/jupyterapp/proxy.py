import logging
import requests
from django.http import HttpResponse
from django.views import View
from django.conf import settings
from rest_framework.exceptions import NotFound
from .models import JupyterSession
import time
import os

logger = logging.getLogger(__name__)

class JupyterProxyView(View):
    """
    Jupyter代理视图，用于将请求转发到Jupyter服务器
    
    支持通过项目ID路由到对应的Jupyter服务实例，实现项目隔离
    """
    
    def dispatch(self, request, project_id, path='', *args, **kwargs):
        """
        处理所有HTTP请求并将其转发到对应项目的Jupyter服务器
        
        Args:
            request: HTTP请求对象
            project_id: 项目ID
            path: 请求路径
            
        Returns:
            转发后的HTTP响应
        """
        start_time = time.time()
        logger.info(f"收到代理请求: 项目ID={project_id}, 路径='{path}', 方法={request.method}")
        
        try:
            # 获取该项目的Jupyter会话
            session = JupyterSession.objects.get(project_id=project_id, status='running')
            
            # 确保使用项目特定的端口
            port = session.port
            if not port:
                logger.error(f"项目ID为 {project_id} 的Jupyter会话没有有效的端口号")
                return HttpResponse(f"Jupyter会话没有有效的端口号", status=500)
            
            # 如果在Docker容器中运行，先执行双向同步确保文件一致
            if session.project.container and not session.process_id:
                try:
                    from container.docker_ops import DockerClient
                    docker_client = DockerClient()
                    
                    # 首先检查容器是否正确挂载了工作目录
                    container_info = docker_client.get_container(session.project.container.container_id)
                    container_mounts = container_info.attrs.get('Mounts', [])
                    
                    # 检查是否有挂载到/workspace的配置
                    workspace_mount_exists = False
                    for mount in container_mounts:
                        if mount.get('Destination') == '/workspace':
                            workspace_mount_exists = True
                            source_path = mount.get('Source')
                            logger.info(f"容器已正确挂载工作目录: {source_path} -> /workspace")
                            break
                    
                    # 只有在挂载不存在时才考虑同步
                    if not workspace_mount_exists:
                        # 同步工作目录
                        workspace_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'workspaces', f'project_{project_id}')
                        
                        # 对特定类型的请求进行文件同步
                        # 当涉及文件操作的请求时才进行同步，提高性能
                        should_sync = False
                        
                        # 检查是否为文件操作相关的路径
                        file_related_paths = [
                            'api/contents', 'edit', 'notebooks', 'files', 'tree'
                        ]
                        
                        # 检查是否为POST/PUT/DELETE请求或文件相关路径
                        if (request.method in ['POST', 'PUT', 'DELETE'] or
                            any(p in path for p in file_related_paths)):
                            should_sync = True
                        
                        if should_sync:
                            logger.info(f"执行文件同步 (项目ID: {project_id}, 容器ID: {session.project.container.container_id})")
                            docker_client.sync_container_directory(
                                container_id=session.project.container.container_id,
                                container_dir='/workspace',
                                host_dir=workspace_dir,
                                direction='both'
                            )
                            logger.info(f"文件同步完成: {workspace_dir} <-> /workspace")
                    else:
                        logger.info("跳过文件同步，容器已正确挂载工作目录")
                except Exception as sync_e:
                    logger.warning(f"同步项目文件时出错: {str(sync_e)}")
            
            # 检查路径并处理特殊路径
            if not path and request.method == 'GET':
                # 如果是根路径GET请求，重定向到/tree路径
                path = 'tree'
                logger.info(f"请求根路径，重定向到 /tree 路径")
            
            # 构建转发URL (使用会话的端口号)
            # 确保URL路径格式正确，避免多余的斜杠
            if path and path.startswith('/'):
                path = path[1:]  # 移除开头的斜杠
            
            jupyter_url = f"http://localhost:{port}/{path}"
            logger.info(f"正在将请求转发到 {jupyter_url} (项目ID: {project_id}, 端口: {port})")
            
            # 构建请求头 (除了Host和Cookie，直接转发其他头)
            headers = {}
            important_headers = [
                'content-type', 'accept', 'authorization',
                'x-requested-with', 'user-agent', 'origin',
                'x-forwarded-for', 'x-forwarded-proto', 'x-forwarded-host'
            ]
            
            for key, value in request.headers.items():
                # 只保留重要的头部，减少请求头大小
                if key.lower() in important_headers:
                    headers[key] = value
                # 跳过可能导致头部过大的字段
                elif key.lower() in ['host', 'cookie', 'connection', 'sec-ch-ua']:
                    continue
            
            # 添加原始主机信息和其他有用的头信息
            headers['X-Forwarded-For'] = request.META.get('REMOTE_ADDR', '')
            headers['X-Forwarded-Proto'] = request.scheme
            headers['X-Forwarded-Host'] = request.get_host()
            
            # 转发Cookie，但添加项目的token
            if 'Cookie' in request.headers:
                headers['Cookie'] = request.headers['Cookie']
            if session.token:
                # 如果Cookie中已经存在token，则不重复添加
                if 'Cookie' in headers and f'token={session.token}' not in headers['Cookie']:
                    headers['Cookie'] = headers.get('Cookie', '') + f'; token={session.token}'
                else:
                    headers['Cookie'] = f'token={session.token}'
            
            method = request.method.lower()
            request_data = request.body if method in ['post', 'put', 'patch'] else None
            
            # 打印详细的请求信息
            logger.debug(f"请求详情: URL={jupyter_url}, 方法={method}, 头信息={headers}")
            
            # 执行请求
            try:
                start_req_time = time.time()
                response = requests.request(
                    method=method,
                    url=jupyter_url,
                    headers=headers,
                    data=request_data,
                    params=request.GET,
                    stream=True,
                    timeout=30  # 超时时间
                )
                request_time = time.time() - start_req_time
                
                # 构建响应
                django_response = HttpResponse(
                    content=response.raw.read(),
                    status=response.status_code,
                )
                
                # 转发响应头
                for key, value in response.headers.items():
                    if key.lower() not in ['content-length', 'transfer-encoding', 'content-encoding']:
                        django_response[key] = value
                
                # 修改响应头，确保允许在iframe中显示
                django_response['X-Frame-Options'] = 'ALLOWALL'
                django_response['Content-Security-Policy'] = "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; frame-ancestors * 'self'"
                django_response['Access-Control-Allow-Origin'] = '*'
                django_response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                django_response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type, X-Requested-With'
                django_response['Access-Control-Allow-Credentials'] = 'true'
                # 增加以下响应头以确保iframe正确加载
                django_response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                django_response['Pragma'] = 'no-cache'
                django_response['Expires'] = '0'
                django_response['P3P'] = 'CP="ALL DSP COR PSAa PSDa OUR NOR ONL UNI COM NAV"'
                
                # 如果是文件操作相关的响应，再次同步文件
                if (method in ['post', 'put', 'delete'] and 
                    'api/contents' in path and 
                    response.status_code in [200, 201, 204] and
                    session.project.container and not session.process_id):
                    try:
                        from container.docker_ops import DockerClient
                        docker_client = DockerClient()
                        
                        # 检查容器是否正确挂载了工作目录
                        container_info = docker_client.get_container(session.project.container.container_id)
                        container_mounts = container_info.attrs.get('Mounts', [])
                        
                        # 检查是否有挂载到/workspace的配置
                        workspace_mount_exists = False
                        for mount in container_mounts:
                            if mount.get('Destination') == '/workspace':
                                workspace_mount_exists = True
                                break
                                
                        # 只有在挂载不存在时才执行同步
                        if not workspace_mount_exists:
                            workspace_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'workspaces', f'project_{project_id}')
                            
                            # 在响应后异步进行同步
                            import threading
                            
                            def delayed_sync():
                                try:
                                    # 等待一秒，确保容器内操作完成
                                    time.sleep(1)
                                    logger.info(f"文件操作后执行同步: {workspace_dir} <-> /workspace")
                                    docker_client.sync_container_directory(
                                        container_id=session.project.container.container_id,
                                        container_dir='/workspace',
                                        host_dir=workspace_dir,
                                        direction='both'
                                    )
                                    logger.info("文件操作后同步完成")
                                except Exception as e:
                                    logger.error(f"延迟同步时出错: {str(e)}")
                            
                            threading.Thread(target=delayed_sync, daemon=True).start()
                        else:
                            logger.info("跳过文件操作后同步，容器已正确挂载工作目录")
                    except Exception as e:
                        logger.warning(f"响应后文件同步失败: {str(e)}")
                
                # 计算总处理时间
                total_time = time.time() - start_time
                logger.info(f"转发请求成功: 状态码={response.status_code}, 请求时间={request_time:.3f}秒, 总时间={total_time:.3f}秒")
                return django_response
            except requests.exceptions.Timeout:
                logger.error(f"请求超时: {jupyter_url}")
                return HttpResponse("Jupyter服务请求超时，请稍后重试", status=504)  # Gateway Timeout
            except requests.exceptions.ConnectionError:
                logger.error(f"连接错误: {jupyter_url}, 可能是Jupyter服务未完全启动或已停止")
                return HttpResponse("无法连接到Jupyter服务，服务可能未完全启动或已停止，请刷新页面重试", status=502)  # Bad Gateway
            
        except JupyterSession.DoesNotExist:
            logger.error(f"找不到项目ID为 {project_id} 的运行中的Jupyter会话")
            raise NotFound(f"找不到项目ID为 {project_id} 的运行中的Jupyter会话")
        except requests.RequestException as e:
            logger.error(f"代理请求失败: {str(e)}")
            return HttpResponse(f"代理请求失败: {str(e)}", status=500)
        except Exception as e:
            logger.error(f"代理请求时发生未知错误: {str(e)}")
            return HttpResponse(f"代理请求时发生未知错误: {str(e)}", status=500)