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

# 设置日志记录器
logger = logging.getLogger(__name__)

class DockerImageViewSet(viewsets.ModelViewSet):
    """
    Docker镜像管理的ViewSet
    
    提供镜像的CRUD操作和拉取新镜像的功能
    """
    queryset = DockerImage.objects.all()
    serializer_class = DockerImageSerializer
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
    
    def list(self, request, *args, **kwargs):
        """获取镜像列表"""
        try:
            # 获取Docker daemon中的实际镜像列表
            docker_images = self.docker_client.list_images()
            # 更新数据库中的镜像记录
            self._sync_images(docker_images)
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Failed to list images: {str(e)}")
            return Response(
                {"error": "Failed to list images"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _sync_images(self, docker_images: list) -> None:
        """
        同步Docker daemon中的镜像到数据库
        
        Args:
            docker_images: Docker daemon中的镜像列表
        """
        # 获取所有镜像ID
        image_ids = [image['id'] for image in docker_images]
        
        # 删除不存在的镜像记录
        DockerImage.objects.exclude(image_id__in=image_ids).delete()
        
        # 更新或创建镜像记录
        for image in docker_images:
            DockerImage.objects.update_or_create(
                image_id=image['id'],
                defaults={
                    'tags': ','.join(image['tags']),
                    'size': image['size'],
                    'created_at': image['created']
                }
            )
    
    @action(detail=False, methods=['post'])
    def pull(self, request):
        """
        拉取新的Docker镜像
        
        请求体参数:
            image_name: 镜像名称
            tag: 镜像标签(可选,默认为latest)
        """
        image_name = request.data.get('image_name')
        tag = request.data.get('tag', 'latest')
        
        if not image_name:
            return Response(
                {"error": "Image name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 拉取镜像
            image = self.docker_client.pull_image(image_name, tag)
            
            # 创建或更新镜像记录
            docker_image, created = DockerImage.objects.update_or_create(
                image_id=image['id'],
                defaults={
                    'tags': ','.join(image['tags']),
                    'size': image['size'],
                    'created_at': image['created']
                }
            )
            
            serializer = self.get_serializer(docker_image)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Failed to pull image {image_name}:{tag}: {str(e)}")
            return Response(
                {"error": f"Failed to pull image: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
