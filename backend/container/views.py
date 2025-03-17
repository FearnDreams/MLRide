"""
This module contains the ViewSets for container management functionality.
It provides API endpoints for managing Docker images, containers and resource quotas.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import DockerImage, ContainerInstance, ResourceQuota
from .serializers import DockerImageSerializer, ContainerInstanceSerializer, ResourceQuotaSerializer
from .docker_ops import DockerClient
from typing import Dict, Any
import logging
from django.conf import settings
from rest_framework import serializers

# 设置日志记录器
logger = logging.getLogger(__name__)

class DockerImageViewSet(viewsets.ModelViewSet):
    """
    Docker镜像视图集
    """
    serializer_class = DockerImageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        获取查询集，只返回当前用户的镜像
        """
        return DockerImage.objects.filter(creator=self.request.user)
    
    def perform_create(self, serializer):
        """
        创建镜像时添加创建者信息
        """
        try:
            # 保存镜像记录
            image = serializer.save()
            
            # 更新状态为构建中
            image.status = 'building'
            image.save(update_fields=['status'])
            
            # 初始化Docker客户端
            docker_client = DockerClient()
            
            # 构建基础镜像名称
            base_image = f"python:{image.python_version}-slim"
            
            # 拉取基础镜像
            logger.info(f"Attempting to pull base image: {base_image}")
            try:
                image_info = docker_client.pull_image(base_image)
                logger.info(f"Successfully pulled/found image: {image_info}")
                
                # 如果是备用镜像，则记录到镜像的错误消息中，但继续处理
                if image_info.get('source') in ['alternative', 'minimal']:
                    image.error_message = f"注意：使用了备用镜像，因为无法拉取 {base_image}。"
                    image.save(update_fields=['error_message'])
                    
                    # 更新基础镜像名称为实际使用的镜像
                    if image_info.get('tags') and len(image_info['tags']) > 0:
                        base_image = image_info['tags'][0]
                        logger.info(f"Using alternative base image: {base_image}")
                
            except Exception as e:
                logger.error(f"Failed to pull image {base_image}: {str(e)}")
                image.status = 'failed'
                image.error_message = f"无法拉取基础镜像: {str(e)}"
                image.save(update_fields=['status', 'error_message'])
                raise Exception(f"无法拉取基础镜像 {base_image}: {str(e)}")
            
            # 构建自定义镜像名称
            custom_image_name = f"mlride-{image.creator.username}-{image.name}"
            custom_image_tag = f"py{image.python_version}"
            full_image_name = f"{custom_image_name}:{custom_image_tag}"
            
            # 保存镜像标签到数据库
            image.image_tag = full_image_name
            image.save(update_fields=['image_tag'])
            
            # 创建Dockerfile内容
            dockerfile_content = f"""
FROM {base_image}

# 设置工作目录
WORKDIR /app

# 安装基本依赖
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir numpy pandas scikit-learn matplotlib jupyter

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 创建用户目录
RUN mkdir -p /home/user && chmod 777 /home/user

# 设置启动命令
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
"""
            
            # 保存Dockerfile内容到数据库
            image.dockerfile = dockerfile_content
            image.save(update_fields=['dockerfile'])
            
            # 构建自定义镜像
            try:
                logger.info(f"Building custom image: {full_image_name}")
                docker_client.build_image_from_dockerfile(
                    dockerfile_content=dockerfile_content,
                    image_name=custom_image_name,
                    image_tag=custom_image_tag
                )
                logger.info(f"Successfully built custom image: {full_image_name}")
                
                # 更新状态为就绪
                image.status = 'ready'
                image.save(update_fields=['status'])
                
            except Exception as e:
                logger.error(f"Failed to build custom image: {str(e)}", exc_info=True)
                image.status = 'failed'
                image.error_message = f"构建镜像失败: {str(e)}"
                image.save(update_fields=['status', 'error_message'])
                raise Exception(f"构建镜像 {full_image_name} 失败: {str(e)}")
            
        except Exception as e:
            # 如果发生错误，更新状态为失败
            if 'image' in locals():
                image.status = 'failed'
                if not image.error_message:  # 只在尚未设置错误消息时设置
                    image.error_message = f"创建镜像失败: {str(e)}"
                image.save(update_fields=['status', 'error_message'])
            logger.error(f"Error creating image: {str(e)}", exc_info=True)
            raise e
    
    def perform_destroy(self, instance):
        """
        删除镜像时同时删除Docker镜像
        
        Args:
            instance: 要删除的DockerImage实例
        """
        try:
            # 初始化Docker客户端
            docker_client = DockerClient()
            
            # 获取所有Docker镜像
            docker_images = docker_client.list_images()
            logger.info(f"Current Docker images: {docker_images}")
            
            # 获取完整的镜像名称
            full_image_name = instance.image_tag
            
            if not full_image_name:
                # 如果没有保存镜像标签，则构建镜像名称
                custom_image_name = f"mlride-{instance.creator.username}-{instance.name}"
                custom_image_tag = f"py{instance.python_version}"
                full_image_name = f"{custom_image_name}:{custom_image_tag}"
                logger.warning(f"Image tag not found in database, using constructed name: {full_image_name}")
            
            # 尝试删除自定义Docker镜像
            try:
                # 查找匹配的镜像
                image_to_delete = None
                for image in docker_images:
                    if any(tag == full_image_name for tag in image.get('tags', [])):
                        image_to_delete = image
                        break
                
                if image_to_delete:
                    logger.info(f"Found image to delete: {image_to_delete}")
                    docker_client.remove_image(image_to_delete['id'], force=True)
                    logger.info(f"Successfully removed Docker image: {full_image_name}")
                else:
                    logger.warning(f"Could not find Docker image to delete: {full_image_name}")
            except Exception as e:
                logger.warning(f"Failed to remove Docker image {full_image_name}: {str(e)}")
                # 即使Docker镜像删除失败，也继续删除数据库记录
            
            # 调用父类的perform_destroy方法删除数据库记录
            super().perform_destroy(instance)
            logger.info(f"Successfully deleted image record: {instance.name}")
            
        except Exception as e:
            logger.error(f"Error during image deletion: {str(e)}", exc_info=True)
            raise
    
    def destroy(self, request, *args, **kwargs):
        """
        重写删除方法，添加错误处理
        """
        try:
            response = super().destroy(request, *args, **kwargs)
            return Response(
                {
                    'status': 'success',
                    'message': '镜像删除成功',
                    'data': None
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Image deletion failed: {str(e)}", exc_info=True)
            return Response(
                {
                    'status': 'error',
                    'message': '删除镜像失败，请重试',
                    'details': str(e) if settings.DEBUG else None
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def create(self, request, *args, **kwargs):
        """
        重写创建方法，添加错误处理
        """
        try:
            response = super().create(request, *args, **kwargs)
            return response
        except serializers.ValidationError as e:
            # 处理验证错误
            logger.warning(f"Image creation validation failed: {str(e)}")
            return Response(
                {
                    'type': 'validation_error',
                    'message': '输入数据验证失败',
                    'details': e.detail if hasattr(e, 'detail') else str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # 处理其他错误
            logger.error(f"Image creation failed: {str(e)}", exc_info=True)
            return Response(
                {
                    'type': 'server_error',
                    'message': '创建镜像失败，请重试',
                    'details': str(e) if settings.DEBUG else None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

class ContainerInstanceViewSet(viewsets.ModelViewSet):
    """
    容器实例管理的ViewSet
    
    提供容器的CRUD操作和状态管理功能
    """
    queryset = ContainerInstance.objects.all()
    serializer_class = ContainerInstanceSerializer
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._docker_client = None
    
    @property
    def docker_client(self):
        """延迟初始化Docker客户端"""
        if self._docker_client is None:
            self._docker_client = DockerClient()
        return self._docker_client
    
    def get_queryset(self):
        """根据用户权限过滤容器实例"""
        if self.request.user.is_staff:
            return ContainerInstance.objects.all()
        return ContainerInstance.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """创建容器实例时自动关联当前用户"""
        try:
            # 获取资源配额
            quota = ResourceQuota.objects.get(user=self.request.user)
            
            # 检查是否超过容器数量限制
            current_containers = ContainerInstance.objects.filter(
                user=self.request.user,
                status__in=['running', 'paused']
            ).count()
            
            if current_containers >= quota.max_containers:
                raise ValueError("Exceeded maximum container limit")
                
            # 创建Docker容器
            container_data = self._prepare_container_data(serializer.validated_data)
            container_info = self.docker_client.create_container(**container_data)
            
            # 保存容器实例
            serializer.save(
                user=self.request.user,
                container_id=container_info['id'],
                status=container_info['status']
            )
        except Exception as e:
            logger.error(f"Failed to create container: {str(e)}")
            raise
    
    def _prepare_container_data(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备创建容器所需的参数
        
        Args:
            validated_data: 序列化器验证后的数据
            
        Returns:
            Dict: 创建容器所需的参数字典
        """
        # 获取用户的资源配额
        quota = ResourceQuota.objects.get(user=self.request.user)
        
        # 获取镜像对象
        image = validated_data['image']
        # 组合完整的镜像名称
        image_name = f"{image.name}:{image.tag}"
        
        return {
            'image_name': image_name,
            'container_name': validated_data.get('name'),
            'command': validated_data.get('command'),
            'environment': validated_data.get('environment'),
            'ports': validated_data.get('ports'),
            'volumes': validated_data.get('volumes'),
            'cpu_count': min(validated_data.get('cpu_limit', quota.max_cpu), quota.max_cpu),
            'memory_limit': f"{min(validated_data.get('memory_limit', quota.max_memory), quota.max_memory)}m"
        }
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """启动容器"""
        instance = self.get_object()
        try:
            self.docker_client.start_container(instance.container_id)
            instance.status = 'running'
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Failed to start container {instance.container_id}: {str(e)}")
            return Response(
                {"error": f"Failed to start container: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止容器"""
        instance = self.get_object()
        try:
            self.docker_client.stop_container(instance.container_id)
            instance.status = 'stopped'
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Failed to stop container {instance.container_id}: {str(e)}")
            return Response(
                {"error": f"Failed to stop container: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def restart(self, request, pk=None):
        """重启容器"""
        instance = self.get_object()
        try:
            self.docker_client.stop_container(instance.container_id)
            self.docker_client.start_container(instance.container_id)
            instance.status = 'running'
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Failed to restart container {instance.container_id}: {str(e)}")
            return Response(
                {"error": f"Failed to restart container: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True)
    def stats(self, request, pk=None):
        """获取容器资源使用统计信息"""
        instance = self.get_object()
        try:
            stats = self.docker_client.get_container_stats(instance.container_id)
            return Response(stats)
        except Exception as e:
            logger.error(f"Failed to get container stats {instance.container_id}: {str(e)}")
            return Response(
                {"error": f"Failed to get container stats: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ResourceQuotaViewSet(viewsets.ModelViewSet):
    """
    资源配额管理的ViewSet
    
    提供用户资源配额的CRUD操作
    """
    queryset = ResourceQuota.objects.all()
    serializer_class = ResourceQuotaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """根据用户权限过滤资源配额"""
        if self.request.user.is_staff:
            return ResourceQuota.objects.all()
        return ResourceQuota.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """创建资源配额时自动关联当前用户"""
        serializer.save(user=self.request.user)
