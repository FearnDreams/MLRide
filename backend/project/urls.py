"""
This module contains the URL configuration for the project management functionality.
包含项目管理功能的URL配置。
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, ProjectFileViewSet, WorkflowViewSet, WorkflowExecutionViewSet
from container.views import DockerImageViewSet

# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'files', ProjectFileViewSet, basename='project-file')
router.register(r'images', DockerImageViewSet, basename='dockerimage')
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'workflow-executions', WorkflowExecutionViewSet, basename='workflow-execution')

# ProjectViewSet 会自动处理 /projects/ 和 /projects/{pk}/
# 以及通过 @action 定义的路由，例如 /projects/{pk}/start/, /projects/{pk}/upload_data/

# URL模式列表
urlpatterns = [
    path('', include(router.urls)),
] 