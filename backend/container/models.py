"""
This module contains the database models for the container management functionality.
包含容器管理功能的数据库模型。
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

class DockerImage(models.Model):
    """Docker镜像信息表
    
    存储系统支持的Docker镜像信息,包括镜像名称、版本、描述等
    
    Attributes:
        name (str): 镜像名称
        description (str): 镜像描述
        python_version (str): Python版本
        created (datetime): 创建时间
        status (str): 镜像状态
        creator (ForeignKey): 创建者
        image_tag (str): Docker镜像标签
    """
    
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('building', '构建中'),
        ('ready', '就绪'),
        ('failed', '失败')
    ]
    
    TYPE_CHOICES = (
        ('ide', 'IDE开发环境'),
        ('notebook', 'Jupyter Notebook'),
        ('canvas', '可视化拖拽编程'),
        ('base', '基础镜像'),
    )

    name = models.CharField('镜像名称', max_length=50)
    description = models.TextField('描述', blank=True)
    python_version = models.CharField('Python版本', max_length=10)
    created = models.DateTimeField('创建时间', default=timezone.now)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='docker_images',
        verbose_name='创建者'
    )
    image_tag = models.CharField('Docker镜像标签', max_length=100, blank=True, null=True)
    
    # 新增字段，但设置为可选
    image_type = models.CharField('镜像类型', max_length=20, choices=TYPE_CHOICES, default='base', blank=True, null=True)
    min_cpu = models.FloatField('最小CPU核心数', default=1, blank=True, null=True)
    min_memory = models.IntegerField('最小内存(MB)', default=1024, blank=True, null=True)
    min_gpu = models.IntegerField('最小GPU数量', default=0, blank=True, null=True)
    dockerfile = models.TextField('Dockerfile内容', blank=True, null=True)
    build_log = models.TextField('构建日志', blank=True, null=True)
    error_message = models.TextField('错误信息', blank=True, null=True)
    use_slim = models.BooleanField('使用slim版本', default=True)
    actual_version = models.CharField('实际Python版本', max_length=10, blank=True, null=True)
    
    # 新增PyTorch和CUDA支持字段
    is_pytorch = models.BooleanField('是否使用PyTorch', default=False)
    pytorch_version = models.CharField('PyTorch版本', max_length=10, blank=True, null=True)
    cuda_version = models.CharField('CUDA版本', max_length=10, blank=True, null=True)
    cuda_available = models.BooleanField('CUDA可用', default=False)

    class Meta:
        verbose_name = 'Docker镜像'
        verbose_name_plural = verbose_name
        ordering = ['-created']

    def __str__(self):
        base_name = f"{self.name} (Python {self.python_version})"
        if self.is_pytorch and self.pytorch_version:
            cuda_info = f", CUDA {self.cuda_version}" if self.cuda_available and self.cuda_version else ""
            return f"{base_name}, PyTorch {self.pytorch_version}{cuda_info}"
        return base_name

    def get_full_image_name(self):
        """
        获取完整的Docker镜像名称
        
        Returns:
            str: 完整的Docker镜像名称，格式为 mlride-{username}-{name}:{tag}
        """
        if not self.image_tag:
            return None
        
        return self.image_tag

class ContainerInstance(models.Model):
    """容器实例表
    
    记录用户创建的容器实例信息
    
    Attributes:
        user (ForeignKey): 关联的用户
        image (ForeignKey): 使用的Docker镜像
        container_id (str): Docker容器ID
        name (str): 容器名称
        status (str): 容器状态
        created_at (datetime): 创建时间
        started_at (datetime): 启动时间
        cpu_limit (int): CPU限制(核)
        memory_limit (int): 内存限制(MB)
        gpu_limit (int): GPU限制(个)
    """
    
    STATUS_CHOICES = [
        ('created', '已创建'),
        ('running', '运行中'),
        ('paused', '已暂停'),
        ('stopped', '已停止'),
        ('deleted', '已删除'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="关联用户"
    )
    image = models.ForeignKey(
        DockerImage,
        on_delete=models.PROTECT,
        help_text="使用的镜像"
    )
    container_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Docker容器ID"
    )
    name = models.CharField(max_length=100, help_text="容器名称")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='created',
        help_text="容器状态"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="创建时间")
    started_at = models.DateTimeField(null=True, blank=True, help_text="启动时间")
    cpu_limit = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="CPU限制(核)"
    )
    memory_limit = models.IntegerField(
        validators=[MinValueValidator(512)],
        help_text="内存限制(MB)"
    )
    gpu_limit = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="GPU限制(个)"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.status})"

class ResourceQuota(models.Model):
    """资源配额表
    
    记录用户的资源使用配额
    
    Attributes:
        user (ForeignKey): 关联的用户
        max_containers (int): 最大容器数量
        max_cpu (int): 最大CPU使用量(核)
        max_memory (int): 最大内存使用量(MB)
        max_gpu (int): 最大GPU使用量(个)
        created_at (datetime): 创建时间
        updated_at (datetime): 更新时间
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="关联用户"
    )
    max_containers = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text="最大容器数量"
    )
    max_cpu = models.IntegerField(
        default=4,
        validators=[MinValueValidator(1)],
        help_text="最大CPU使用量(核)"
    )
    max_memory = models.IntegerField(
        default=8192,
        validators=[MinValueValidator(1024)],
        help_text="最大内存使用量(MB)"
    )
    max_gpu = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0)],
        help_text="最大GPU使用量(个)"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="创建时间")
    updated_at = models.DateTimeField(auto_now=True, help_text="更新时间")

    def __str__(self):
        return f"{self.user.username}'s quota"

class Container(models.Model):
    """容器模型"""
    STATUS_CHOICES = (
        ('created', '已创建'),
        ('running', '运行中'),
        ('exited', '已停止'),
        ('paused', '已暂停'),
        ('restarting', '重启中'),
        ('removing', '删除中'),
        ('error', '错误'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    docker_id = models.CharField('Docker容器ID', max_length=64, blank=True, null=True)
    name = models.CharField('容器名称', max_length=100)
    image = models.ForeignKey(DockerImage, on_delete=models.CASCADE, related_name='containers', verbose_name='镜像')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    port_mappings = models.JSONField('端口映射', blank=True, null=True)
    environment = models.JSONField('环境变量', blank=True, null=True)
    volumes = models.JSONField('数据卷', blank=True, null=True)
    
    # 添加容器详细状态信息
    container_logs = models.TextField('容器日志', blank=True, null=True)
    exit_code = models.IntegerField('退出代码', null=True, blank=True)
    error_message = models.TextField('错误信息', blank=True, null=True)
    
    # IDE服务状态
    ide_ready = models.BooleanField('IDE服务就绪', default=False)
    ide_url = models.CharField('IDE URL', max_length=200, blank=True, null=True)
    ide_startup_logs = models.TextField('IDE启动日志', blank=True, null=True)
    
    class Meta:
        verbose_name = '容器'
        verbose_name_plural = '容器'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
