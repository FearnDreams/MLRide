"""
This module contains the serializers for the project management functionality.
包含项目管理功能的序列化器。
"""

from rest_framework import serializers
from django.utils import timezone
from .models import Project, ProjectFile
from container.serializers import DockerImageSerializer, ContainerInstanceSerializer


class ProjectFileSerializer(serializers.ModelSerializer):
    """项目文件序列化器
    
    用于序列化和反序列化项目文件信息
    
    Fields:
        id: 文件ID
        project: 关联项目
        name: 文件名称
        path: 文件路径
        content_type: 内容类型
        size: 文件大小(字节)
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    class Meta:
        model = ProjectFile
        fields = ['id', 'project', 'name', 'path', 'content_type', 'size', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    """项目序列化器
    
    用于序列化和反序列化项目信息
    
    Fields:
        id: 项目ID
        name: 项目名称
        description: 项目描述
        project_type: 项目类型
        created_at: 创建时间
        updated_at: 更新时间
        user: 创建者ID
        image: 使用的镜像ID
        container: 关联的容器ID
        is_public: 是否公开
        status: 项目状态
        image_details: 镜像详情
        container_details: 容器详情
        files: 项目文件列表
    """
    
    image_details = DockerImageSerializer(source='image', read_only=True)
    container_details = ContainerInstanceSerializer(source='container', read_only=True)
    files = ProjectFileSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'project_type', 'created_at', 'updated_at', 
            'user', 'image', 'container', 'is_public', 'status', 'image_details', 
            'container_details', 'files', 'username'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'status', 'container', 'user']
    
    def validate_name(self, value):
        """
        验证项目名称
        """
        if not value:
            raise serializers.ValidationError("项目名称不能为空")
        if len(value) > 100:
            raise serializers.ValidationError("项目名称不能超过100个字符")
        # 检查当前用户是否已有同名项目
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if Project.objects.filter(user=request.user, name=value).exists():
                if self.instance and self.instance.name == value:
                    return value
                raise serializers.ValidationError("您已有同名项目，请更换名称")
        return value
    
    def create(self, validated_data):
        """
        创建项目
        """
        # 设置用户
        request = self.context.get('request')
        validated_data['user'] = request.user
        
        # 创建项目
        project = Project.objects.create(**validated_data)
        return project 