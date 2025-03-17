"""
Jupyter请求代理模块，用于将请求转发到Docker容器中运行的Jupyter服务
"""

import requests
from urllib.parse import urlparse, parse_qs
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import JupyterSession

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
    # 获取会话信息
    try:
        session = get_object_or_404(
            JupyterSession, 
            id=session_id, 
            project__user=request.user,
            status='running'
        )
    except Exception as e:
        return HttpResponse(f'获取Jupyter会话失败: {str(e)}', status=404)
    
    if not session.token:
        return HttpResponse('Jupyter会话未启动或Token无效', status=400)
    
    # 构建请求URL
    # 这里假设Docker容器和主机在同一网络，可以通过容器名称访问
    container_name = session.project.container.name
    jupyter_port = '8888'  # Jupyter默认端口
    
    url = f"http://{container_name}:{jupyter_port}/{path}"
    if request.META.get('QUERY_STRING'):
        url += f"?{request.META['QUERY_STRING']}"
    
    # 设置请求头
    headers = {}
    for key, value in request.META.items():
        if key.startswith('HTTP_') and key not in ('HTTP_HOST', 'HTTP_COOKIE'):
            header_name = key[5:].replace('_', '-').title()
            headers[header_name] = value
    
    # 设置认证信息
    cookies = {'token': session.token}
    
    # 发送请求到Jupyter服务
    try:
        response = requests.request(
            method=request.method,
            url=url,
            data=request.body if request.method in ('POST', 'PUT', 'PATCH') else None,
            headers=headers,
            cookies=cookies,
            stream=True,
            timeout=30  # 设置超时时间
        )
        
        # 构建响应
        django_response = StreamingHttpResponse(
            streaming_content=response.iter_content(chunk_size=8192),
            content_type=response.headers.get('Content-Type', 'text/plain'),
            status=response.status_code
        )
        
        # 复制响应头
        for key, value in response.headers.items():
            if key.lower() not in ('content-encoding', 'content-length', 'transfer-encoding', 'connection'):
                django_response[key] = value
        
        return django_response
    except Exception as e:
        return HttpResponse(f"请求Jupyter服务失败: {str(e)}", status=500)
