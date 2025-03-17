"""
This module contains the database models for the project management functionality.
包含项目管理功能的数据库模型。
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from container.models import DockerImage, ContainerInstance

class Project(models.Model):
    """项目表
    
    记录用户创建的项目信息
    
    Attributes:
        name (str): 项目名称
        description (str): 项目描述
        project_type (str): 项目类型(IDE/Notebook/Canvas)
        created_at (datetime): 创建时间
        updated_at (datetime): 更新时间
        user (ForeignKey): 项目创建者
        image (ForeignKey): 使用的Docker镜像
        container (ForeignKey): 关联的容器实例
        is_public (bool): 是否公开
        status (str): 项目状态
    """
    
    # 项目类型选择
    TYPE_CHOICES = [
        ('ide', 'IDE开发环境'),
        ('notebook', 'Jupyter Notebook'),
        ('canvas', '可视化拖拽编程'),
    ]
    
    # 项目状态选择
    STATUS_CHOICES = [
        ('creating', '创建中'),
        ('running', '运行中'),
        ('stopped', '已停止'),
        ('error', '错误'),
    ]
    
    name = models.CharField('项目名称', max_length=100)
    description = models.TextField('项目描述', blank=True)
    project_type = models.CharField('项目类型', max_length=20, choices=TYPE_CHOICES, default='ide')
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='projects',
        verbose_name='创建者'
    )
    image = models.ForeignKey(
        DockerImage,
        on_delete=models.PROTECT, 
        related_name='projects',
        verbose_name='使用镜像'
    )
    container = models.OneToOneField(
        ContainerInstance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project',
        verbose_name='关联容器'
    )
    is_public = models.BooleanField('是否公开', default=False)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='creating')
    
    class Meta:
        verbose_name = '项目'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} ({self.get_project_type_display()})"
        
class ProjectFile(models.Model):
    """项目文件表
    
    记录项目中的文件信息
    
    Attributes:
        project (ForeignKey): 关联的项目
        name (str): 文件名称
        path (str): 文件路径
        content_type (str): 内容类型
        size (int): 文件大小(字节)
        created_at (datetime): 创建时间
        updated_at (datetime): 更新时间
    """
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name='关联项目'
    )
    name = models.CharField('文件名称', max_length=255)
    path = models.CharField('文件路径', max_length=1000)
    content_type = models.CharField('内容类型', max_length=100)
    size = models.IntegerField('文件大小', default=0)
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '项目文件'
        verbose_name_plural = verbose_name
        ordering = ['path', 'name']
        
    def __str__(self):
        return f"{self.path}/{self.name}"
