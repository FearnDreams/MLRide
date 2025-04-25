"""
This module contains the database models for the dataset management functionality.
包含数据集管理功能的数据库模型。
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import os
import uuid

def dataset_file_path(instance, filename):
    """
    生成数据集文件存储路径
    
    格式为: datasets/{用户ID}/{数据集ID}/{原始文件名}
    确保用户隔离和数据安全
    
    Args:
        instance: Dataset实例
        filename: 原始文件名
        
    Returns:
        str: 存储路径
    """
    # 如果是新创建的实例，可能还没有ID，使用UUID作为临时目录名
    folder_name = str(instance.id) if instance.id else str(uuid.uuid4())
    return f'datasets/{instance.creator.id}/{folder_name}/{filename}'

class Dataset(models.Model):
    """数据集表
    
    记录用户上传的数据集信息
    
    Attributes:
        name (str): 数据集名称
        description (str): 数据集描述
        file (FileField): 数据集文件
        file_size (BigIntegerField): 文件大小，单位为字节
        file_type (str): 文件类型 (例如 csv, json, zip等)
        created (datetime): 创建时间
        updated (datetime): 更新时间
        status (str): 数据集状态 (pending, processing, ready, failed)
        creator (ForeignKey): 创建者
        visibility (str): 可见性 (private, public)
        tags (str): 标签，存储为JSON字符串
        license (str): 许可证类型
        preview_available (bool): 是否可预览
        preview_path (str): 预览文件路径
        downloads (int): 下载次数
        error_message (str): 处理失败时的错误信息
    """
    
    # 状态选择
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('processing', '处理中'),
        ('ready', '就绪'),
        ('failed', '失败')
    ]
    
    # 可见性选择
    VISIBILITY_CHOICES = [
        ('private', '私有'),
        ('public', '公开')
    ]
    
    name = models.CharField('数据集名称', max_length=100)
    description = models.TextField('数据集描述', blank=True)
    file = models.FileField('数据集文件', upload_to=dataset_file_path, max_length=500)
    file_size = models.BigIntegerField('文件大小', default=0)
    file_type = models.CharField('文件类型', max_length=20)
    created = models.DateTimeField('创建时间', default=timezone.now)
    updated = models.DateTimeField('更新时间', auto_now=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='datasets',
        verbose_name='创建者'
    )
    visibility = models.CharField('可见性', max_length=20, choices=VISIBILITY_CHOICES, default='private')
    tags = models.TextField('标签', blank=True, help_text='存储为JSON字符串')
    license = models.CharField('许可证', max_length=100, blank=True)
    preview_available = models.BooleanField('是否可预览', default=False)
    preview_path = models.CharField('预览文件路径', max_length=500, blank=True)
    downloads = models.IntegerField('下载次数', default=0)
    error_message = models.TextField('错误信息', blank=True)
    
    class Meta:
        verbose_name = '数据集'
        verbose_name_plural = verbose_name
        ordering = ['-created']
        
    def __str__(self):
        return self.name
    
    def get_absolute_file_path(self):
        """
        获取数据集文件的绝对路径
        
        Returns:
            str: 数据集文件的绝对路径
        """
        if self.file:
            return self.file.path
        return None
        
    def get_file_extension(self):
        """
        获取文件扩展名
        
        Returns:
            str: 文件扩展名（小写）
        """
        if self.file:
            _, ext = os.path.splitext(self.file.name)
            return ext.lower().lstrip('.')
        return ''
    
    def is_image(self):
        """
        判断文件是否为图片
        
        Returns:
            bool: 是否为图片
        """
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        return self.get_file_extension() in image_extensions
    
    def is_tabular(self):
        """
        确定数据集是否为表格格式，用于决定是否可预览
        支持的表格格式：CSV, XLSX/XLS, JSON
        """
        if not self.file:
            return False
        
        tabular_extensions = ['csv', 'xlsx', 'xls', 'json', 'txt']
        file_ext = self.get_file_extension()
        return file_ext in tabular_extensions
        
    def delete(self, *args, **kwargs):
        """
        重写删除方法，同时删除文件系统中的文件
        """
        # 删除存储的文件
        if self.file:
            file_path = self.file.path
            if os.path.isfile(file_path):
                os.remove(file_path)
            
            # 如果目录为空，删除目录
            dir_path = os.path.dirname(file_path)
            if os.path.exists(dir_path) and not os.listdir(dir_path):
                os.rmdir(dir_path)
                
        # 删除预览文件
        if self.preview_path:
            preview_path = os.path.join(settings.MEDIA_ROOT, self.preview_path)
            if os.path.isfile(preview_path):
                os.remove(preview_path)
                
        # 调用父类删除方法
        super().delete(*args, **kwargs)

class DatasetPreview(models.Model):
    """数据集预览表
    
    存储数据集预览信息
    
    Attributes:
        dataset (ForeignKey): 关联的数据集
        preview_type (str): 预览类型 (image, csv, json等)
        preview_data (TextField): 预览数据，存储为JSON字符串
        created (datetime): 创建时间
        updated (datetime): 更新时间
    """
    
    PREVIEW_TYPE_CHOICES = [
        ('image', '图片'),
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
        ('text', '文本'),
        ('other', '其他')
    ]
    
    dataset = models.OneToOneField(
        Dataset,
        on_delete=models.CASCADE,
        related_name='preview',
        verbose_name='数据集'
    )
    preview_type = models.CharField('预览类型', max_length=20, choices=PREVIEW_TYPE_CHOICES)
    preview_data = models.TextField('预览数据', help_text='存储为JSON字符串')
    thumbnail_path = models.CharField('缩略图路径', max_length=500, blank=True)
    created = models.DateTimeField('创建时间', default=timezone.now)
    updated = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '数据集预览'
        verbose_name_plural = verbose_name
        
    def __str__(self):
        return f"{self.dataset.name} 的预览"
        
    def delete(self, *args, **kwargs):
        """
        重写删除方法，同时删除文件系统中的缩略图
        """
        # 删除缩略图
        if self.thumbnail_path:
            thumbnail_path = os.path.join(settings.MEDIA_ROOT, self.thumbnail_path)
            if os.path.isfile(thumbnail_path):
                os.remove(thumbnail_path)
                
        # 调用父类删除方法
        super().delete(*args, **kwargs)
