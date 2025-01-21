"""
URL configuration for mlride project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    #拼接路径，完整路径为http://127.0.0.1:8000/api/auth/register/和http://127.0.0.1:8000/api/auth/login/还有http://127.0.0.1:8000/api/auth/logout/
    path('api/auth/', include('authentication.urls')),#包含authentication.urls中的所有路径
]
