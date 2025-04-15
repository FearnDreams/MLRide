from django.db import models
from project.models import Project

# Create your models here.

class JupyterSession(models.Model):
    """Jupyter会话模型，用于管理与项目关联的Jupyter会话"""
    
    STATUS_CHOICES = (
        ('creating', '创建中'),
        ('running', '运行中'),
        ('stopped', '已停止'),
        ('error', '错误'),
    )
    
    project = models.OneToOneField(
        Project, 
        on_delete=models.CASCADE, 
        related_name='jupyter_session',
        verbose_name='关联项目'
    )
    token = models.CharField(
        max_length=64, 
        blank=True, 
        null=True,
        verbose_name='访问令牌'
    )
    url = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name='访问URL'
    )
    port = models.IntegerField(
        blank=True, 
        null=True,
        verbose_name='端口号'
    )
    workspace_dir = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='工作目录'
    )
    process_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='进程ID'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='creating',
        verbose_name='状态'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        verbose_name = 'Jupyter会话'
        verbose_name_plural = 'Jupyter会话'
        
    def __str__(self):
        return f"Jupyter会话 - {self.project.name}"
