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
            
            # 检查是否是PyTorch镜像
            if image.is_pytorch:
                # 根据是否使用CUDA构建不同的基础镜像名称
                if image.cuda_available and image.cuda_version:
                    # 使用PyTorch+CUDA镜像
                    base_image = f"pytorch/pytorch:{image.pytorch_version}-cuda{image.cuda_version}-cudnn8-runtime"
                    logger.info(f"使用PyTorch+CUDA镜像: {base_image}")
                else:
                    # 使用PyTorch CPU镜像
                    base_image = f"pytorch/pytorch:{image.pytorch_version}-cpu"
                    logger.info(f"使用PyTorch CPU镜像: {base_image}")
            else:
                # 直接使用常规Python版本（不带slim后缀）
                version = image.python_version
                base_image = f"python:{version}"
                logger.info(f"使用常规Python版本: {base_image}")
            
            image_info = None
            actual_python_version = None
            
            # 首先检查本地是否存在匹配的基础镜像
            try:
                all_images = docker_client.client.images.list()
                # 检查是否有精确匹配的本地镜像
                local_image = None
                for img in all_images:
                    # 检查镜像标签是否匹配
                    for tag in img.tags:
                        if base_image in tag:
                            local_image = img
                            logger.info(f"找到本地匹配的镜像: {tag}")
                            break
                    if local_image:
                        break
                
                if local_image:
                    logger.info(f"使用本地镜像: {local_image.tags}")
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
                    # 从镜像名称中提取镜像名和标签
                    if ":" in base_image:
                        image_parts = base_image.split(':')
                        image_name = image_parts[0]  # 例如 pytorch/pytorch 或 python
                        image_tag = image_parts[1]   # 例如 1.13.0-cuda11.7-cudnn8-runtime 或 3.9
                    else:
                        image_name = base_image
                        image_tag = 'latest'
                    
                    # 拉取用户指定的基础镜像版本
                    logger.info(f"拉取镜像: name={image_name}, tag={image_tag}")
                    
                    # 设置镜像源为国内源加速下载
                    build_args = None
                    if image.is_pytorch and "pytorch/" in image_name:
                        # PyTorch镜像构建参数，使用清华源
                        build_args = {
                            "PIP_INDEX_URL": "https://pypi.tuna.tsinghua.edu.cn/simple",
                            "PIP_TRUSTED_HOST": "pypi.tuna.tsinghua.edu.cn"
                        }
                        logger.info("使用清华PyPI源加速PyTorch镜像构建")
                    
                    # 拉取镜像
                    image_info = docker_client.pull_image(image_name=image_name, tag=image_tag)
                    logger.info(f"成功拉取/找到镜像: {image_info}")
                    
                except Exception as e:
                    logger.error(f"拉取镜像 {base_image} 失败: {str(e)}", exc_info=True)
                    
                    # 如果是PyTorch镜像，尝试多种替代方法
                    if image.is_pytorch:
                        # 对于PyTorch+CUDA镜像，尝试使用不同的构建方法
                        if image.cuda_available and image.cuda_version:
                            # 首先尝试使用纯PyTorch CPU版本作为替代 
                            try:
                                logger.info("CUDA版本获取失败，尝试降级到PyTorch CPU版本")
                                cpu_image = f"pytorch/pytorch:{image.pytorch_version}-cpu"
                                cpu_parts = cpu_image.split(':')
                                cpu_image_name = cpu_parts[0]
                                cpu_image_tag = cpu_parts[1]
                                
                                cpu_image_info = docker_client.pull_image(image_name=cpu_image_name, tag=cpu_image_tag)
                                if cpu_image_info:
                                    logger.info(f"成功获取PyTorch CPU版本: {cpu_image_info}")
                                    base_image = cpu_image
                                    image.cuda_available = False  # 禁用CUDA
                                    image.error_message = f"注意: 无法获取PyTorch+CUDA镜像，已降级为CPU版本"
                                    image.save(update_fields=['cuda_available', 'error_message'])
                                    image_info = cpu_image_info
                                    # 已经找到可用镜像，可以继续
                                    break_error_handling = True
                            except Exception as cpu_error:
                                logger.error(f"PyTorch CPU版本也获取失败: {str(cpu_error)}")
                                break_error_handling = False
                                
                        # 如果降级到CPU版本也失败，尝试构建自定义Dockerfile
                        if not break_error_handling:
                            try:
                                logger.info("尝试使用Python基础镜像构建自定义PyTorch环境")
                                # 使用对应版本的Python基础镜像
                                python_base_image = f"python:{image.python_version}"
                                python_image_name = "python"
                                python_image_tag = image.python_version
                                
                                # 拉取Python基础镜像
                                logger.info(f"尝试拉取Python基础镜像: {python_base_image}")
                                python_image_info = docker_client.pull_image(image_name=python_image_name, tag=python_image_tag)
                                
                                if python_image_info:
                                    logger.info(f"成功拉取Python基础镜像: {python_image_info}")
                                    
                                    # 创建自定义Dockerfile直接使用Python镜像安装PyTorch
                                    if image.cuda_available and image.cuda_version:
                                        image.error_message = "注意: 无法获取PyTorch官方镜像，将使用Python基础镜像并通过pip安装PyTorch+CUDA"
                                    else:
                                        image.error_message = "注意: 无法获取PyTorch官方镜像，将使用Python基础镜像并通过pip安装PyTorch CPU版本"
                                    
                                    # 更新基础镜像和错误信息
                                    base_image = python_base_image
                                    image.save(update_fields=['error_message'])
                                    
                                    # 更新image_info
                                    image_info = python_image_info
                                    
                                    # 继续处理
                                    logger.info("将在Dockerfile中添加PyTorch安装命令")
                                    # 成功获取到Python基础镜像，跳过错误处理，继续后续流程
                                    break_error_handling = True
                            except Exception as py_error:
                                logger.error(f"Python基础镜像也拉取失败: {str(py_error)}")
                                # 仍然提供原始错误信息
                                break_error_handling = False
                        
                        # 如果成功获取到替代镜像，跳过错误处理
                        if break_error_handling:
                            # 跳过后续的错误处理代码
                            pass
                        else:
                            # 根据错误类型提供更详细的错误信息和处理建议
                            error_message = str(e)
                            if "context deadline exceeded" in error_message or "timeout" in error_message.lower():
                                error_msg = f"拉取PyTorch镜像超时: {error_message}\n\n建议解决方案:\n"
                                error_msg += "1. 检查网络连接\n"
                                error_msg += "2. 尝试使用CPU版本的PyTorch镜像（不含CUDA）\n"
                                error_msg += "3. 尝试使用其他版本的PyTorch和CUDA组合\n"
                                error_msg += "4. 确保Docker配置允许访问外部网络\n"
                            elif "not found" in error_message.lower():
                                error_msg = f"未找到指定的PyTorch镜像: {error_message}\n\n建议解决方案:\n"
                                error_msg += "1. 检查PyTorch版本和CUDA版本是否匹配\n"
                                error_msg += f"2. 检查是否存在PyTorch {image.pytorch_version}与CUDA {image.cuda_version}的组合\n"
                                error_msg += "3. 尝试访问PyTorch官方文档查询兼容版本\n"
                                error_msg += "4. 尝试使用CPU版本\n"
                            else:
                                error_msg = f"拉取PyTorch镜像失败: {error_message}\n\n建议解决方案:\n"
                                error_msg += "1. 检查Docker服务是否正常运行\n"
                                error_msg += "2. 检查网络连接，尝试手动拉取测试\n"
                                error_msg += "3. 考虑使用其他版本的PyTorch或CUDA组合\n"
                                error_msg += "4. 尝试使用CPU版本的PyTorch\n"
                            
                            image.status = 'failed'
                            image.error_message = error_msg
                            image.save(update_fields=['status', 'error_message'])
                            raise Exception(error_msg)
                    
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
                        image.error_message = f"注意: 无法获取Python {image.python_version}版本，已使用latest版本"
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
                            minimal_image_name = f"python-minimal-{image.python_version}"
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
                            raise Exception(f"无法获取或创建Python镜像，请检查Docker服务状态")
            
            # 确保我们有有效的基础镜像和镜像信息
            if not base_image or not image_info:
                image.status = 'failed'
                image.error_message = "无法确定要使用的基础镜像"
                image.save(update_fields=['status', 'error_message'])
                raise Exception("无法确定要使用的基础镜像")
                
            # 构建自定义镜像名称
            custom_image_name = f"mlride-{image.creator.username}-{image.name}"
            
            # 构建镜像标签，包含Python版本和其他特性
            tag_parts = [f"py{image.python_version}"]
            
            # 检查镜像类型
            logger.info(f"镜像类型: {image.image_type}, 是否PyTorch: {image.is_pytorch}, CUDA可用: {image.cuda_available}")
            
            # 添加PyTorch和CUDA信息
            if image.is_pytorch:
                logger.info(f"PyTorch版本: {image.pytorch_version}")
                tag_parts.append(f"pt{image.pytorch_version}")
                
                if image.cuda_available and image.cuda_version:
                    logger.info(f"CUDA版本: {image.cuda_version}")
                    tag_parts.append(f"cuda{image.cuda_version}")
                else:
                    logger.info("未启用CUDA")
            else:
                logger.info("未启用PyTorch")
            
            custom_image_tag = "-".join(tag_parts)
            full_image_name = f"{custom_image_name}:{custom_image_tag}"
            logger.info(f"镜像全名: {full_image_name}")
            
            # 保存镜像标签到数据库
            image.image_tag = full_image_name
            image.save(update_fields=['image_tag'])
            
            # 创建Dockerfile内容
            
            # 选择基础镜像，不使用官方PyTorch镜像
            if image.is_pytorch:
                # 使用标准Python镜像，为了稳定性不使用slim版本
                base_image = f"python:{image.python_version}"
                logger.info(f"Using Python base image: {base_image}")
            
            dockerfile_content = f"""
FROM {base_image}

# 设置工作目录
WORKDIR /app

# 设置pip镜像源以加速依赖安装
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \\
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 安装基本依赖
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir numpy pandas scikit-learn matplotlib jupyter
"""

            # 如果是PyTorch镜像，使用pip安装PyTorch
            if image.is_pytorch:
                # 根据是否需要CUDA选择安装命令
                if image.cuda_available and image.cuda_version:
                    # 将CUDA版本格式化为不带点的形式 (例如 11.6 -> 116)
                    cuda_version_no_dots = image.cuda_version.replace('.', '')
                    
                    # 增加CUDA相关的设置和安装命令
                    pytorch_packages = f"""
# 安装CUDA和PyTorch相关依赖
RUN apt-get update && apt-get install -y --no-install-recommends \\
    wget \\
    gnupg2 \\
    ca-certificates && \\
    rm -rf /var/lib/apt/lists/*

# 设置CUDA环境变量
ENV CUDA_VERSION={image.cuda_version}
ENV PATH=/usr/local/cuda/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 安装PyTorch CUDA版本
RUN pip install --no-cache-dir torch=={image.pytorch_version} torchvision torchaudio --index-url https://download.pytorch.org/whl/cu{cuda_version_no_dots}

# 验证PyTorch可以访问GPU
RUN python -c "import torch; print('GPU可用情况:', torch.cuda.is_available()); print('PyTorch版本:', torch.__version__); print('CUDA版本:', torch.version.cuda if torch.cuda.is_available() else 'N/A')" || echo "无法验证GPU"
"""
                else:
                    # CPU版本的PyTorch安装更简单
                    pytorch_packages = f"""
# 安装PyTorch CPU版本
RUN pip install --no-cache-dir torch=={image.pytorch_version} torchvision torchaudio

# 验证PyTorch版本
RUN python -c "import torch; print('PyTorch版本:', torch.__version__)" || echo "无法验证PyTorch版本"
"""
                
                dockerfile_content += pytorch_packages

            # 添加通用的环境设置和CMD
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
                
                # 设置构建参数，使用国内镜像源
                build_args = {
                    "PIP_INDEX_URL": "https://pypi.tuna.tsinghua.edu.cn/simple",
                    "PIP_TRUSTED_HOST": "mirrors.tuna.tsinghua.edu.cn"
                }
                
                # 如果使用PyTorch，添加PyTorch相关的构建参数
                if image.is_pytorch:
                    logger.info(f"Adding PyTorch build args with version: {image.pytorch_version}")
                    build_args["PYTORCH_VERSION"] = image.pytorch_version
                    
                    # 如果使用CUDA，添加CUDA相关的构建参数
                    if image.cuda_available and image.cuda_version:
                        logger.info(f"Adding CUDA build args with version: {image.cuda_version}")
                        build_args.update({
                            "CUDA_VERSION": image.cuda_version,
                            # NVIDIA CUDA镜像允许使用下面的环境变量绕过交互式安装
                            "DEBIAN_FRONTEND": "noninteractive",
                            "FORCE_CUDA": "1"
                        })
                
                # 保存构建参数以供后续故障诊断使用
                logger.info(f"使用构建参数: {build_args}")
                
                # 构建镜像，注意传递is_pytorch参数
                build_result = docker_client.build_image_from_dockerfile(
                    dockerfile_content=dockerfile_content,
                    image_name=custom_image_name,
                    image_tag=custom_image_tag,
                    python_version=image.python_version,
                    build_args=build_args,
                    is_pytorch=image.is_pytorch
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
                    if not actual_python_version.startswith(image.python_version):
                        image.error_message = f"警告: 镜像使用的实际Python版本({actual_python_version})与请求的版本({image.python_version})不完全匹配"
                        image.save(update_fields=['error_message'])
                
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
            
            # 重新抛出异常，返回给客户端
            raise serializers.ValidationError({"detail": str(e)})
    
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
