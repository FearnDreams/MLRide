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
from django.conf import settings
from rest_framework.parsers import MultiPartParser
import re

from .models import Project, ProjectFile, Workflow, WorkflowExecution, WorkflowComponentExecution
from .serializers import (
    ProjectSerializer, ProjectFileSerializer, 
    WorkflowSerializer, WorkflowListSerializer, 
    WorkflowExecutionSerializer, WorkflowComponentExecutionSerializer
)
from container.models import ContainerInstance, DockerImage
from container.docker_ops import DockerClient
from dataset.models import Dataset
from workflow_engine.engine import WorkflowEngineManager

import logging
import json
import os
import shutil
import datetime
import uuid
from typing import Dict, Any, List

# 设置日志记录器
logger = logging.getLogger(__name__)

User = get_user_model()

def simple_secure_filename(filename: str) -> str:
    """
    一个非常基础和简化的文件名清理函数。
    将非字母数字、下划线、点、连字符替换为下划线。
    生产环境建议使用更健壮的库如 Werkzeug 的 secure_filename。
    """
    # 移除非法字符
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    # 防止文件名以点或连字符开头
    if filename.startswith(('.', '-')):
        filename = '_' + filename[1:]
    # 防止文件名过长 (可选)
    # max_len = 200 
    # if len(filename) > max_len:
    #     name, ext = os.path.splitext(filename)
    #     filename = name[:max_len - len(ext) -1] + ext
    return filename

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
                    
                    # 添加工作目录挂载 - 修改为使用正确的宿主机目录
                    import os
                    # 获取项目工作目录的绝对路径
                    workspace_dir = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                        'workspaces', 
                        f'project_{project.id}'
                    )
                    # 确保工作目录存在
                    os.makedirs(workspace_dir, exist_ok=True)
                    logger.info(f"为项目 {project.id} 创建工作目录: {workspace_dir}")
                    
                    # 设置挂载点，将宿主机工作目录挂载到容器的/workspace目录
                    container_config['volumes'] = {
                        os.path.abspath(workspace_dir): {'bind': '/workspace', 'mode': 'rw'}
                    }
                    logger.info(f"设置容器挂载: {os.path.abspath(workspace_dir)} -> /workspace")
                    
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
                
                # 检查并删除关联的工作流（如果表存在）
                try:
                    # 尝试手动删除关联的工作流，避免级联删除失败
                    if hasattr(project, 'workflows'):
                        workflows = project.workflows.all()
                        for workflow in workflows:
                            # 先删除工作流执行记录
                            try:
                                executions = workflow.executions.all()
                                for execution in executions:
                                    # 删除组件执行记录
                                    execution.component_executions.all().delete()
                                    execution.delete()
                            except Exception as e:
                                logger.warning(f"删除工作流执行记录时出错: {str(e)}")
                            # 删除工作流本身
                            workflow.delete()
                except Exception as e:
                    # 如果工作流相关表不存在，记录警告但继续执行
                    logger.warning(f"删除工作流记录时出错（表可能不存在）: {str(e)}")
                
                # 删除项目文件记录
                try:
                    project.files.all().delete()
                except Exception as e:
                    logger.warning(f"删除项目文件记录时出错: {str(e)}")
                
                # 删除项目
                project.delete()
                
                return Response(status=status.HTTP_204_NO_CONTENT)
                
        except Exception as e:
            logger.error(f"删除项目失败: {str(e)}")
            return Response(
                {"detail": f"删除项目失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @action(detail=True, methods=['post'])
    def create_snapshot(self, request, pk=None):
        """
        创建项目文件快照
        """
        project = self.get_object()
        
        # 获取请求数据
        version = request.data.get('version', '')
        description = request.data.get('description', '')
        
        # 验证输入
        if not version:
            return Response(
                {"detail": "请提供版本号"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 获取项目工作目录
            workspace_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                'workspaces', 
                f'project_{project.id}'
            )
            
            # 检查工作目录是否存在
            if not os.path.exists(workspace_dir):
                return Response(
                    {"detail": "项目工作目录不存在"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # 创建快照目录
            snapshots_dir = os.path.join(workspace_dir, 'snapshots')
            os.makedirs(snapshots_dir, exist_ok=True)
            
            # 生成唯一的快照ID
            snapshot_id = str(uuid.uuid4())
            snapshot_dir = os.path.join(snapshots_dir, snapshot_id)
            
            # 创建快照目录
            os.makedirs(snapshot_dir)
            
            # 复制工作目录中的文件到快照目录
            files_copied = []
            for root, dirs, files in os.walk(workspace_dir):
                # 跳过snapshots目录
                if 'snapshots' in root.split(os.path.sep):
                    continue
                    
                for file in files:
                    src_path = os.path.join(root, file)
                    # 计算相对路径
                    rel_path = os.path.relpath(src_path, workspace_dir)
                    dst_path = os.path.join(snapshot_dir, rel_path)
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    # 复制文件
                    shutil.copy2(src_path, dst_path)
                    files_copied.append(rel_path)
            
            # 创建快照元数据
            snapshot_metadata = {
                'id': snapshot_id,
                'version': version,
                'description': description,
                'files': files_copied,
                'created_at': datetime.datetime.now().isoformat(),
                'created_by': request.user.username
            }
            
            # 保存快照元数据
            metadata_path = os.path.join(snapshot_dir, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(snapshot_metadata, f)
                
            # 更新snapshots索引文件
            index_path = os.path.join(snapshots_dir, 'index.json')
            snapshots_index = []
            
            if os.path.exists(index_path):
                try:
                    with open(index_path, 'r') as f:
                        snapshots_index = json.load(f)
                except:
                    snapshots_index = []
            
            # 添加新快照到索引
            snapshots_index.append({
                'id': snapshot_id,
                'version': version,
                'description': description,
                'created_at': snapshot_metadata['created_at'],
                'created_by': snapshot_metadata['created_by']
            })
            
            # 按创建时间排序
            snapshots_index.sort(key=lambda x: x['created_at'], reverse=True)
            
            # 保存更新后的索引
            with open(index_path, 'w') as f:
                json.dump(snapshots_index, f)
                
            return Response({
                'id': snapshot_id,
                'version': version,
                'description': description,
                'file_count': len(files_copied),
                'created_at': snapshot_metadata['created_at']
            })
            
        except Exception as e:
            logger.error(f"创建项目快照失败: {str(e)}")
            return Response(
                {"detail": f"创建项目快照失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def list_snapshots(self, request, pk=None):
        """
        获取项目的快照列表
        """
        project = self.get_object()
        
        try:
            # 获取项目工作目录
            workspace_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                'workspaces', 
                f'project_{project.id}'
            )
            
            # 检查工作目录是否存在
            if not os.path.exists(workspace_dir):
                return Response([])
                
            # 检查快照目录是否存在
            snapshots_dir = os.path.join(workspace_dir, 'snapshots')
            if not os.path.exists(snapshots_dir):
                return Response([])
                
            # 读取快照索引
            index_path = os.path.join(snapshots_dir, 'index.json')
            if not os.path.exists(index_path):
                return Response([])
                
            with open(index_path, 'r') as f:
                snapshots_index = json.load(f)
                
            return Response(snapshots_index)
            
        except Exception as e:
            logger.error(f"获取项目快照列表失败: {str(e)}")
            return Response(
                {"detail": f"获取项目快照列表失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def get_snapshot(self, request, pk=None):
        """
        获取项目快照详情
        """
        project = self.get_object()
        snapshot_id = request.query_params.get('snapshot_id')
        
        if not snapshot_id:
            return Response(
                {"detail": "请提供快照ID"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 获取项目工作目录
            workspace_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                'workspaces', 
                f'project_{project.id}'
            )
            
            # 检查快照目录是否存在
            snapshot_dir = os.path.join(workspace_dir, 'snapshots', snapshot_id)
            if not os.path.exists(snapshot_dir):
                return Response(
                    {"detail": "快照不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # 读取快照元数据
            metadata_path = os.path.join(snapshot_dir, 'metadata.json')
            with open(metadata_path, 'r') as f:
                snapshot_metadata = json.load(f)
                
            return Response(snapshot_metadata)
            
        except Exception as e:
            logger.error(f"获取项目快照详情失败: {str(e)}")
            return Response(
                {"detail": f"获取项目快照详情失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def get_snapshot_file(self, request, pk=None):
        """
        获取项目快照中特定文件的内容
        """
        project = self.get_object()
        snapshot_id = request.query_params.get('snapshot_id')
        file_path = request.query_params.get('file_path')
        
        if not snapshot_id:
            return Response(
                {"detail": "请提供快照ID"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not file_path:
            return Response(
                {"detail": "请提供文件路径"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 清理文件路径，移除末尾的斜杠或反斜杠
        file_path = file_path.rstrip('/\\')
        
        try:
            # 获取项目工作目录
            workspace_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                'workspaces', 
                f'project_{project.id}'
            )
            
            # 记录详细日志
            logger.info(f"尝试获取快照文件: 项目ID={project.id}, 快照ID={snapshot_id}, 文件路径={file_path}")
            
            # 检查快照目录是否存在
            snapshot_dir = os.path.join(workspace_dir, 'snapshots', snapshot_id)
            if not os.path.exists(snapshot_dir):
                logger.error(f"快照目录不存在: {snapshot_dir}")
                return Response(
                    {"detail": "快照不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 获取文件路径
            file_full_path = os.path.join(snapshot_dir, file_path)
            logger.info(f"文件完整路径: {file_full_path}")
            
            # 检查文件是否存在于快照中
            if not os.path.exists(file_full_path) or not os.path.isfile(file_full_path):
                logger.error(f"文件不存在: {file_full_path}")
                return Response(
                    {"detail": "文件不存在于此快照中"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 获取文件类型
            _, ext = os.path.splitext(file_path)
            file_type = ext.lstrip('.')
            
            # 二进制文件类型列表 - 移除ipynb，允许它作为文本文件处理
            binary_extensions = [
                'pyc', 'pyd', 'pyo', 'so', 'dll', 'exe', 'bin', 'jpg', 'jpeg', 
                'png', 'gif', 'bmp', 'ico', 'pdf', 'doc', 'docx', 'xls', 'xlsx',
                'zip', 'tar', 'gz', 'rar', '7z', 'mp3', 'mp4', 'avi', 'mov'
            ]
            
            # 检查是否是二进制文件
            if file_type.lower() in binary_extensions:
                logger.info(f"检测到二进制文件类型: {file_type}")
                return Response({
                    'file_path': file_path,
                    'content': f"[二进制文件: {file_path}]",
                    'file_type': file_type,
                    'is_binary': True
                })
            
            # 尝试读取文件前先检查文件大小
            file_size = os.path.getsize(file_full_path)
            logger.info(f"文件大小: {file_size} 字节")
            
            # 放宽文件大小限制，提高到5MB
            if file_size > 5 * 1024 * 1024:  # 5MB
                logger.warning(f"文件过大: {file_size} 字节")
                return Response({
                    'file_path': file_path,
                    'content': f"[文件过大: {file_size} 字节]",
                    'file_type': file_type,
                    'is_large_file': True
                })
            
            # 对于 ipynb 文件特殊处理
            if file_type.lower() == 'ipynb':
                try:
                    # 尝试读取并简化内容
                    with open(file_full_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    return Response({
                        'file_path': file_path,
                        'content': content,
                        'file_type': file_type
                    })
                except Exception as e:
                    logger.error(f"处理ipynb文件时出错: {str(e)}")
                    return Response({
                        'file_path': file_path,
                        'content': f"[Jupyter Notebook文件: {file_path}]",
                        'file_type': file_type,
                        'is_notebook': True
                    })
            
            # 依次尝试多种编码方式读取文件
            encoding_attempts = ['utf-8', 'gbk', 'latin-1', 'cp1252', 'iso-8859-1']
            content = None
            
            for encoding in encoding_attempts:
                try:
                    with open(file_full_path, 'r', encoding=encoding, errors='replace') as f:
                        content = f.read()
                    logger.info(f"成功使用 {encoding} 编码读取文件")
                    break
                except Exception as e:
                    logger.warning(f"使用 {encoding} 编码读取文件失败: {str(e)}")
                    continue
            
            if content is None:
                # 作为最后的尝试，使用二进制模式读取并转换为字符串
                try:
                    with open(file_full_path, 'rb') as f:
                        binary_data = f.read()
                    # 尝试将二进制数据转换为字符串
                    try:
                        content = binary_data.decode('utf-8', errors='replace')
                    except:
                        content = str(binary_data)
                    logger.info("使用二进制模式读取文件并转换为字符串")
                except Exception as e:
                    logger.error(f"所有读取尝试均失败: {str(e)}")
                    return Response(
                        {"detail": f"无法读取文件内容: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            return Response({
                'file_path': file_path,
                'content': content,
                'file_type': file_type
            })
            
        except Exception as e:
            logger.error(f"获取项目快照中文件内容失败: {str(e)}")
            return Response(
                {"detail": f"获取项目快照中文件内容失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def restore_snapshot(self, request, pk=None):
        """
        恢复项目到指定快照
        """
        project = self.get_object()
        snapshot_id = request.data.get('snapshot_id')
        
        if not snapshot_id:
            return Response(
                {"detail": "请提供快照ID"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 获取项目工作目录
            workspace_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                'workspaces', 
                f'project_{project.id}'
            )
            
            # 检查快照目录是否存在
            snapshot_dir = os.path.join(workspace_dir, 'snapshots', snapshot_id)
            if not os.path.exists(snapshot_dir):
                return Response(
                    {"detail": "快照不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # 读取快照元数据
            metadata_path = os.path.join(snapshot_dir, 'metadata.json')
            with open(metadata_path, 'r') as f:
                snapshot_metadata = json.load(f)
            
            # 在恢复前创建当前状态的临时快照
            backup_id = f"backup_{uuid.uuid4()}"
            backup_dir = os.path.join(workspace_dir, 'snapshots', backup_id)
            os.makedirs(backup_dir)
            
            # 复制当前工作目录到备份
            for root, dirs, files in os.walk(workspace_dir):
                # 跳过snapshots目录
                if 'snapshots' in root.split(os.path.sep):
                    continue
                    
                for file in files:
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, workspace_dir)
                    dst_path = os.path.join(backup_dir, rel_path)
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    # 复制文件
                    shutil.copy2(src_path, dst_path)
            
            # 清空工作目录（除了snapshots目录）
            for item in os.listdir(workspace_dir):
                if item == 'snapshots':
                    continue
                    
                item_path = os.path.join(workspace_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            
            # 从快照恢复文件
            for root, dirs, files in os.walk(snapshot_dir):
                # 跳过metadata.json文件
                if root == snapshot_dir:
                    files = [f for f in files if f != 'metadata.json']
                    
                for file in files:
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, snapshot_dir)
                    dst_path = os.path.join(workspace_dir, rel_path)
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    # 复制文件
                    shutil.copy2(src_path, dst_path)
            
            return Response({
                "detail": f"已成功恢复到版本 {snapshot_metadata['version']}",
                "backup_id": backup_id
            })
            
        except Exception as e:
            logger.error(f"恢复项目快照失败: {str(e)}")
            return Response(
                {"detail": f"恢复项目快照失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def delete_snapshot(self, request, pk=None):
        """
        删除项目快照
        """
        project = self.get_object()
        snapshot_id = request.data.get('snapshot_id')
        
        if not snapshot_id:
            return Response(
                {"detail": "请提供快照ID"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # 获取项目工作目录
            workspace_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                'workspaces', 
                f'project_{project.id}'
            )
            
            # 检查快照目录是否存在
            snapshots_dir = os.path.join(workspace_dir, 'snapshots')
            snapshot_dir = os.path.join(snapshots_dir, snapshot_id)
            
            if not os.path.exists(snapshot_dir):
                return Response(
                    {"detail": "快照不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # 读取快照索引
            index_path = os.path.join(snapshots_dir, 'index.json')
            snapshots_index = []
            
            if os.path.exists(index_path):
                try:
                    with open(index_path, 'r') as f:
                        snapshots_index = json.load(f)
                except Exception as e:
                    logger.error(f"读取快照索引失败: {str(e)}")
                    return Response(
                        {"detail": f"读取快照索引失败: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # 从索引中移除要删除的快照
            snapshots_index = [s for s in snapshots_index if s['id'] != snapshot_id]
            
            # 保存更新后的索引
            with open(index_path, 'w') as f:
                json.dump(snapshots_index, f)
                
            # 删除快照目录
            shutil.rmtree(snapshot_dir)
            
            return Response({
                "status": "success",
                "message": "快照删除成功"
            })
                
        except Exception as e:
            logger.error(f"删除项目快照失败: {str(e)}")
            return Response(
                {"detail": f"删除项目快照失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def current_files(self, request, pk=None):
        """
        获取当前项目工作区中的所有文件列表
        """
        project = self.get_object()
        
        try:
            # 获取项目工作目录
            workspace_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                'workspaces', 
                f'project_{project.id}'
            )
            
            logger.info(f"获取当前项目文件列表，项目ID={project.id}，工作目录={workspace_dir}")
            
            # 检查工作目录是否存在
            if not os.path.exists(workspace_dir):
                logger.warning(f"项目工作目录不存在: {workspace_dir}")
                return Response(
                    {"detail": "项目工作目录不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # 递归获取所有文件
            all_files = []
            
            def list_files_recursively(directory, base_path=''):
                for item in os.listdir(directory):
                    full_path = os.path.join(directory, item)
                    relative_path = os.path.join(base_path, item)
                    
                    # 检查是否要忽略的特殊文件/目录
                    if item.startswith(".git") or \
                       ".ipynb_checkpoints" in relative_path or \
                       ".Trash" in relative_path or \
                       item.endswith(".pyc") or \
                       "__pycache__" in relative_path:
                        continue
                    
                    if os.path.isdir(full_path):
                        # 递归处理子目录
                        list_files_recursively(full_path, relative_path)
                    else:
                        # 添加文件到列表
                        all_files.append(relative_path.replace("\\", "/"))
            
            # 开始递归扫描文件
            list_files_recursively(workspace_dir)
            
            logger.info(f"找到 {len(all_files)} 个文件")
            
            return Response({
                "status": "success",
                "message": "获取当前项目文件列表成功",
                "data": {
                    "files": all_files
                }
            })
                
        except Exception as e:
            logger.error(f"获取当前项目文件列表失败: {str(e)}")
            return Response(
                {"status": "error", "message": f"获取当前项目文件列表失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def current_file_content(self, request, pk=None):
        """
        获取当前项目工作区中特定文件的内容
        """
        project = self.get_object()
        file_path = request.query_params.get('file_path')
        
        if not file_path:
            return Response(
                {"status": "error", "message": "请提供文件路径"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 清理文件路径，移除末尾的斜杠或反斜杠
        file_path = file_path.rstrip('/\\')
        
        try:
            # 获取项目工作目录
            workspace_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                'workspaces', 
                f'project_{project.id}'
            )
            
            # 记录详细日志
            logger.info(f"尝试获取当前工作区文件: 项目ID={project.id}, 文件路径={file_path}")
            
            # 获取文件完整路径
            file_full_path = os.path.join(workspace_dir, file_path)
            logger.info(f"文件完整路径: {file_full_path}")
            
            # 检查文件是否存在
            if not os.path.exists(file_full_path) or not os.path.isfile(file_full_path):
                logger.error(f"文件不存在: {file_full_path}")
                return Response(
                    {"status": "error", "message": "文件不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 获取文件类型
            _, ext = os.path.splitext(file_path)
            file_type = ext.lstrip('.')
            
            # 二进制文件类型列表 - 移除ipynb，允许它作为文本文件处理
            binary_extensions = [
                'pyc', 'pyd', 'pyo', 'so', 'dll', 'exe', 'bin', 'jpg', 'jpeg', 
                'png', 'gif', 'bmp', 'ico', 'pdf', 'doc', 'docx', 'xls', 'xlsx',
                'zip', 'tar', 'gz', 'rar', '7z', 'mp3', 'mp4', 'avi', 'mov'
            ]
            
            # 检查是否是二进制文件
            if file_type.lower() in binary_extensions:
                logger.info(f"检测到二进制文件类型: {file_type}")
                return Response({
                    "status": "success",
                    "message": "获取文件内容成功",
                    "data": {
                        'file_path': file_path,
                        'content': f"[二进制文件: {file_path}]",
                        'file_type': file_type,
                        'is_binary': True
                    }
                })
            
            # 尝试读取文件前先检查文件大小
            file_size = os.path.getsize(file_full_path)
            logger.info(f"文件大小: {file_size} 字节")
            
            # 放宽文件大小限制，提高到5MB
            if file_size > 5 * 1024 * 1024:  # 5MB
                logger.warning(f"文件过大: {file_size} 字节")
                return Response({
                    "status": "success",
                    "message": "获取文件内容成功",
                    "data": {
                        'file_path': file_path,
                        'content': f"[文件过大: {file_size} 字节]",
                        'file_type': file_type,
                        'is_large_file': True
                    }
                })
            
            # 对于 ipynb 文件特殊处理
            if file_type.lower() == 'ipynb':
                try:
                    # 尝试读取并简化内容
                    with open(file_full_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    return Response({
                        "status": "success",
                        "message": "获取文件内容成功",
                        "data": {
                            'file_path': file_path,
                            'content': content,
                            'file_type': file_type
                        }
                    })
                except Exception as e:
                    logger.error(f"处理ipynb文件时出错: {str(e)}")
                    return Response({
                        "status": "success",
                        "message": "获取文件内容成功",
                        "data": {
                            'file_path': file_path,
                            'content': f"[Jupyter Notebook文件: {file_path}]",
                            'file_type': file_type,
                            'is_notebook': True
                        }
                    })
            
            # 依次尝试多种编码方式读取文件
            encoding_attempts = ['utf-8', 'gbk', 'latin-1', 'cp1252', 'iso-8859-1']
            content = None
            
            for encoding in encoding_attempts:
                try:
                    with open(file_full_path, 'r', encoding=encoding, errors='replace') as f:
                        content = f.read()
                    logger.info(f"成功使用 {encoding} 编码读取文件")
                    break
                except Exception as e:
                    logger.warning(f"使用 {encoding} 编码读取文件失败: {str(e)}")
                    continue
            
            if content is None:
                # 作为最后的尝试，使用二进制模式读取并转换为字符串
                try:
                    with open(file_full_path, 'rb') as f:
                        binary_data = f.read()
                    # 尝试将二进制数据转换为字符串
                    try:
                        content = binary_data.decode('utf-8', errors='replace')
                    except:
                        content = str(binary_data)
                    logger.info("使用二进制模式读取文件并转换为字符串")
                except Exception as e:
                    logger.error(f"所有读取尝试均失败: {str(e)}")
                    return Response(
                        {"status": "error", "message": f"无法读取文件内容: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            return Response({
                "status": "success",
                "message": "获取文件内容成功",
                "data": {
                    'file_path': file_path,
                    'content': content,
                    'file_type': file_type
                }
            })
            
        except Exception as e:
            logger.error(f"获取当前项目文件内容失败: {str(e)}")
            return Response(
                {"status": "error", "message": f"获取当前项目文件内容失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def upload_data(self, request, pk=None):
        """
        上传数据到项目工作区
        支持从用户的数据集或本地文件上传
        """
        try:
            project = self.get_object() # 获取项目实例
        except Exception as e:
            logger.error(f"获取项目 {pk} 失败: {str(e)}")
            return Response({"status": "error", "message": "找不到指定的项目"}, status=status.HTTP_404_NOT_FOUND)

        # 检查用户是否有权限操作此项目 (通常 get_object 会处理，但可以加一层保险)
        if project.user != request.user:
            return Response({"status": "error", "message": "权限不足"}, status=status.HTTP_403_FORBIDDEN)

        # 确定项目工作区路径
        workspace_path = os.path.join(settings.WORKSPACE_DIR, f'project_{project.id}')
        os.makedirs(workspace_path, exist_ok=True) # 确保目录存在

        uploaded_files = []
        warnings = []

        # 检查请求类型并处理
        content_type = request.content_type
        logger.info(f"接收到上传请求: 项目ID={pk}, Content-Type={content_type}")

        try:
            # 情况1: 从数据集上传 (Content-Type: application/json)
            if 'application/json' in content_type:
                dataset_ids = request.data.get('dataset_ids', [])
                logger.info(f"处理从数据集上传: IDs={dataset_ids}")
                if not dataset_ids:
                    return Response({"status": "error", "message": "未选择任何数据集"}, status=status.HTTP_400_BAD_REQUEST)

                # 查询选中的数据集 (确保是用户自己的且状态为 ready)
                datasets_to_upload = Dataset.objects.filter(
                    id__in=dataset_ids,
                    creator=request.user,
                    status='ready'
                )
                
                found_ids = [str(ds.id) for ds in datasets_to_upload]
                missing_ids = [item for item in map(str, dataset_ids) if item not in found_ids]
                if missing_ids:
                    warnings.append(f"以下数据集未找到、非用户创建或状态未就绪，已跳过: {', '.join(missing_ids)}")

                if not datasets_to_upload.exists():
                     return Response({"status": "warning", "message": "没有有效的数据集可供上传", "warnings": warnings}, status=status.HTTP_400_BAD_REQUEST)

                for dataset in datasets_to_upload:
                    source_path = dataset.get_absolute_file_path()
                    if source_path and os.path.isfile(source_path):
                        base_filename = os.path.basename(dataset.file.name)
                        target_path = os.path.join(workspace_path, base_filename)
                        
                        # 处理文件名冲突 (简单处理：如果已存在则跳过并警告)
                        if os.path.exists(target_path):
                            warnings.append(f"文件 '{base_filename}' 已存在于项目目录中，已跳过上传。")
                            logger.warning(f"文件冲突: {target_path} 已存在，跳过数据集 {dataset.id}")
                            continue
                            
                        try:
                            shutil.copy2(source_path, target_path) # copy2 尝试保留元数据
                            uploaded_files.append(base_filename)
                            logger.info(f"成功复制数据集文件: {source_path} -> {target_path}")
                        except Exception as copy_err:
                            error_msg = f"复制数据集文件 '{base_filename}' 时出错: {copy_err}"
                            warnings.append(error_msg)
                            logger.error(error_msg)
                    else:
                        warnings.append(f"数据集 '{dataset.name}' (ID: {dataset.id}) 的源文件未找到或无效，已跳过。")
                        logger.warning(f"数据集源文件无效: ID={dataset.id}, Path={source_path}")
            
            # 情况2: 从本地上传 (Content-Type: multipart/form-data)
            elif 'multipart/form-data' in content_type:
                files = request.FILES.getlist('files') # 获取所有名为 'files' 的文件
                logger.info(f"处理从本地上传: 文件数量={len(files)}")
                if not files:
                    return Response({"status": "error", "message": "没有选择任何本地文件"}, status=status.HTTP_400_BAD_REQUEST)

                for uploaded_file in files:
                    file_name = uploaded_file.name
                    target_path = os.path.join(workspace_path, file_name)
                    
                    # 处理文件名冲突 (简单处理：如果已存在则跳过并警告)
                    if os.path.exists(target_path):
                        warnings.append(f"文件 '{file_name}' 已存在于项目目录中，已跳过上传。")
                        logger.warning(f"文件冲突: {target_path} 已存在，跳过本地文件 {file_name}")
                        continue
                        
                    try:
                        # 分块写入以处理大文件
                        with open(target_path, 'wb+') as destination:
                            for chunk in uploaded_file.chunks():
                                destination.write(chunk)
                        uploaded_files.append(file_name)
                        logger.info(f"成功保存本地上传文件: {target_path}")
                    except Exception as save_err:
                        error_msg = f"保存本地文件 '{file_name}' 时出错: {save_err}"
                        warnings.append(error_msg)
                        logger.error(error_msg)
                        # 如果保存失败，尝试删除可能已创建的不完整文件
                        if os.path.exists(target_path):
                            try:
                                os.remove(target_path)
                            except OSError as remove_err:
                                logger.error(f"删除不完整文件 {target_path} 失败: {remove_err}")
            
            # 其他 Content-Type 不支持
            else:
                return Response({"status": "error", "message": f"不支持的 Content-Type: {content_type}"}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        except Exception as e:
            logger.exception(f"处理上传数据时发生意外错误: 项目ID={pk}, Error: {str(e)}")
            return Response({"status": "error", "message": f"处理上传时发生内部错误: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 根据上传结果返回响应
        if not uploaded_files and not warnings:
             # 这种情况理论上不应该发生，除非所有文件都因冲突被跳过且没有其他警告
             return Response({"status": "info", "message": "没有文件被上传（可能所有文件已存在或无效）"}, status=status.HTTP_200_OK)
        elif not uploaded_files and warnings:
            return Response({"status": "warning", "message": "数据上传失败或已存在", "warnings": warnings}, status=status.HTTP_400_BAD_REQUEST)
        elif uploaded_files and warnings:
            return Response({"status": "warning", "message": f"部分数据上传成功，但有警告", "uploaded_files": uploaded_files, "warnings": warnings}, status=status.HTTP_200_OK)
        else: # uploaded_files and not warnings
            return Response({"status": "success", "message": f"成功上传 {len(uploaded_files)} 个文件", "uploaded_files": uploaded_files}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='upload-file', parser_classes=[MultiPartParser])
    def upload_workflow_file(self, request, pk=None):
        """
        处理专用于工作流组件的文件上传（例如CSV输入）。
        文件将保存到项目工作区的 'uploads' 子目录中，并返回相对路径。
        期望的表单字段名为 'file'。
        """
        try:
            project = self.get_object() # pk 是 project_id
        except Exception as e:
            logger.error(f"获取项目 {pk} 失败: {str(e)}")
            return Response({"detail": "找不到指定的项目。"}, status=status.HTTP_404_NOT_FOUND)

        file_obj = request.FILES.get('file') # 前端发送的字段名是 'file'

        if not file_obj:
            return Response({'detail': '未提供文件。'}, status=status.HTTP_400_BAD_REQUEST)

        # 基本的文件类型校验 (仅允许CSV)
        if not file_obj.name.lower().endswith('.csv'):
            return Response({'detail': '文件类型无效，仅支持CSV文件。'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 文件大小校验 (可选, 例如最大50MB)
        # max_size_mb = 50
        # if file_obj.size > max_size_mb * 1024 * 1024:
        #     return Response({'detail': f'文件过大，最大允许 {max_size_mb}MB。'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 确定项目工作区在宿主机上的绝对路径
            # 这里的路径构建逻辑应与 perform_create 中创建工作区和Docker卷挂载的逻辑一致
            # 例如: settings.BASE_DIR -> backend/ -> workspaces/ -> project_{project.id}
            # 或者如果 settings.WORKSPACE_DIR 已定义为 backend/workspaces/
            if hasattr(settings, 'WORKSPACE_SUBDIR') and hasattr(settings, 'PROJECT_DIR_PREFIX'):
                 # 基于您现有 upload_data 的 settings.WORKSPACE_DIR 和 project_id 结构
                 # settings.WORKSPACE_DIR 可能是指向 '.../backend/workspaces/'
                 host_project_workspace_root = os.path.join(settings.WORKSPACE_DIR, f'{settings.PROJECT_DIR_PREFIX}{project.id}')
            else: # 后备，基于 perform_create 中的结构
                 # settings.BASE_DIR 通常是 Django 项目的根目录 (manage.py 所在的目录)
                 # 如果 views.py 在 backend/project/views.py, 那么 settings.BASE_DIR/../workspaces/project_{project.id}
                 # 或者更安全的方式是从 settings 获取工作区基础路径
                 base_workspace_dir = getattr(settings, 'PROJECT_WORKSPACES_ROOT', 
                                             os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'workspaces'))
                 host_project_workspace_root = os.path.join(base_workspace_dir, f'project_{project.id}')


            uploads_subdir_name = 'uploads' # 工作流组件上传文件的子目录
            host_uploads_dir = os.path.join(host_project_workspace_root, uploads_subdir_name)
            
            os.makedirs(host_uploads_dir, exist_ok=True) # 确保 'uploads' 子目录存在
            logger.info(f"项目 {project.id} 的上传目录: {host_uploads_dir}")

            # 清理原始文件名并创建唯一文件名以避免冲突
            original_filename, original_extension = os.path.splitext(file_obj.name)
            safe_original_filename = simple_secure_filename(original_filename) # 使用我们定义的清理函数
            
            # 生成更短的UUID部分或时间戳确保唯一性
            unique_suffix = uuid.uuid4().hex[:8] 
            unique_filename = f"{safe_original_filename}_{unique_suffix}{original_extension.lower()}"
            
            host_file_path = os.path.join(host_uploads_dir, unique_filename)

            # 保存文件
            with open(host_file_path, 'wb+') as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)
            
            # 返回给前端的路径是相对于项目工作区根目录的 (即容器内 /workspace/uploads/unique_filename.csv)
            relative_path_for_component = os.path.join(uploads_subdir_name, unique_filename).replace("\\\\", "/") # 确保使用正斜杠

            logger.info(f"文件 {file_obj.name} 已作为 {unique_filename} 上传到项目 {project.id} 的 {relative_path_for_component}")
            
            return Response({
                'detail': '文件上传成功。',
                'file_path': relative_path_for_component, # 这是组件参数将使用的路径
                'filename': unique_filename # 实际保存的文件名
            }, status=status.HTTP_201_CREATED)

        except IOError as e:
            logger.error(f"保存上传文件到 {host_file_path if 'host_file_path' in locals() else 'unknown path'} 失败: {e}")
            return Response({'detail': f'文件保存失败: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.exception(f"处理项目 {project.id} 的文件上传时发生意外错误: {e}")
            return Response({'detail': f'处理文件上传时发生内部错误: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['POST'])
    def ensure_uploads_directory(self, request, pk=None):
        """确保项目的uploads目录存在
        
        创建uploads目录(如果不存在)，确保文件上传有效。
        """
        try:
            project = self.get_object()
            
            # 获取项目工作区路径
            workspace_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                'workspaces', 
                f'project_{project.id}'
            )
            
            # 创建标准化路径，确保使用正斜杠
            uploads_dir = os.path.join(workspace_dir, 'uploads').replace('\\', '/')
            
            # 确保uploads目录存在
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir, exist_ok=True)
                logger.info(f"为项目 {project.id} 创建了uploads目录: {uploads_dir}")
            else:
                logger.info(f"uploads目录已存在: {uploads_dir}")
            
            # 检查容器中是否也需要创建uploads目录
            docker_client = DockerClient()
            
            if project.container:
                try:
                    # 在容器中执行命令创建目录
                    cmd = ['mkdir', '-p', '/workspace/uploads']
                    result = docker_client.exec_command_in_container(project.container.container_id, cmd)
                    logger.info(f"在容器 {project.container.container_id} 中创建uploads目录，结果: {result}")
                except Exception as e:
                    logger.warning(f"无法在容器中创建uploads目录: {str(e)}")
            
            return Response({'status': 'success', 'message': 'uploads目录已创建或已确认存在'})
        except Exception as e:
            logger.error(f"确保uploads目录存在时出错: {str(e)}")
            return Response(
                {'status': 'error', 'message': f"创建uploads目录失败: {str(e)}"}, 
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
        serializer.save()
    
    @action(detail=False, methods=['get'], url_path='project/(?P<project_id>[^/.]+)')
    def list_by_project(self, request, project_id=None):
        """
        按项目列出文件
        """
        try:
            project = Project.objects.get(id=project_id, user=request.user)
        except Project.DoesNotExist:
            return Response(
                {"status": "error", "message": "找不到指定的项目或没有权限访问"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        files = ProjectFile.objects.filter(project=project)
        serializer = self.get_serializer(files, many=True)
        return Response(serializer.data)


class WorkflowViewSet(viewsets.ModelViewSet):
    """
    工作流视图集
    
    提供工作流的CRUD操作和执行功能
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """
        根据操作类型返回不同的序列化器
        列表视图使用简化版，详情视图使用完整版
        """
        if self.action == 'list':
            return WorkflowListSerializer
        return WorkflowSerializer
    
    def get_queryset(self):
        """
        获取查询集，只返回当前用户项目的工作流
        """
        user = self.request.user
        return Workflow.objects.filter(project__user=user)
    
    def perform_create(self, serializer):
        """
        创建工作流
        """
        # 验证项目是否存在并且属于当前用户
        project_id = self.request.data.get('project')
        if project_id:
            try:
                project = Project.objects.get(id=project_id, user=self.request.user)
            except Project.DoesNotExist:
                raise serializers.ValidationError("项目不存在或无权访问该项目")
                
        serializer.save()
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """
        获取工作流的所有执行记录
        """
        workflow = self.get_object()
        executions = WorkflowExecution.objects.filter(workflow=workflow)
        serializer = WorkflowExecutionSerializer(executions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        执行工作流
        """
        workflow = self.get_object()
        
        # 确保关联项目有运行中的容器
        project = workflow.project
        if not project.container or project.status != 'running':
            return Response(
                {"detail": "无法执行工作流：项目容器未运行"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建执行记录
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            status='pending'
        )
        
        try:
            # 使用工作流引擎管理器创建并启动执行引擎
            engine = WorkflowEngineManager.create_engine(execution.id)
            success = engine.start()
            
            if not success:
                return Response(
                    {"detail": "启动工作流执行失败，请查看执行日志"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 返回执行记录，客户端可以通过轮询执行记录状态了解执行进度
            serializer = WorkflowExecutionSerializer(execution)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"启动工作流执行失败: {str(e)}")
            execution.status = 'failed'
            execution.logs = f"[{timezone.now().isoformat()}] 工作流执行失败: {str(e)}\n"
            execution.save()
            
            return Response(
                {"detail": f"执行工作流失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='project/(?P<project_id>[^/.]+)')
    def list_by_project(self, request, project_id=None):
        """
        按项目列出工作流
        """
        try:
            project = Project.objects.get(id=project_id, user=request.user)
        except Project.DoesNotExist:
            return Response(
                {"status": "error", "message": "找不到指定的项目或没有权限访问"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        workflows = Workflow.objects.filter(project=project)
        serializer = WorkflowListSerializer(workflows, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """
        克隆工作流
        """
        original_workflow = self.get_object()
        
        # 获取新工作流名称，默认为"复制 - 原始名称"
        name = request.data.get('name', f"复制 - {original_workflow.name}")
        
        # 创建新工作流
        new_workflow = Workflow.objects.create(
            project=original_workflow.project,
            name=name,
            description=original_workflow.description,
            definition=original_workflow.definition,
            version=1
        )
        
        serializer = self.get_serializer(new_workflow)
        return Response(serializer.data)


class WorkflowExecutionViewSet(viewsets.ModelViewSet):
    """
    工作流执行记录视图集
    
    提供工作流执行记录的查询和管理
    """
    serializer_class = WorkflowExecutionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        获取查询集，只返回当前用户项目的工作流执行记录
        """
        user = self.request.user
        return WorkflowExecution.objects.filter(workflow__project__user=user)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        获取工作流执行状态
        """
        execution = self.get_object()
        serializer = self.get_serializer(execution)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        取消正在执行的工作流
        """
        execution = self.get_object()
        
        # 只有等待中或运行中的工作流可以取消
        if execution.status not in ['pending', 'running']:
            return Response(
                {"detail": "只能取消等待中或运行中的工作流"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取对应的执行引擎
        engine = WorkflowEngineManager.get_engine(execution.id)
        if engine:
            # 取消执行
            success = engine.cancel()
            if not success:
                return Response(
                    {"detail": "取消工作流执行失败"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            # 找不到执行引擎，直接更新状态
            execution.status = 'canceled'
            execution.end_time = timezone.now()
            execution.logs += f"[{timezone.now().isoformat()}] 工作流执行已取消\n"
            execution.save()
        
        serializer = self.get_serializer(execution)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def components(self, request, pk=None):
        """
        获取工作流执行中各组件的执行记录
        """
        execution = self.get_object()
        component_executions = WorkflowComponentExecution.objects.filter(execution=execution)
        serializer = WorkflowComponentExecutionSerializer(component_executions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='workflow/(?P<workflow_id>[^/.]+)')
    def list_by_workflow(self, request, workflow_id=None):
        """
        按工作流列出执行记录
        """
        try:
            workflow = Workflow.objects.get(id=workflow_id, project__user=request.user)
        except Workflow.DoesNotExist:
            return Response(
                {"status": "error", "message": "找不到指定的工作流或没有权限访问"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        executions = WorkflowExecution.objects.filter(workflow=workflow)
        serializer = self.get_serializer(executions, many=True)
        return Response(serializer.data)
