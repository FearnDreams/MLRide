from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import secrets

from .models import JupyterSession
from .serializers import JupyterSessionSerializer
from project.models import Project
from container.docker_ops import DockerClient

class JupyterSessionViewSet(viewsets.ModelViewSet):
    """Jupyter会话管理视图集"""
    serializer_class = JupyterSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """只返回当前用户的Jupyter会话"""
        return JupyterSession.objects.filter(project__user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_project(self, request):
        """根据项目ID获取或创建Jupyter会话"""
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response({
                "status": "error",
                "message": "缺少project_id参数"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 验证项目存在且属于当前用户
            project = get_object_or_404(Project, id=project_id, user=request.user)
            
            # 获取或创建会话
            session, created = JupyterSession.objects.get_or_create(project=project)
            
            serializer = self.get_serializer(session)
            return Response({
                "status": "success",
                "data": serializer.data
            })
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"获取Jupyter会话失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """启动Jupyter会话"""
        session = self.get_object()
        project = session.project
        
        # 检查项目状态
        if project.status != 'running':
            return Response({
                "status": "error",
                "message": "项目容器未运行，无法启动Jupyter"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 初始化Docker客户端
        docker_client = DockerClient()
        
        try:
            # 生成新的token
            token = secrets.token_hex(16)
            
            # 在容器中启动Jupyter
            container = docker_client.get_container(project.container.container_id)
            
            # 首先检查是否已有Jupyter实例在运行
            exec_result = container.exec_run("pkill -f jupyter")
            
            # 启动新的Jupyter实例
            exec_result = container.exec_run(
                cmd=f"jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token={token} --notebook-dir=/workspace",
                detach=True
            )
            
            # 更新会话信息
            session.token = token
            session.status = 'running'
            session.save()
            
            return Response({
                "status": "success",
                "message": "Jupyter会话已启动",
                "data": {
                    "token": token,
                    "session_id": session.id
                }
            })
        except Exception as e:
            session.status = 'error'
            session.save()
            return Response({
                "status": "error",
                "message": f"启动Jupyter失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止Jupyter会话"""
        session = self.get_object()
        project = session.project
        
        # 检查项目状态
        if project.status != 'running':
            return Response({
                "status": "error",
                "message": "项目容器未运行，无法操作Jupyter"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 初始化Docker客户端
            docker_client = DockerClient()
            container = docker_client.get_container(project.container.container_id)
            
            # 在容器中停止Jupyter进程
            exec_result = container.exec_run("pkill -f jupyter")
            
            # 更新会话状态
            session.status = 'stopped'
            session.token = None
            session.save()
            
            return Response({
                "status": "success",
                "message": "Jupyter会话已停止"
            })
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"停止Jupyter失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
