import logging
import requests
from django.http import HttpResponse
from django.views import View
from django.conf import settings
from rest_framework.exceptions import NotFound
from .models import JupyterSession
import time

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
            for key, value in request.headers.items():
                if key.lower() not in ['host', 'cookie']:
                    headers[key] = value
            
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