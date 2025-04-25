"""
This module contains signal handlers for the dataset app.
数据集应用的信号处理器。
"""

import os
import json
import logging
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from .models import Dataset, DatasetPreview

# 设置日志记录器
logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Dataset)
def set_file_info(sender, instance, **kwargs):
    """
    在保存数据集前设置文件信息
    """
    # 对于新创建的数据集（没有ID）
    if not instance.id and instance.file:
        # 设置文件大小
        instance.file_size = instance.file.size
        
        # 设置文件类型（从文件名获取扩展名）
        _, ext = os.path.splitext(instance.file.name)
        instance.file_type = ext.lower().lstrip('.')
        
        # 如果没有创建时间，设置为当前时间
        if not instance.created:
            instance.created = timezone.now()
            
        logger.info(f"设置数据集 {instance.name} 的文件信息: 大小={instance.file_size}字节, 类型={instance.file_type}")

@receiver(post_save, sender=Dataset)
def process_dataset(sender, instance, created, **kwargs):
    """
    数据集保存后处理
    """
    if created:
        logger.info(f"新数据集 {instance.name} (ID: {instance.id}) 已创建，开始处理")
        
        # 设置状态为处理中
        instance.status = 'processing'
        instance.save(update_fields=['status'])
        
        try:
            # 检查是否为可预览的文件类型
            if instance.is_tabular() or instance.is_image():
                logger.info(f"数据集 {instance.name} 是可预览的类型: {instance.file_type}")
                
                # 在这里可以异步启动预览生成任务
                # 例如使用Celery任务队列
                # 但目前先用同步方式简单实现
                generate_preview(instance)
            else:
                logger.info(f"数据集 {instance.name} 类型 {instance.file_type} 不支持预览")
                # 直接标记为就绪状态
                instance.status = 'ready'
                instance.save(update_fields=['status'])
        except Exception as e:
            logger.error(f"处理数据集 {instance.name} 时出错: {str(e)}")
            instance.status = 'failed'
            instance.error_message = str(e)
            instance.save(update_fields=['status', 'error_message'])

def generate_preview(dataset):
    """
    生成数据集预览
    
    根据文件类型设置 preview_available 标志和 preview_type
    """
    try:
        logger.info(f"开始为数据集 {dataset.name} 生成预览")
        
        preview_data = {}
        preview_type = 'other' # 默认类型
        preview_available = False # 默认不可预览
        preview_path = '' # 默认预览路径为空
        
        # 根据文件类型生成不同的预览
        file_ext = dataset.get_file_extension()
        
        # 处理CSV文件
        if file_ext == 'csv':
            preview_type = 'csv'
            preview_data = {'supported': True, 'message': 'CSV预览可用'}
            preview_available = True
            
        # 处理Excel文件
        elif file_ext in ['xlsx', 'xls']:
            preview_type = 'excel'
            preview_data = {'supported': True, 'message': 'Excel预览可用'}
            preview_available = True
            
        # 处理JSON文件
        elif file_ext == 'json':
            preview_type = 'json'
            preview_data = {'supported': True, 'message': 'JSON预览可用'}
            preview_available = True

        # 处理TXT文件
        elif file_ext == 'txt':
            preview_type = 'text' # 与 DatasetPreview 模型中的 choices 保持一致
            preview_data = {'supported': True, 'message': 'TXT预览可用'}
            preview_available = True
            
        # 处理图片文件
        elif dataset.is_image():
            preview_type = 'image'
            preview_data = {'supported': True, 'message': '图片预览可用'}
            preview_available = True
            preview_path = dataset.file.name # 图片预览直接使用原文件
            
        # 保存预览数据
        DatasetPreview.objects.update_or_create(
            dataset=dataset,
            defaults={
                'preview_type': preview_type,
                'preview_data': json.dumps(preview_data),
                # thumbnail_path 目前只用于图片，可以在这里根据需要设置
            }
        )
        
        # 更新数据集状态和预览相关字段
        dataset.status = 'ready'
        dataset.preview_available = preview_available
        dataset.preview_path = preview_path
        
        # 添加日志，确认即将保存的状态
        logger.info(f"准备更新数据集 {dataset.name} (ID: {dataset.id}): status='{dataset.status}', preview_available={dataset.preview_available}, preview_path='{dataset.preview_path}'")
        
        dataset.save(update_fields=['status', 'preview_available', 'preview_path']) # 确保包含 preview_available
        
        logger.info(f"数据集 {dataset.name} 的预览生成完成，类型: {preview_type}, 可预览: {preview_available}")
        
    except Exception as e:
        logger.error(f"生成数据集 {dataset.name} 的预览时出错: {str(e)}", exc_info=True)
        dataset.status = 'failed'
        dataset.error_message = f"生成预览失败: {str(e)}"
        dataset.save(update_fields=['status', 'error_message']) 