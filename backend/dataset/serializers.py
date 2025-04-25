"""
This module contains the serializers for the dataset management functionality.
包含数据集管理功能的序列化器。
"""

import json
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Dataset, DatasetPreview

User = get_user_model()

class DatasetSerializer(serializers.ModelSerializer):
    """数据集序列化器
    
    用于序列化和反序列化数据集信息
    
    Fields:
        id: 数据集ID
        name: 数据集名称
        description: 数据集描述
        file: 数据集文件
        file_size: 文件大小(字节)
        file_type: 文件类型
        created: 创建时间
        updated: 更新时间
        status: 数据集状态
        creator: 创建者ID
        creator_name: 创建者名称(只读)
        visibility: 可见性
        tags: 标签
        license: 许可证
        preview_available: 是否可预览(只读)
        downloads: 下载次数(只读)
    """
    
    creator_name = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Dataset
        fields = [
            'id', 'name', 'description', 'file', 'file_size', 'file_size_display',
            'file_type', 'created', 'updated', 'status', 'status_display', 'creator',
            'creator_name', 'visibility', 'tags', 'license', 'preview_available',
            'downloads'
        ]
        read_only_fields = [
            'id', 'file_size', 'file_type', 'created', 'updated', 
            'status', 'creator', 'preview_available', 'downloads'
        ]
    
    def get_creator_name(self, obj):
        """获取创建者名称"""
        return obj.creator.username if obj.creator else None
    
    def get_tags(self, obj):
        """获取标签列表"""
        if not obj.tags:
            return []
        try:
            return json.loads(obj.tags)
        except:
            # 如果JSON解析失败，尝试以逗号分隔的字符串解析
            return [tag.strip() for tag in obj.tags.split(',') if tag.strip()]
    
    def get_file_size_display(self, obj):
        """获取格式化的文件大小"""
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.2f} KB"
        elif obj.file_size < 1024 * 1024 * 1024:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
        else:
            return f"{obj.file_size / (1024 * 1024 * 1024):.2f} GB"
    
    def get_status_display(self, obj):
        """获取状态显示名称"""
        status_map = {
            'pending': '等待中',
            'processing': '处理中',
            'ready': '就绪',
            'failed': '失败'
        }
        return status_map.get(obj.status, obj.status)
    
    def validate_file(self, value):
        """验证文件"""
        # 检查文件大小，限制为10GB
        if value.size > 10 * 1024 * 1024 * 1024:  # 10GB
            raise serializers.ValidationError("文件必须小于10GB")
        return value
    
    def create(self, validated_data):
        """创建数据集"""
        # 设置创建者为当前用户
        validated_data['creator'] = self.context['request'].user
        
        # 处理标签
        tags = self.context['request'].data.get('tags', [])
        if tags:
            # 如果是字符串，尝试解析为JSON
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    # 如果解析失败，尝试以逗号分隔的方式解析
                    tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
                    
            # 如果是列表，转换为JSON字符串
            if isinstance(tags, list):
                validated_data['tags'] = json.dumps(tags)
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """更新数据集"""
        # 处理标签
        tags = self.context['request'].data.get('tags')
        if tags is not None:
            # 如果是字符串，尝试解析为JSON
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    # 如果解析失败，尝试以逗号分隔的方式解析
                    tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
                    
            # 如果是列表，转换为JSON字符串
            if isinstance(tags, list):
                validated_data['tags'] = json.dumps(tags)
        
        return super().update(instance, validated_data)

class DatasetPreviewSerializer(serializers.ModelSerializer):
    """数据集预览序列化器
    
    用于序列化和反序列化数据集预览信息
    
    Fields:
        dataset: 关联的数据集ID
        preview_type: 预览类型
        preview_data: 预览数据
        thumbnail_path: 缩略图路径
        created: 创建时间
        updated: 更新时间
    """
    
    class Meta:
        model = DatasetPreview
        fields = [
            'dataset', 'preview_type', 'preview_data', 'thumbnail_path',
            'created', 'updated'
        ]
        read_only_fields = ['created', 'updated'] 