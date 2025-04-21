class CustomSecurityMiddleware:
    """自定义安全中间件，用于设置适当的安全响应头，允许在iframe中嵌入内容"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # 设置X-Frame-Options为ALLOWALL以允许在iframe中嵌入
        response['X-Frame-Options'] = 'ALLOWALL'
        
        # 设置CSP允许iframe
        response['Content-Security-Policy'] = (
            "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; "
            "frame-ancestors * 'self' http://localhost:*; "
            "script-src * 'unsafe-inline' 'unsafe-eval'"
        )
        
        # 设置CORS头以允许跨域请求
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type, X-Requested-With'
        response['Access-Control-Allow-Credentials'] = 'true'
        
        return response 