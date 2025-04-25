"""
This module contains the URL configuration for the dataset management functionality.
包含数据集管理功能的URL配置。
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DatasetViewSet

# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'datasets', DatasetViewSet, basename='dataset')

# URL模式列表
urlpatterns = [
    path('', include(router.urls)),
] 