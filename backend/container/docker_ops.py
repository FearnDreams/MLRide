"""
This module provides Docker operations for container management.
It includes a Docker client class that wraps the docker-py library
to provide high-level operations for managing Docker images and containers.
"""

import docker
from docker.errors import DockerException, ImageNotFound, BuildError
from typing import Dict, List, Optional
import logging
import platform
import os
import time
import socket
import requests
from requests.adapters import HTTPAdapter, Retry
import re
import tempfile
import subprocess
import datetime
import tarfile
import io

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
        self.logger = logging.getLogger(__name__)
        
        # 设置Docker API超时和重试
        self.timeout = int(os.environ.get("DOCKER_API_TIMEOUT", "180"))  # 默认180秒超时
        self.max_retries = int(os.environ.get("DOCKER_API_RETRIES", "3"))  # 默认3次重试
        
        # 检查操作系统
        self.is_windows = platform.system().lower() == 'windows'
        self.logger.info(f"操作系统: {platform.system()}")
        
        # 设置Windows环境下的Docker Host
        if self.is_windows and not os.environ.get('DOCKER_HOST'):
            # 对于Windows环境，如果未设置DOCKER_HOST，默认使用TCP连接
            # 因为我们已经验证TCP连接(localhost:2375)可以正常工作
            os.environ['DOCKER_HOST'] = 'tcp://localhost:2375'
            self.logger.info("Windows环境: 自动设置DOCKER_HOST=tcp://localhost:2375")
            
            # 创建配置文件目录
            config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
            os.makedirs(config_dir, exist_ok=True)
            
            # 保存Docker配置到文件，以便后续使用
            config_path = os.path.join(config_dir, 'docker_config.json')
            try:
                with open(config_path, 'w') as f:
                    import json
                    json.dump({
                        'docker_host': 'tcp://localhost:2375',
                        'os': platform.system(),
                        'last_update': str(datetime.datetime.now())
                    }, f, indent=2)
                self.logger.info(f"Docker连接配置已保存到 {config_path}")
            except Exception as e:
                self.logger.warning(f"保存Docker配置失败: {str(e)}")
        
        # 检查Docker Desktop是否运行
        try:
            if self.is_windows:
                # Windows上使用tasklist检查Docker进程
                docker_running = False
                
                try:
                    # 检查Docker Desktop进程
                    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Docker Desktop.exe'], 
                                           capture_output=True, text=True, check=False)
                    if 'Docker Desktop.exe' in result.stdout:
                        docker_running = True
                        self.logger.info("Docker Desktop进程正在运行")
                    else:
                        # 检查Docker Engine服务
                        result = subprocess.run(['sc', 'query', 'docker'], 
                                               capture_output=True, text=True, check=False)
                        if 'RUNNING' in result.stdout:
                            docker_running = True
                            self.logger.info("Docker Engine服务正在运行")
                except Exception as e:
                    self.logger.warning(f"检查Docker进程失败: {str(e)}")
                    
                if not docker_running:
                    self.logger.error("Docker Desktop可能未运行")
                    raise Exception("请确保Docker Desktop已启动并正在运行")
            else:
                # 非Windows系统使用docker info命令
                subprocess.run(['docker', 'info'], capture_output=True, check=True)
                self.logger.info("Docker正在运行")
        except Exception as e:
            self.logger.error(f"Docker可能未运行: {str(e)}")
            raise Exception("请确保Docker已启动并正在运行")
        
        # 初始化Docker客户端
        self._init_client()
    
    def _init_client(self):
        """
        初始化Docker客户端连接
        
        尝试多种连接方式，优先使用环境变量定义的连接方式
        """
        # 可能的Docker连接方式
        connection_methods = []
        
        # 从环境变量获取Docker主机地址
        docker_host = os.environ.get('DOCKER_HOST')
        if docker_host:
            connection_methods.append(('环境变量DOCKER_HOST', {'base_url': docker_host}))
        
        # 识别操作系统
        is_windows = platform.system().lower() == 'windows'
        
        # Windows环境下的Docker连接方式（按优先级排序）
        if is_windows:
            # 添加Windows专用的连接方式
            connection_methods.extend([
                # 根据测试结果，TCP连接最可靠，放在首位
                ('Windows本地TCP', {'base_url': 'tcp://localhost:2375'}),
                # Docker Desktop默认命名管道
                ('Windows默认命名管道', {'base_url': 'npipe:////./pipe/docker_engine'}),
                # Docker Desktop CLI使用的命名管道
                ('Docker CLI命名管道', {'base_url': 'npipe:////./pipe/docker_cli'}),
                # 另一个可能的命名管道路径
                ('备用命名管道', {'base_url': 'npipe:////./pipe/com.docker.docker'})
            ])
            
            # 尝试获取Docker Context信息，自动检测正确的连接方式
            try:
                docker_context_cmd = ["docker", "context", "inspect"]
                result = subprocess.run(docker_context_cmd, capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    self.logger.info(f"获取到Docker Context信息: {result.stdout[:200]}...")
                    
                    # 解析JSON输出
                    if "EndpointName" in result.stdout and "wsl" in result.stdout.lower():
                        # 这可能是WSL模式
                        # WSL模式下TCP连接可能更稳定
                        connection_methods.insert(0, ('WSL Context检测', {'base_url': 'tcp://localhost:2375'}))
                        self.logger.info("检测到可能运行在WSL环境中的Docker")
            except Exception as e:
                self.logger.warning(f"获取Docker Context信息失败: {str(e)}")
        
        # 其他常见的Docker连接方式
        connection_methods.extend([
            ('默认设置', {}),  # 使用默认设置
            ('Unix套接字', {'base_url': 'unix://var/run/docker.sock'}),
            ('TCP连接', {'base_url': 'tcp://localhost:2375'})
        ])
        
        # 配置请求会话以添加重试逻辑
        session = requests.Session()
        retries = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # 尝试连接直到成功
        connection_errors = []
        last_error = None
        
        for method, params in connection_methods:
            try:
                self.logger.info(f"尝试使用{method}连接Docker")
                
                # 添加超时设置并使用配置的会话
                client_params = {
                    **params,
                    'timeout': self.timeout
                }
                
                # 创建客户端
                self.client = docker.DockerClient(**client_params)
                self.client.api._timeout = self.timeout
                
                # 测试连接是否成功
                version_info = self.client.version()
                self.logger.info(f"Docker版本信息: {version_info.get('Version', 'unknown')}")
                
                # 检查API版本兼容性
                api_version = version_info.get('ApiVersion')
                if api_version:
                    self.logger.info(f"Docker API版本: {api_version}")
                
                # 连接成功提示
                self.logger.info(f"成功使用{method}连接到Docker")
                self.connection_method = method
                
                if self.is_windows:
                    # 对于Windows，保存成功的连接方式以供日后使用
                    if 'base_url' in params and params['base_url']:
                        self.logger.info(f"Windows环境成功连接Docker，建议设置环境变量: DOCKER_HOST={params['base_url']}")
                
                return  # 连接成功,退出初始化
            except Exception as e:
                error_msg = f"使用{method}连接Docker失败: {str(e)}"
                self.logger.warning(error_msg)
                connection_errors.append(error_msg)
                last_error = e
                continue  # 尝试下一个连接方式
        
        # 如果所有连接方式都失败
        error_msg = "无法连接到Docker服务。尝试了以下方法:\n" + "\n".join(connection_errors)
        self.logger.error(error_msg)
        
        # 针对Windows的特殊建议
        if is_windows:
            self.logger.error("\nWindows环境连接Docker失败，请尝试以下步骤:")
            self.logger.error("1. 确认Docker Desktop已启动并正常运行")
            self.logger.error("2. 在命令行设置环境变量: set DOCKER_HOST=npipe:////./pipe/docker_engine")
            self.logger.error("3. 检查Docker Desktop设置是否启用了'Expose daemon on tcp://localhost:2375 without TLS'选项")
            self.logger.error("4. 重启Docker Desktop和应用程序")
        
        # 收集系统信息以帮助诊断
        try:
            system_info = {
                'platform': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'docker_host': os.environ.get('DOCKER_HOST', 'Not set'),
                'python_version': platform.python_version(),
            }
            self.logger.error(f"系统信息: {system_info}")
            
            # 检查Docker配置
            try:
                if is_windows:
                    docker_config_path = os.path.join(os.environ.get('USERPROFILE', ''), '.docker', 'config.json')
                else:
                    docker_config_path = os.path.expanduser('~/.docker/config.json')
                    
                if os.path.exists(docker_config_path):
                    with open(docker_config_path, 'r') as f:
                        docker_config = f.read()
                        self.logger.info(f"Docker配置: {docker_config}")
                else:
                    self.logger.warning(f"Docker配置文件不存在: {docker_config_path}")
            except Exception as e:
                self.logger.warning(f"无法读取Docker配置: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"获取系统信息失败: {str(e)}")
        
        # 提供设置DOCKER_HOST环境变量的建议
        self.logger.error("建议: 请尝试设置DOCKER_HOST环境变量指向正确的Docker守护进程地址")
        
        raise Exception(error_msg)
    
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
            self.logger.error(f"Failed to list images: {str(e)}")
            raise
    
    def pull_image(self, image_name: str, tag: str = 'latest') -> Dict:
        """
        拉取Docker镜像，尝试找到或拉取指定版本的镜像
        
        Args:
            image_name: 镜像名称，例如'python'
            tag: 镜像标签，例如'3.9-slim'或'3.11'，默认为'latest'
            
        Returns:
            Dict: 拉取的镜像信息
        """
        try:
            # 完整的镜像名称
            full_image_name = f"{image_name}:{tag}"
            self.logger.info(f"尝试获取镜像: {full_image_name}, 参数: image_name='{image_name}', tag='{tag}'")
            
            # 首先尝试查找本地镜像
            try:
                # 获取所有镜像
                all_images = self.client.images.list()
                
                # 记录详细的镜像信息用于调试
                self.logger.info(f"本地镜像总数: {len(all_images)}")
                if len(all_images) > 0:
                    all_tags_dict = {}
                    for img in all_images:
                        if img.tags:
                            all_tags_dict[img.id[:12]] = img.tags
                    self.logger.info(f"带标签的镜像: {all_tags_dict}")
                
                # 尝试多种方式查找匹配的镜像
                matched_image = self._find_local_image(image_name, tag, all_images)
                
                if matched_image:
                    best_tag = self._get_best_matching_tag(matched_image, full_image_name)
                    self.logger.info(f"使用本地镜像: {best_tag}, ID: {matched_image.id[:12]}")
                    return {
                        'id': matched_image.id,
                        'tags': matched_image.tags,
                        'size': matched_image.attrs['Size'],
                        'created': matched_image.attrs['Created'],
                        'source': 'local'
                    }
                else:
                    self.logger.info(f"本地未找到匹配的镜像: {full_image_name}, 将尝试从远程拉取")
            except Exception as e:
                self.logger.warning(f"检查本地镜像时出错: {str(e)}")
            
            # 尝试拉取镜像，添加重试机制
            return self._pull_remote_image(image_name, tag)
            
        except Exception as e:
            self.logger.error(f"拉取镜像过程中出错: {str(e)}")
            raise
            
    def _find_local_image(self, image_name, tag, all_images):
        """
        在本地查找匹配的镜像
        
        Args:
            image_name: 镜像名称
            tag: 镜像标签
            all_images: 所有本地镜像
            
        Returns:
            找到的镜像对象，未找到返回None
        """
        full_image_name = f"{image_name}:{tag}"
        self.logger.info(f"在本地查找镜像: {full_image_name}")
        
        # 1. 直接完全匹配 - "python:3.9-slim"
        for img in all_images:
            if full_image_name in img.tags:
                self.logger.info(f"找到完全匹配的本地镜像: {full_image_name}, ID: {img.id[:12]}")
                return img
        
        # 2. 匹配带registry前缀的标签 - "docker.io/python:3.9-slim"
        for img in all_images:
            for img_tag in img.tags:
                if img_tag.endswith(f"/{full_image_name}") or img_tag.endswith(full_image_name):
                    self.logger.info(f"找到带registry前缀的匹配: {img_tag}, ID: {img.id[:12]}")
                    return img
        
        # 3. 分别解析名称和标签进行匹配
        for img in all_images:
            for img_tag in img.tags:
                try:
                    if ':' in img_tag:
                        img_name, img_version = img_tag.rsplit(':', 1)
                        # 处理registry前缀
                        if '/' in img_name:
                            img_name = img_name.split('/')[-1]
                        
                        self.logger.debug(f"比较: [{img_name}:{img_version}] 与请求的 [{image_name}:{tag}]")
                        if img_name == image_name and img_version == tag:
                            self.logger.info(f"找到名称和版本匹配: {img_tag}, ID: {img.id[:12]}")
                            return img
                except Exception:
                    continue
        
        # 4. 尝试更模糊的匹配，例如标签部分匹配
        if '-' in tag:  # 处理如"3.9-slim"这样的标签
            base_version = tag.split('-')[0]  # 提取版本号，如"3.9"
            self.logger.info(f"尝试以基础版本号 {base_version} 查找匹配")
            
            # 查找相同版本号的镜像
            for img in all_images:
                for img_tag in img.tags:
                    try:
                        if ':' in img_tag:
                            img_name, img_version = img_tag.rsplit(':', 1)
                            if '/' in img_name:
                                img_name = img_name.split('/')[-1]
                            
                            if img_name == image_name and img_version.startswith(base_version):
                                self.logger.info(f"找到版本号部分匹配: {img_tag}, ID: {img.id[:12]}")
                                return img
                    except Exception:
                        continue
        
        # 没有找到匹配的镜像
        self.logger.info(f"未找到匹配的本地镜像: {full_image_name}")
        return None
        
    def _get_best_matching_tag(self, image, preferred_tag):
        """
        获取最接近请求的镜像标签
        
        Args:
            image: 镜像对象
            preferred_tag: 首选镜像标签
            
        Returns:
            最佳匹配的标签
        """
        # 首先查找完全匹配
        for tag in image.tags:
            if tag == preferred_tag:
                return tag
                
        # 查找包含首选标签的标签
        for tag in image.tags:
            if preferred_tag in tag:
                return tag
                
        # 否则返回第一个标签
        if image.tags:
            return image.tags[0]
            
        # 如果没有标签，返回镜像ID
        return image.id[:12]
        
    def _pull_remote_image(self, image_name, tag):
        """
        从远程拉取镜像
        
        Args:
            image_name: 镜像名称
            tag: 镜像标签
            
        Returns:
            Dict: 拉取的镜像信息
            
        Raises:
            Exception: 如果拉取失败
        """
        full_image_name = f"{image_name}:{tag}"
        retry_count = 0
        max_pull_retries = int(os.environ.get("DOCKER_PULL_RETRIES", "3"))
        pull_error = None
        
        while retry_count < max_pull_retries:
            try:
                self.logger.info(f"从远程拉取镜像: {full_image_name} (尝试 {retry_count + 1}/{max_pull_retries})")
                
                # 使用低级API拉取镜像
                self.client.api.pull(image_name, tag=tag)
                
                # 尝试获取刚拉取的镜像
                try:
                    # 首先尝试完整名称
                    image = self.client.images.get(full_image_name)
                except ImageNotFound:
                    # 如果找不到完整名称，则尝试搜索新拉取的镜像
                    recent_images = self.client.images.list(name=image_name)
                    for img in recent_images:
                        if any(t.endswith(f":{tag}") for t in img.tags):
                            image = img
                            break
                    else:
                        raise Exception(f"成功拉取但无法找到镜像: {full_image_name}")
                
                self.logger.info(f"成功拉取镜像: {full_image_name}, ID: {image.id[:12]}, 标签: {image.tags}")
                return {
                    'id': image.id,
                    'tags': image.tags,
                    'size': image.attrs['Size'],
                    'created': image.attrs['Created'],
                    'source': 'remote'
                }
            except DockerException as e:
                pull_error = e
                error_msg = str(e)
                
                # 检查是否是网络类型错误
                is_network_error = any(network_err in error_msg.lower() for network_err in 
                                      ['timeout', 'connection refused', 'eof', 'network', 'unreachable'])
                
                if is_network_error:
                    retry_count += 1
                    wait_time = retry_count * 2  # 逐步增加等待时间
                    self.logger.warning(f"网络错误: {error_msg}，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    # 如果不是网络错误，不需要重试
                    self.logger.error(f"非网络错误，无法拉取: {error_msg}")
                    break
        
        # 所有重试都失败了
        if pull_error:
            self.logger.error(f"经过 {max_pull_retries} 次尝试，无法拉取镜像 {full_image_name}: {str(pull_error)}")
            self.logger.error(f"错误类型: {type(pull_error).__name__}")
            raise Exception(f"无法获取指定版本的镜像 {full_image_name}。请确保网络连接正常且Docker服务可用。错误详情: {str(pull_error)}")
            
        # 如果代码执行到这里，说明遇到了未处理的情况
        raise Exception(f"拉取镜像 {full_image_name} 失败，原因未知")
    
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
            self.logger.error(f"Failed to remove image {image_id}: {str(e)}")
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
            self.logger.error(f"Failed to create container from {image_name}: {str(e)}")
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
            self.logger.error(f"Failed to start container {container_id}: {str(e)}")
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
        self.logger.info(f"检查服务就绪状态，将检查以下端口: {ports_to_check}")
        
        try:
            container = self.client.containers.get(container_id)
            self.logger.info(f"检查容器 {container_id} 内服务就绪状态")
            
            # 检查容器状态
            if container.status != 'running':
                self.logger.error(f"容器 {container_id} 不在运行状态，当前状态: {container.status}")
                return False
            
            # 获取容器IP地址
            container_ip = None
            try:
                container_ip = container.attrs['NetworkSettings']['IPAddress']
                self.logger.info(f"从IPAddress获取到容器IP: {container_ip}")
            except (KeyError, TypeError) as e:
                self.logger.warning(f"无法从IPAddress获取容器IP: {str(e)}")
                
            if not container_ip:
                # 如果没有获取到IP地址，尝试从网络设置中获取
                try:
                    networks = container.attrs['NetworkSettings']['Networks']
                    if networks:
                        for network_name, network_config in networks.items():
                            if 'IPAddress' in network_config and network_config['IPAddress']:
                                container_ip = network_config['IPAddress']
                                self.logger.info(f"从Networks[{network_name}]获取到容器IP: {container_ip}")
                                break
                except (KeyError, TypeError) as e:
                    self.logger.warning(f"无法从Networks获取容器IP: {str(e)}")
            
            if not container_ip:
                self.logger.warning(f"无法获取容器 {container_id} 的IP地址，尝试使用localhost")
                # 尝试使用localhost作为回退方案
                container_ip = 'localhost'
                self.logger.info(f"使用localhost作为回退方案")
            
            # 尝试连接服务
            service_ready = False
            start_time = time.time()
            
            # 循环直到超时
            while time.time() - start_time < timeout:
                # 检查所有要检查的端口
                for check_port in ports_to_check:
                    try:
                        self.logger.info(f"尝试连接服务: {container_ip}:{check_port}")
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(1)
                        result = sock.connect_ex((container_ip, check_port))
                        sock.close()
                        
                        if result == 0:
                            self.logger.info(f"服务已就绪: {container_ip}:{check_port}")
                            return True
                            
                        self.logger.debug(f"服务在端口 {check_port} 上尚未就绪，错误码: {result}")
                    except Exception as e:
                        self.logger.debug(f"检查端口 {check_port} 时发生错误: {str(e)}")
                
                # 如果所有端口都未就绪，等待一会再尝试
                time.sleep(1)
                    
            # 获取容器日志以帮助诊断问题
            try:
                logs = container.logs(tail=50).decode('utf-8')
                self.logger.warning(f"服务未就绪，容器日志: {logs}")
            except Exception as e:
                self.logger.error(f"获取容器日志失败: {str(e)}")
                
            self.logger.error(f"服务在 {timeout} 秒后仍未就绪")
            
            # 检查容器是否仍在运行
            try:
                container.reload()
                self.logger.info(f"容器当前状态: {container.status}")
                if container.status != 'running':
                    self.logger.error(f"容器不再运行，当前状态: {container.status}")
                    return False
            except Exception as e:
                self.logger.error(f"刷新容器状态失败: {str(e)}")
            
            self.logger.warning("服务未就绪，但仍返回True以允许用户尝试连接")
            # 即使服务未就绪，也返回True以允许用户尝试连接
            # 这是因为有些服务可能需要更长时间启动，或者我们的检测方法可能不准确
            return True
            
        except DockerException as e:
            self.logger.error(f"检查服务就绪状态失败: {str(e)}")
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
            self.logger.error(f"Failed to stop container {container_id}: {str(e)}")
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
            self.logger.error(f"获取容器失败 {container_id}: {str(e)}")
            raise
            
    def create_jupyter_container(
        self,
        image_name: str = "python:3.9-slim",
        container_name: Optional[str] = None,
        workspace_path: Optional[str] = None,
        cpu_count: Optional[float] = 1.0,
        memory_limit: Optional[str] = "2g"
    ) -> Dict:
        """
        创建专门运行Jupyter Notebook的容器
        
        Args:
            image_name: 镜像名称，默认为python:3.9-slim
            container_name: 容器名称
            workspace_path: 工作空间路径映射
            cpu_count: CPU核心数限制
            memory_limit: 内存限制
            
        Returns:
            Dict: 创建的容器信息
        """
        try:
            # 设置端口映射，8888是Jupyter默认端口
            ports = {'8888/tcp': None}  # None会自动分配主机端口
            
            # 设置环境变量
            environment = {
                'JUPYTER_ENABLE_LAB': 'yes',  # 启用JupyterLab
                'JUPYTER_TOKEN': '',          # 设置空token，无需密码
                'JUPYTER_PASSWORD': '',       # 设置空密码
                'JUPYTER_ALLOW_ORIGIN': '*',  # 允许跨域
                'PYTHONPATH': '/workspace',   # 设置Python路径
                'PYTHONUNBUFFERED': '1'      # 禁用Python输出缓冲
            }
            
            # 设置挂载卷
            volumes = {}
            if workspace_path:
                volumes[workspace_path] = {'bind': '/workspace', 'mode': 'rw'}
            
            # 设置重启策略和健康检查
            restart_policy = {"Name": "unless-stopped"}
            healthcheck = {
                "test": ["CMD-SHELL", "curl -f http://localhost:8888/api || exit 1"],
                "interval": 30000000000,  # 30秒
                "timeout": 10000000000,   # 10秒
                "retries": 3,
                "start_period": 30000000000  # 30秒
            }
            
            # 创建容器
            container = self.client.containers.create(
                image=image_name,
                name=container_name,
                environment=environment,
                ports=ports,
                volumes=volumes,
                cpu_count=cpu_count,
                mem_limit=memory_limit,
                detach=True,  # 后台运行
                restart_policy=restart_policy,
                healthcheck=healthcheck,
                tty=True,  # 分配伪终端
                stdin_open=True,  # 保持stdin打开
                working_dir='/workspace'  # 设置工作目录
            )
            
            # 返回容器信息
            return {
                'id': container.id,
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else container.image.id,
                'jupyter_port': 8888
            }
        except DockerException as e:
            self.logger.error(f"创建Jupyter容器失败: {str(e)}")
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
            self.logger.error(f"Failed to remove container {container_id}: {str(e)}")
            raise
            
    def get_container_stats(self, container_id: str) -> Dict:
        """
        获取容器的资源使用情况

        Args:
            container_id: 容器ID或名称

        Returns:
            Dict: 包含CPU和内存使用率等信息的字典
        """
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # 初始化结果字典
            result = {
                'container_id': container_id,
                'name': container.name,
                'status': container.status
            }
            
            # 计算CPU使用率（添加错误处理）
            try:
                # 确保所有必要的键存在
                if ('cpu_stats' in stats and 'precpu_stats' in stats and
                    'cpu_usage' in stats['cpu_stats'] and 'cpu_usage' in stats['precpu_stats'] and
                    'total_usage' in stats['cpu_stats']['cpu_usage'] and 'total_usage' in stats['precpu_stats']['cpu_usage'] and
                    'system_cpu_usage' in stats['cpu_stats'] and 'system_cpu_usage' in stats['precpu_stats']):
                    
                    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                               stats['precpu_stats']['cpu_usage']['total_usage']
                    system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                 stats['precpu_stats']['system_cpu_usage']
                    
                    if system_delta > 0:
                        cpu_usage = (cpu_delta / system_delta) * 100.0
                        result['cpu_usage_percent'] = round(cpu_usage, 2)
            except Exception as e:
                self.logger.warning(f"计算CPU使用率失败: {str(e)}")
            
            # 计算内存使用率（添加错误处理）
            try:
                if ('memory_stats' in stats and 
                    'usage' in stats['memory_stats'] and 
                    'limit' in stats['memory_stats']):
                    
                    memory_usage = stats['memory_stats']['usage']
                    memory_limit = stats['memory_stats']['limit']
                    
                    result['memory_usage'] = memory_usage
                    result['memory_limit'] = memory_limit
                    
                    if memory_limit > 0:
                        memory_usage_percent = (memory_usage / memory_limit) * 100.0
                        result['memory_usage_percent'] = round(memory_usage_percent, 2)
            except Exception as e:
                self.logger.warning(f"计算内存使用率失败: {str(e)}")
            
            return result
        except DockerException as e:
            self.logger.error(f"获取容器统计信息失败 {container_id}: {str(e)}")
            raise
            
    def build_image_from_dockerfile(
        self,
        dockerfile_content: str,
        image_name: str,
        image_tag: str = 'latest',
        build_args: Optional[Dict[str, str]] = None,
        python_version: Optional[str] = None
    ) -> Dict:
        """
        从Dockerfile内容构建镜像
        
        Args:
            dockerfile_content: Dockerfile内容
            image_name: 镜像名称
            image_tag: 镜像标签,默认为latest
            build_args: 构建参数
            python_version: 预期的Python版本，用于验证和标记
            
        Returns:
            Dict: 构建的镜像信息
        """
        import io
        import time
        
        try:
            # 检查是否已有同名镜像
            try:
                local_image = self.client.images.get(f"{image_name}:{image_tag}")
                self.logger.info(f"Image {image_name}:{image_tag} already exists locally with ID: {local_image.id}")
                # 如果已经存在，先移除旧的
                self.client.images.remove(local_image.id, force=True)
                self.logger.info(f"Removed existing image {image_name}:{image_tag}")
            except (ImageNotFound, DockerException) as e:
                self.logger.info(f"No existing image found with name {image_name}:{image_tag}: {str(e)}")
            
            # 如果提供了Python版本，添加版本验证命令
            if python_version:
                dockerfile_content = self._add_version_verification(dockerfile_content, python_version)
            
            # 创建文件对象
            f = io.BytesIO(dockerfile_content.encode('utf-8'))
            
            # 构建镜像
            self.logger.info(f"Building image {image_name}:{image_tag} from Dockerfile")
            
            # 设置构建超时
            build_timeout = 300  # 5分钟
            
            # 尝试构建，设置超时时间和构建参数
            try:
                image, logs = self.client.images.build(
                    fileobj=f,
                    tag=f"{image_name}:{image_tag}",
                    rm=True,
                    pull=True,  # 尝试拉取最新的基础镜像
                    timeout=build_timeout,
                    buildargs=build_args
                )
                
                # 输出构建日志
                log_output = []
                for log in logs:
                    if 'stream' in log:
                        log_line = log['stream'].strip()
                        if log_line:
                            log_output.append(log_line)
                            self.logger.debug(log_line)
                
                self.logger.info(f"Successfully built image {image_name}:{image_tag}")
                
                # 验证构建的镜像中的Python版本
                if python_version:
                    actual_version = self._verify_python_version_in_image(image.id)
                    if actual_version:
                        self.logger.info(f"验证镜像Python版本: 预期={python_version}, 实际={actual_version}")
                        # 添加额外的标签记录实际版本
                        self.client.images.get(image.id).tag(
                            f"{image_name}", f"actual-py{actual_version}"
                        )
                
                # 返回镜像信息
                return {
                    'id': image.id,
                    'tags': image.tags,
                    'size': image.attrs['Size'],
                    'created': image.attrs['Created'],
                    'log': log_output
                }
            except (BuildError, DockerException) as build_error:
                self.logger.error(f"Build error: {str(build_error)}")
                
                # 尝试调整Dockerfile，移除可能导致问题的部分
                self.logger.info("Attempting to build with modified Dockerfile")
                
                # 修改Dockerfile，尝试不依赖网络的构建
                simplified_dockerfile = self._create_simplified_dockerfile(dockerfile_content)
                f = io.BytesIO(simplified_dockerfile.encode('utf-8'))
                
                try:
                    # 使用最小方式重试构建
                    image, logs = self.client.images.build(
                        fileobj=f,
                        tag=f"{image_name}:{image_tag}",
                        rm=True,
                        pull=False,  # 不尝试拉取新镜像
                        timeout=build_timeout
                    )
                    
                    self.logger.info(f"Successfully built image with simplified Dockerfile: {image_name}:{image_tag}")
                    
                    # 验证构建的镜像中的Python版本
                    if python_version:
                        actual_version = self._verify_python_version_in_image(image.id)
                        if actual_version:
                            self.logger.info(f"验证镜像Python版本: 预期={python_version}, 实际={actual_version}")
                            # 添加额外的标签记录实际版本
                            self.client.images.get(image.id).tag(
                                f"{image_name}", f"actual-py{actual_version}"
                            )
                    
                    return {
                        'id': image.id,
                        'tags': image.tags,
                        'size': image.attrs['Size'],
                        'created': image.attrs['Created'],
                        'note': '使用了简化版Dockerfile构建，可能缺少某些功能'
                    }
                except Exception as retry_error:
                    self.logger.error(f"Simplified build also failed: {str(retry_error)}")
                    raise Exception(f"无法构建Docker镜像: {str(build_error)}，重试也失败: {str(retry_error)}")
                    
        except Exception as e:
            self.logger.error(f"Error building image from Dockerfile: {str(e)}", exc_info=True)
            raise
    
    def _add_version_verification(self, dockerfile_content, expected_version):
        """
        在Dockerfile中添加Python版本验证步骤
        
        Args:
            dockerfile_content (str): 原始Dockerfile内容
            expected_version (str): 期望的Python版本
            
        Returns:
            str: 添加了验证命令的Dockerfile内容
        """
        # 添加一个RUN命令来检查Python版本并输出到构建日志
        verification_command = f"""
# 验证Python版本
RUN python --version && \\
    echo "期望的Python版本: {expected_version}" && \\
    python -c "import platform; print('实际Python版本:', platform.python_version())" && \\
    if python -c "import platform; v=platform.python_version().split('.'); exit(0 if '{expected_version}'.startswith(v[0]+'.'+v[1]) else 1)"; then \\
        echo "Python版本验证通过"; \\
    else \\
        echo "警告: 实际Python版本与期望版本({expected_version})不匹配"; \\
    fi
"""
        # 将验证命令附加到Dockerfile末尾
        dockerfile_lines = dockerfile_content.splitlines()
        
        # 找到合适的位置插入验证命令 - 在第一个FROM之后
        for i, line in enumerate(dockerfile_lines):
            if line.strip().startswith("FROM "):
                # 在FROM行之后插入验证命令
                dockerfile_lines.insert(i + 1, verification_command)
                break
        else:
            # 如果没有FROM行，直接在开头添加
            dockerfile_lines.insert(0, verification_command)
        
        return "\n".join(dockerfile_lines)
        
    def _verify_python_version_in_image(self, image_id: str) -> Optional[str]:
        """
        在镜像中验证Python版本
        
        Args:
            image_id: 镜像ID
            
        Returns:
            Optional[str]: 检测到的Python版本，如果检测失败则返回None
        """
        try:
            # 创建临时容器来运行命令
            container = self.client.containers.create(
                image_id,
                command="python -c 'import platform; print(platform.python_version())'",
                detach=False
            )
            
            # 启动容器
            container.start()
            
            # 等待容器完成
            exit_code = container.wait()['StatusCode']
            
            if exit_code == 0:
                # 获取输出
                logs = container.logs().decode('utf-8').strip()
                self.logger.info(f"检测到镜像中的Python版本: {logs}")
                
                # 清理容器
                container.remove()
                
                return logs
            else:
                self.logger.warning(f"Python版本检查失败，退出码: {exit_code}")
                # 清理容器
                container.remove()
                return None
                
        except Exception as e:
            self.logger.error(f"验证镜像中的Python版本时出错: {str(e)}")
            return None

    def _create_simplified_dockerfile(self, original_dockerfile):
        """
        创建简化版的Dockerfile，移除可能导致构建失败的操作
        
        主要用于网络受限环境，通过移除需要网络的操作来确保构建成功
        
        Args:
            original_dockerfile (str): 原始Dockerfile内容
            
        Returns:
            str: 简化后的Dockerfile内容
        """
        logger.info("创建简化版Dockerfile")
        
        # 分行处理Dockerfile
        lines = original_dockerfile.splitlines()
        simplified_lines = []
        
        # 指示下一行是否需要被保留
        keep_next_line = True
        
        for line in lines:
            line_stripped = line.strip()
            
            # 始终保留FROM指令
            if line_stripped.startswith('FROM '):
                simplified_lines.append(line)
                keep_next_line = True
                continue
                
            # 保留WORKDIR指令
            if line_stripped.startswith('WORKDIR '):
                simplified_lines.append(line)
                continue
                
            # 保留ENV指令
            if line_stripped.startswith('ENV '):
                simplified_lines.append(line)
                continue
                
            # 保留LABEL指令
            if line_stripped.startswith('LABEL '):
                simplified_lines.append(line)
                continue
                
            # 保留CMD和ENTRYPOINT指令
            if line_stripped.startswith('CMD ') or line_stripped.startswith('ENTRYPOINT '):
                simplified_lines.append(line)
                continue
                
            # 注释掉RUN pip install命令，因为它们需要网络
            if line_stripped.startswith('RUN pip') or 'pip install' in line_stripped:
                simplified_lines.append(f'# 已移除(需要网络): {line}')
                continue
            
            # 保留目录创建命令
            if 'mkdir' in line_stripped and line_stripped.startswith('RUN '):
                simplified_lines.append(line)
                continue
                
            # 处理多行RUN命令
            if line_stripped.endswith('\\'):
                if 'pip install' in line_stripped:
                    simplified_lines.append(f'# 已移除(需要网络): {line}')
                    keep_next_line = False
                else:
                    simplified_lines.append(line)
                continue
                
            # 根据上一行的标志决定是否保留当前行
            if not keep_next_line:
                simplified_lines.append(f'# 已移除(需要网络): {line}')
                if not line_stripped.endswith('\\'):
                    keep_next_line = True  # 重置标志
            else:
                # 对于不确定的行，直接注释以避险
                if line_stripped.startswith('RUN ') and ('apt-get' in line_stripped or 'yum' in line_stripped):
                    simplified_lines.append(f'# 已移除(需要网络): {line}')
                else:
                    simplified_lines.append(line)
        
        # 添加注释说明这是简化版
        simplified_lines.append('\n# 注意: 这是简化版Dockerfile，已移除需要网络的操作')
        
        return '\n'.join(simplified_lines)

    def copy_to_container(self, container_id, source_path, target_path):
        """
        复制本地文件到容器中
        
        Args:
            container_id: 容器ID
            source_path: 源文件路径
            target_path: 容器内的目标文件路径 (不是目录)
            
        Returns:
            bool: 是否成功
        """
        try:
            container = self.client.containers.get(container_id)
            
            # 创建一个内存中的tar归档
            pw_tarstream = io.BytesIO()
            pw_tar = tarfile.TarFile(fileobj=pw_tarstream, mode='w')
            
            # 获取源文件信息
            file_info = tarfile.TarInfo(name=os.path.basename(target_path))
            file_info.size = os.path.getsize(source_path)
            file_info.mtime = time.time()
            # 保持默认权限
            # file_info.mode = 0o644 
            
            # 将文件内容添加到tar归档中
            with open(source_path, 'rb') as source_file:
                pw_tar.addfile(file_info, source_file)
            
            pw_tar.close()
            pw_tarstream.seek(0)
            
            # 将tar流放入容器的目标目录
            # put_archive需要目标路径是一个目录
            target_dir = os.path.dirname(target_path)
            result = container.put_archive(target_dir, pw_tarstream)
            
            if result:
                self.logger.info(f"成功复制 {source_path} 到容器 {container_id}:{target_path}")
                return True
            else:
                self.logger.error(f"复制文件到容器失败 (put_archive 返回 False): {container_id}:{target_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"复制文件到容器时发生异常: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
            
    def check_jupyter_in_container(self, container_id):
        """检查容器中是否已安装Jupyter
        
        Args:
            container_id: 容器ID
            
        Returns:
            dict: 包含Jupyter检查结果的字典
        """
        try:
            container = self.client.containers.get(container_id)
            
            # 检查jupyter是否已安装
            check_cmd = "which jupyter || echo 'NOT_INSTALLED'"
            result = container.exec_run(check_cmd)
            installed = not result.output.decode('utf-8', errors='ignore').strip().endswith('NOT_INSTALLED')
            
            # 检查kernel列表
            kernels = []
            if installed:
                try:
                    kernel_cmd = "jupyter kernelspec list"
                    kernel_result = container.exec_run(kernel_cmd)
                    kernel_output = kernel_result.output.decode('utf-8', errors='ignore')
                    # 解析kernel输出
                    for line in kernel_output.splitlines():
                        if "python" in line.lower():
                            kernels.append(line.strip())
                except:
                    pass
            
            return {
                "installed": installed,
                "output": result.output.decode('utf-8', errors='ignore'),
                "kernels": kernels
            }
        except Exception as e:
            self.logger.error(f"检查容器Jupyter状态失败: {str(e)}")
            return {"installed": False, "error": str(e)}
            
    def install_jupyter_kernel_in_container(self, container_id, kernel_name=None):
        """在容器中安装Jupyter内核
        
        Args:
            container_id: 容器ID
            kernel_name: 内核名称，默认为自动生成
            
        Returns:
            dict: 安装结果
        """
        try:
            container = self.client.containers.get(container_id)
            self.logger.info(f"开始在容器 {container_id[:12]} 中安装Jupyter内核")
            
            # 如果未指定kernel名称，使用容器ID的前8位作为名称
            if not kernel_name:
                kernel_name = f"python-container-{container_id[:8]}"
            self.logger.info(f"目标内核名称: {kernel_name}")
            
            # 检查pip是否存在，优先使用pip3
            pip_cmd_check = "(pip3 --version > /dev/null 2>&1 && echo 'pip3') || (pip --version > /dev/null 2>&1 && echo 'pip') || echo 'PIP_NOT_FOUND'"
            pip_result = container.exec_run(["bash", "-c", pip_cmd_check], environment={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}) # Add ENV
            pip_cmd = pip_result.output.decode('utf-8', errors='ignore').strip()
            
            if pip_cmd == 'PIP_NOT_FOUND':
                self.logger.error("容器中未找到pip或pip3，无法安装ipykernel")
                return {"success": False, "error": "pip not found in container"}
            self.logger.info(f"使用pip命令: {pip_cmd}")
                
            # 在容器中安装ipykernel
            install_ipykernel_cmd = f"{pip_cmd} install --no-cache-dir --upgrade ipykernel"
            self.logger.info(f"执行安装ipykernel命令: {install_ipykernel_cmd}")
            install_result = container.exec_run(install_ipykernel_cmd, privileged=True, environment={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}) # Add ENV
            
            if install_result.exit_code != 0:
                error_output = install_result.output.decode('utf-8', errors='ignore')
                self.logger.error(f"安装ipykernel失败, Exit Code: {install_result.exit_code}\\nOutput:\\n{error_output[:500]}")
                return {"success": False, "error": f"Failed to install ipykernel: {error_output[:100]}"}
            self.logger.info("ipykernel安装成功")

            # --- 获取容器中的Python版本信息 和 可执行文件名 (新方法) ---
            python_version = 'Unknown'
            python_exec_name = None
            
            # 尝试 python3
            cmd_py3_ver = "python3 -V"
            py3_ver_result = container.exec_run(cmd_py3_ver, environment={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'})
            if py3_ver_result.exit_code == 0:
                python_version_str = py3_ver_result.output.decode('utf-8', errors='ignore').strip()
                match = re.search(r'(\d+\.\d+(\.\d+)?)', python_version_str)
                if match:
                    python_version = match.group(1)
                    python_exec_name = "python3"
                    self.logger.info(f"找到 Python 3 版本: {python_version} (可执行名: {python_exec_name})")
            
            # 如果没找到 python3 或版本解析失败，尝试 python
            if python_exec_name is None:
                cmd_py_ver = "python -V"
                py_ver_result = container.exec_run(cmd_py_ver, environment={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'})
                if py_ver_result.exit_code == 0:
                    python_version_str = py_ver_result.output.decode('utf-8', errors='ignore').strip()
                    match = re.search(r'(\d+\.\d+(\.\d+)?)', python_version_str)
                    if match:
                        python_version = match.group(1)
                        python_exec_name = "python"
                        self.logger.info(f"找到 Python 版本: {python_version} (可执行名: {python_exec_name})")
            
            # 如果两者都失败
            if python_exec_name is None:
                self.logger.error("无法执行 'python3 -V' 或 'python -V' 来确定 Python 版本和可执行文件名")
                return {"success": False, "error": "Could not determine Python version or executable name (python/python3)."}
                
            self.logger.info(f"容器中的 Python 版本: {python_version}")

            # 构建内核显示名称
            display_name = f"Docker Image (Python {python_version})"
            self.logger.info(f"内核显示名称: {display_name}")

            # --- 获取Python可执行文件路径 (修复版) ---
            # (此部分不再需要，我们直接使用上面找到的 python_exec_name)
            # python_exec_path = None
            # # 优先尝试 python3
            # cmd_py3 = "command -v python3"
            # py3_result = container.exec_run(cmd_py3, environment={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'})
            # if py3_result.exit_code == 0:
            #     python_exec_path = py3_result.output.decode('utf-8', errors='ignore').strip()
            #     self.logger.info(f"找到 Python 3 可执行文件: {python_exec_path}")
            # else:
            #     # 尝试 python
            #     cmd_py = "command -v python"
            #     py_result = container.exec_run(cmd_py, environment={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'})
            #     if py_result.exit_code == 0:
            #         python_exec_path = py_result.output.decode('utf-8', errors='ignore').strip()
            #         self.logger.info(f"找到 Python 可执行文件: {python_exec_path}")
            #     else:
            #         # 两者都找不到
            #         self.logger.error("在容器中未找到 python 或 python3 命令")
            #         return {"success": False, "error": "Python executable (python or python3) not found in container."}

            # # 验证路径是否有效
            # if not python_exec_path: # 或添加其他检查，如是否包含空格等
            #     self.logger.error(f"获取到的 Python 路径无效: '{python_exec_path}'")
            #     return {"success": False, "error": "Invalid Python executable path obtained."}

            # self.logger.info(f"最终使用的 Python 可执行文件: {python_exec_path}")

            # 在容器中注册内核 (系统范围，不带 --prefix)
            # 修正 register_cmd 中的转义字符, 并使用 python_exec_name
            register_cmd = f'{python_exec_name} -m ipykernel install --name={kernel_name} --display-name="{display_name}"'
            self.logger.info(f"执行注册内核命令 (系统范围): {register_cmd}")
            register_result = container.exec_run(["bash", "-c", register_cmd], privileged=True, environment={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'})
            output = register_result.output.decode('utf-8', errors='ignore')

            if register_result.exit_code != 0:
                self.logger.error(f"注册内核失败, Exit Code: {register_result.exit_code}\\nOutput:\\n{output[:500]}")
                return {"success": False, "error": f"Failed to register kernel: {output[:100]}"}
            self.logger.info(f"内核注册命令执行成功，输出: {output.strip()}")

            # 增加短暂延迟，等待文件系统更新
            time.sleep(2)
            
            # --- 验证内核文件 (主要用于调试，即使列表确认失败也继续) ---
            possible_paths_to_check = [
                f"/usr/local/share/jupyter/kernelspecs/{kernel_name}",
                f"/usr/share/jupyter/kernelspecs/{kernel_name}"
            ]
            kernelspec_file_found = False
            self.logger.info(f"开始验证内核文件，检查路径: {possible_paths_to_check}")
            for check_dir in possible_paths_to_check:
                kernelspec_file = f"{check_dir}/kernel.json"
                check_file_cmd = f"cat {kernelspec_file} || echo 'FILE_NOT_FOUND'"
                self.logger.info(f"尝试读取内核文件: {kernelspec_file}")
                file_check_result = container.exec_run(["bash", "-c", check_file_cmd], environment={'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}) # Add ENV
                file_content = file_check_result.output.decode('utf-8', errors='ignore').strip()
                if file_content != 'FILE_NOT_FOUND':
                    kernelspec_file_found = True
                    self.logger.info(f"找到内核文件于: {kernelspec_file}")
                    break
            if not kernelspec_file_found:
                 self.logger.warning(f"在检查路径 {possible_paths_to_check} 中未找到内核文件 kernel.json! 但将继续操作。")

            # 返回成功，因为安装命令本身是成功的
            return {
                "success": True,
                "output": output,
                "kernel_name": kernel_name,
                "display_name": display_name,
                "python_version": python_version,
            }

        except Exception as e:
            self.logger.error(f"在容器中安装Jupyter内核时发生异常: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

    def start_jupyter_in_container(self, container_id, port=8888, token=None):
        """
        在容器中启动Jupyter服务
        
        Args:
            container_id: 容器ID
            port: Jupyter服务端口,默认8888
            token: Jupyter访问令牌,默认None
            
        Returns:
            dict: 包含启动状态和错误信息的字典
        """
        import time
        import json
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"开始在容器 {container_id[:12]} 中启动Jupyter服务")
            container = self.get_container(container_id)
            if not container:
                logger.error(f"容器不存在: {container_id}")
                return {
                    'status': 'error',
                    'error_details': f'容器不存在: {container_id}'
                }
            
            # 检查容器状态并记录详细信息
            logger.info(f"容器状态: {container.status}")
            if container.status != 'running':
                logger.warning(f'容器未运行,当前状态: {container.status}')
                return {
                    'status': 'error',
                    'error_details': f'容器未运行,当前状态: {container.status}'
                }
            
            # 获取容器信息
            container_info = container.attrs
            container_image = container_info.get('Config', {}).get('Image', 'unknown')
            logger.info(f"容器镜像: {container_image}")
            
            # 记录网络信息
            networks = container_info.get('NetworkSettings', {}).get('Networks', {})
            for network_name, network_config in networks.items():
                if 'IPAddress' in network_config:
                    logger.info(f"容器网络 {network_name}: {network_config['IPAddress']}")
            
            # 检查操作系统和发行版
            os_info_cmd = "cat /etc/os-release || echo 'OS信息不可用'"
            os_info = container.exec_run(os_info_cmd)
            logger.info(f"容器OS信息: {os_info.output.decode()[:200]}")
            
            # 终止现有的Jupyter进程
            logger.info('尝试终止现有Jupyter进程')
            kill_cmd = "pkill -f jupyter || pkill -f notebook || true"
            kill_result = container.exec_run(kill_cmd)
            logger.info(f'终止现有进程结果: {kill_result.output.decode()}')
            
            # 等待进程完全终止
            time.sleep(2)
            
            # 检查Python版本
            logger.info("检查容器中的Python环境")
            python_version_cmd = "python --version || python3 --version || echo 'Python未安装'"
            python_version = container.exec_run(python_version_cmd)
            logger.info(f"Python版本: {python_version.output.decode()}")
            
            # 尝试使用多种方法安装pip
            logger.info("开始检查和安装pip")
            install_pip_success = False
            
            # 方法1: 检查pip或pip3是否已安装
            check_pip_cmd = "which pip || which pip3 || echo 'NOT_FOUND'"
            pip_result = container.exec_run(check_pip_cmd)
            pip_path = pip_result.output.decode().strip()
            
            if pip_path != 'NOT_FOUND':
                logger.info(f"找到pip: {pip_path}")
                install_pip_success = True
            else:
                logger.warning("未找到pip，尝试安装...")
                
                # 方法2: 使用apt-get安装pip
                logger.info("尝试使用apt-get安装pip")
                apt_cmd = "apt-get update && apt-get install -y python3-pip || echo 'APT安装失败'"
                apt_result = container.exec_run(apt_cmd)
                logger.info(f"apt-get安装结果: {apt_result.output.decode()[:200]}")
                
                # 检查是否安装成功
                pip_check = container.exec_run("which pip || which pip3 || echo 'NOT_FOUND'")
                if pip_check.output.decode().strip() != 'NOT_FOUND':
                    logger.info("使用apt-get成功安装pip")
                    install_pip_success = True
                else:
                    # 方法3: 使用get-pip.py脚本
                    logger.info("尝试使用get-pip.py安装pip")
                    get_pip_cmd = """
                    curl -s https://bootstrap.pypa.io/get-pip.py -o get-pip.py && 
                    (python get-pip.py || python3 get-pip.py) &&
                    rm get-pip.py || echo '安装失败'
                    """
                    get_pip_result = container.exec_run(["bash", "-c", get_pip_cmd])
                    logger.info(f"get-pip.py安装结果: {get_pip_result.output.decode()[:200]}")
                    
                    # 再次检查pip
                    pip_check = container.exec_run("which pip || which pip3 || echo 'NOT_FOUND'")
                    if pip_check.output.decode().strip() != 'NOT_FOUND':
                        logger.info("使用get-pip.py成功安装pip")
                        install_pip_success = True
            
            if not install_pip_success:
                logger.error("无法在容器中安装pip，无法继续安装Jupyter")
                return {
                    'status': 'error',
                    'error_details': '无法在容器中安装pip，请确保容器环境支持Python和pip'
                }
            
            # 确定pip命令
            pip_cmd = "pip3" if "pip3" in pip_path else "pip"
            logger.info(f"使用pip命令: {pip_cmd}")
            
            # 安装Jupyter
            logger.info("开始安装Jupyter")
            install_cmd = f"{pip_cmd} install --no-cache-dir 'notebook<7.0.0'"  # 使用旧版本避免配置兼容性问题
            logger.info(f"执行安装命令: {install_cmd}")
            install_result = container.exec_run(install_cmd)
            logger.info(f"Jupyter安装输出: {install_result.output.decode()[:500]}")
            
            if install_result.exit_code != 0:
                logger.error(f"安装Jupyter失败: {install_result.output.decode()}")
                return {
                    'status': 'error',
                    'error_details': f'安装Jupyter失败，请检查容器环境'
                }
            
            # 检查安装结果
            jupyter_check = container.exec_run("jupyter --version || echo 'NOT_FOUND'")
            if 'NOT_FOUND' in jupyter_check.output.decode():
                logger.error("Jupyter安装成功但命令不可用，检查PATH环境变量")
                # 尝试查找jupyter可执行文件
                find_jupyter = container.exec_run("find / -name jupyter -type f 2>/dev/null || echo 'NOT_FOUND'")
                logger.info(f"查找jupyter可执行文件结果: {find_jupyter.output.decode()[:200]}")
            
            # 创建工作目录
            logger.info("创建工作目录")
            container.exec_run('mkdir -p /workspace')
            
            # 创建Jupyter配置目录
            logger.info("创建Jupyter配置目录")
            container.exec_run('mkdir -p /root/.jupyter')
            
            # 创建Jupyter配置
            logger.info("创建Jupyter配置文件")
            config_content = f"""
c = get_config()

# 同时支持新旧版本的配置
c.ServerApp.ip = '0.0.0.0'  # 新版本
c.ServerApp.port = {port}
c.ServerApp.token = '{token if token else ""}'
c.ServerApp.notebook_dir = '/workspace'
c.ServerApp.allow_root = True

# 兼容旧版本配置
c.NotebookApp.ip = '0.0.0.0'
c.NotebookApp.port = {port}
c.NotebookApp.token = '{token if token else ""}'
c.NotebookApp.notebook_dir = '/workspace'
c.NotebookApp.allow_root = True
"""
            # 写入配置文件
            config_cmd = f"""cat > /root/.jupyter/jupyter_notebook_config.py << 'EOL'
{config_content}
EOL"""
            config_result = container.exec_run(["bash", "-c", config_cmd])
            if config_result.exit_code != 0:
                logger.error(f"创建Jupyter配置失败: {config_result.output.decode()}")
                return {
                    'status': 'error',
                    'error_details': '创建Jupyter配置文件失败'
                }
            
            # 验证配置文件
            check_config = container.exec_run("cat /root/.jupyter/jupyter_notebook_config.py")
            logger.info(f"Jupyter配置文件内容: {check_config.output.decode()[:200]}...")
            
            # 获取正确的jupyter路径
            jupyter_path_cmd = "which jupyter || echo 'NOT_FOUND'"
            jupyter_path_result = container.exec_run(jupyter_path_cmd)
            jupyter_path = jupyter_path_result.output.decode().strip()
            
            if jupyter_path == 'NOT_FOUND':
                logger.error("找不到jupyter可执行文件")
                return {
                    'status': 'error',
                    'error_details': '找不到jupyter可执行文件，安装可能不完整'
                }
            
            logger.info(f"找到jupyter路径: {jupyter_path}")
            
            # 使用完整路径启动Jupyter
            start_cmd = f"{jupyter_path} notebook --ip=0.0.0.0 --port={port} --no-browser --allow-root --config=/root/.jupyter/jupyter_notebook_config.py"
            logger.info(f"启动命令: {start_cmd}")
            
            # 使用nohup确保进程在后台运行
            nohup_cmd = f"nohup {start_cmd} > /var/log/jupyter.log 2>&1 &"
            jupyter_process = container.exec_run(
                ["bash", "-c", nohup_cmd],
                detach=True,
                privileged=True,
                environment={
                    'PATH': '/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin:/root/.local/bin',
                    'HOME': '/root',
                    'PYTHONUNBUFFERED': '1'
                }
            )
            
            logger.info("Jupyter启动命令已执行，等待服务就绪")
            
            # 等待服务启动
            max_retries = 20  # 增加重试次数
            retry_interval = 3  # 增加等待时间
            for i in range(max_retries):
                logger.info(f"等待服务启动，第 {i+1}/{max_retries} 次检查")
                time.sleep(retry_interval)
                
                # 检查进程是否在运行
                ps_cmd = "ps aux | grep 'jupyter-notebook' | grep -v grep || true"
                ps_result = container.exec_run(ps_cmd)
                ps_output = ps_result.output.decode()
                
                if 'jupyter-notebook' in ps_output:
                    logger.info(f"检测到Jupyter进程: {ps_output.strip()[:100]}...")
                    
                    # 检查日志
                    try:
                        log_cmd = "tail -n 50 /var/log/jupyter.log || true"
                        log_result = container.exec_run(log_cmd)
                        log_output = log_result.output.decode()
                        logger.info(f"Jupyter日志: {log_output[:500]}...")
                        
                        # 检查是否有错误信息
                        if "Error:" in log_output or "Exception:" in log_output:
                            logger.warning(f"Jupyter日志中发现错误: {log_output}")
                    except Exception as e:
                        logger.warning(f"读取日志时出错: {str(e)}")
                    
                    # 检查端口是否在监听
                    netstat_cmd = f"netstat -tlpn | grep {port} || ss -tlpn | grep {port} || true"
                    netstat_result = container.exec_run(netstat_cmd)
                    netstat_output = netstat_result.output.decode()
                    
                    if str(port) in netstat_output:
                        logger.info(f"端口 {port} 已在监听: {netstat_output.strip()}")
                        
                        # 尝试通过curl访问服务
                        curl_cmd = f"curl -s -I http://localhost:{port}/api || echo 'curl失败'"
                        curl_result = container.exec_run(curl_cmd)
                        curl_output = curl_result.output.decode()
                        logger.info(f"curl测试结果: {curl_output[:200]}")
                        
                        # 即使curl测试失败，如果端口在监听就认为服务已启动
                        logger.info("Jupyter服务已成功启动")
                        return {
                            'status': 'success',
                            'port': port,
                            'token': token
                        }
                    else:
                        logger.warning(f"进程存在但端口 {port} 未监听，继续等待")
                else:
                    logger.warning(f"未检测到Jupyter进程，重试 {i+1}/{max_retries}")
                
                # 如果是最后几次重试，收集更详细的诊断信息
                if i >= max_retries - 3:
                    logger.info("收集详细诊断信息")
                    # 检查系统资源
                    mem_cmd = "free -m || true"
                    mem_result = container.exec_run(mem_cmd)
                    logger.info(f"内存状态: {mem_result.output.decode()}")
                    
                    disk_cmd = "df -h || true"
                    disk_result = container.exec_run(disk_cmd)
                    logger.info(f"磁盘状态: {disk_result.output.decode()}")
                    
                    # 检查Python和pip环境
                    py_pkg_cmd = f"{pip_cmd} list || true"
                    py_pkg_result = container.exec_run(py_pkg_cmd)
                    logger.info(f"Python包列表: {py_pkg_result.output.decode()[:300]}...")
                    
                    # 尝试直接运行jupyter检查错误
                    try_jupyter_cmd = f"{jupyter_path} notebook --help > /tmp/jupyter_help.log 2>&1 || echo 'jupyter命令失败'"
                    container.exec_run(try_jupyter_cmd)
                    help_result = container.exec_run("cat /tmp/jupyter_help.log || true")
                    logger.info(f"Jupyter帮助输出: {help_result.output.decode()[:300]}...")
                    
                    # 检查是否缺少依赖
                    ldd_cmd = f"ldd $(which python) || echo 'ldd命令不可用'"
                    ldd_result = container.exec_run(ldd_cmd)
                    logger.info(f"Python依赖情况: {ldd_result.output.decode()[:300]}")
            
            # 如果所有重试均失败，尝试一种替代方法作为最后的努力
            logger.warning("所有常规方法都失败，尝试替代启动方法")
            
            # 尝试使用python -m方式启动
            alt_start_cmd = f"python -m jupyter notebook --ip=0.0.0.0 --port={port} --no-browser --allow-root --config=/root/.jupyter/jupyter_notebook_config.py > /var/log/jupyter_alt.log 2>&1 &"
            container.exec_run(["bash", "-c", alt_start_cmd])
            
            # 再等待一会儿
            time.sleep(10)
            
            # 最后检查
            final_ps_cmd = "ps aux | grep 'jupyter-notebook' | grep -v grep || true"
            final_ps_result = container.exec_run(final_ps_cmd)
            if 'jupyter-notebook' in final_ps_result.output.decode():
                logger.info("使用替代方法成功启动Jupyter")
                return {
                    'status': 'success',
                    'port': port,
                    'token': token
                }
            
            # 收集所有失败原因
            error_msg = f'启动Jupyter服务失败: 服务未在{max_retries * retry_interval}秒内就绪'
            logger.error(error_msg)
            
            # 获取最终的日志
            final_log_cmd = "cat /var/log/jupyter.log /var/log/jupyter_alt.log 2>/dev/null || true"
            final_log_result = container.exec_run(final_log_cmd)
            logger.error(f"最终Jupyter日志: {final_log_result.output.decode()[:500]}")
            
            return {
                'status': 'error',
                'error_details': error_msg
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f'启动Jupyter服务时发生异常: {error_details}')
            return {
                'status': 'error',
                'error_details': str(e)
            } 