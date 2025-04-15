from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JupyterSessionViewSet
from .proxy import JupyterProxyView

# 创建路由器并注册视图集
router = DefaultRouter()
router.register(r'sessions', JupyterSessionViewSet)

urlpatterns = [
    # 包含路由器生成的URL
    path('', include(router.urls)),
    
    # Jupyter代理路由 - 添加项目ID参数
    path('proxy/<str:project_id>/<path:path>', JupyterProxyView.as_view(), name='jupyter-proxy-with-path'),
    path('proxy/<str:project_id>/', JupyterProxyView.as_view(), name='jupyter-proxy-root'),
]
