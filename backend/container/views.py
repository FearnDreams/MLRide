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
import threading

# 设置日志记录器
logger = logging.getLogger(__name__)

# 添加异步构建镜像的函数
def build_image_async(image_id):
    """
    异步构建Docker镜像
    
    Args:
        image_id (int): 数据库中的镜像ID
    """
    try:
        # 获取镜像记录
        image = DockerImage.objects.get(id=image_id)
        if image.status != 'building':
            logger.warning(f"镜像状态不为building，跳过构建: {image.status}")
            return
            
        logger.info(f"异步构建镜像开始: ID={image_id}, 名称={image.name}")
        
        # 初始化Docker客户端
        docker_client = DockerClient()
        
        # 直接使用常规Python版本（不带slim后缀）
        version = image.python_version
        base_image = f"python:{version}"
        logger.info(f"使用常规Python版本: {base_image}")
        
        image_info = None
        actual_python_version = None
        
        # 首先检查本地是否存在匹配的Python镜像
        try:
            all_images = docker_client.client.images.list()
            # 检查是否有精确匹配的本地镜像
            local_image = None
            for img in all_images:
                if f"python:{version}" in img.tags:
                    local_image = img
                    logger.info(f"找到本地精确匹配的Python镜像: {img.tags}")
                    break
                # 也检查带registry前缀的镜像
                for tag in img.tags:
                    if tag.endswith(f"/python:{version}") or tag == f"python:{version}":
                        local_image = img
                        logger.info(f"找到本地匹配的Python镜像: {tag}")
                        break
                if local_image:
                    break
            
            if local_image:
                logger.info(f"使用本地Python镜像: {local_image.tags}")
                image_info = {
                    'id': local_image.id,
                    'tags': local_image.tags,
                    'size': local_image.attrs['Size'],
                    'created': local_image.attrs['Created'],
                    'source': 'local'
                }
                # 尝试获取本地镜像的实际Python版本
                actual_python_version = docker_client._verify_python_version_in_image(local_image.id)
                if actual_python_version:
                    logger.info(f"本地镜像的Python版本: {actual_python_version}")
                    
        except Exception as e:
            logger.warning(f"检查本地镜像时出错: {str(e)}")
        
        # 如果没有找到本地镜像，尝试从远程拉取
        if not image_info:
            try:
                # 解析基础镜像的名称和标签
                image_parts = base_image.split(':')
                image_name = image_parts[0]  # python
                image_tag = image_parts[1] if len(image_parts) > 1 else 'latest'
                
                # 拉取用户指定的基础镜像版本
                logger.info(f"拉取镜像: name={image_name}, tag={image_tag}")
                image_info = docker_client.pull_image(image_name=image_name, tag=image_tag)
                logger.info(f"成功拉取/找到镜像: {image_info}")
                
            except Exception as e:
                logger.error(f"拉取镜像 {base_image} 失败: {str(e)}", exc_info=True)
                
                # 如果指定版本失败，尝试latest作为后备方案
                try:
                    latest_image = "python:latest"
                    logger.info(f"指定版本失败，尝试latest版本: {latest_image}")
                    
                    image_parts = latest_image.split(':')
                    image_name = image_parts[0]
                    image_tag = image_parts[1]
                    
                    image_info = docker_client.pull_image(image_name=image_name, tag=image_tag)
                    logger.info(f"成功拉取/找到latest版本: {image_info}")
                    
                    # 更新使用的基础镜像
                    base_image = latest_image
                    image.error_message = f"注意: 无法获取Python {version}版本，已使用latest版本"
                    image.save(update_fields=['error_message'])
                except Exception as e2:
                    # 最后一个备选方案：检查本地系统镜像
                    try:
                        logger.info("尝试使用本地系统Python或从本地创建基础镜像")
                        
                        # 创建一个最小的Dockerfile直接使用现有的Python
                        minimal_dockerfile = f"""FROM ubuntu:latest
RUN apt-get update && apt-get install -y python3 python3-pip
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN python -m pip install --upgrade pip
ENV PYTHONUNBUFFERED=1
"""
                        # 构建最小化Python镜像
                        minimal_image_name = f"python-minimal-{version}"
                        minimal_image_tag = "latest"
                        
                        # 使用简单的Dockerfile构建基础镜像
                        minimal_image = docker_client.build_image_from_dockerfile(
                            dockerfile_content=minimal_dockerfile,
                            image_name=minimal_image_name,
                            image_tag=minimal_image_tag
                        )
                        
                        logger.info(f"成功创建最小化Python镜像: {minimal_image}")
                        
                        # 使用这个最小镜像作为基础
                        base_image = f"{minimal_image_name}:{minimal_image_tag}"
                        image.error_message = f"注意: 由于无法获取指定版本的Python镜像，已创建最小化系统基础镜像"
                        image.save(update_fields=['error_message'])
                        
                        # 使用这个新构建的镜像信息
                        image_info = minimal_image
                        
                    except Exception as e3:
                        # 所有尝试都失败
                        logger.error(f"所有镜像获取方法都失败: {str(e3)}")
                        image.status = 'failed'
                        image.error_message = f"无法获取或创建Python镜像: {str(e)}"
                        image.save(update_fields=['status', 'error_message'])
                        return
        
        # 确保我们有有效的基础镜像和镜像信息
        if not base_image or not image_info:
            image.status = 'failed'
            image.error_message = "无法确定要使用的基础镜像"
            image.save(update_fields=['status', 'error_message'])
            return
            
        # 构建自定义镜像名称
        custom_image_name = f"mlride-{image.creator.username}-{image.name}"
        custom_image_tag = f"py{image.python_version}"
        
        # 如果有PyTorch和CUDA版本，则添加到标签中
        if image.pytorch_version and image.cuda_version:
            custom_image_tag += f"-pt{image.pytorch_version}-cuda{image.cuda_version}"
            
        full_image_name = f"{custom_image_name}:{custom_image_tag}"
        
        # 保存镜像标签到数据库
        image.image_tag = full_image_name
        image.save(update_fields=['image_tag'])
        
        # 创建Dockerfile内容
        dockerfile_content = f"""
FROM {base_image}

# 设置工作目录
WORKDIR /app

"""
        
        # 添加基本依赖和PyTorch+CUDA安装
        if image.pytorch_version and image.cuda_version:
            # 根据PyTorch和CUDA版本确定安装命令
            pytorch_install_cmd = DockerImageViewSet._get_pytorch_install_cmd(image.pytorch_version, image.cuda_version)
            
            dockerfile_content += f"""
# 安装基本依赖和PyTorch+CUDA
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir numpy pandas scikit-learn matplotlib jupyter && \\
    {pytorch_install_cmd}

# 安装CUDA相关工具
RUN apt-get update && \\
    apt-get install -y --no-install-recommends \\
    build-essential \\
    curl \\
    git \\
    wget \\
    ca-certificates && \\
    apt-get clean && \\
    rm -rf /var/lib/apt/lists/*
"""
        else:
            dockerfile_content += """
# 安装基本依赖
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir numpy pandas scikit-learn matplotlib jupyter
"""

        dockerfile_content += """
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
            build_result = docker_client.build_image_from_dockerfile(
                dockerfile_content=dockerfile_content,
                image_name=custom_image_name,
                image_tag=custom_image_tag,
                python_version=version  # 传递预期的Python版本
            )
            logger.info(f"Successfully built custom image: {full_image_name}")
            
            # 检查构建的镜像中是否返回了实际版本信息
            if 'actual_python_version' in build_result:
                actual_python_version = build_result['actual_python_version']
                logger.info(f"构建的镜像实际Python版本: {actual_python_version}")
                
                # 将实际版本信息保存到数据库
                image.actual_version = actual_python_version
                image.save(update_fields=['actual_version'])
                
                # 如果实际版本与预期不符，记录警告
                if not actual_python_version.startswith(version):
                    image.error_message = f"警告: 镜像使用的实际Python版本({actual_python_version})与请求的版本({version})不完全匹配"
                    image.save(update_fields=['error_message'])
            
            # 更新状态为就绪
            image.status = 'ready'
            image.save(update_fields=['status'])
            
        except Exception as e:
            logger.error(f"Failed to build custom image: {str(e)}", exc_info=True)
            image.status = 'failed'
            image.error_message = f"构建镜像失败: {str(e)}"
            image.save(update_fields=['status', 'error_message'])
    
    except Exception as e:
        # 如果发生错误，更新状态为失败
        try:
            image = DockerImage.objects.get(id=image_id)
            image.status = 'failed'
            if not image.error_message:  # 只在尚未设置错误消息时设置
                image.error_message = f"创建镜像失败: {str(e)}"
            image.save(update_fields=['status', 'error_message'])
        except Exception as inner_e:
            logger.error(f"更新镜像状态失败: {str(inner_e)}")
        
        logger.error(f"异步构建镜像失败: {str(e)}", exc_info=True)

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
        创建镜像时添加创建者信息，并异步执行镜像构建
        """
        try:
            # 保存镜像记录，状态设置为构建中
            image = serializer.save(status='building')
            logger.info(f"镜像记录已创建，ID={image.id}，名称={image.name}")
            
            # 在单独的线程中执行镜像构建
            thread = threading.Thread(target=build_image_async, args=(image.id,))
            thread.daemon = True  # 设置为守护线程，这样主程序退出时线程也会退出
            thread.start()
            
            logger.info(f"镜像构建已在后台启动: ID={image.id}")
        except Exception as e:
            logger.error(f"创建镜像记录失败: {str(e)}", exc_info=True)
            raise e
    
    @staticmethod
    def _get_pytorch_install_cmd(pytorch_version, cuda_version):
        """
        根据PyTorch和CUDA版本返回适当的安装命令
        
        Args:
            pytorch_version (str): PyTorch版本，例如 '1.12'
            cuda_version (str): CUDA版本，例如 '11.3'
            
        Returns:
            str: PyTorch安装命令
        """
        # 将CUDA版本转换为PyTorch版本格式（如11.3 -> cu113）
        cuda_short = "cu" + cuda_version.replace('.', '')
        
        # 特殊情况处理 - CUDA 12.x
        if cuda_version.startswith('12.'):
            if pytorch_version in ['1.10', '1.11', '1.12', '1.13', '2.0']:
                # 这些版本不支持CUDA 12.x，使用11.8作为替代
                cuda_short = 'cu118'
                logger.warning(f"PyTorch {pytorch_version}不支持CUDA {cuda_version}，将使用CUDA 11.8替代")
        
        # 针对早期CUDA版本的特殊处理
        if cuda_version in ['11.0', '11.1', '11.2']:
            if pytorch_version not in ['1.10', '1.11']:
                logger.warning(f"PyTorch {pytorch_version}可能与CUDA {cuda_version}不完全兼容，建议检查")
        
        # 使用清华大学镜像源替代官方源，避免网络问题
        tsinghua_mirror = "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch/linux-64"
                
        # 针对最新版本的特殊处理
        if pytorch_version in ['2.6', '2.7'] and cuda_version == '12.6':
            return f'pip install --no-cache-dir torch=={pytorch_version}.* --index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/torch/'
        
        # 针对1.10版本的特殊处理
        if pytorch_version == '1.10' and cuda_version in ['11.0', '11.1']:
            # 使用清华镜像源
            return f'pip install --no-cache-dir torch==1.10.* torchvision==0.11.* torchaudio==0.10.* -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/'
            
        # 通用情况
        return f'pip install --no-cache-dir torch=={pytorch_version}.* torchvision torchaudio -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/'
    
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
        # 使用镜像标签作为完整镜像名称
        image_name = image.image_tag
        
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
