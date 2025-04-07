"""
This module contains the ViewSets for project management functionality.
It provides API endpoints for managing projects and project files.
"""

from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import Project, ProjectFile
from .serializers import ProjectSerializer, ProjectFileSerializer
from container.models import ContainerInstance, DockerImage
from container.docker_ops import DockerClient

import logging
import json
import os
from typing import Dict, Any, List

# 设置日志记录器
logger = logging.getLogger(__name__)

User = get_user_model()

class ProjectViewSet(viewsets.ModelViewSet):
    """
    项目视图集
    
    提供项目的CRUD操作和特殊功能
    """
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._docker_client = None
    
    @property
    def docker_client(self):
        if self._docker_client is None:
            self._docker_client = DockerClient()
        return self._docker_client
    
    def get_queryset(self):
        """
        获取查询集，只返回当前用户的项目
        """
        user = self.request.user
        return Project.objects.filter(user=user)
    
    def perform_create(self, serializer):
        """
        创建项目并分配容器
        """
        try:
            with transaction.atomic():
                # 保存项目基本信息
                project = serializer.save(user=self.request.user, status='creating')
                
                # 获取镜像信息
                image = project.image
                
                # 创建容器
                container_name = f"mlride-project-{project.id}-{self.request.user.username}"
                
                # 准备容器创建数据
                container_data = {
                    'user': self.request.user,
                    'image': image,
                    'name': container_name,
                    'cpu_limit': 1,  # 默认配置
                    'memory_limit': 2048,  # 默认2GB
                    'gpu_limit': 0
                }
                
                # 创建容器实例
                container = ContainerInstance.objects.create(**container_data)
                
                # 使用Docker客户端创建Docker容器
                container_config = {
                    'image_name': image.get_full_image_name(),
                    'container_name': container_name,
                    'cpu_count': container_data['cpu_limit'],
                    'memory_limit': f"{container_data['memory_limit']}m"
                }
                
                # 根据项目类型配置端口和环境变量
                if project.project_type == 'notebook':
                    # 为Jupyter Notebook配置端口映射和工作目录
                    container_config['ports'] = {'8888/tcp': None}  # Jupyter端口
                    container_config['environment'] = {
                        'PROJECT_ID': str(project.id),
                        'PROJECT_TYPE': 'notebook',
                        'JUPYTER_TOKEN': '',  # 禁用token认证
                        'JUPYTER_CONFIG_DIR': '/root/.jupyter',
                        'JUPYTER_DATA_DIR': '/root/.local/share/jupyter',
                        'JUPYTER_RUNTIME_DIR': '/root/.local/share/jupyter/runtime',
                        'PATH': '/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin:/root/.local/bin'  # 添加PATH环境变量
                    }
                    # 添加工作目录挂载
                    project_workspace = f'/workspace/project-{project.id}'
                    container_config['volumes'] = {
                        project_workspace: {'bind': '/workspace', 'mode': 'rw'}
                    }
                    
                    # 不使用直接的jupyter命令作为启动命令，而是使用bash脚本在容器启动后安装和运行jupyter
                    container_config['command'] = [
                        "/bin/bash", 
                        "-c", 
                        "pip install --no-cache-dir notebook && " +
                        "jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root " +
                        "--NotebookApp.token='' --NotebookApp.password='' --notebook-dir=/workspace"
                    ]
                elif project.project_type == 'canvas':
                    container_config['ports'] = {'8080/tcp': None}  # Canvas端口
                    container_config['environment'] = {
                        'PROJECT_ID': str(project.id),
                        'PROJECT_TYPE': 'canvas'
                    }
                
                # 创建Docker容器
                docker_container = self.docker_client.create_container(**container_config)
                
                # 更新容器ID
                container.container_id = docker_container['id']
                container.save()
                
                # 启动容器
                self.docker_client.start_container(container.container_id)
                
                # 更新项目状态和关联的容器
                project.container = container
                project.status = 'running'
                project.save()
                
        except Exception as e:
            logger.error(f"创建项目失败: {str(e)}")
            # 回滚由Django事务管理
            raise
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        启动项目容器
        """
        project = self.get_object()
        
        if not project.container:
            return Response(
                {"detail": "项目没有关联的容器"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 启动容器
            self.docker_client.start_container(project.container.container_id)
            
            # 更新容器状态
            project.container.status = 'running'
            project.container.started_at = timezone.now()
            project.container.save()
            
            # 更新项目状态
            project.status = 'running'
            project.save()
            
            return Response({"detail": "项目已启动"})
            
        except Exception as e:
            logger.error(f"启动项目失败: {str(e)}")
            return Response(
                {"detail": f"启动项目失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """
        停止项目容器
        """
        project = self.get_object()
        
        if not project.container:
            return Response(
                {"detail": "项目没有关联的容器"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 停止容器
            self.docker_client.stop_container(project.container.container_id)
            
            # 停止关联的Jupyter会话
            try:
                from jupyterapp.models import JupyterSession
                # 获取关联的Jupyter会话（如果存在）
                jupyter_session = JupyterSession.objects.filter(project=project).first()
                if jupyter_session:
                    logger.info(f"停止项目时发现关联的Jupyter会话: {jupyter_session.id}")
                    # 获取PID文件路径
                    import os, signal, time
                    workspace_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                               'workspaces', f'project_{project.id}')
                    pid_file = os.path.join(workspace_dir, '.jupyter.pid')
                    
                    # 如果PID文件存在，尝试终止进程
                    if os.path.exists(pid_file):
                        try:
                            with open(pid_file, 'r') as f:
                                pid = int(f.read().strip())
                            os.kill(pid, signal.SIGTERM)
                            time.sleep(1)  # 等待进程结束
                            os.remove(pid_file)
                            logger.info(f"成功终止Jupyter进程，PID: {pid}")
                        except Exception as e:
                            logger.warning(f"终止Jupyter进程时出错: {str(e)}")
                    
                    # 更新会话状态
                    jupyter_session.status = 'stopped'
                    jupyter_session.url = None
                    jupyter_session.save()
                    logger.info("已更新Jupyter会话状态为stopped")
            except Exception as e:
                logger.warning(f"尝试停止Jupyter会话时出错: {str(e)}")
            
            # 更新容器状态
            project.container.status = 'stopped'
            project.container.save()
            
            # 更新项目状态
            project.status = 'stopped'
            project.save()
            
            return Response({"detail": "项目已停止"})
            
        except Exception as e:
            logger.error(f"停止项目失败: {str(e)}")
            return Response(
                {"detail": f"停止项目失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        获取项目容器的资源使用情况
        """
        project = self.get_object()
        
        if not project.container:
            return Response(
                {"detail": "项目没有关联的容器"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 获取容器状态
            stats = self.docker_client.get_container_stats(project.container.container_id)
            return Response(stats)
            
        except Exception as e:
            logger.error(f"获取项目状态失败: {str(e)}")
            return Response(
                {"detail": f"获取项目状态失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    def destroy(self, request, *args, **kwargs):
        """
        删除项目及其关联的容器
        """
        project = self.get_object()
        
        try:
            with transaction.atomic():
                # 如果有关联容器，先停止并删除容器
                if project.container:
                    try:
                        # 停止容器
                        self.docker_client.stop_container(project.container.container_id)
                        # 删除容器
                        self.docker_client.remove_container(project.container.container_id, force=True)
                    except Exception as e:
                        logger.warning(f"删除项目容器时出错: {str(e)}")
                    
                    # 删除容器实例记录
                    project.container.delete()
                
                # 删除项目
                project.delete()
                
                return Response(status=status.HTTP_204_NO_CONTENT)
                
        except Exception as e:
            logger.error(f"删除项目失败: {str(e)}")
            return Response(
                {"detail": f"删除项目失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class ProjectFileViewSet(viewsets.ModelViewSet):
    """
    项目文件视图集
    
    提供项目文件的CRUD操作
    """
    serializer_class = ProjectFileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        获取查询集，只返回当前用户项目的文件
        """
        user = self.request.user
        return ProjectFile.objects.filter(project__user=user)
    
    def perform_create(self, serializer):
        """
        创建项目文件
        """
        # 确保项目属于当前用户
        project = serializer.validated_data.get('project')
        if project.user != self.request.user:
            raise serializers.ValidationError("您没有权限在此项目中创建文件")
        
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def list_by_project(self, request):
        """
        按项目列出文件
        """
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response(
                {"detail": "缺少项目ID参数"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 确保项目存在且属于当前用户
        project = get_object_or_404(Project, id=project_id, user=request.user)
        
        files = ProjectFile.objects.filter(project=project)
        serializer = self.get_serializer(files, many=True)
        
        return Response(serializer.data)
