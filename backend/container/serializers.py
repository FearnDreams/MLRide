"""
This module contains the serializers for the container management functionality.
包含容器管理功能的序列化器。
"""

from rest_framework import serializers
from django.utils import timezone
import logging
from .models import DockerImage, ContainerInstance, ResourceQuota

# 设置日志记录器
logger = logging.getLogger(__name__)

class DockerImageSerializer(serializers.ModelSerializer):
    """Docker镜像序列化器
    
    用于序列化和反序列化Docker镜像信息
    
    Fields:
        id: 镜像ID
        name: 镜像名称
        description: 镜像描述
        python_version: Python版本
        creator: 创建者ID
        created: 创建时间
        status: 镜像状态
        image_tag: Docker镜像标签
        use_slim: 是否使用slim版本
        pytorch_version: PyTorch版本
        cuda_version: CUDA版本
    """
    
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    creator = serializers.PrimaryKeyRelatedField(read_only=True)  # 设置为只读字段，不需要客户端提供
    
    class Meta:
        model = DockerImage
        fields = [
            'id', 'name', 'description', 'python_version', 'creator', 
            'created', 'status', 'image_tag', 'creator_name', 'error_message',
            'use_slim', 'pytorch_version', 'cuda_version'
        ]
        read_only_fields = ['id', 'created', 'status', 'image_tag', 'creator_name', 'error_message', 'creator']

    def validate(self, data):
        """
        验证整个数据
        """
        # 记录传入的数据用于调试
        logger.info(f"DockerImageSerializer validating data: {data}")
        
        # 记录请求上下文
        request = self.context.get('request')
        if request:
            logger.info(f"Request user: {request.user}")
            logger.info(f"Request data: {request.data}")
        else:
            logger.warning("No request in context")
            
        # 检查必需字段
        if 'python_version' not in data:
            logger.error("python_version field is missing from the data")
            # 检查是否以替代名称提供
            if self.initial_data.get('pythonVersion'):
                logger.info(f"Found pythonVersion: {self.initial_data.get('pythonVersion')}")
                data['python_version'] = self.initial_data.get('pythonVersion')
                logger.info("Mapped pythonVersion to python_version")
            else:
                logger.error("No pythonVersion found in initial data either")
                raise serializers.ValidationError({"python_version": "Python版本不能为空"})
                
        if 'name' not in data:
            logger.error("name field is missing from the data")
            raise serializers.ValidationError({"name": "镜像名称不能为空"})
            
        # 检查创建者
        if 'creator' not in data and request:
            logger.info(f"Setting creator from request user: {request.user.id}")
            data['creator'] = request.user
            
        # 验证PyTorch和CUDA版本的兼容性
        pytorch_version = data.get('pytorch_version')
        cuda_version = data.get('cuda_version')
        python_version = data.get('python_version')
        
        if pytorch_version and cuda_version:
            logger.info(f"Validating compatibility: Python {python_version}, PyTorch {pytorch_version}, CUDA {cuda_version}")
            
            # 检查Python、PyTorch和CUDA版本的兼容性
            is_compatible = self._check_compatibility(python_version, pytorch_version, cuda_version)
            if not is_compatible:
                raise serializers.ValidationError(
                    f"Python {python_version}, PyTorch {pytorch_version} 和 CUDA {cuda_version} 版本不兼容。"
                    "请参考PyTorch官方的兼容性表格选择适合的版本组合。"
                )
                
        return data

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

    def validate_python_version(self, value):
        """
        验证Python版本
        """
        logger.info(f"Validating python_version: {value}")
        valid_versions = ['3.8', '3.9', '3.10', '3.11']
        if value not in valid_versions:
            raise serializers.ValidationError(f"Python版本必须是以下之一: {', '.join(valid_versions)}")
        return value

    def validate_pytorch_version(self, value):
        """
        验证PyTorch版本
        """
        if not value:  # 如果为空则跳过验证
            return value
            
        logger.info(f"Validating pytorch_version: {value}")
        valid_versions = ['1.10', '1.11', '1.12', '1.13', '2.0', '2.1', '2.2', '2.3', '2.4', '2.5', '2.6', '2.7']
        if value not in valid_versions:
            raise serializers.ValidationError(f"PyTorch版本必须是以下之一: {', '.join(valid_versions)}")
        return value
        
    def validate_cuda_version(self, value):
        """
        验证CUDA版本
        """
        if not value:  # 如果为空则跳过验证
            return value
            
        logger.info(f"Validating cuda_version: {value}")
        valid_versions = ['11.0', '11.1', '11.2', '11.3', '11.6', '11.7', '11.8', '12.1', '12.4', '12.6']
        if value not in valid_versions:
            raise serializers.ValidationError(f"CUDA版本必须是以下之一: {', '.join(valid_versions)}")
        return value

    def create(self, validated_data):
        """
        创建Docker镜像
        
        Args:
            validated_data: 验证后的数据
            
        Returns:
            DockerImage: 创建的Docker镜像对象
        """
        logger.info(f"Creating Docker image with data: {validated_data}")
        request = self.context.get('request')
        if request:
            logger.info(f"Setting creator from request user: {request.user.id}")
            validated_data['creator'] = request.user
        else:
            logger.warning("No request in context, creator might be missing")
        
        # 设置use_slim为False，始终使用常规版本
        validated_data['use_slim'] = False
        logger.info("Setting use_slim=False to always use regular Python versions")
            
        image = DockerImage.objects.create(
            **validated_data
        )
        logger.info(f"Created Docker image: {image.id}")
        return image

    def _check_compatibility(self, python_version, pytorch_version, cuda_version):
        """
        检查Python、PyTorch和CUDA版本的兼容性
        
        根据PyTorch官方的兼容性表格建立兼容性规则
        """
        # 兼容性映射表
        compatibility_map = {
            # PyTorch 2.7
            '2.7': {
                'python': ['3.9', '3.10', '3.11'],
                'cuda': ['11.8', '12.6']
            },
            # PyTorch 2.6
            '2.6': {
                'python': ['3.9', '3.10', '3.11'],
                'cuda': ['11.8', '12.4']
            },
            # PyTorch 2.5
            '2.5': {
                'python': ['3.9', '3.10', '3.11'],
                'cuda': ['11.8', '12.1', '12.4']
            },
            # PyTorch 2.4
            '2.4': {
                'python': ['3.8', '3.9', '3.10', '3.11'],
                'cuda': ['11.8', '12.1']
            },
            # PyTorch 2.3
            '2.3': {
                'python': ['3.8', '3.9', '3.10', '3.11'],
                'cuda': ['11.8', '12.1']
            },
            # PyTorch 2.2
            '2.2': {
                'python': ['3.8', '3.9', '3.10', '3.11'],
                'cuda': ['11.8', '12.1']
            },
            # PyTorch 2.1
            '2.1': {
                'python': ['3.8', '3.9', '3.10', '3.11'],
                'cuda': ['11.8', '12.1']
            },
            # PyTorch 2.0
            '2.0': {
                'python': ['3.8', '3.9', '3.10', '3.11'],
                'cuda': ['11.7', '11.8']
            },
            # PyTorch 1.13
            '1.13': {
                'python': ['3.7', '3.8', '3.9', '3.10'],
                'cuda': ['11.6', '11.7']
            },
            # PyTorch 1.12
            '1.12': {
                'python': ['3.7', '3.8', '3.9', '3.10'],
                'cuda': ['11.3', '11.6']
            },
            # PyTorch 1.11
            '1.11': {
                'python': ['3.7', '3.8', '3.9', '3.10'],
                'cuda': ['11.1', '11.2', '11.3']
            },
            # PyTorch 1.10
            '1.10': {
                'python': ['3.7', '3.8', '3.9', '3.10'],
                'cuda': ['11.0', '11.1', '11.3']
            },
        }
        
        # 检查PyTorch版本是否存在于映射表中
        if pytorch_version not in compatibility_map:
            logger.warning(f"PyTorch version {pytorch_version} not found in compatibility map")
            return False
            
        # 检查Python版本是否兼容
        if python_version not in compatibility_map[pytorch_version]['python']:
            logger.warning(
                f"Python {python_version} is not compatible with PyTorch {pytorch_version}. "
                f"Compatible Python versions: {compatibility_map[pytorch_version]['python']}"
            )
            return False
            
        # 检查CUDA版本是否兼容
        if cuda_version not in compatibility_map[pytorch_version]['cuda']:
            logger.warning(
                f"CUDA {cuda_version} is not compatible with PyTorch {pytorch_version}. "
                f"Compatible CUDA versions: {compatibility_map[pytorch_version]['cuda']}"
            )
            return False
            
        return True


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