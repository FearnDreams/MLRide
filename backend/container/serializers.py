"""
This module contains the serializers for the container management functionality.
包含容器管理功能的序列化器。
"""

from rest_framework import serializers
from django.utils import timezone
from .models import DockerImage, ContainerInstance, ResourceQuota


class DockerImageSerializer(serializers.ModelSerializer):
    """Docker镜像序列化器
    
    用于序列化和反序列化Docker镜像信息
    
    Fields:
        id: 镜像ID
        name: 镜像名称
        description: 镜像描述
        pythonVersion: Python版本
        created: 创建时间
        status: 镜像状态
        creator_username: 创建者用户名
    """
    
    pythonVersion = serializers.CharField(source='python_version')
    creator_username = serializers.CharField(source='creator.username', read_only=True)
    
    class Meta:
        model = DockerImage
        fields = ['id', 'name', 'description', 'pythonVersion', 'created', 'status', 'creator_username']
        read_only_fields = ['id', 'created', 'status', 'creator_username']

    def validate_name(self, value):
        """
        验证镜像名称
        """
        if not value:
            raise serializers.ValidationError("镜像名称不能为空")
        if len(value) > 50:
            raise serializers.ValidationError("镜像名称不能超过50个字符")
        if not all(c.isalnum() or c in '-_' for c in value):
            raise serializers.ValidationError("镜像名称只能包含字母、数字、下划线和连字符")
        return value

    def validate_pythonVersion(self, value):
        """
        验证Python版本
        """
        valid_versions = ['3.8', '3.9', '3.10', '3.11']
        if value not in valid_versions:
            raise serializers.ValidationError(f"Python版本必须是以下之一: {', '.join(valid_versions)}")
        return value

    def create(self, validated_data):
        """
        创建镜像
        """
        # 从validated_data中获取python_version
        python_version = validated_data.pop('python_version', None)
        if not python_version:
            raise serializers.ValidationError("Python版本是必需的")
            
        # 设置初始状态
        validated_data['status'] = 'pending'
        
        # 确保creator字段存在
        if not self.context.get('request'):
            raise serializers.ValidationError("缺少请求上下文")
            
        validated_data['creator'] = self.context['request'].user
        
        # 创建镜像实例
        image = DockerImage.objects.create(
            python_version=python_version,
            **validated_data
        )
        return image


class ResourceQuotaSerializer(serializers.ModelSerializer):
    """资源配额序列化器
    
    用于序列化和反序列化用户资源配额信息
    
    Fields:
        id: 配额ID
        user: 关联用户
        max_containers: 最大容器数量
        max_cpu: 最大CPU使用量
        max_memory: 最大内存使用量
        max_gpu: 最大GPU使用量
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    class Meta:
        model = ResourceQuota
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, data):
        """验证资源配额数据
        
        确保资源配额限制合理
        
        Args:
            data: 待验证的数据

        Returns:
            验证后的数据

        Raises:
            serializers.ValidationError: 当验证失败时抛出
        """
        if data.get('max_memory') < 1024:
            raise serializers.ValidationError("最大内存配额不能小于1024MB")
            
        if data.get('max_cpu') < 1:
            raise serializers.ValidationError("最大CPU配额不能小于1核")
            
        if data.get('max_containers') < 1:
            raise serializers.ValidationError("最大容器数量不能小于1个")
            
        return data


class ContainerInstanceSerializer(serializers.ModelSerializer):
    """容器实例序列化器
    
    用于序列化和反序列化容器实例信息
    
    Fields:
        id: 容器ID
        user: 关联用户
        image: 使用的镜像
        container_id: Docker容器ID
        name: 容器名称
        status: 容器状态
        cpu_limit: CPU限制
        memory_limit: 内存限制
        gpu_limit: GPU限制
        created_at: 创建时间
        started_at: 启动时间
        port_mappings: 端口映射信息
    """
    
    image_details = DockerImageSerializer(source='image', read_only=True)
    port_mappings = serializers.JSONField(required=False, allow_null=True)
    
    class Meta:
        model = ContainerInstance
        fields = '__all__'
        read_only_fields = ('container_id', 'created_at', 'started_at', 'status')

    def validate(self, data):
        """验证容器实例数据
        
        确保资源限制符合配额要求且不低于镜像最低要求
        
        Args:
            data: 待验证的数据

        Returns:
            验证后的数据

        Raises:
            serializers.ValidationError: 当验证失败时抛出
        """
        user = data.get('user')
        image = data.get('image')
        
        # 验证资源限制不低于镜像要求
        if data.get('cpu_limit') < image.min_cpu:
            raise serializers.ValidationError(
                f"CPU限制不能低于镜像要求的{image.min_cpu}核"
            )
            
        if data.get('memory_limit') < image.min_memory:
            raise serializers.ValidationError(
                f"内存限制不能低于镜像要求的{image.min_memory}MB"
            )
            
        if data.get('gpu_limit') < image.min_gpu:
            raise serializers.ValidationError(
                f"GPU限制不能低于镜像要求的{image.min_gpu}个"
            )
            
        # 验证是否超过用户配额
        try:
            quota = ResourceQuota.objects.get(user=user)
            
            if data.get('cpu_limit') > quota.max_cpu:
                raise serializers.ValidationError(
                    f"CPU限制不能超过配额{quota.max_cpu}核"
                )
                
            if data.get('memory_limit') > quota.max_memory:
                raise serializers.ValidationError(
                    f"内存限制不能超过配额{quota.max_memory}MB"
                )
                
            if data.get('gpu_limit') > quota.max_gpu:
                raise serializers.ValidationError(
                    f"GPU限制不能超过配额{quota.max_gpu}个"
                )
                
            # 检查容器数量是否超过配额
            current_containers = ContainerInstance.objects.filter(
                user=user,
                status__in=['created', 'running', 'paused']
            ).count()
            
            if current_containers >= quota.max_containers:
                raise serializers.ValidationError(
                    f"已达到最大容器数量限制{quota.max_containers}个"
                )
                
        except ResourceQuota.DoesNotExist:
            raise serializers.ValidationError("用户没有资源配额配置")
            
        return data

    def create(self, validated_data):
        """创建容器实例
        
        设置容器初始状态并记录创建时间
        
        Args:
            validated_data: 验证后的数据

        Returns:
            新创建的容器实例
        """
        validated_data['status'] = 'created'
        validated_data['created_at'] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """更新容器实例
        
        更新容器状态时记录相应时间戳
        
        Args:
            instance: 现有实例
            validated_data: 验证后的数据

        Returns:
            更新后的容器实例
        """
        if 'status' in validated_data:
            new_status = validated_data['status']
            if new_status == 'running' and instance.status != 'running':
                validated_data['started_at'] = timezone.now()
                
        return super().update(instance, validated_data) 