"""
Jupyter请求代理模块，用于将请求转发到Docker容器中运行的Jupyter服务
"""

import requests
import json
import logging
import docker
import re
from urllib.parse import urlparse, parse_qs, urlencode
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import JupyterSession
from project.models import Project

# 配置日志
logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
@permission_classes([IsAuthenticated])
def jupyter_proxy(request, session_id, path=''):
    """
    代理Jupyter请求到Docker容器中的Jupyter服务
    
    Args:
        request: HTTP请求对象
        session_id: Jupyter会话ID
        path: 请求路径
        
    Returns:
        代理后的响应
    """
    # 设置详细日志
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"接收到Jupyter代理请求: session_id={session_id}, path={path}")
    
    # 从URL参数中尝试获取项目ID
    project_id = None
    if request.GET.get('project_id'):
        project_id = request.GET.get('project_id')
        logger.info(f"从URL参数获取项目ID: {project_id}")
    
    # 优先通过项目ID查找会话
    session = None
    if project_id:
        try:
            # 清理project_id
            if isinstance(project_id, str) and '/' in project_id:
                project_id = project_id.rstrip('/')
            
            project = get_object_or_404(Project, id=project_id, user=request.user)
            logger.info(f"找到项目: id={project.id}, name={project.name}")
            
            # 先查找运行中的会话
            try:
                session = JupyterSession.objects.get(project=project, status='running')
                logger.info(f"找到运行中的会话: id={session.id}")
            except JupyterSession.DoesNotExist:
                # 如果没有运行中的会话，尝试获取任何状态的会话
                session = JupyterSession.objects.filter(project=project).first()
                if session:
                    logger.info(f"找到非运行状态的会话: id={session.id}, status={session.status}")
                else:
                    # 如果没有会话，创建一个新的
                    session = JupyterSession.objects.create(project=project)
                    logger.info(f"创建新会话: id={session.id}")
        except Exception as e:
            logger.error(f"通过项目ID查找会话失败: {str(e)}")
            return HttpResponse(f"通过项目ID查找会话失败: {str(e)}", status=500)
    else:
        # 如果没有项目ID，尝试通过会话ID查找
        try:
            session = JupyterSession.objects.get(id=session_id, project__user=request.user)
            logger.info(f"找到会话: id={session.id}, status={session.status}, project={session.project.name}")
        except JupyterSession.DoesNotExist:
            logger.warning(f"无法通过ID {session_id} 找到会话")
            return HttpResponse(f"无法找到Jupyter会话: {session_id}", status=404)
    
    # 如果会话不是运行状态，尝试重新启动
    if session.status != 'running':
        logger.warning(f"会话 {session.id} 状态不是running，当前状态: {session.status}，尝试更新状态")
        
        # 检查容器状态
        from container.docker_ops import DockerClient
        
        try:
            container_id = session.project.container.container_id
            docker_client = DockerClient()
            container = docker_client.get_container(container_id)
            
            # 检查Docker容器是否运行
            if container.status == 'running':
                # 容器已运行，检查Jupyter进程
                exec_result = container.exec_run(
                    cmd="pgrep -f 'jupyter-notebook'",
                    privileged=True
                )
                
                if exec_result.exit_code == 0:
                    # Jupyter进程存在，更新会话状态
                    logger.info(f"容器中存在Jupyter进程，更新会话 {session.id} 状态为running")
                    session.status = 'running'
                    session.save()
        except Exception as e:
            logger.error(f"检查容器状态失败: {str(e)}")
            
    # 允许空token
    # if not session.token:
    #     return HttpResponse('Jupyter会话未启动或Token无效', status=400)
    
    # 构建请求URL
    try:
        # 获取相关的容器信息
        container_instance = session.project.container
        if not container_instance:
            return HttpResponse("项目未关联容器实例", status=400)
            
        # 正确获取容器ID
        import logging
        logger = logging.getLogger(__name__)
        
        # 从ContainerInstance模型获取容器ID
        container_id = container_instance.container_id
        if not container_id:
            return HttpResponse("容器ID未找到", status=400)
            
        # 记录信息以便调试
        logger.info(f"尝试获取容器信息, 容器ID: {container_id}")
        
        # 直接使用Docker API获取容器信息
        try:
            client = docker.from_env()
            container_obj = client.containers.get(container_id)
            logger.info(f"容器状态: {container_obj.status}")
            
            # 检查容器是否在运行
            if container_obj.status != 'running':
                return HttpResponse(f"容器未运行，当前状态: {container_obj.status}", status=400)
                
            # 尝试使用容器名称访问
            container_name = container_instance.name
            logger.info(f"容器名称: {container_name}")
            
            # 尝试多种连接方式
            container_ip = None
            jupyter_port = '8888'  # Jupyter默认端口
            host_port = None
            
            # 方式1: 尝试使用端口映射（最可靠）
            port_bindings = container_obj.attrs['NetworkSettings']['Ports']
            
            if f'{jupyter_port}/tcp' in port_bindings and port_bindings[f'{jupyter_port}/tcp']:
                port_binding = port_bindings[f'{jupyter_port}/tcp'][0]
                host_port = port_binding.get('HostPort')
                
                if host_port:
                    logger.info(f"使用端口映射 {jupyter_port} -> {host_port}")
                    container_ip = 'localhost'  # 或 '127.0.0.1'
                    jupyter_port = host_port
            
            # 方式2: 直接使用容器IP（如果方式1失败）
            if not container_ip:
                logger.info("尝试获取容器IP地址")
                
                # 尝试从NetworkSettings获取IP
                container_ip = container_obj.attrs['NetworkSettings']['IPAddress']
                logger.info(f"从NetworkSettings获取IP: {container_ip}")
                
                # 如果还是获取不到IP，尝试从Networks字段获取
                if not container_ip:
                    networks = container_obj.attrs['NetworkSettings']['Networks']
                    
                    # 首先尝试bridge网络
                    if 'bridge' in networks and networks['bridge'].get('IPAddress'):
                        container_ip = networks['bridge']['IPAddress']
                        logger.info(f"从bridge网络获取IP: {container_ip}")
                    
                    # 如果bridge网络没有IP，尝试其他网络
                    if not container_ip:
                        for network_name, network_config in networks.items():
                            if network_config.get('IPAddress'):
                                container_ip = network_config['IPAddress']
                                logger.info(f"从{network_name}网络获取IP: {container_ip}")
                                break
            
            # 方式3: 最后的回退，使用localhost（可能会失败）
            if not container_ip:
                logger.warning("无法获取容器IP地址，使用localhost作为回退")
                container_ip = 'localhost'
                
            # 构建最终的请求URL
            url = f"http://{container_ip}:{jupyter_port}/{path}"
            
            # 添加token参数（仅当token不为空时）
            query_string = request.META.get('QUERY_STRING', '')
            
            # 确保token总是被添加到URL中，即使它已经在查询字符串中
            if session.token:
                # 从查询字符串中移除可能存在的token参数
                query_params = {}
                if query_string:
                    for param in query_string.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            if key.lower() != 'token':
                                query_params[key] = value
                
                # 添加会话token
                query_params['token'] = session.token
                
                # 重建查询字符串
                new_query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
                
                # 将新的查询字符串附加到URL
                if new_query_string:
                    url += f"?{new_query_string}"
            elif query_string:
                url += f"?{query_string}"
                
            logger.info(f"Jupyter代理最终请求URL: {url}")
            
        except docker.errors.NotFound:
            return HttpResponse(f"找不到容器，ID: {container_id}", status=404)
        except docker.errors.APIError as e:
            logger.error(f"Docker API错误: {str(e)}")
            return HttpResponse(f"Docker API错误: {str(e)}", status=500)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"获取容器信息失败: {str(e)}\n{error_details}")
            return HttpResponse(f"获取容器信息失败: {str(e)}", status=500)
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"代理处理异常: {str(e)}\n{error_details}")
        return HttpResponse(f"代理处理异常: {str(e)}", status=500)
    
    # 设置请求头
    headers = {}
    for header in request.META:
        if header.startswith('HTTP_'):
            name = header[5:].replace('_', '-').title()
            if name not in ['Host', 'Origin', 'Referer']:
                headers[name] = request.META[header]
    
    # 设置特定的头，覆盖原来的
    headers['Host'] = container_ip
    
    # 创建代理请求
    try:
        # 设置请求体
        data = request.body if request.body else None
        
        # 发送代理请求
        proxy_response = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=data,
            stream=True
        )
        
        # 创建Django响应
        response = HttpResponse(
            content=proxy_response.content,
            status=proxy_response.status_code,
        )
        
        # 处理响应头
        for header, value in proxy_response.headers.items():
            # 定义hop-by-hop头部列表（Django WSGI处理程序不允许这些头部）
            hop_by_hop_headers = [
                'connection', 'keep-alive', 'proxy-authenticate', 
                'proxy-authorization', 'te', 'trailers', 
                'transfer-encoding', 'upgrade'
            ]
            
            # 过滤掉hop-by-hop头部和其他不需要的头部
            if (header.lower() not in hop_by_hop_headers and 
                header.lower() not in ['content-encoding', 'content-length']):
                response[header] = value
                
        # 如果是HTML响应，修改静态资源路径
        if 'content-type' in proxy_response.headers and 'text/html' in proxy_response.headers['content-type'].lower():
            content = proxy_response.content.decode('utf-8')
            
            # 替换静态资源路径
            base_path = f"/api/jupyter/proxy/{session.id}/"
            
            # 避免嵌套路径问题 - 使用更精确的正则表达式
            
            # 替换绝对路径引用 (以 / 开头)
            content = re.sub(r'(src|href)="/(static/[^"]*)"', fr'\1="{base_path}\2"', content)
            
            # 替换相对路径引用 (不以 http 或 / 开头)
            content = re.sub(r'(src|href)="(?!http)(?!/api/jupyter/proxy)(?!/)([\w\-\.]+[^"]*)"', fr'\1="{base_path}\2"', content)
            
            # 替换 sourceMappingURL
            content = re.sub(r'(sourceMappingURL=)/(static/[^"\s]*)', fr'\1{base_path}\2', content)
            
            # 防止重复替换已经正确的路径
            content = re.sub(r'(src|href)="(/api/jupyter/proxy/\d+/api/jupyter/proxy/\d+/)', fr'\1="/api/jupyter/proxy/{session.id}/', content)
            
            response.content = content.encode('utf-8')
        
        return response
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"代理请求失败: {str(e)}\n{error_details}")
        return HttpResponse(f"代理请求失败: {str(e)}", status=500)
