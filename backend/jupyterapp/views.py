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
import random
from django.conf import settings
from django.urls import reverse

from .models import JupyterSession
from .serializers import JupyterSessionSerializer
from project.models import Project

# 设置日志
logger = logging.getLogger(__name__)

# 定义端口范围
JUPYTER_PORT_MIN = 8801
JUPYTER_PORT_MAX = 9000

class JupyterSessionViewSet(viewsets.ModelViewSet):
    """Jupyter会话管理视图集"""
    queryset = JupyterSession.objects.all()
    serializer_class = JupyterSessionSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return JupyterSession.objects.all()
    
    def _clean_expired_sessions(self):
        """清理可能已经过期但状态未更新的会话"""
        logger.info("检查并清理过期会话...")
        try:
            # 获取所有标记为运行中的会话
            running_sessions = JupyterSession.objects.filter(status='running')
            
            for session in running_sessions:
                # 检查PID是否存在
                if session.process_id:
                    try:
                        # Windows上使用tasklist检查进程，Linux/Mac上使用os.kill
                        pid_exists = False
                        if os.name == 'nt':  # Windows
                            result = subprocess.run(['tasklist', '/FI', f'PID eq {session.process_id}'], 
                                                 capture_output=True, text=True)
                            pid_exists = str(session.process_id) in result.stdout
                        else:  # Unix-like
                            try:
                                # 发送信号0进行检查，但捕获任何错误
                                os.kill(session.process_id, 0)
                                pid_exists = True
                            except OSError:
                                pid_exists = False
                        
                        if not pid_exists:
                            # 进程不存在，更新会话状态
                            logger.info(f"会话ID={session.id}的进程PID={session.process_id}不存在，清理会话状态")
                            session.status = 'stopped'
                            session.process_id = None
                            session.save()
                    except Exception as e:
                        # 检查失败，记录错误但继续处理
                        logger.error(f"检查会话ID={session.id}的进程PID={session.process_id}状态时出错: {str(e)}")
            
            logger.info("会话清理完成")
        except Exception as e:
            logger.error(f"清理过期会话时出错: {str(e)}")
    
    def _get_available_port(self):
        """获取可用的Jupyter端口"""
        # 获取已使用的端口
        used_ports = set(JupyterSession.objects.exclude(port__isnull=True).values_list('port', flat=True))
        
        # 记录已分配的端口
        logger.info(f"当前已分配的端口: {list(used_ports)}")
        
        # 从可用端口范围中选择未使用的端口
        available_ports = set(range(JUPYTER_PORT_MIN, JUPYTER_PORT_MAX + 1)) - used_ports
        if not available_ports:
            # 如果所有端口都被占用，选择一个随机端口
            random_port = random.randint(JUPYTER_PORT_MIN, JUPYTER_PORT_MAX)
            logger.warning(f"所有端口均已分配，随机选择端口: {random_port}")
            return random_port
        
        # 返回第一个可用端口
        port = min(available_ports)
        logger.info(f"分配新端口: {port}")
        return port
    
    @action(detail=False, methods=['get'])
    def by_project(self, request):
        """根据项目ID获取或创建Jupyter会话"""
        # 清理可能已经过期的会话
        self._clean_expired_sessions()
        
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
            
            # 查找或创建会话
            try:
                session = JupyterSession.objects.get(project=project)
                logger.info(f"找到现有会话: ID={session.id}, 状态={session.status}, URL={session.url}")
                
                # 如果会话已存在但没有端口号，分配一个新端口
                if session.port is None:
                    session.port = self._get_available_port()
                    session.save()
                
                # 只有当会话不是运行状态时，才重置它
                if session.status != 'running':
                    # 强制重置会话状态使其重新启动
                    session.status = 'stopped'
                    session.url = None
                    session.workspace_dir = workspace_dir  # 设置工作目录
                    session.process_id = None  # 清除进程ID
                    session.save()
                    logger.info(f"重置会话状态: 状态={session.status}, 端口={session.port}")
                else:
                    # 如果会话已在运行，确保工作目录是正确的
                    if session.workspace_dir != workspace_dir:
                        session.workspace_dir = workspace_dir
                        session.save()
                    logger.info(f"会话已在运行中，保持状态不变: 状态={session.status}, 端口={session.port}")
                
            except JupyterSession.DoesNotExist:
                # 为新会话分配端口
                port = self._get_available_port()
                session = JupyterSession.objects.create(
                    project=project,
                    status='starting',
                    workspace_dir=workspace_dir,  # 设置工作目录
                    port=port  # 设置端口
                )
                logger.info(f"创建新会话: ID={session.id}, 状态={session.status}, 端口={session.port}")
            
            # 创建jupyter_notebook_config.py配置文件（使用项目特定端口）
            config_file = os.path.join(jupyter_conf_dir, 'jupyter_notebook_config.py')
            # 将工作目录路径转为绝对路径并处理Windows路径分隔符
            abs_workspace_dir = os.path.abspath(workspace_dir).replace('\\', '\\\\')
            logger.info(f"使用工作目录绝对路径: {abs_workspace_dir}")
            
            with open(config_file, 'w') as f:
                f.write(f"""
# Jupyter notebook配置文件
c = get_config()  # 获取配置对象
c.ServerApp.token = ''
c.ServerApp.password = ''
c.ServerApp.allow_origin = '*'
c.ServerApp.allow_remote_access = True
c.ServerApp.disable_check_xsrf = True
c.ServerApp.open_browser = False
c.ServerApp.ip = '0.0.0.0'  # 监听所有网络接口
c.ServerApp.port = {session.port}  # 使用项目特定端口
c.ServerApp.tornado_settings = {{"headers": {{"Content-Security-Policy": "", "X-Frame-Options": ""}}}}
c.ServerApp.trust_xheaders = True
c.ServerApp.allow_root = True
c.ServerApp.root_dir = "{abs_workspace_dir}"  # 使用绝对路径确保正确加载工作目录

# 旧版本兼容配置（不设置IP，避免重复）
c.NotebookApp.token = ''
c.NotebookApp.password = ''
c.NotebookApp.allow_origin = '*'
c.NotebookApp.allow_remote_access = True
c.NotebookApp.disable_check_xsrf = True
c.NotebookApp.open_browser = False
c.NotebookApp.port = {session.port}  # 使用项目特定端口
                """)
            
            # 如果会话不是运行状态，启动Jupyter
            if session.status != 'running':
                # 确保工作目录存在
                if not os.path.exists(workspace_dir):
                    os.makedirs(workspace_dir, exist_ok=True)
                    logger.info(f"创建工作目录: {workspace_dir}")
                
                # 检查是否有旧的进程
                pid_file = os.path.join(workspace_dir, '.jupyter.pid')
                if os.path.exists(pid_file):
                    try:
                        with open(pid_file, 'r') as f:
                            old_pid_str = f.read().strip()
                            if old_pid_str and old_pid_str.isdigit():
                                old_pid = int(old_pid_str)
                                # 检查进程是否存在
                                try:
                                    if os.name == 'nt':  # Windows
                                        result = subprocess.run(['tasklist', '/FI', f'PID eq {old_pid}'], 
                                                            capture_output=True, text=True)
                                        if str(old_pid) in result.stdout:
                                            os.kill(old_pid, signal.SIGTERM)
                                            time.sleep(1)  # 等待进程结束
                                            logger.info(f"终止旧进程: PID={old_pid}")
                                    else:  # Unix-like
                                        os.kill(old_pid, signal.SIGTERM)
                                        time.sleep(1)  # 等待进程结束
                                        logger.info(f"终止旧进程: PID={old_pid}")
                                except Exception as e:
                                    logger.info(f"终止旧进程失败或进程已不存在: {str(e)}")
                        # 无论成功与否，删除旧的PID文件
                        os.remove(pid_file)
                    except Exception as e:
                        logger.info(f"读取或删除PID文件失败: {str(e)}")
                
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
                        f'--port={session.port}',  # 显式指定端口号
                        '--ip=0.0.0.0',  # 绑定到所有接口，使其可以从外部访问
                        '--NotebookApp.use_redirect_file=False',  # 避免生成重定向文件
                        '--NotebookApp.terminals_enabled=True',  # 启用终端
                        '--NotebookApp.allow_remote_access=True',  # 允许远程访问
                        '--ServerApp.allow_remote_access=True',  # 允许远程访问(新版本)
                    ]
                    
                    logger.info(f"启动命令: {' '.join(cmd)}")
                    
                    # 设置日志文件
                    stdout_log = os.path.join(workspace_dir, 'jupyter_stdout.log')
                    stderr_log = os.path.join(workspace_dir, 'jupyter_stderr.log')
                    
                    # 启动进程
                    process = subprocess.Popen(
                        cmd,
                        stdout=open(stdout_log, 'w'),
                        stderr=open(stderr_log, 'w'),
                        start_new_session=True,
                        cwd=workspace_dir  # 设置工作目录
                    )
                    
                    # 等待服务启动
                    time.sleep(5)  # 增加等待时间，确保服务完全启动
                    
                    # 检查进程是否正常启动
                    if process.poll() is not None:
                        # 进程已退出
                        error_msg = "未知错误"
                        
                        # 等待一下确保日志文件写入完成
                        time.sleep(0.5)
                        
                        # 读取错误日志
                        try:
                            if os.path.exists(stderr_log) and os.path.getsize(stderr_log) > 0:
                                with open(stderr_log, 'r', encoding='utf-8', errors='ignore') as f:
                                    error_log = f.read()
                                    if error_log:
                                        # 截取最有用的部分（通常是前1000个字符）
                                        error_msg = error_log[:1000] + ("..." if len(error_log) > 1000 else "")
                            else:
                                logger.error("错误日志文件不存在或为空")
                        except Exception as e:
                            logger.error(f"读取错误日志失败: {str(e)}")
                        
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
                    
                    # 生成令牌（用于身份验证）
                    token = f"project_{project.id}_{int(time.time())}"
                    
                    # 构建代理URL
                    scheme = request.scheme
                    host = request.get_host()
                    base_url = f"{scheme}://{host}"
                    
                    # 两种URL: 代理URL和直接URL
                    proxy_url = f"{base_url}/api/jupyter/proxy/{project.id}/"
                    direct_url = f"http://localhost:{session.port}/tree"  # 直接访问的URL
                    
                    logger.info(f"代理URL: {proxy_url}")
                    logger.info(f"直接URL: {direct_url}")
                    
                    # 保存两种URL
                    url_to_use = proxy_url  # 默认使用代理URL
                    
                    # 根据请求来源决定使用哪种URL
                    referer = request.META.get('HTTP_REFERER', '')
                    logger.info(f"请求来源: {referer}")
                    
                    # 创建预热请求，加速Jupyter启动
                    try:
                        # 预热请求可能会失败，但不会影响主流程
                        import threading
                        def warmup_request():
                            try:
                                time.sleep(2)  # 等待Jupyter服务启动
                                # 发送预热请求到Jupyter服务
                                import requests
                                warmup_url = f"http://127.0.0.1:{session.port}/api/terminals?1=1"
                                logger.info(f"发送预热请求: {warmup_url}")
                                resp = requests.get(warmup_url, timeout=3)
                                logger.info(f"预热请求成功: 状态码={resp.status_code}")
                                
                                # 尝试多次预热请求以确保页面加载完全
                                warmup_url2 = f"http://127.0.0.1:{session.port}/tree"
                                logger.info(f"发送第二次预热请求: {warmup_url2}")
                                resp2 = requests.get(warmup_url2, timeout=3)
                                logger.info(f"第二次预热请求成功: 状态码={resp2.status_code}")
                            except Exception as e:
                                logger.info(f"预热请求失败: {str(e)}")
                        
                        # 在后台线程中发送预热请求
                        threading.Thread(target=warmup_request).start()
                    except Exception as e:
                        logger.warning(f"创建预热请求失败: {str(e)}")
                    
                    # 更新会话状态
                    session.status = 'running'
                    session.url = url_to_use
                    session.token = token  # 设置令牌
                    session.process_id = process.pid  # 设置进程ID
                    session.save()
                    
                    logger.info(f"Jupyter服务已启动，PID: {process.pid}, 端口: {session.port}, URL: {session.url}")
                    
                except Exception as e:
                    logger.error(f"启动Jupyter失败: {str(e)}")
                    session.status = 'error'
                    session.save()
                    return Response({
                        "error": "启动Jupyter失败",
                        "details": str(e)
                    }, status=500)
            
            serialized_data = self.get_serializer(session).data
            
            # 添加直接访问URL，确保使用正确的端口号
            direct_access_url = f"http://localhost:{session.port}/tree"
            serialized_data['direct_access_url'] = direct_access_url
            
            # 记录正确的直接访问URL
            logger.info(f"直接访问URL: {direct_access_url}")
            
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
            workspace_dir = session.workspace_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'workspaces', f'project_{session.project.id}')
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
            session.process_id = None  # 清除进程ID
            # 不要清除端口，保持端口分配的稳定性
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
