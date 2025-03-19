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
            # 清理project_id，移除非数字字符
            cleaned_project_id = ''.join(filter(str.isdigit, str(project_id)))
            if not cleaned_project_id:
                return Response({
                    "status": "error",
                    "message": f"无效的项目ID: {project_id}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 验证项目存在且属于当前用户
            project = get_object_or_404(Project, id=cleaned_project_id, user=request.user)
            
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
        
        try:
            # 初始化Docker客户端
            docker_client = DockerClient()
            container = docker_client.get_container(project.container.container_id)
            
            # 检查容器中的Jupyter进程
            exec_result = container.exec_run(
                cmd="pgrep -f 'jupyter-notebook'",
                privileged=True
            )
            
            if exec_result.exit_code != 0:
                # 如果没有运行的Jupyter进程，启动一个新实例
                
                # 首先创建禁用认证的配置文件
                container.exec_run(
                    cmd=[
                        "bash", "-c",
                        "mkdir -p /root/.jupyter && echo 'c.NotebookApp.token = \"\"' > /root/.jupyter/jupyter_notebook_config.py && "
                        "echo 'c.NotebookApp.password = \"\"' >> /root/.jupyter/jupyter_notebook_config.py && "
                        "echo 'c.NotebookApp.allow_origin = \"*\"' >> /root/.jupyter/jupyter_notebook_config.py && "
                        "echo 'c.NotebookApp.allow_remote_access = True' >> /root/.jupyter/jupyter_notebook_config.py && "
                        "echo 'c.NotebookApp.disable_check_xsrf = True' >> /root/.jupyter/jupyter_notebook_config.py && "
                        "echo 'c.NotebookApp.tornado_settings = {\"headers\": {\"Content-Security-Policy\": \"\", \"X-Frame-Options\": \"\"}}' >> /root/.jupyter/jupyter_notebook_config.py && "
                        "echo 'c.JupyterApp.answer_yes = True' >> /root/.jupyter/jupyter_notebook_config.py && "
                        "echo 'c.NotebookApp.open_browser = False' >> /root/.jupyter/jupyter_notebook_config.py"
                    ],
                    privileged=True
                )
                
                # 启动Jupyter，使用新配置
                exec_result = container.exec_run(
                    cmd=[
                        "jupyter", "notebook",
                        "--ip=0.0.0.0",
                        "--port=8888",
                        "--no-browser",
                        "--allow-root",
                        "--notebook-dir=/workspace"
                    ],
                    detach=True,
                    privileged=True
                )
            
                # 保存token到会话（为了保持兼容性）
                session.token = ""
            else:
                # 如果已经有Jupyter进程，使用空token保持一致性
                session.token = ""
                
                # 确保Jupyter使用空token配置
                try:
                    # 先创建配置文件
                    container.exec_run(
                        cmd=[
                            "bash", "-c",
                            "mkdir -p /root/.jupyter && echo 'c.NotebookApp.token = \"\"' > /root/.jupyter/jupyter_notebook_config.py && "
                            "echo 'c.NotebookApp.password = \"\"' >> /root/.jupyter/jupyter_notebook_config.py && "
                            "echo 'c.NotebookApp.allow_origin = \"*\"' >> /root/.jupyter/jupyter_notebook_config.py && "
                            "echo 'c.NotebookApp.allow_remote_access = True' >> /root/.jupyter/jupyter_notebook_config.py && "
                            "echo 'c.NotebookApp.disable_check_xsrf = True' >> /root/.jupyter/jupyter_notebook_config.py && "
                            "echo 'c.NotebookApp.tornado_settings = {\"headers\": {\"Content-Security-Policy\": \"\", \"X-Frame-Options\": \"\"}}' >> /root/.jupyter/jupyter_notebook_config.py && "
                            "echo 'c.JupyterApp.answer_yes = True' >> /root/.jupyter/jupyter_notebook_config.py && "
                            "echo 'c.NotebookApp.open_browser = False' >> /root/.jupyter/jupyter_notebook_config.py"
                        ],
                        privileged=True
                    )
                
                    # 尝试重启Jupyter进程以确保使用新配置
                    container.exec_run("pkill -f jupyter", privileged=True)
                    # 启动带配置文件的Jupyter
                    exec_result = container.exec_run(
                        cmd=[
                            "jupyter", "notebook",
                            "--ip=0.0.0.0",
                            "--port=8888",
                            "--no-browser",
                            "--allow-root",
                            "--notebook-dir=/workspace"
                        ],
                        detach=True,
                        privileged=True
                    )
                except Exception as e:
                    # 如果重启失败，记录错误但继续尝试使用现有进程
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"重启Jupyter进程失败: {str(e)}")
            
            # 更新会话状态
            session.status = 'running'
            session.save()
            
            return Response({
                "status": "success",
                "message": "Jupyter会话已启动",
                "data": {
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
            # 如果项目已经不在运行状态，直接更新会话状态
            session.status = 'stopped'
            session.token = ""
            session.save()
            return Response({
                "status": "success",
                "message": "项目未运行，会话已标记为停止"
            })
        
        try:
            # 初始化Docker客户端
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"尝试停止Jupyter会话, ID: {session.id}, 项目: {project.id}")
            
            docker_client = DockerClient()
            
            # 确保容器实例存在
            if not project.container:
                logger.warning(f"项目 {project.id} 没有关联的容器")
                session.status = 'stopped'
                session.token = ""
                session.save()
                return Response({
                    "status": "success",
                    "message": "项目没有关联容器，会话已标记为停止"
                })
            
            # 获取容器ID
            container_id = project.container.container_id
            if not container_id:
                logger.warning(f"项目 {project.id} 的容器没有ID")
                session.status = 'stopped'
                session.token = ""
                session.save()
                return Response({
                    "status": "success",
                    "message": "容器ID不存在，会话已标记为停止"
                })
                
            # 尝试获取容器对象
            try:
                container = docker_client.get_container(container_id)
                
                # 在容器中停止Jupyter进程
                logger.info(f"在容器 {container_id} 中执行pkill命令")
                exec_result = container.exec_run("pkill -f jupyter", privileged=True)
                logger.info(f"pkill命令执行结果: 退出码 {exec_result.exit_code}")
                
                # 无论命令执行成功与否，都更新会话状态
                session.status = 'stopped'
                session.token = ""
                session.save()
                
                return Response({
                    "status": "success",
                    "message": "Jupyter会话已停止"
                })
            except Exception as e:
                logger.error(f"操作容器 {container_id} 失败: {str(e)}")
                # 即使容器操作失败，也更新会话状态
                session.status = 'stopped'
                session.token = ""
                session.save()
                return Response({
                    "status": "success",
                    "message": f"容器操作失败，但会话已标记为停止: {str(e)}"
                })
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"停止Jupyter会话失败: {str(e)}\n{error_details}")
            
            # 即使发生错误，也尝试更新会话状态
            try:
                session.status = 'error'
                session.save()
            except:
                pass
                
            return Response({
                "status": "error",
                "message": f"停止Jupyter失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
