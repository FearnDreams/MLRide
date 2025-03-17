from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JupyterSessionViewSet
from .proxy import jupyter_proxy

# 创建路由器并注册视图
router = DefaultRouter()
router.register(r'sessions', JupyterSessionViewSet, basename='jupyter-session')

urlpatterns = [
    path('', include(router.urls)),
    # 添加Jupyter代理路由
    path('proxy/<int:session_id>/', jupyter_proxy, name='jupyter-proxy'),
    path('proxy/<int:session_id>/<path:path>', jupyter_proxy, name='jupyter-proxy-path'),
]
