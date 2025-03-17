"""
This module contains the URL configuration for the project management functionality.
包含项目管理功能的URL配置。
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, ProjectFileViewSet

# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'files', ProjectFileViewSet, basename='project-file')

# URL模式列表
urlpatterns = [
    path('', include(router.urls)),
] 