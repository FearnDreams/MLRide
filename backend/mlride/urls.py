"""
This module contains the main URL configuration for the MLRide project.
包含MLRide项目的主URL配置。
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    #拼接路径，完整路径为http://127.0.0.1:8000/api/auth/register/和http://127.0.0.1:8000/api/auth/login/还有http://127.0.0.1:8000/api/auth/logout/
    path('api/auth/', include('authentication.urls')),#包含authentication.urls中的所有路径
    path('api/container/', include('container.urls')),
]

# 在开发环境中添加媒体文件的URL配置
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
