"""
This module contains the URL configuration for the container management functionality.
包含容器管理功能的URL配置。
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'images', views.DockerImageViewSet, basename='image')
router.register(r'containers', views.ContainerInstanceViewSet, basename='container')
router.register(r'quotas', views.ResourceQuotaViewSet, basename='quota')

# URL模式列表
urlpatterns = [
    path('', include(router.urls)),
] 