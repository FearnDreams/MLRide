from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import logging
import subprocess
import os
import signal
import sys
import time
from django.conf import settings
from django.urls import reverse

from .models import JupyterSession
from .serializers import JupyterSessionSerializer
from project.models import Project

# 设置日志
logger = logging.getLogger(__name__)

class JupyterSessionViewSet(viewsets.ModelViewSet):
    """Jupyter会话管理视图集"""
    queryset = JupyterSession.objects.all()
    serializer_class = JupyterSessionSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return JupyterSession.objects.all()
    
    @action(detail=False, methods=['get'])
    def by_project(self, request):
        """根据项目ID获取或创建Jupyter会话"""
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response({"error": "必须提供项目ID"}, status=400)
            
        try:
            # 获取或创建项目的工作目录
            project = Project.objects.get(id=project_id)
            workspace_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'workspaces', f'project_{project_id}')
            os.makedirs(workspace_dir, exist_ok=True)
            
            # 创建Jupyter配置文件目录
            jupyter_conf_dir = os.path.join(workspace_dir, '.jupyter')
            os.makedirs(jupyter_conf_dir, exist_ok=True)
            
            # 创建jupyter_notebook_config.py配置文件
            config_file = os.path.join(jupyter_conf_dir, 'jupyter_notebook_config.py')
            with open(config_file, 'w') as f:
                f.write("""
# Jupyter notebook配置文件
c.NotebookApp.token = ''
c.NotebookApp.password = ''
c.NotebookApp.allow_origin = '*'
c.NotebookApp.allow_remote_access = True
c.NotebookApp.disable_check_xsrf = True
c.NotebookApp.open_browser = False
c.NotebookApp.ip = '127.0.0.1'
c.NotebookApp.port = 8888
c.NotebookApp.tornado_settings = {"headers": {"Content-Security-Policy": "", "X-Frame-Options": ""}}
c.NotebookApp.trust_xheaders = True
c.NotebookApp.allow_root = True
c.NotebookApp.authenticate_prometheus = False
                """)
            
            # 查找或创建会话
            try:
                session = JupyterSession.objects.get(project=project)
                logger.info(f"找到现有会话: ID={session.id}, 状态={session.status}, URL={session.url}")
                
                # 强制重置会话状态使其重新启动
                session.status = 'stopped'
                session.url = None
                session.save()
                logger.info(f"重置会话状态: 状态={session.status}")
                
            except JupyterSession.DoesNotExist:
                session = JupyterSession.objects.create(
                    project=project,
                    status='starting'
                )
                logger.info(f"创建新会话: ID={session.id}, 状态={session.status}")
            
            # 如果会话不是运行状态，启动Jupyter
            if session.status != 'running':
                # 检查是否有旧的进程
                pid_file = os.path.join(workspace_dir, '.jupyter.pid')
                if os.path.exists(pid_file):
                    try:
                        with open(pid_file, 'r') as f:
                            old_pid = int(f.read().strip())
                        os.kill(old_pid, signal.SIGTERM)
                        time.sleep(1)  # 等待进程结束
                        logger.info(f"终止旧进程: PID={old_pid}")
                    except Exception as e:
                        logger.info(f"终止旧进程失败: {str(e)}")
                
                try:
                    # 获取当前Python解释器路径
                    python_path = sys.executable
                    logger.info(f"使用Python解释器: {python_path}")
                    
                    # 检查jupyter是否已安装
                    try:
                        import jupyter
                        jupyter_path = os.path.dirname(jupyter.__file__)
                        logger.info(f"找到Jupyter安装路径: {jupyter_path}")
                    except ImportError:
                        logger.error("Jupyter未安装")
                        return Response({
                            "error": "Jupyter未安装",
                            "details": "请先安装jupyter: pip install jupyter"
                        }, status=500)
                    
                    # 构建启动命令
                    cmd = [
                        python_path,
                        '-m', 'notebook',
                        f'--notebook-dir={workspace_dir}',
                        f'--config={config_file}',  # 使用配置文件
                        '--no-browser',
                    ]
                    
                    logger.info(f"启动命令: {' '.join(cmd)}")
                    
                    # 启动进程
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        start_new_session=True,
                        cwd=workspace_dir  # 设置工作目录
                    )
                    
                    # 等待服务启动
                    time.sleep(3)  # 增加等待时间，确保服务完全启动
                    
                    # 检查进程是否正常启动
                    if process.poll() is not None:
                        # 进程已退出
                        stdout, stderr = process.communicate()
                        error_msg = stderr.decode('utf-8', errors='ignore')
                        logger.error(f"Jupyter启动失败: {error_msg}")
                        session.status = 'error'
                        session.save()
                        return Response({
                            "error": "Jupyter启动失败",
                            "details": error_msg
                        }, status=500)
                    
                    # 保存进程ID
                    with open(pid_file, 'w') as f:
                        f.write(str(process.pid))
                    
                    # 构建代理URL
                    scheme = request.scheme
                    host = request.get_host()
                    proxy_url = f"{scheme}://{host}/api/jupyter/proxy"
                    logger.info(f"代理URL: {proxy_url}")
                    
                    # 更新会话状态
                    session.status = 'running'
                    session.url = proxy_url
                    session.save()
                    
                    logger.info(f"Jupyter服务已启动，PID: {process.pid}, URL: {session.url}")
                    
                except Exception as e:
                    logger.error(f"启动Jupyter失败: {str(e)}")
                    session.status = 'error'
                    session.save()
                    return Response({
                        "error": "启动Jupyter失败",
                        "details": str(e)
                    }, status=500)
            
            serialized_data = self.get_serializer(session).data
            logger.info(f"返回会话数据: {serialized_data}")
            return Response(serialized_data)
            
        except Project.DoesNotExist:
            return Response({"error": "项目不存在"}, status=404)
        except Exception as e:
            logger.error(f"处理Jupyter会话请求失败: {str(e)}")
            return Response({"error": str(e)}, status=500)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止Jupyter会话"""
        session = self.get_object()
        
        try:
            # 获取PID文件路径
            workspace_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'workspaces', f'project_{session.project.id}')
            pid_file = os.path.join(workspace_dir, '.jupyter.pid')
            
            # 如果PID文件存在，尝试终止进程
            if os.path.exists(pid_file):
                try:
                    with open(pid_file, 'r') as f:
                        pid = int(f.read().strip())
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)  # 等待进程结束
                    os.remove(pid_file)
                except:
                    pass  # 忽略错误
            
            # 更新会话状态
            session.status = 'stopped'
            session.url = None
            session.save()
            
            return Response({
                "status": "success",
                "message": "Jupyter会话已停止"
            })
            
        except Exception as e:
            logger.error(f"停止Jupyter会话失败: {str(e)}")
            return Response({
                "status": "error",
                "message": f"停止Jupyter失败: {str(e)}"
            }, status=500)
