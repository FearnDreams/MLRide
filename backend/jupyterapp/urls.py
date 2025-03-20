from django.urls import path, re_path
from rest_framework.routers import DefaultRouter
from .views import JupyterSessionViewSet
from .proxy import JupyterProxyView

# 创建路由器并注册viewsets
router = DefaultRouter()
router.register(r'sessions', JupyterSessionViewSet)

# URL模式列表
urlpatterns = [
    # 代理所有Jupyter请求
    re_path(r'^proxy/(?P<path>.*)$', JupyterProxyView.as_view(), name='jupyter_proxy'),
] + router.urls
