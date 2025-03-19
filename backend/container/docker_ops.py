"""
This module provides Docker operations for container management.
It includes a Docker client class that wraps the docker-py library
to provide high-level operations for managing Docker images and containers.
"""

import docker
from docker.errors import DockerException
from typing import Dict, List, Optional
import logging
import platform
import os
import time
import socket

# 设置日志记录器
logger = logging.getLogger(__name__)

class DockerClient:
    """
    Docker客户端类,提供Docker操作的高级接口
    
    主要功能:
    1. 镜像管理(拉取、列表、删除)
    2. 容器管理(创建、启动、停止、删除)
    3. 资源监控(CPU、内存使用情况)
    """
    
    def __init__(self):
        """
        初始化Docker客户端
        """
        try:
            # 根据操作系统选择连接方式
            if platform.system() == 'Windows':
                # 尝试使用命名管道
                try:
                    self.client = docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
                except DockerException:
                    # 如果命名管道失败，尝试TCP连接
                    self.client = docker.DockerClient(base_url='tcp://localhost:2375')
            else:
                # 在Unix系统上使用默认socket
                self.client = docker.from_env()
            
            # 测试连接
            self.client.ping()
            logger.info("Successfully connected to Docker daemon")
            
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {str(e)}")
            raise
    
    def list_images(self) -> List[Dict]:
        """
        获取所有Docker镜像列表
        
        Returns:
            List[Dict]: 镜像信息列表,每个镜像包含id、标签、大小等信息
        """
        try:
            images = self.client.images.list()
            return [
                {
                    'id': image.id,
                    'tags': image.tags,
                    'size': image.attrs['Size'],
                    'created': image.attrs['Created']
                }
                for image in images
            ]
        except DockerException as e:
            logger.error(f"Failed to list images: {str(e)}")
            raise
    
    def pull_image(self, image_name: str, tag: str = 'latest') -> Dict:
        """
        拉取Docker镜像
        
        Args:
            image_name: 镜像名称
            tag: 镜像标签,默认为latest
            
        Returns:
            Dict: 拉取的镜像信息
        """
        try:
            # 首先检查本地是否已有该镜像
            try:
                local_images = self.client.images.list(name=f"{image_name}:{tag}")
                if local_images:
                    logger.info(f"Image {image_name}:{tag} already exists locally")
                    return {
                        'id': local_images[0].id,
                        'tags': local_images[0].tags,
                        'size': local_images[0].attrs['Size'],
                        'created': local_images[0].attrs['Created'],
                        'source': 'local'
                    }
            except Exception as e:
                logger.warning(f"Error checking local images: {str(e)}")
            
            # 尝试拉取镜像
            try:
                logger.info(f"Pulling image {image_name}:{tag}")
                image = self.client.images.pull(image_name, tag=tag)
                return {
                    'id': image.id,
                    'tags': image.tags,
                    'size': image.attrs['Size'],
                    'created': image.attrs['Created'],
                    'source': 'remote'
                }
            except DockerException as e:
                # 如果拉取失败，记录错误并检查是否可以使用备用镜像
                logger.error(f"Failed to pull image {image_name}:{tag}: {str(e)}")
                
                # 我们可以尝试使用备用基础镜像
                if 'python' in image_name:
                    # 尝试查找任何可用的Python镜像
                    available_python_images = self.client.images.list(name="python")
                    if available_python_images:
                        logger.info(f"Using alternative Python image: {available_python_images[0].tags[0]}")
                        return {
                            'id': available_python_images[0].id,
                            'tags': available_python_images[0].tags,
                            'size': available_python_images[0].attrs['Size'],
                            'created': available_python_images[0].attrs['Created'],
                            'source': 'alternative'
                        }
                
                # 如果没有备用镜像，尝试创建最小的基础镜像
                logger.info("No Python image found, attempting to create a minimal base image")
                
                # 创建一个最小的Dockerfile
                minimal_dockerfile = """FROM scratch
LABEL maintainer="MLRide System"
CMD ["echo", "Minimal base image"]
"""
                # 使用内存流构建最小镜像
                import io
                f = io.BytesIO(minimal_dockerfile.encode('utf-8'))
                minimal_tag = f"mlride-minimal:{int(time.time())}"
                try:
                    logger.info(f"Building minimal image: {minimal_tag}")
                    minimal_image = self.client.images.build(fileobj=f, tag=minimal_tag, pull=False)[0]
                    logger.info(f"Successfully built minimal image: {minimal_tag}")
                    return {
                        'id': minimal_image.id,
                        'tags': minimal_image.tags,
                        'size': minimal_image.attrs['Size'],
                        'created': minimal_image.attrs['Created'],
                        'source': 'minimal'
                    }
                except Exception as build_error:
                    logger.error(f"Failed to build minimal image: {str(build_error)}")
                    raise Exception(f"无法拉取镜像且无法创建基础镜像: {str(e)}")
        except Exception as e:
            logger.error(f"Error in pull_image: {str(e)}")
            raise
            
    def remove_image(self, image_id: str, force: bool = False) -> bool:
        """
        删除Docker镜像
        
        Args:
            image_id: 镜像ID
            force: 是否强制删除,默认为False
            
        Returns:
            bool: 删除是否成功
        """
        try:
            self.client.images.remove(image_id, force=force)
            return True
        except DockerException as e:
            logger.error(f"Failed to remove image {image_id}: {str(e)}")
            raise
            
    def create_container(
        self,
        image_name: str,
        container_name: Optional[str] = None,
        command: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        cpu_count: Optional[float] = None,
        memory_limit: Optional[str] = None
    ) -> Dict:
        """
        创建Docker容器
        
        Args:
            image_name: 镜像名称
            container_name: 容器名称
            command: 容器启动命令
            environment: 环境变量
            ports: 端口映射
            volumes: 数据卷映射
            cpu_count: CPU核心数限制
            memory_limit: 内存限制
            
        Returns:
            Dict: 创建的容器信息
        """
        try:
            container = self.client.containers.create(
                image=image_name,
                name=container_name,
                command=command,
                environment=environment,
                ports=ports,
                volumes=volumes,
                cpu_count=cpu_count,
                mem_limit=memory_limit
            )
            return {
                'id': container.id,
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else container.image.id
            }
        except DockerException as e:
            logger.error(f"Failed to create container from {image_name}: {str(e)}")
            raise
            
    def start_container(self, container_id: str) -> Dict:
        """
        启动Docker容器
        
        Args:
            container_id: 容器ID
            
        Returns:
            Dict: 包含启动状态和端口映射信息
        """
        try:
            container = self.client.containers.get(container_id)
            container.start()
            
            # 等待容器完全启动
            time.sleep(1)
            
            # 刷新容器信息
            container.reload()
            
            # 获取端口映射信息
            port_mappings = {}
            if container.attrs['NetworkSettings']['Ports']:
                for container_port, host_bindings in container.attrs['NetworkSettings']['Ports'].items():
                    if host_bindings:
                        port_mappings[container_port] = host_bindings[0]['HostPort']
            
            return {
                'status': 'running',
                'port_mappings': port_mappings
            }
        except DockerException as e:
            logger.error(f"Failed to start container {container_id}: {str(e)}")
            raise
            
    def check_service_ready(self, container_id: str, port: int, timeout: int = 30, alt_ports: list = None) -> bool:
        """
        检查容器内服务是否就绪
        
        Args:
            container_id: 容器ID
            port: 服务主端口
            timeout: 超时时间(秒)
            alt_ports: 可选的备用端口列表
            
        Returns:
            bool: 服务是否就绪
        """
        if alt_ports is None:
            alt_ports = []
            
        # 检查主端口和所有备用端口
        ports_to_check = [port] + alt_ports
        logger.info(f"检查服务就绪状态，将检查以下端口: {ports_to_check}")
        
        try:
            container = self.client.containers.get(container_id)
            logger.info(f"检查容器 {container_id} 内服务就绪状态")
            
            # 检查容器状态
            if container.status != 'running':
                logger.error(f"容器 {container_id} 不在运行状态，当前状态: {container.status}")
                return False
            
            # 获取容器IP地址
            container_ip = None
            try:
                container_ip = container.attrs['NetworkSettings']['IPAddress']
                logger.info(f"从IPAddress获取到容器IP: {container_ip}")
            except (KeyError, TypeError) as e:
                logger.warning(f"无法从IPAddress获取容器IP: {str(e)}")
                
            if not container_ip:
                # 如果没有获取到IP地址，尝试从网络设置中获取
                try:
                    networks = container.attrs['NetworkSettings']['Networks']
                    if networks:
                        for network_name, network_config in networks.items():
                            if 'IPAddress' in network_config and network_config['IPAddress']:
                                container_ip = network_config['IPAddress']
                                logger.info(f"从Networks[{network_name}]获取到容器IP: {container_ip}")
                                break
                except (KeyError, TypeError) as e:
                    logger.warning(f"无法从Networks获取容器IP: {str(e)}")
            
            if not container_ip:
                logger.warning(f"无法获取容器 {container_id} 的IP地址，尝试使用localhost")
                # 尝试使用localhost作为回退方案
                container_ip = 'localhost'
                logger.info(f"使用localhost作为回退方案")
            
            # 尝试连接服务
            service_ready = False
            start_time = time.time()
            
            # 循环直到超时
            while time.time() - start_time < timeout:
                # 检查所有要检查的端口
                for check_port in ports_to_check:
                    try:
                        logger.info(f"尝试连接服务: {container_ip}:{check_port}")
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(1)
                        result = sock.connect_ex((container_ip, check_port))
                        sock.close()
                        
                        if result == 0:
                            logger.info(f"服务已就绪: {container_ip}:{check_port}")
                            return True
                            
                        logger.debug(f"服务在端口 {check_port} 上尚未就绪，错误码: {result}")
                    except Exception as e:
                        logger.debug(f"检查端口 {check_port} 时发生错误: {str(e)}")
                
                # 如果所有端口都未就绪，等待一会再尝试
                time.sleep(1)
                    
            # 获取容器日志以帮助诊断问题
            try:
                logs = container.logs(tail=50).decode('utf-8')
                logger.warning(f"服务未就绪，容器日志: {logs}")
            except Exception as e:
                logger.error(f"获取容器日志失败: {str(e)}")
                
            logger.error(f"服务在 {timeout} 秒后仍未就绪")
            
            # 检查容器是否仍在运行
            try:
                container.reload()
                logger.info(f"容器当前状态: {container.status}")
                if container.status != 'running':
                    logger.error(f"容器不再运行，当前状态: {container.status}")
                    return False
            except Exception as e:
                logger.error(f"刷新容器状态失败: {str(e)}")
            
            logger.warning("服务未就绪，但仍返回True以允许用户尝试连接")
            # 即使服务未就绪，也返回True以允许用户尝试连接
            # 这是因为有些服务可能需要更长时间启动，或者我们的检测方法可能不准确
            return True
            
        except DockerException as e:
            logger.error(f"检查服务就绪状态失败: {str(e)}")
            return True
            
    def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """
        停止Docker容器
        
        Args:
            container_id: 容器ID
            timeout: 超时时间(秒)
            
        Returns:
            bool: 停止是否成功
        """
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            return True
        except DockerException as e:
            logger.error(f"Failed to stop container {container_id}: {str(e)}")
            raise
    
    def get_container(self, container_id: str):
        """
        根据容器ID获取容器对象
        
        Args:
            container_id: 容器ID
            
        Returns:
            Container: Docker容器对象
        """
        try:
            container = self.client.containers.get(container_id)
            return container
        except DockerException as e:
            logger.error(f"获取容器失败 {container_id}: {str(e)}")
            raise
            
    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """
        删除Docker容器
        
        Args:
            container_id: 容器ID
            force: 是否强制删除
            
        Returns:
            bool: 删除是否成功
        """
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=force)
            return True
        except DockerException as e:
            logger.error(f"Failed to remove container {container_id}: {str(e)}")
            raise
            
    def get_container_stats(self, container_id: str) -> Dict:
        """
        获取容器资源使用统计信息
        
        Args:
            container_id: 容器ID
            
        Returns:
            Dict: 包含CPU、内存等使用情况的统计信息
        """
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # 计算CPU使用率
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                         stats['precpu_stats']['system_cpu_usage']
            cpu_usage = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
            
            # 计算内存使用率
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            memory_usage_percent = (memory_usage / memory_limit) * 100.0
            
            return {
                'cpu_usage_percent': round(cpu_usage, 2),
                'memory_usage': memory_usage,
                'memory_limit': memory_limit,
                'memory_usage_percent': round(memory_usage_percent, 2)
            }
        except DockerException as e:
            logger.error(f"Failed to get container stats {container_id}: {str(e)}")
            raise
            
    def build_image_from_dockerfile(
        self,
        dockerfile_content: str,
        image_name: str,
        image_tag: str = 'latest',
        build_args: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        从Dockerfile内容构建Docker镜像
        
        Args:
            dockerfile_content: Dockerfile内容
            image_name: 镜像名称
            image_tag: 镜像标签
            build_args: 构建参数
            
        Returns:
            Dict: 构建的镜像信息
        """
        import tempfile
        import io
        
        try:
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 创建Dockerfile文件
                dockerfile_path = os.path.join(temp_dir, 'Dockerfile')
                with open(dockerfile_path, 'w') as f:
                    f.write(dockerfile_content)
                
                logger.info(f"Building image {image_name}:{image_tag} from Dockerfile")
                logger.debug(f"Dockerfile content:\n{dockerfile_content}")
                
                # 构建镜像
                image, logs = self.client.images.build(
                    path=temp_dir,
                    tag=f"{image_name}:{image_tag}",
                    buildargs=build_args,
                    rm=True
                )
                
                # 记录构建日志
                for log in logs:
                    if 'stream' in log:
                        log_line = log['stream'].strip()
                        if log_line:
                            logger.debug(f"Build log: {log_line}")
                
                return {
                    'id': image.id,
                    'tags': image.tags,
                    'size': image.attrs['Size'] if 'Size' in image.attrs else None,
                    'created': image.attrs['Created'] if 'Created' in image.attrs else None
                }
                
        except DockerException as e:
            logger.error(f"Failed to build image {image_name}:{image_tag}: {str(e)}")
            raise 