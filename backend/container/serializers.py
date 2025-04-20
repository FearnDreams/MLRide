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

# PyTorch和CUDA版本兼容性表
# 格式: {pytorch_version: [compatible_cuda_versions]}
PYTORCH_CUDA_COMPATIBILITY = {
    "1.10.0": ["10.2", "11.1", "11.3"],
    "1.10.1": ["10.2", "11.1", "11.3"],
    "1.10.2": ["10.2", "11.1", "11.3"],
    "1.11.0": ["10.2", "11.3", "11.5"],
    "1.12.0": ["10.2", "11.3", "11.6"],
    "1.12.1": ["10.2", "11.3", "11.6"],
    "1.13.0": ["11.6", "11.7"],
    "1.13.1": ["11.6", "11.7"],
    "2.0.0": ["11.7", "11.8"],
    "2.0.1": ["11.7", "11.8"],
    "2.1.0": ["11.8", "12.1"],
    "2.1.1": ["11.8", "12.1"],
    "2.1.2": ["11.8", "12.1"],
    "2.2.0": ["11.8", "12.1"],
    "2.2.1": ["11.8", "12.1"],
}

# Python版本兼容性表
# 格式: {python_version: [compatible_pytorch_versions]}
PYTHON_PYTORCH_COMPATIBILITY = {
    "3.7": ["1.10.0", "1.10.1", "1.10.2", "1.11.0", "1.12.0", "1.12.1", "1.13.0", "1.13.1"],
    "3.8": ["1.10.0", "1.10.1", "1.10.2", "1.11.0", "1.12.0", "1.12.1", "1.13.0", "1.13.1", "2.0.0", "2.0.1", "2.1.0", "2.1.1", "2.1.2"],
    "3.9": ["1.10.0", "1.10.1", "1.10.2", "1.11.0", "1.12.0", "1.12.1", "1.13.0", "1.13.1", "2.0.0", "2.0.1", "2.1.0", "2.1.1", "2.1.2", "2.2.0", "2.2.1"],
    "3.10": ["1.11.0", "1.12.0", "1.12.1", "1.13.0", "1.13.1", "2.0.0", "2.0.1", "2.1.0", "2.1.1", "2.1.2", "2.2.0", "2.2.1"],
    "3.11": ["2.0.0", "2.0.1", "2.1.0", "2.1.1", "2.1.2", "2.2.0", "2.2.1"],
}

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
        is_pytorch: 是否使用PyTorch
        pytorch_version: PyTorch版本
        cuda_version: CUDA版本
        cuda_available: CUDA是否可用
    """
    
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    creator = serializers.PrimaryKeyRelatedField(read_only=True)  # 设置为只读字段，不需要客户端提供
    
    class Meta:
        model = DockerImage
        fields = [
            'id', 'name', 'description', 'python_version', 'creator', 
            'created', 'status', 'image_tag', 'creator_name', 'error_message',
            'use_slim', 'is_pytorch', 'pytorch_version', 'cuda_version', 'cuda_available'
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
            
        # 检查是否使用PyTorch
        if 'is_pytorch' in data and data['is_pytorch']:
            # 如果是PyTorch镜像，必须提供PyTorch版本
            if 'pytorch_version' not in data or not data['pytorch_version']:
                raise serializers.ValidationError({"pytorch_version": "PyTorch版本不能为空"})
                
            # 检查Python和PyTorch版本兼容性
            python_version = data['python_version']
            pytorch_version = data['pytorch_version']
            
            # 确保所选Python版本支持所选PyTorch版本
            compatible_pytorch_versions = PYTHON_PYTORCH_COMPATIBILITY.get(python_version, [])
            if pytorch_version not in compatible_pytorch_versions:
                raise serializers.ValidationError({
                    "pytorch_version": f"Python {python_version} 不兼容 PyTorch {pytorch_version}。"
                    f"支持的PyTorch版本: {', '.join(compatible_pytorch_versions)}"
                })
                
            # 检查是否使用CUDA
            cuda_available = data.get('cuda_available', False)
            if cuda_available:
                # 如果使用CUDA，必须提供CUDA版本
                if 'cuda_version' not in data or not data['cuda_version']:
                    raise serializers.ValidationError({"cuda_version": "CUDA版本不能为空"})
                    
                # 检查PyTorch和CUDA版本兼容性
                cuda_version = data['cuda_version']
                compatible_cuda_versions = PYTORCH_CUDA_COMPATIBILITY.get(pytorch_version, [])
                if cuda_version not in compatible_cuda_versions:
                    raise serializers.ValidationError({
                        "cuda_version": f"PyTorch {pytorch_version} 不兼容 CUDA {cuda_version}。"
                        f"支持的CUDA版本: {', '.join(compatible_cuda_versions)}"
                    })
                    
                # 如果使用CUDA，设置最小GPU需求
                data['min_gpu'] = 1
            
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
        valid_versions = list(PYTHON_PYTORCH_COMPATIBILITY.keys())
        if value not in valid_versions:
            raise serializers.ValidationError(f"Python版本必须是以下之一: {', '.join(valid_versions)}")
        return value
        
    def validate_pytorch_version(self, value):
        """
        验证PyTorch版本
        """
        if not value:
            return value
            
        valid_versions = []
        for versions in PYTORCH_CUDA_COMPATIBILITY:
            valid_versions.append(versions)
            
        if value not in valid_versions:
            raise serializers.ValidationError(f"PyTorch版本必须是以下之一: {', '.join(valid_versions)}")
            
        return value
        
    def validate_cuda_version(self, value):
        """
        验证CUDA版本
        """
        if not value:
            return value
            
        valid_versions = set()
        for cuda_versions in PYTORCH_CUDA_COMPATIBILITY.values():
            valid_versions.update(cuda_versions)
            
        if value not in valid_versions:
            raise serializers.ValidationError(f"CUDA版本必须是以下之一: {', '.join(sorted(valid_versions))}")
            
        return value

    def create(self, validated_data):
        """
        创建Docker镜像
        
        Args:
            validated_data: 验证后的数据
            
        Returns:
            DockerImage: 创建的Docker镜像实例
        """
        logger.info(f"Creating DockerImage with data: {validated_data}")
        
        # 获取请求的用户并设置creator
        request = self.context.get('request')
        if request:
            logger.info(f"Setting creator from request user: {request.user.id}")
            validated_data['creator'] = request.user
        else:
            logger.warning("No request in context, creator might be missing")
            
        # 处理Python版本
        python_version = validated_data.get('python_version')
        if not python_version:
            raise serializers.ValidationError({"python_version": "Python版本不能为空"})
            
        # 设置镜像状态为pending
        validated_data['status'] = 'pending'
        
        # 检查是否启用PyTorch
        pytorch_version = validated_data.get('pytorch_version')
        cuda_version = validated_data.get('cuda_version')
        
        # 确保设置is_pytorch标记
        if pytorch_version:
            validated_data['is_pytorch'] = True
        
        # 确保设置cuda_available标记    
        if cuda_version:
            validated_data['cuda_available'] = True
        
        # 设置use_slim为False，始终使用常规版本以提高镜像稳定性
        validated_data['use_slim'] = False
        logger.info("Setting use_slim=False to always use regular Python versions")
            
        # 创建Docker镜像
        image = DockerImage.objects.create(**validated_data)
        logger.info(f"Created Docker image: {image.id}")
        
        # 确保镜像记录有正确的is_pytorch和cuda_available标记
        if 'is_pytorch' in validated_data and validated_data['is_pytorch']:
            image.is_pytorch = True
        if 'cuda_available' in validated_data and validated_data['cuda_available']:
            image.cuda_available = True
        
        # 保存更新
        if image.is_pytorch or image.cuda_available:
            image.save(update_fields=['is_pytorch', 'cuda_available'])
        
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