import requests
from django.http import HttpResponse, StreamingHttpResponse
from django.views import View
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

class JupyterProxyView(View):
    """代理Jupyter请求的视图"""
    
    def dispatch(self, request, *args, **kwargs):
        """处理所有类型的请求"""
        try:
            # 构建目标URL
            jupyter_url = 'http://127.0.0.1:8888'
            path = request.path.replace('/api/jupyter/proxy', '')
            if not path:
                path = '/'  # 如果路径为空，添加/作为根路径
            target_url = urljoin(jupyter_url, path)
            
            logger.info(f"收到代理请求: {request.method} {request.path}")
            logger.info(f"代理转发到: {target_url}")
            
            # 获取请求方法
            method = request.method.lower()
            
            # 准备请求参数
            request_kwargs = {
                'method': method,
                'url': target_url,
                'headers': {
                    key: value
                    for key, value in request.headers.items()
                    if key.lower() not in ['host', 'cookie']
                },
                'allow_redirects': False,
                'stream': True,
            }
            
            # 添加请求体
            if method in ['post', 'put', 'patch']:
                request_kwargs['data'] = request.body
            
            # 添加查询参数
            if request.GET:
                request_kwargs['params'] = request.GET
                
            logger.info(f"代理请求: {method.upper()} {target_url}")
            
            # 发送请求
            response = requests.request(**request_kwargs)
            
            # 记录响应信息
            logger.info(f"代理响应: 状态码={response.status_code}, 内容类型={response.headers.get('content-type', 'unknown')}")
            
            # 创建响应
            proxy_response = StreamingHttpResponse(
                streaming_content=response.iter_content(chunk_size=8192),
                status=response.status_code,
                content_type=response.headers.get('content-type', 'text/plain'),
            )
            
            # 复制响应头
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            for key, value in response.headers.items():
                if key.lower() not in excluded_headers:
                    proxy_response[key] = value
            
            return proxy_response
            
        except Exception as e:
            logger.error(f"代理请求失败: {str(e)}")
        return HttpResponse(f"代理请求失败: {str(e)}", status=500)