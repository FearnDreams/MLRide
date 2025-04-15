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
            # 获取项目信息
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
                
                # 检查该项目是否关联了容器和Docker镜像
                use_docker = False
                docker_client = None
                
                if project.container and project.image and project.image.image_tag:
                    logger.info(f"项目已关联容器ID={project.container.container_id}和镜像={project.image.image_tag}")
                    # 尝试使用Docker启动Jupyter
                    try:
                        from container.docker_ops import DockerClient
                        docker_client = DockerClient()
                        
                        # 检查容器状态
                        container_id = project.container.container_id
                        logger.info(f"检查容器状态: ID={container_id}")
                        
                        # 获取容器对象
                        container_info = docker_client.get_container(container_id)
                        
                        # 使用对象属性检查状态
                        if container_info and container_info.status == 'running':
                            logger.info(f"容器已在运行中: ID={container_id}")
                            use_docker = True
                        else:
                            # 如果容器存在但没有运行，尝试启动它
                            logger.info(f"容器存在但未运行，尝试启动: ID={container_id}")
                            docker_client.start_container(container_id)
                            time.sleep(5)  # 等待容器启动
                            
                            # 再次检查状态，刷新容器对象
                            container_info = docker_client.get_container(container_id)
                            if container_info and container_info.status == 'running':
                                logger.info(f"成功启动容器: ID={container_id}")
                                use_docker = True
                            else:
                                logger.warning(f"无法启动容器: ID={container_id}")
                    except Exception as e:
                        logger.error(f"检查/启动容器时出错: {str(e)}")
                        
                if use_docker and docker_client:
                    try:
                        logger.info("使用Docker容器启动Jupyter")
                        
                        # 检查容器是否安装了jupyter
                        jupyter_check = docker_client.check_jupyter_in_container(project.container.container_id)
                        if not jupyter_check.get('installed', False):
                            logger.warning("容器中没有安装Jupyter，尝试安装")
                            
                            # 在容器中安装jupyter
                            install_cmd = f"pip install --no-cache-dir notebook ipykernel"
                            docker_client.client.containers.get(project.container.container_id).exec_run(
                                install_cmd, 
                                privileged=True,
                                stream=False
                            )
                            
                            # 再次检查是否安装成功
                            jupyter_check = docker_client.check_jupyter_in_container(project.container.container_id)
                            if not jupyter_check.get('installed', False):
                                logger.error("无法在容器中安装Jupyter")
                                raise Exception("无法在容器中安装Jupyter")
                        
                        # 安装和注册内核
                        logger.info("检查容器内是否有已注册的内核")
                        kernel_name = f"python-docker-{project.id}"
                        
                        # 获取当前内核列表
                        current_kernels = jupyter_check.get('kernels', [])
                        logger.info(f"当前内核列表 (来自 check_jupyter_in_container): {current_kernels}")
                        
                        # 检查目标内核是否已存在
                        kernel_exists = any(kernel_name in kernel_spec for kernel_spec in current_kernels)
                        
                        if not kernel_exists:
                            logger.info(f"未找到目标内核 {kernel_name}，开始安装")
                            kernel_result = docker_client.install_jupyter_kernel_in_container(
                                project.container.container_id,
                                kernel_name # 使用我们定义的内核名称
                            )
                            
                            if kernel_result.get('success', False):
                                registered_info = kernel_result.get('registered_kernel_info')
                                if registered_info:
                                     logger.info(f"内核安装并注册成功: {registered_info}")
                                else:
                                    logger.warning("内核安装声称成功，但在列表确认时失败")
                                    # 尝试再次检查内核列表
                                    jupyter_check_after_install = docker_client.check_jupyter_in_container(project.container.container_id)
                                    logger.info(f"安装后再次检查内核列表: {jupyter_check_after_install.get('kernels', [])}")
                            else:
                                logger.error(f"内核安装失败: {kernel_result.get('error')}")
                                # 即使安装失败，也继续尝试启动Jupyter，可能已有其他内核
                        else:
                            logger.info(f"目标内核 {kernel_name} 已存在于容器中")
                        
                        # 复制jupyter配置文件到容器
                        container_config_dir = "/root/.jupyter"
                        
                        # 为确保配置目录存在，先创建
                        docker_client.client.containers.get(project.container.container_id).exec_run(
                            f"mkdir -p {container_config_dir}",
                            privileged=True
                        )
                        
                        # 生成适用于容器内的配置
                        kernel_name = f"python-docker-{project.id}"
                        # 定义需要 Jupyter 扫描的内核目录 (移除，因为配置项不被识别)
                        # kernel_dirs = ... # 不再需要此行
                        container_config = f"""
# Jupyter notebook配置文件
c = get_config()
c.ServerApp.token = ''
c.ServerApp.password = ''
c.ServerApp.allow_origin = '*'
c.ServerApp.allow_remote_access = True
c.ServerApp.disable_check_xsrf = True
c.ServerApp.open_browser = False
c.ServerApp.ip = '0.0.0.0'
c.ServerApp.port = 8888
c.ServerApp.tornado_settings = {{"headers": {{"Content-Security-Policy": "", "X-Frame-Options": ""}}}}
c.ServerApp.trust_xheaders = True
c.ServerApp.allow_root = True
c.ServerApp.root_dir = "/workspace"

# 确保使用容器内的Python环境作为默认内核
c.MultiKernelManager.default_kernel_name = "{kernel_name}"
# c.MultiKernelManager.ensure_native_kernel = False # 移除，因为配置项不被识别

# 显式指定内核查找目录 (移除)
# c.KernelSpecManager.kernel_dirs = ... # 移除插值

# 旧版本兼容配置 (保持这些，因为日志中有相关警告)
c.NotebookApp.token = ''
c.NotebookApp.password = ''
c.NotebookApp.allow_origin = '*'
c.NotebookApp.allow_remote_access = True
c.NotebookApp.disable_check_xsrf = True
c.NotebookApp.open_browser = False
c.NotebookApp.port = 8888
"""
                        
                        # 将配置写入临时文件，然后复制到容器
                        config_temp_file = os.path.join(workspace_dir, 'jupyter_container_config.py')
                        with open(config_temp_file, 'w') as f:
                            f.write(container_config)
                        
                        docker_client.copy_to_container(
                            project.container.container_id,
                            config_temp_file,
                            f"{container_config_dir}/jupyter_notebook_config.py"
                        )
                        
                        # 清理旧的内核缓存 (如果存在) - 尝试取消注释解决内核识别问题
                        clear_cache_cmd = "rm -rf /root/.local/share/jupyter/kernels/* || true"
                        logger.info(f"执行清理内核缓存命令: {clear_cache_cmd}")
                        docker_client.client.containers.get(project.container.container_id).exec_run(
                            ["bash", "-c", clear_cache_cmd],
                            privileged=True
                        )
                        
                        # --- 再次确认 Jupyter 命令路径 (改回 which) ---
                        jupyter_path_cmd = "which jupyter" # 改回使用 which
                        logger.info(f"执行命令查找 Jupyter 路径: {jupyter_path_cmd}")
                        # 添加 environment 参数
                        jupyter_path_result = docker_client.client.containers.get(project.container.container_id).exec_run(
                            jupyter_path_cmd,
                            environment={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}
                        )
                        
                        # 检查退出码
                        if jupyter_path_result.exit_code != 0:
                            # 尝试获取更详细的错误输出
                            err_output = jupyter_path_result.output.decode('utf-8', errors='ignore').strip()
                            logger.error(f"在容器中查找 Jupyter 命令 ('which jupyter') 失败 (exit code: {jupyter_path_result.exit_code}), Output: {err_output}")
                            # which 失败通常是 exit code 1 (找不到)
                            if jupyter_path_result.exit_code == 1:
                                raise Exception("Jupyter command not found using 'which'.")
                            else:
                                # 保留对 126 的检查以防万一
                                raise Exception(f"Failed to find Jupyter command using 'which' (exit code {jupyter_path_result.exit_code}). Check permissions or PATH.")
                        
                        # 获取并清理路径
                        jupyter_path = jupyter_path_result.output.decode('utf-8', errors='ignore').strip()
                        
                        # 验证路径是否有效 (例如不为空，不包含换行或异常字符)
                        if not jupyter_path or '\n' in jupyter_path or not jupyter_path.startswith('/'):
                            logger.error(f"'which jupyter' 返回的路径无效: '{jupyter_path}'")
                            raise Exception(f"Invalid path returned by 'which jupyter': {jupyter_path}")
                            
                        logger.info(f"确认 Jupyter 命令路径: {jupyter_path}")
                        
                        # --- 添加执行权限 (保留) ---
                        chmod_cmd = f"chmod +x {jupyter_path}"
                        logger.info(f"为 Jupyter 添加执行权限: {chmod_cmd}")
                        chmod_result = docker_client.client.containers.get(project.container.container_id).exec_run(
                            ["bash", "-c", chmod_cmd],
                            privileged=True
                        )
                        if chmod_result.exit_code != 0:
                            # 记录警告但继续，也许它已经有权限了
                            chmod_output = chmod_result.output.decode('utf-8', errors='ignore')[:200]
                            logger.warning(f"chmod +x 命令失败 (Exit Code: {chmod_result.exit_code}), Output: {chmod_output}. 尝试继续...")
                        else:
                            logger.info("成功为 Jupyter 添加执行权限")
                        
                        # 在容器中启动Jupyter
                        # 使用 --debug 获取更详细的日志
                        # 注意：不再重定向到 /var/log/jupyter.log，直接让其输出到容器 stdout/stderr
                        # 修正命令构造，确保 jupyter_path 是干净的
                        jupyter_cmd = f"{jupyter_path.strip()} notebook --config=/root/.jupyter/jupyter_notebook_config.py --allow-root --debug"
                        logger.info(f"准备执行Jupyter启动命令: {jupyter_cmd}")
                        
                        # 使用 bash -c 执行，并且后台运行 (依然 detach)
                        logger.info(f"实际执行的后台命令: nohup {jupyter_cmd} &") # 打印实际执行的命令
                        exec_result = docker_client.client.containers.get(project.container.container_id).exec_run(
                            ["bash", "-c", f"nohup {jupyter_cmd} &"] , # 使用 nohup 和 & 在后台运行
                            detach=False, # detach=False 配合 & 使用，让 exec_run 等待 bash 命令结束，而不是等待 nohup 的后台进程
                            stream=False,
                            privileged=True,
                            environment={
                                "JUPYTER_CONFIG_DIR": "/root/.jupyter",
                                "PYTHONPATH": "/usr/local/bin:/usr/bin:/bin", # 可能需要更全的PATH
                                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", # 明确设置PATH
                                "HOME": "/root", # 显式设置HOME可能有助于找到.local
                                "PYTHONUNBUFFERED": "1" # 确保日志立即输出
                            }
                        )
                        
                        # 检查 exec_run 的退出码
                        if exec_result.exit_code != 0:
                             log_output_on_error = exec_result.output.decode('utf-8', errors='ignore')[:500]
                             logger.error(f"执行后台启动命令失败, Exit Code: {exec_result.exit_code}, Output: {log_output_on_error}")
                             raise Exception(f"Failed to execute jupyter start command, exit code: {exec_result.exit_code}") # 抛出异常以便捕获
                        else:
                            logger.info(f"在容器中启动Jupyter的后台命令已成功执行 (exec_run exit_code=0)")
                        
                        # 等待Jupyter启动 (给后台进程一点时间)
                        time.sleep(8)
                        
                        # --- 直接获取容器日志 ---
                        try:
                            container_obj = docker_client.client.containers.get(project.container.container_id)
                            container_logs = container_obj.logs(tail=100, stdout=True, stderr=True)
                            log_output = container_logs.decode('utf-8', errors='ignore').strip()
                            if log_output:
                                logger.info(f"容器最新日志 (stdout/stderr):\n------ START CONTAINER LOG ------\n{log_output}\n------ END CONTAINER LOG ------")
                            else:
                                logger.warning("无法获取到容器的最新日志")
                        except Exception as log_e:
                            logger.error(f"获取容器日志时出错: {str(log_e)}")

                        # 获取容器端口映射 (需要刷新容器对象)
                        container_info = docker_client.get_container(project.container.container_id)
                        port_mappings = container_info.attrs.get('NetworkSettings', {}).get('Ports', {})
                        
                        # 查找jupyter端口映射
                        host_port = None
                        jupyter_container_port = '8888/tcp' # Jupyter默认是TCP
                        if jupyter_container_port in port_mappings and port_mappings[jupyter_container_port]:
                             host_port = port_mappings[jupyter_container_port][0].get('HostPort')
                        
                        if not host_port:
                            # 如果没有找到映射，使用我们自己分配的端口
                            host_port = str(session.port)
                            logger.info(f"未找到端口映射，将使用会话端口 {host_port} 并尝试重新绑定")
                            
                            # 尝试停止并重新启动容器以绑定端口
                            try:
                                docker_client.client.api.stop(project.container.container_id)
                                time.sleep(2)
                                docker_client.client.api.start(
                                    project.container.container_id,
                                    port_bindings={8888: session.port}
                                )
                                time.sleep(5)
                                logger.info(f"容器已重启并尝试绑定端口 {session.port}")
                            except Exception as restart_e:
                                logger.error(f"重启容器以绑定端口时出错: {str(restart_e)}")
                                # 如果重启失败，继续尝试使用原始端口
                                host_port = str(session.port)
                        
                        logger.info(f"容器Jupyter端口映射: 容器内8888 -> 主机 {host_port}")
                        
                        # 构建访问URL
                        scheme = request.scheme
                        host = request.get_host()
                        base_url = f"{scheme}://{host}"
                        
                        # 使用端口映射构建URL
                        proxy_url = f"{base_url}/api/jupyter/proxy/{project.id}/"
                        direct_url = f"http://localhost:{host_port}/tree"
                        
                        logger.info(f"Docker容器中的Jupyter访问URL: 代理={proxy_url}, 直接={direct_url}")
                        
                        # 更新会话状态
                        session.status = 'running'
                        session.url = proxy_url
                        session.process_id = None  # 容器中运行，不需要进程ID
                        session.save()
                        
                        # 更新项目和容器状态
                        project.status = 'running'
                        project.save()
                        
                        if project.container:
                            project.container.status = 'running'
                            project.container.save()
                        
                        # 获取容器内的内核信息
                        try:
                            # 检查容器内的内核信息
                            kernel_check_cmd = "jupyter kernelspec list --json"
                            kernel_info_result = docker_client.client.containers.get(project.container.container_id).exec_run(
                                kernel_check_cmd
                            )
                            kernel_info = {}
                            
                            if kernel_info_result.exit_code == 0:
                                import json
                                kernel_output = kernel_info_result.output.decode('utf-8', errors='ignore')
                                try:
                                    kernel_data = json.loads(kernel_output)
                                    kernel_name = f"python-docker-{project.id}"
                                    if kernel_name in kernel_data.get('kernelspecs', {}):
                                        spec_info = kernel_data['kernelspecs'][kernel_name]
                                        kernel_info = {
                                            'name': kernel_name,
                                            'display_name': spec_info.get('spec', {}).get('display_name', f'Docker Python ({project.id})')
                                        }
                                    else:
                                        # 如果找不到特定内核，使用第一个Python内核
                                        for k_name, k_info in kernel_data.get('kernelspecs', {}).items():
                                            if 'python' in k_name.lower():
                                                kernel_info = {
                                                    'name': k_name,
                                                    'display_name': k_info.get('spec', {}).get('display_name', 'Docker Python')
                                                }
                                                break
                                except json.JSONDecodeError:
                                    logger.warning(f"无法解析内核JSON数据: {kernel_output[:200]}")
                            
                            logger.info(f"获取到的内核信息: {kernel_info}")
                        except Exception as e:
                            logger.warning(f"获取内核信息失败: {str(e)}")
                            kernel_info = {}
                        
                        # 成功使用Docker启动Jupyter
                        serialized_data = self.get_serializer(session).data
                        serialized_data['direct_access_url'] = direct_url
                        serialized_data['running_in_docker'] = True # 确保这里设置为 True
                        serialized_data['docker_image'] = project.image.image_tag
                        
                        # 添加内核信息
                        if kernel_info:
                            serialized_data['kernel_info'] = kernel_info
                        else: # 如果获取失败，尝试给一个默认值
                            serialized_data['kernel_info'] = {'name': kernel_name, 'display_name': f'Docker Image ({project.id})'}
                        
                        logger.info(f"成功在Docker容器中启动Jupyter并返回会话数据: {serialized_data}")
                        return Response(serialized_data)
                    except Exception as e:
                        logger.error(f"使用Docker启动Jupyter失败: {str(e)}")
                        # 如果Docker启动失败，回退到本地启动
                        logger.info("尝试回退到本地启动Jupyter")
                
                # 如果没有使用Docker或Docker启动失败，回退到本地启动Jupyter
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
            
            # --- 修复：根据运行环境确定直接访问URL和状态 ---
            if session.status == 'running':
                is_docker = session.process_id is None
                serialized_data['running_in_docker'] = is_docker
                
                if is_docker:
                    # Docker环境: 重新获取映射的主机端口
                    try:
                        from container.docker_ops import DockerClient
                        docker_client = DockerClient()
                        container_info = docker_client.get_container(project.container.container_id)
                        port_mappings = container_info.attrs.get('NetworkSettings', {}).get('Ports', {})
                        host_port = None
                        jupyter_container_port = '8888/tcp'
                        if jupyter_container_port in port_mappings and port_mappings[jupyter_container_port]:
                            host_port = port_mappings[jupyter_container_port][0].get('HostPort')
                        
                        if host_port:
                            direct_access_url = f"http://localhost:{host_port}/tree"
                            logger.info(f"Docker运行中，获取到映射端口 {host_port}, 直接URL: {direct_access_url}")
                        else:
                            # 如果找不到映射，使用会话端口作为后备（可能不准确）
                            direct_access_url = f"http://localhost:{session.port}/tree"
                            logger.warning(f"Docker运行中，但未找到8888端口映射，回退使用会话端口 {session.port}")
                            
                    except Exception as e:
                        logger.error(f"获取Docker端口映射失败: {str(e)}，回退使用会话端口 {session.port}")
                        direct_access_url = f"http://localhost:{session.port}/tree"
                else:
                    # 本地环境: 使用会话端口
                    direct_access_url = f"http://localhost:{session.port}/tree"
                    logger.info(f"本地运行中，直接URL: {direct_access_url}")
                    
                serialized_data['direct_access_url'] = direct_access_url
                
            else:
                # 非运行状态: 默认值
                serialized_data['running_in_docker'] = False
                # 提供一个默认或基于会话端口的URL，虽然此时可能无效
                direct_access_url = f"http://localhost:{session.port}/tree" 
                serialized_data['direct_access_url'] = direct_access_url
                logger.info(f"会话非运行状态，默认直接URL: {direct_access_url}")
            
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
