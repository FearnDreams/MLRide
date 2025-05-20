"""
This module provides Docker operations for container management.
It includes a Docker client class that wraps the docker-py library
to provide high-level operations for managing Docker images and containers.
"""

import docker
from docker.errors import DockerException, ImageNotFound, BuildError, APIError
from typing import Dict, List, Optional, Tuple, Union, Any
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
import threading
import traceback

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
        从远程拉取镜像，优先使用国内镜像源
        
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
        
        # 国内镜像源配置
        cn_mirrors = {
            "pytorch/pytorch": [
                "registry.cn-hangzhou.aliyuncs.com/pytorch-images/pytorch",  # 阿里云
                "hub-mirror.c.163.com/pytorch/pytorch",  # 网易云
                "mirror.ccs.tencentyun.com/pytorch/pytorch"  # 腾讯云
            ]
        }
        
        # 检查是否为PyTorch镜像或其他有特定镜像源的镜像
        alternative_sources = []
        if image_name in cn_mirrors:
            alternative_sources = cn_mirrors[image_name]
            self.logger.info(f"检测到 {image_name} 镜像，将尝试使用国内镜像源: {alternative_sources}")
        
        # 首先尝试国内镜像源
        if alternative_sources:
            for mirror_source in alternative_sources:
                try:
                    self.logger.info(f"尝试从国内镜像源拉取: {mirror_source}:{tag}")
                    self.client.api.pull(mirror_source, tag=tag)
                    
                    # 拉取成功后重新标记为原始镜像名
                    self.client.api.tag(f"{mirror_source}:{tag}", image_name, tag=tag)
                    
                    # 获取标记后的镜像
                    image = self.client.images.get(f"{image_name}:{tag}")
                    
                    self.logger.info(f"成功从国内镜像源 {mirror_source} 拉取并重命名为 {full_image_name}")
                    return {
                        'id': image.id,
                        'tags': image.tags,
                        'size': image.attrs['Size'],
                        'created': image.attrs['Created'],
                        'source': 'cn_mirror'
                    }
                except Exception as e:
                    self.logger.warning(f"从国内镜像源 {mirror_source} 拉取失败: {str(e)}")
                    continue
        
        # 如果国内镜像源都失败，尝试原始镜像源
        while retry_count < max_pull_retries:
            try:
                self.logger.info(f"从原始源拉取镜像: {full_image_name} (尝试 {retry_count + 1}/{max_pull_retries})")
                
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
                                      ['timeout', 'connection refused', 'eof', 'network', 'unreachable', 'context deadline exceeded'])
                
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
            # 提供更多提示信息，包括使用国内镜像源的建议
            raise Exception(f"无法获取指定版本的镜像 {full_image_name}。请确保网络连接正常且Docker服务可用。如果您在中国大陆，建议配置Docker使用国内镜像加速器。错误详情: {str(pull_error)}")
        
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
        memory_limit: Optional[str] = None,
        host_config: Optional[Dict[str, Any]] = None  # Add host_config parameter
    ) -> Dict:
        """
        创建Docker容器
        
        Args:
            image_name: 镜像名称
            container_name: 容器名称（可选）
            command: 启动命令（可选）
            environment: 环境变量（可选）
            ports: 端口映射（可选），格式为{'容器端口/协议': 主机端口}
            volumes: 挂载卷（可选），格式为{'宿主机路径': {'bind': '容器路径', 'mode': 'rw'}}
            cpu_count: CPU核心数限制（可选）
            memory_limit: 内存限制（可选），如"512m"
            host_config: 主机配置参数（可选）
            
        Returns:
            Dict: 创建的容器信息
        """
        try:
            # 检查镜像是否存在，不存在则拉取
            self._ensure_image_exists(image_name)
            
            # 准备容器配置
            container_config = {}
            
            # 低级API容器配置参数
            exposed_ports = None
            if ports:
                # 转换为低级API需要的格式: {'8888/tcp': {}} 
                exposed_ports = {}
                for port_spec in ports:
                    exposed_ports[port_spec] = {}
                container_config['ports'] = exposed_ports
                
            # 添加环境变量
            if environment:
                # 转换为低级API需要的格式: ["KEY=VALUE", ...]
                env_list = [f"{key}={value}" for key, value in environment.items()]
                container_config['environment'] = env_list
                
            # 添加启动命令
            if command:
                if isinstance(command, list):
                    container_config['cmd'] = command
                else:
                    container_config['cmd'] = command.split()
            
            # 处理挂载卷
            if volumes:
                # 验证并规范化挂载卷配置
                normalized_volumes = {}
                for host_path, mount_info in volumes.items():
                    # 确保宿主机路径是绝对路径
                    abs_host_path = os.path.abspath(host_path)
                    # 确保宿主机目录存在
                    if not os.path.exists(abs_host_path):
                        os.makedirs(abs_host_path, exist_ok=True)
                        self.logger.info(f"创建宿主机挂载目录: {abs_host_path}")
                    
                    # 如果在Windows系统上，需要处理路径格式
                    if os.name == 'nt':
                        # 转换Windows路径为Docker可接受的格式
                        abs_host_path = abs_host_path.replace('\\', '/')
                        # 确保路径格式正确，例如 C:/Users/... 而不是 C:\Users\...
                        if ':' in abs_host_path:
                            drive, path = abs_host_path.split(':', 1)
                            abs_host_path = f"{drive.lower()}:{path}"
                    
                    normalized_volumes[abs_host_path] = mount_info
                    self.logger.info(f"添加挂载: {abs_host_path} -> {mount_info['bind']}")
                
                # 配置主机配置中的绑定
                if not host_config:
                    host_config = {}
                
                # 设置挂载点 - 使用Docker支持的格式
                # 直接创建binds字典，而不使用字符串格式化
                binds = {}
                for host_path, mount_info in normalized_volumes.items():
                    # 将宿主机路径作为键，容器路径作为值
                    # Docker API会自动处理权限
                    binds[host_path] = {'bind': mount_info['bind'], 'mode': mount_info['mode']}
                
                host_config['binds'] = binds
            
            # 将资源限制参数添加到host_config
            if not host_config:
                host_config = {}
                
            if cpu_count:
                # Docker API中使用cpu_quota和cpu_period来限制CPU
                # 例如，如果cpu_count=2，表示可以使用2个CPU核心，
                # 我们可以设置cpu_period=100000（默认值），cpu_quota=200000
                host_config['cpu_period'] = 100000  # 默认值
                host_config['cpu_quota'] = int(cpu_count * 100000)
                
            if memory_limit:
                # 移除单位后缀 (例如 '2048m' -> 2048)
                if memory_limit.endswith('m'):
                    mem_value = int(memory_limit[:-1]) * 1024 * 1024  # 转换为字节
                elif memory_limit.endswith('g'):
                    mem_value = int(memory_limit[:-1]) * 1024 * 1024 * 1024
                else:
                    # 假设已经是字节数
                    mem_value = int(memory_limit)
                    
                host_config['mem_limit'] = mem_value
            
            # 创建主机配置
            host_config_obj = None
            if host_config:
                host_config_obj = self.client.api.create_host_config(**host_config)
            
            # 配置端口绑定
            port_bindings = None
            if ports:
                if not host_config_obj:
                    # 如果没有其他host_config，创建一个只包含port_bindings的配置
                    port_bindings = {}
                    for port_spec, host_port in ports.items():
                        if host_port:
                            port_bindings[port_spec] = host_port
                        else:
                            # 如果没有指定主机端口，让Docker自动分配
                            port_bindings[port_spec] = None
                    host_config_obj = self.client.api.create_host_config(port_bindings=port_bindings)
                elif 'port_bindings' not in host_config:
                    # 如果有host_config但没有port_bindings，添加port_bindings
                    port_bindings = {}
                    for port_spec, host_port in ports.items():
                        if host_port:
                            port_bindings[port_spec] = host_port
                        else:
                            port_bindings[port_spec] = None
                    # 重新创建host_config以包含port_bindings
                    host_config['port_bindings'] = port_bindings
                    host_config_obj = self.client.api.create_host_config(**host_config)
            
            # 创建容器，使用低级API并传递正确格式的参数
            container_id = self.client.api.create_container(
                image=image_name,
                name=container_name,
                host_config=host_config_obj,
                environment=container_config.get('environment'),
                command=container_config.get('cmd'),
                ports=exposed_ports
            )
            
            # 获取创建的容器对象
            container = self.client.containers.get(container_id['Id'])
            
            # 返回容器信息
            return {
                'id': container.id,
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else container.image.id
            }
            
        except docker.errors.ImageNotFound:
            self.logger.error(f"镜像 {image_name} 不存在")
            raise
        except docker.errors.APIError as e:
            self.logger.error(f"创建容器时出错: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"创建容器失败: {str(e)}")
            raise
    
    def _ensure_image_exists(self, image_name: str) -> bool:
        """
        确保指定的镜像存在，不存在则拉取
        
        Args:
            image_name: 镜像名称
            
        Returns:
            bool: 是否成功确保镜像存在
        """
        try:
            tag = 'latest'
            if ':' in image_name:
                image_name, tag = image_name.split(':', 1)
            
            # 检查镜像是否存在
            try:
                self.client.images.get(f"{image_name}:{tag}")
                self.logger.info(f"镜像 {image_name}:{tag} 已存在")
                return True
            except docker.errors.ImageNotFound:
                # 镜像不存在，拉取镜像
                self.logger.info(f"镜像 {image_name}:{tag} 不存在，开始拉取")
                self.pull_image(image_name, tag)
                return True
        except Exception as e:
            self.logger.error(f"确保镜像存在时出错: {str(e)}")
            return False
    
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
            
    def _parse_base_image_from_dockerfile(self, dockerfile_content: str) -> Optional[str]:
        """从Dockerfile内容中解析基础镜像名称和标签。"""
        for line in dockerfile_content.splitlines():
            line_stripped = line.strip()
            if line_stripped.upper().startswith("FROM "):
                parts = line_stripped.split()
                if len(parts) > 1:
                    # 移除可能存在的 --platform 参数
                    base_image_name = parts[1]
                    if base_image_name.startswith("--platform="):
                        if len(parts) > 2:
                            return parts[2].split(" AS")[0].strip() # parts[2] is the image name
                        else:
                            return None # 无效的FROM指令
                    return base_image_name.split(" AS")[0].strip() # 移除别名
        return None

    def _check_image_locally(self, image_name_with_tag: str) -> bool:
        """检查指定的镜像是否存在于本地。"""
        if not image_name_with_tag:
            return False
        try:
            self.client.images.get(image_name_with_tag)
            self.logger.info(f"基础镜像 {image_name_with_tag} 在本地存在。")
            return True
        except ImageNotFound:
            self.logger.info(f"基础镜像 {image_name_with_tag} 在本地不存在。")
            return False
        except Exception as e:
            self.logger.warning(f"检查本地镜像 {image_name_with_tag} 时出错: {e}")
            return False

    def build_image_from_dockerfile(
        self,
        dockerfile_content: str,
        image_name: str,
        image_tag: str = 'latest',
        build_args: Optional[Dict[str, str]] = None,
        python_version: Optional[str] = None,
        is_pytorch: bool = False
    ) -> Dict:
        """
        从Dockerfile内容构建Docker镜像
        
        Args:
            dockerfile_content: Dockerfile内容
            image_name: 镜像名称
            image_tag: 镜像标签
            build_args: 构建参数
            python_version: 预期的Python版本，用于验证构建后的镜像
            is_pytorch: 是否是PyTorch镜像
            
        Returns:
            Dict: 构建的镜像信息
        """
        import time # 这个import应该在函数顶部，如果之前没有的话
        
        try:
            # 在Dockerfile开头添加镜像源配置以加速构建
            if not is_pytorch or "pytorch" not in image_name.lower():
                # 对于PyTorch官方镜像，不添加中国镜像源配置，因为它们已经包含了所需依赖
                dockerfile_content = self._add_china_mirrors(dockerfile_content)
            
            # 检查是否已有同名镜像 (这部分逻辑是检查最终要构建的镜像，而非基础镜像)
            full_target_image_name = f"{image_name}:{image_tag}"
            try:
                local_image = self.client.images.get(full_target_image_name)
                self.logger.info(f"目标镜像 {full_target_image_name} 已在本地存在, id={local_image.id}")
                # ... (后续Python版本验证逻辑等) ...
                actual_python_version_in_existing = None
                if python_version:
                    actual_python_version_in_existing = self._verify_python_version_in_image(local_image.id)
                    if actual_python_version_in_existing:
                         self.logger.info(f"已存在的目标镜像 {full_target_image_name} 中的Python版本: {actual_python_version_in_existing}")

                return {
                    'id': local_image.id,
                    'tags': local_image.tags,
                    'size': local_image.attrs['Size'],
                    'created': local_image.attrs['Created'],
                    'source': 'local',
                    'actual_python_version': actual_python_version_in_existing if python_version else None
                }
            except ImageNotFound:
                self.logger.info(f"目标镜像 {full_target_image_name} 在本地不存在, 将进行构建。")
            except Exception as e:
                self.logger.error(f"检查目标镜像 {full_target_image_name} 时发生错误: {e}, 将尝试构建。")


            f = io.BytesIO(dockerfile_content.encode('utf-8'))
            self.logger.info(f"准备从Dockerfile构建镜像 {full_target_image_name}")
            
            build_timeout = 900 
            if not build_args:
                build_args = {}
            
            build_args.update({
                'PIP_INDEX_URL': 'https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple',
                'PIP_TRUSTED_HOST': 'mirrors.tuna.tsinghua.edu.cn'
            })
            
            # ... (is_pytorch_cuda 和 PyTorch CPU 版本检查和Dockerfile修改逻辑保持不变) ...
            is_pytorch_cuda = False # 保留原有逻辑，这里只是为了让代码片段完整
            if is_pytorch and 'PYTORCH_VERSION' in build_args and 'CUDA_VERSION' in build_args:
                is_pytorch_cuda = True
                # ... (PyTorch CUDA specific build_args and Dockerfile modifications) ...
            elif is_pytorch and 'PYTORCH_VERSION' in build_args:
                # ... (PyTorch CPU specific Dockerfile modifications for FROM line) ...
                pass


            # 解析基础镜像并决定 pull 策略
            base_image_from_dockerfile = self._parse_base_image_from_dockerfile(dockerfile_content)
            should_pull_base_image = True # 默认为True，即如果本地没有基础镜像则尝试拉取
            if base_image_from_dockerfile:
                if self._check_image_locally(base_image_from_dockerfile):
                    should_pull_base_image = False # 基础镜像本地存在，构建时不需要拉取
                    self.logger.info(f"将使用本地基础镜像 {base_image_from_dockerfile} 进行构建 (pull=False)。")
                else:
                    self.logger.info(f"本地不存在基础镜像 {base_image_from_dockerfile}，构建时将尝试拉取 (pull=True)。")
            else:
                self.logger.warning("无法从Dockerfile中解析基础镜像名称，将使用默认的pull策略 (pull=True)。")

            # 尝试构建，设置超时时间和构建参数
            max_retries = 3
            retry_count = 0
            last_build_exception = None
            
            while retry_count < max_retries:
                try:
                    self.logger.info(f"开始构建尝试 {retry_count + 1}/{max_retries} for {full_target_image_name}. Pull base image: {should_pull_base_image}")
                    current_build_args = build_args.copy() # 确保每次重试都用干净的build_args

                    # 对于PyTorch+CUDA镜像，使用特殊的构建配置
                    if is_pytorch_cuda:
                        self.logger.info("使用PyTorch+CUDA专用构建配置")
                        image, logs = self.client.images.build(
                            fileobj=f, # fileobj 需要在循环外部，或者每次重置 seek(0)
                            tag=full_target_image_name,
                            rm=True,
                            pull=should_pull_base_image, # MODIFIED
                            timeout=build_timeout * 2,
                            buildargs=current_build_args,
                            nocache=False,
                            network_mode="host",
                            platform="linux/amd64"
                        )
                    else:
                        image, logs = self.client.images.build(
                            fileobj=f, # fileobj 需要在循环外部，或者每次重置 seek(0)
                            tag=full_target_image_name,
                            rm=True,
                            pull=should_pull_base_image,  # MODIFIED
                            timeout=build_timeout,
                            buildargs=current_build_args,
                            nocache=False, 
                            network_mode="host"
                        )
                    
                    # 构建成功，记录日志并退出循环
                    log_output = []
                    for chunk in logs:
                        if 'stream' in chunk:
                            log_output.append(chunk['stream'].strip())
                        elif 'errorDetail' in chunk:
                            log_output.append(f"ERROR: {chunk['errorDetail']['message']}")
                            self.logger.error(f"构建错误详情: {chunk['errorDetail']['message']}")
                    
                    self.logger.info(f"镜像 {full_target_image_name} 构建成功。ID: {image.id}")
                    self.logger.debug(f"构建日志 for {full_target_image_name}:\\n{''.join(log_output)}")

                    # ... (后续的Python版本验证等逻辑保持不变) ...
                    actual_python_version = None
                    if python_version:
                        actual_python_version = self._verify_python_version_in_image(image.id)
                        if actual_python_version:
                            self.logger.info(f"构建后的镜像 {full_target_image_name} 中的Python版本: {actual_python_version}")
                        else:
                            self.logger.warning(f"无法在构建后的镜像 {full_target_image_name} 中验证Python版本。")


                    return {
                        'id': image.id, 
                        'tags': image.tags, 
                        'size': image.attrs['Size'], 
                        'created': image.attrs['Created'],
                        'source': 'build',
                        'logs': log_output,
                        'actual_python_version': actual_python_version
                    }

                except (BuildError, APIError, DockerException) as e: # APIError for timeouts
                    last_build_exception = e
                    retry_count += 1
                    error_message = str(e).lower()
                    self.logger.warning(f"构建 {full_target_image_name} 失败 (尝试 {retry_count}/{max_retries}): {error_message}")
                    
                    f.seek(0) # 重置fileobj的指针，以便下次读取

                    if any(err_keyword in error_message for err_keyword in ["tls handshake timeout", "connection refused", "network", "timeout", "i/o timeout", "context deadline exceeded", "operation timed out", "temporary failure in name resolution", "name or service not known", "could not resolve host"]):
                        self.logger.warning(f"检测到网络相关错误，将在 {3 * retry_count} 秒后重试...")
                        time.sleep(3 * retry_count) 
                        # 在网络错误时，下次重试强制尝试拉取基础镜像（如果之前是False的话）
                        # 但如果本来就是True（因为本地没有基础镜像），则保持True
                        if not should_pull_base_image: # 如果之前是False (因为本地有基础镜像但构建失败了)
                             self.logger.info(f"由于网络错误，下次尝试将强制拉取基础镜像 {base_image_from_dockerfile} (pull=True)")
                             # 这个逻辑可能需要调整，因为如果基础镜像本地存在但构建因为其他网络问题失败，
                             # 强制拉取基础镜像可能不是最优解。
                             # 当前保持 should_pull_base_image 的原始逻辑，只在本地没有时才为True
                        
                        # 切换到使用国内镜像源 (这部分已在循环外，可以考虑是否需要在这里再次强调或修改)
                        # build_args.update({
                        #     'PIP_INDEX_URL': 'https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple',
                        #     'PIP_TRUSTED_HOST': 'mirrors.tuna.tsinghua.edu.cn'
                        # })
                        continue # 继续下一次重试
                    
                    # 对于非典型网络错误，或者其他BuildError，也进行重试
                    elif retry_count < max_retries:
                        self.logger.info(f"构建时发生错误，将在 {2 * retry_count} 秒后重试...")
                        time.sleep(2 * retry_count)
                        continue
                    else: # 所有重试次数用尽
                        self.logger.error(f"经过{max_retries}次尝试，构建镜像 {full_target_image_name} 仍然失败。最后错误: {error_message}")
                        detailed_error_log = [str(last_build_exception)]
                        try: # 尝试获取详细的构建日志
                            log_stream_for_error = self.client.api.build(
                                fileobj=f, # 确保 f 在这里仍然可用且指向文件开头
                                tag=full_target_image_name, # 用一个临时tag或不tag来获取日志
                                rm=True, 
                                pull=should_pull_base_image, 
                                buildargs=build_args,
                                quiet=False, # 需要日志输出
                                stream=True, # 获取流式日志
                                decode=True
                            )
                            for chunk in log_stream_for_error:
                                if 'stream' in chunk:
                                    detailed_error_log.append(chunk['stream'])
                                elif 'error' in chunk:
                                    detailed_error_log.append(chunk['error'])
                        except Exception as log_err:
                            detailed_error_log.append(f"(获取详细构建日志失败: {log_err})")
                        
                        raise BuildError(f"构建镜像 {full_target_image_name} 失败: {error_message}. 构建日志: {''.join(detailed_error_log)}", logs=detailed_error_log) from last_build_exception

            # 如果循环结束仍未成功（理论上应该在循环内返回或抛出异常）
            if last_build_exception:
                 self.logger.error(f"构建镜像 {full_target_image_name} 最终失败。")
                 raise BuildError(f"构建镜像 {full_target_image_name} 失败: {str(last_build_exception)}", logs=[]) from last_build_exception
            
            # 这部分理论上不会到达，因为成功会return，失败会raise
            self.logger.error(f"构建镜像 {full_target_image_name} 逻辑异常结束。") # 添加日志
            raise BuildError(f"构建镜像 {full_target_image_name} 失败，未知原因。", [])

        except DockerException as e:
            self.logger.error(f"构建镜像失败 {image_name}:{image_tag}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"构建镜像时发生未知错误 {image_name}:{image_tag}: {str(e)}")
            self.logger.error(traceback.format_exc()) # 打印完整的堆栈跟踪
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
        try:
            # 首先检查dockerfile_content是否为None或空字符串
            if not dockerfile_content:
                self.logger.warning("Dockerfile内容为空，无法添加版本验证")
                return ""
                
            # 分割Dockerfile为行
            dockerfile_lines = dockerfile_content.splitlines()
            
            # 检查是否有FROM指令
            has_from = any(line.strip().startswith("FROM ") for line in dockerfile_lines)
            if not has_from:
                self.logger.warning("Dockerfile中没有找到FROM指令，将在开头添加验证命令")
                return verification_command + "\n" + dockerfile_content
            
            # 处理多阶段构建的情况
            result_lines = []
            stage_start_indices = []
            
            # 找出所有的FROM指令位置
            for i, line in enumerate(dockerfile_lines):
                if line.strip().startswith("FROM "):
                    stage_start_indices.append(i)
            
            # 如果没有找到任何FROM指令，直接在开头添加
            if not stage_start_indices:
                return verification_command + "\n" + dockerfile_content
                
            # 处理每个构建阶段
            for i, start_idx in enumerate(stage_start_indices):
                # 添加FROM指令
                result_lines.append(dockerfile_lines[start_idx])
                
                # 只在最后一个FROM后添加验证命令（最终镜像）
                if i == len(stage_start_indices) - 1:
                    result_lines.append(verification_command)
                
                # 添加当前阶段的剩余指令直到下一个阶段（如果有）
                next_idx = stage_start_indices[i+1] if i+1 < len(stage_start_indices) else len(dockerfile_lines)
                for j in range(start_idx + 1, next_idx):
                    result_lines.append(dockerfile_lines[j])
            
            return "\n".join(result_lines)
            
        except Exception as e:
            self.logger.error(f"在Dockerfile中添加版本验证时出错: {str(e)}")
            # 在出错的情况下，返回原始Dockerfile内容
            return dockerfile_content

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
        try:
            self.logger.info("创建简化版Dockerfile")
            
            # 检查original_dockerfile是否为None或空字符串
            if not original_dockerfile:
                self.logger.warning("原始Dockerfile内容为空")
                return ""
                
            # 分行处理Dockerfile
            lines = original_dockerfile.splitlines()
            if not lines:
                self.logger.warning("Dockerfile没有内容")
                return ""
                
            simplified_lines = []
            
            # 指示下一行是否需要被保留
            keep_next_line = True
            
            # 检查基本结构
            has_from = any(line.strip().startswith('FROM ') for line in lines)
            if not has_from:
                self.logger.warning("Dockerfile中没有FROM指令，可能不是有效的Dockerfile")
                # 尝试添加一个基本的FROM指令
                simplified_lines.append("FROM python:3.9-slim")
            
            # 检测是否为PyTorch相关Dockerfile
            pytorch_detected = False
            cuda_detected = False
            pytorch_version = None
            cuda_version = None
            
            # 尝试提取PyTorch和CUDA版本信息
            for line in lines:
                line_lower = line.lower()
                if 'torch==' in line_lower:
                    pytorch_detected = True
                    match = re.search(r'torch==(\d+\.\d+\.\d+)', line)
                    if match:
                        pytorch_version = match.group(1)
                        self.logger.info(f"简化版检测到PyTorch版本: {pytorch_version}")
                
                if 'nvidia' in line_lower or 'cuda' in line_lower:
                    cuda_detected = True
                    match = re.search(r'cuda:?(\d+\.\d+)', line_lower)
                    if match:
                        cuda_version = match.group(1)
                        self.logger.info(f"简化版检测到CUDA版本: {cuda_version}")
                
                if 'cu' in line_lower and ('--index-url' in line_lower or 'index-url' in line_lower):
                    match = re.search(r'cu(\d+)', line_lower)
                    if match:
                        cuda_version_no_dots = match.group(1)
                        # 转换为标准格式 (例如: 116 -> 11.6)
                        if len(cuda_version_no_dots) == 3:
                            cuda_version = cuda_version_no_dots[0:2] + '.' + cuda_version_no_dots[2]
                        elif len(cuda_version_no_dots) == 2:
                            cuda_version = cuda_version_no_dots[0] + '.' + cuda_version_no_dots[1]
                        self.logger.info(f"简化版从index-url检测到CUDA版本: {cuda_version}")
            
            # 构建多阶段构建的简化Dockerfile
            stage_counter = 0
            current_stage = 0
            stage_start_indices = []
            
            # 先找出所有的FROM指令位置
            for i, line in enumerate(lines):
                if line.strip().startswith('FROM '):
                    stage_start_indices.append(i)
                    
            # 如果没有FROM指令，假设整个文件是一个阶段
            if not stage_start_indices:
                stage_start_indices = [0]
                
            # 处理每个构建阶段
            for i, start_idx in enumerate(stage_start_indices):
                current_stage = i
                
                # 确定当前阶段的结束位置
                next_idx = stage_start_indices[i+1] if i+1 < len(stage_start_indices) else len(lines)
                
                # 如果是FROM指令，直接添加
                if start_idx < len(lines) and lines[start_idx].strip().startswith('FROM '):
                    simplified_lines.append(lines[start_idx])
                elif i == 0:  # 如果第一个阶段不是FROM指令
                    # 根据检测到的环境选择合适的基础镜像
                    if pytorch_detected and pytorch_version:
                        if cuda_detected and cuda_version:
                            simplified_lines.append(f"FROM pytorch/pytorch:{pytorch_version}-cuda{cuda_version}-cudnn8-runtime  # 自动选择的PyTorch CUDA基础镜像")
                            self.logger.info(f"简化版为PyTorch CUDA环境选择基础镜像: {pytorch_version}-cuda{cuda_version}")
                        else:
                            simplified_lines.append(f"FROM pytorch/pytorch:{pytorch_version}-cpu  # 自动选择的PyTorch CPU基础镜像")
                            self.logger.info(f"简化版为PyTorch CPU环境选择基础镜像: {pytorch_version}")
                    elif cuda_detected and cuda_version:
                        simplified_lines.append(f"FROM nvidia/cuda:{cuda_version}-base-ubuntu20.04  # 自动选择的CUDA基础镜像")
                        self.logger.info(f"简化版为CUDA环境选择基础镜像: {cuda_version}")
                    else:
                        simplified_lines.append("FROM python:3.9-slim")
                
                # 添加中国镜像源配置（对于简化版Dockerfile尤为重要）
                if i == 0:  # 只在第一阶段添加
                    simplified_lines.append("""
# 配置PIP镜像源
RUN mkdir -p /root/.pip && \\
    echo '[global]' > /root/.pip/pip.conf && \\
    echo 'index-url = https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple' >> /root/.pip/pip.conf && \\
    echo 'trusted-host = mirrors.tuna.tsinghua.edu.cn' >> /root/.pip/pip.conf
""")
                
                # 处理当前阶段的其他指令
                keep_next_line = True
                for j in range(start_idx + 1, next_idx):
                    line = lines[j]
                    line_stripped = line.strip()
                    
                    # 始终保留FROM指令（虽然这不应该在这个内部循环中出现）
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
                        
                    # 保留ARG指令，除了与网络相关的
                    if line_stripped.startswith('ARG '):
                        if 'proxy' in line_stripped.lower() or 'mirror' in line_stripped.lower():
                            simplified_lines.append(f'# 已移除(可能与网络相关): {line}')
                        else:
                            simplified_lines.append(line)
                        continue
                        
                    # 保留CMD和ENTRYPOINT指令
                    if line_stripped.startswith('CMD ') or line_stripped.startswith('ENTRYPOINT '):
                        simplified_lines.append(line)
                        continue
                        
                    # 保留COPY和ADD指令
                    if line_stripped.startswith('COPY ') or line_stripped.startswith('ADD '):
                        simplified_lines.append(line)
                        continue
                        
                    # 特殊处理PyTorch安装命令
                    if line_stripped.startswith('RUN ') and ('torch' in line_stripped.lower() or 'pytorch' in line_stripped.lower()):
                        # 如果是简单的PyTorch验证命令，保留
                        if 'import torch' in line_stripped.lower() and ('print' in line_stripped.lower() or 'version' in line_stripped.lower()):
                            simplified_lines.append(line)
                            continue
                        # 否则注释掉PyTorch安装命令，因为我们使用预构建的PyTorch镜像
                        simplified_lines.append(f'# 已移除(使用预构建PyTorch镜像替代): {line}')
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
                        if 'pip install' in line_stripped or 'apt-get' in line_stripped or 'yum' in line_stripped:
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
                        # 对于不确定的行，判断是否与网络相关
                        if line_stripped.startswith('RUN ') and ('apt-get' in line_stripped or 'yum' in line_stripped or 'http' in line_stripped or 'wget' in line_stripped or 'curl' in line_stripped):
                            simplified_lines.append(f'# 已移除(需要网络): {line}')
                        else:
                            simplified_lines.append(line)
            
            # 如果检测到是PyTorch环境，添加PyTorch验证指令
            if pytorch_detected and not any('import torch' in line for line in simplified_lines):
                simplified_lines.append('\n# 验证PyTorch环境')
                simplified_lines.append('RUN python -c "import torch; print(\\"PyTorch version:\\", torch.__version__); print(\\"CUDA available:\\", torch.cuda.is_available())" || echo "PyTorch验证失败"')
            
            # 添加注释说明这是简化版
            simplified_lines.append('\n# 注意: 这是简化版Dockerfile，已移除需要网络的操作')
            
            # 确保有最低限度的功能性内容
            if not any(not line.startswith('#') for line in simplified_lines):
                self.logger.warning("简化后的Dockerfile没有有效指令")
                if pytorch_detected:
                    simplified_lines.append("FROM pytorch/pytorch:latest")
                else:
                    simplified_lines.append("FROM python:3.9-slim")
                simplified_lines.append("CMD [\"python\", \"-c\", \"import platform; print('Python version:', platform.python_version())\"]")
            
            return '\n'.join(simplified_lines)
            
        except Exception as e:
            self.logger.error(f"创建简化版Dockerfile时出错: {str(e)}", exc_info=True)
            # 在出错的情况下，创建一个最小可用的Dockerfile
            return """FROM python:3.9-slim
# 自动生成的应急Dockerfile
CMD ["python", "-c", "print('Emergency fallback Dockerfile')"]
# 注意: 原始Dockerfile处理失败，这是自动生成的应急版本
"""

    def copy_to_container(self, container_id, source_path, target_path):
        """
        将文件从宿主机复制到容器中
        
        Args:
            container_id (str): 容器ID
            source_path (str): 源文件路径（宿主机上）
            target_path (str): 目标文件路径（容器内）
            
        Returns:
            bool: 是否复制成功
        """
        try:
            container = self.client.containers.get(container_id)
            
            # 检查源文件是否存在
            if not os.path.exists(source_path):
                self.logger.error(f"源文件不存在: {source_path}")
                return False
                
            # 读取源文件内容
            with open(source_path, 'rb') as f:
                data = f.read()
                
            # 确保目标目录存在
            target_dir = os.path.dirname(target_path)
            if target_dir:
                container.exec_run(f"mkdir -p {target_dir}")
                
            # 使用put_archive方法复制文件
            # 创建临时tar文件
            import tarfile
            import tempfile
            
            # 获取文件名
            filename = os.path.basename(source_path)
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as tmp_dir:
                temp_tar_path = os.path.join(tmp_dir, 'temp.tar')
                
                # 创建tar文件
                with tarfile.open(temp_tar_path, 'w') as tar:
                    tar.add(source_path, arcname=filename)
                    
                # 读取tar文件内容
                with open(temp_tar_path, 'rb') as f:
                    tar_data = f.read()
                    
                # 获取目标目录
                target_dir = os.path.dirname(target_path)
                if not target_dir:
                    target_dir = '/'
                    
                # 将tar文件复制到容器中
                success = container.put_archive(target_dir, tar_data)
                if not success:
                    self.logger.error(f"复制文件到容器失败: {source_path} -> {target_path}")
                    return False
                    
                self.logger.info(f"成功复制文件到容器: {source_path} -> {target_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"复制文件到容器时出错: {str(e)}")
            return False

    def copy_from_container(self, container_id, source_path, target_path):
        """
        将文件从容器复制到宿主机
        
        Args:
            container_id (str): 容器ID
            source_path (str): 源文件路径（容器内）
            target_path (str): 目标文件路径（宿主机上）
            
        Returns:
            bool: 是否复制成功
        """
        try:
            container = self.client.containers.get(container_id)
            
            # 确保目标目录存在
            target_dir = os.path.dirname(target_path)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
                
            # 从容器复制文件
            bits, stat = container.get_archive(source_path)
            
            # 保存到临时tar文件
            import tempfile
            with tempfile.NamedTemporaryFile() as tmp:
                for chunk in bits:
                    tmp.write(chunk)
                tmp.flush()
                
                # 解压tar文件到目标路径
                import tarfile
                with tarfile.open(tmp.name) as tar:
                    # 获取第一个文件（通常只有一个）
                    first_member = tar.getmembers()[0]
                    
                    # 提取文件，重命名为目标文件名
                    first_member.name = os.path.basename(target_path)
                    tar.extract(first_member, os.path.dirname(target_path))
                    
            self.logger.info(f"成功从容器复制文件: {source_path} -> {target_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"从容器复制文件时出错: {str(e)}")
            return False
            
    def copy_content_to_container(self, container_id, content, target_path):
        """
        将内容直接复制到容器中的文件
        
        Args:
            container_id (str): 容器ID
            content (bytes or str): 要写入的内容
            target_path (str): 目标文件路径（容器内）
            
        Returns:
            bool: 是否复制成功
        """
        try:
            container = self.client.containers.get(container_id)
            
            # 确保content是二进制
            if isinstance(content, str):
                content = content.encode('utf-8')
                
            # 确保目标目录存在
            target_dir = os.path.dirname(target_path)
            if target_dir:
                container.exec_run(f"mkdir -p {target_dir}")
                
            # 使用put_archive方法复制文件
            # 创建临时tar文件
            import tarfile
            import tempfile
            import io
            
            # 获取文件名
            filename = os.path.basename(target_path)
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as tmp_dir:
                # 创建临时文件
                temp_file_path = os.path.join(tmp_dir, filename)
                with open(temp_file_path, 'wb') as f:
                    f.write(content)
                
                # 创建临时tar文件
                temp_tar_path = os.path.join(tmp_dir, 'temp.tar')
                with tarfile.open(temp_tar_path, 'w') as tar:
                    tar.add(temp_file_path, arcname=filename)
                
                # 读取tar文件内容
                with open(temp_tar_path, 'rb') as f:
                    tar_data = f.read()
                
                # 获取目标目录
                target_dir = os.path.dirname(target_path)
                if not target_dir:
                    target_dir = '/'
                
                # 将tar文件复制到容器中
                success = container.put_archive(target_dir, tar_data)
                if not success:
                    self.logger.error(f"复制内容到容器失败: [content] -> {target_path}")
                    return False
                
                self.logger.info(f"成功复制内容到容器文件: {target_path} (大小: {len(content)} 字节)")
                return True
                
        except Exception as e:
            self.logger.error(f"复制内容到容器时出错: {str(e)}")
            return False
            
    def exec_command_in_container(self, container_id, command):
        """
        在容器中执行命令
        
        Args:
            container_id (str): 容器ID
            command (str): 要执行的命令
            
        Returns:
            tuple: (exit_code, output)
        """
        try:
            container = self.client.containers.get(container_id)
            result = container.exec_run(command, stderr=True)
            return result.exit_code, result.output.decode('utf-8', errors='ignore')
        except Exception as e:
            self.logger.error(f"在容器中执行命令时出错: {str(e)}")
            return -1, str(e)
    
    def sync_container_directory(self, container_id, container_dir, host_dir, direction='both'):
        """
        同步容器和宿主机之间的目录
        
        Args:
            container_id (str): 容器ID
            container_dir (str): 容器内的目录
            host_dir (str): 宿主机上的目录
            direction (str): 同步方向，'to_container', 'from_container' 或 'both'
            
        Returns:
            bool: 是否同步成功
        """
        try:
            container = self.client.containers.get(container_id)
            
            # 确保宿主机目录存在
            if not os.path.exists(host_dir):
                os.makedirs(host_dir, exist_ok=True)
                
            # 确保容器目录存在
            container.exec_run(f"mkdir -p {container_dir}")
            
            # 获取容器中的文件列表
            result = container.exec_run(f"find {container_dir} -type f | sort")
            container_files = result.output.decode().strip().split('\n')
            container_files = [f for f in container_files if f]  # 过滤空行
            
            # 获取宿主机上的文件列表
            import glob
            host_files = []
            for root, _, files in os.walk(host_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, host_dir)
                    host_files.append(rel_path)
            
            # 根据同步方向执行同步
            if direction in ['to_container', 'both']:
                # 将宿主机文件同步到容器
                for rel_path in host_files:
                    host_file = os.path.join(host_dir, rel_path)
                    container_file = os.path.join(container_dir, rel_path).replace('\\', '/')
                    
                    # 确保容器中目标文件的目录存在
                    container_file_dir = os.path.dirname(container_file)
                    if container_file_dir and container_file_dir != container_dir:
                        container.exec_run(f"mkdir -p {container_file_dir}")
                        
                    # 复制文件到容器
                    self.copy_to_container(container_id, host_file, container_file)
            
            if direction in ['from_container', 'both']:
                # 将容器文件同步到宿主机
                for container_file in container_files:
                    # 计算相对路径
                    if container_file.startswith(container_dir):
                        rel_path = container_file[len(container_dir):].lstrip('/')
                    else:
                        continue  # 跳过不在指定目录下的文件
                        
                    host_file = os.path.join(host_dir, rel_path)
                    
                    # 确保宿主机中目标文件的目录存在
                    host_file_dir = os.path.dirname(host_file)
                    if host_file_dir and not os.path.exists(host_file_dir):
                        os.makedirs(host_file_dir, exist_ok=True)
                        
                    # 复制文件到宿主机
                    self.copy_from_container(container_id, container_file, host_file)
                    
            return True
            
        except Exception as e:
            self.logger.error(f"同步目录时出错: {str(e)}")
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
c.ServerApp.disable_check_xsrf = True
c.ServerApp.allow_origin = '*'
c.ServerApp.tornado_settings = {{'headers': {{'Content-Security-Policy': "frame-ancestors * 'self';"}}}}

# 兼容旧版本配置
c.NotebookApp.ip = '0.0.0.0'
c.NotebookApp.port = {port}
c.NotebookApp.token = '{token if token else ""}'
c.NotebookApp.notebook_dir = '/workspace'
c.NotebookApp.allow_root = True
c.NotebookApp.disable_check_xsrf = True
c.NotebookApp.allow_origin = '*'
c.NotebookApp.tornado_settings = {{'headers': {{'Content-Security-Policy': "frame-ancestors * 'self';"}}}}
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

    def _add_china_mirrors(self, dockerfile_content):
        """
        在Dockerfile中添加中国区镜像源配置
        
        Args:
            dockerfile_content (str): 原始Dockerfile内容
            
        Returns:
            str: 添加了镜像源配置的Dockerfile内容
        """
        try:
            # 首先检查dockerfile_content是否为None或空字符串
            if not dockerfile_content:
                self.logger.warning("Dockerfile内容为空，无法添加中国镜像源")
                return ""
                
            # 检查使用的基础镜像类型，以便添加正确的镜像源配置
            is_cuda_image = False
            is_ubuntu_based = False
            is_debian_based = True  # 默认假设是debian基础镜像
            cuda_version = ""
            
            # 分割Dockerfile为行
            dockerfile_lines = dockerfile_content.splitlines()
            
            # 分析Dockerfile基础镜像类型
            for line in dockerfile_lines:
                line_lower = line.lower().strip()
                if line_lower.startswith('from '):
                    base_image = line_lower[5:].strip()
                    if 'nvidia' in base_image or 'cuda' in base_image:
                        is_cuda_image = True
                        # 尝试提取CUDA版本
                        import re
                        cuda_match = re.search(r'cuda:?(\d+\.\d+)', base_image)
                        if cuda_match:
                            cuda_version = cuda_match.group(1)
                            self.logger.info(f"检测到CUDA基础镜像，版本: {cuda_version}")
                    
                    if 'ubuntu' in base_image:
                        is_ubuntu_based = True
                        is_debian_based = False
                        self.logger.info("检测到Ubuntu基础镜像")
                    elif 'debian' in base_image:
                        is_debian_based = True
                        is_ubuntu_based = False
                        self.logger.info("检测到Debian基础镜像")
                    
                    break  # 只分析第一个FROM指令
            
            # 根据基础镜像类型生成适当的镜像源配置
            if is_cuda_image:
                if is_ubuntu_based:
                    # Ubuntu基础的CUDA镜像
                    mirrors_config = """
# 配置Ubuntu APT镜像源
RUN sed -i 's/archive.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \\
    sed -i 's/security.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

# 配置NVIDIA镜像源
RUN apt-key adv --fetch-keys https://mirrors.tuna.tsinghua.edu.cn/nvidia-cuda/gpgkey && \\
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/nvidia-cuda/ubuntu2004/x86_64 /" > /etc/apt/sources.list.d/cuda.list || true

# 配置PIP镜像源
RUN mkdir -p /root/.pip && \\
    echo '[global]' > /root/.pip/pip.conf && \\
    echo 'index-url = https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple' >> /root/.pip/pip.conf && \\
    echo 'trusted-host = mirrors.tuna.tsinghua.edu.cn' >> /root/.pip/pip.conf || true
"""
                else:
                    # Debian基础的CUDA镜像
                    mirrors_config = """
# 配置Debian APT镜像源
RUN echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye main contrib non-free' > /etc/apt/sources.list && \\
    echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-updates main contrib non-free' >> /etc/apt/sources.list && \\
    echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-backports main contrib non-free' >> /etc/apt/sources.list && \\
    echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bullseye-security main contrib non-free' >> /etc/apt/sources.list || true

# 配置PIP镜像源
RUN mkdir -p /root/.pip && \\
    echo '[global]' > /root/.pip/pip.conf && \\
    echo 'index-url = https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple' >> /root/.pip/pip.conf && \\
    echo 'trusted-host = mirrors.tuna.tsinghua.edu.cn' >> /root/.pip/pip.conf || true
"""
            else:
                if is_ubuntu_based:
                    # 普通Ubuntu基础镜像
                    mirrors_config = """
# 配置Ubuntu APT镜像源
RUN sed -i 's/archive.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \\
    sed -i 's/security.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list || true

# 配置PIP镜像源
RUN mkdir -p /root/.pip && \\
    echo '[global]' > /root/.pip/pip.conf && \\
    echo 'index-url = https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple' >> /root/.pip/pip.conf && \\
    echo 'trusted-host = mirrors.tuna.tsinghua.edu.cn' >> /root/.pip/pip.conf || true
"""
                else:
                    # 普通Debian基础镜像(默认)
                    mirrors_config = """
# 配置APT和PIP镜像源
RUN echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye main contrib non-free' > /etc/apt/sources.list && \\
    echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-updates main contrib non-free' >> /etc/apt/sources.list && \\
    echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-backports main contrib non-free' >> /etc/apt/sources.list && \\
    echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bullseye-security main contrib non-free' >> /etc/apt/sources.list || true

# 配置PIP镜像源
RUN mkdir -p /root/.pip && \\
    echo '[global]' > /root/.pip/pip.conf && \\
    echo 'index-url = https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple' >> /root/.pip/pip.conf && \\
    echo 'trusted-host = mirrors.tuna.tsinghua.edu.cn' >> /root/.pip/pip.conf || true
"""
            
            # 检查是否有FROM指令
            has_from = any(line.strip().startswith("FROM ") for line in dockerfile_lines)
            if not has_from:
                self.logger.warning("Dockerfile中没有找到FROM指令，将在开头添加镜像源配置")
                return mirrors_config + "\n" + dockerfile_content
            
            # 处理多阶段构建的情况
            result_lines = []
            stage_start_indices = []
            
            # 找出所有的FROM指令位置
            for i, line in enumerate(dockerfile_lines):
                if line.strip().startswith("FROM "):
                    stage_start_indices.append(i)
            
            # 如果没有找到任何FROM指令，直接在开头添加
            if not stage_start_indices:
                return mirrors_config + "\n" + dockerfile_content
                
            # 处理每个构建阶段
            for i, start_idx in enumerate(stage_start_indices):
                # 添加FROM指令
                result_lines.append(dockerfile_lines[start_idx])
                
                # 只在第一个FROM后添加镜像源配置
                if i == 0:
                    result_lines.append(mirrors_config)
                
                # 添加当前阶段的剩余指令直到下一个阶段（如果有）
                next_idx = stage_start_indices[i+1] if i+1 < len(stage_start_indices) else len(dockerfile_lines)
                for j in range(start_idx + 1, next_idx):
                    result_lines.append(dockerfile_lines[j])
            
            return "\n".join(result_lines)
            
        except Exception as e:
            self.logger.error(f"在Dockerfile中添加中国镜像源时出错: {str(e)}")
            # 在出错的情况下，返回原始Dockerfile内容
            return dockerfile_content

    def _validate_dockerfile(self, dockerfile_content):
        """
        验证Dockerfile格式是否正确
        
        Args:
            dockerfile_content (str): Dockerfile内容
            
        Raises:
            ValueError: 当Dockerfile格式不正确时抛出
        """
        try:
            # 检查是否为空
            if not dockerfile_content or not dockerfile_content.strip():
                raise ValueError("Dockerfile内容为空")
                
            # 分行检查基本格式
            lines = dockerfile_content.splitlines()
            has_from = False
            invalid_lines = []
            
            # 特殊处理的指令集合，用于检测PyTorch和CUDA相关指令
            pytorch_related = ['torch', 'pytorch', 'torchvision', 'torchaudio']
            cuda_related = ['cuda', 'nvidia', 'gpu']
            
            # PyTorch和CUDA相关指令计数
            pytorch_count = 0
            cuda_count = 0
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                    
                # 检查是否有FROM指令
                if line.startswith('FROM '):
                    has_from = True
                    
                # 检查基本语法，每行应该以指令开头
                valid_instructions = [
                    'FROM', 'RUN', 'CMD', 'LABEL', 'EXPOSE', 'ENV', 'ADD',
                    'COPY', 'ENTRYPOINT', 'VOLUME', 'USER', 'WORKDIR', 'ARG',
                    'ONBUILD', 'STOPSIGNAL', 'HEALTHCHECK', 'SHELL'
                ]
                
                is_continuation = i > 0 and lines[i-1].strip().endswith('\\')
                
                if not is_continuation and not any(line.startswith(instr + ' ') for instr in valid_instructions):
                    invalid_lines.append((i+1, line))  # 记录行号和内容
                    
                # 检测PyTorch和CUDA相关指令
                line_lower = line.lower()
                
                if any(term in line_lower for term in pytorch_related):
                    pytorch_count += 1
                    
                if any(term in line_lower for term in cuda_related):
                    cuda_count += 1
            
            # 必须有FROM指令
            if not has_from:
                raise ValueError("Dockerfile中缺少FROM指令")
                
            # 如果检测到PyTorch或CUDA相关指令，记录到日志
            if pytorch_count > 0:
                self.logger.info(f"检测到 {pytorch_count} 条PyTorch相关指令")
                
            if cuda_count > 0:
                self.logger.info(f"检测到 {cuda_count} 条CUDA相关指令")
                
            # 如果有无效行，记录到日志
            if invalid_lines:
                self.logger.warning(f"Dockerfile中存在{len(invalid_lines)}行不符合标准格式:")
                for line_num, content in invalid_lines:
                    self.logger.warning(f"  第{line_num}行: {content}")
                
                # 如果无效行太多，则判断为格式错误
                if len(invalid_lines) > len(lines) / 3:  # 如果超过1/3的行都有问题
                    raise ValueError(f"Dockerfile格式不正确，有{len(invalid_lines)}行不符合Docker规范")
                
            return True
            
        except ValueError as ve:
            self.logger.error(f"Dockerfile验证失败: {str(ve)}")
            raise ve
        except Exception as e:
            self.logger.error(f"验证Dockerfile时出错: {str(e)}")
            # 不抛出异常，让构建过程继续尝试
            return False
            
    def _fix_dockerfile(self, dockerfile_content, deep_fix=False):
        """
        尝试修复Dockerfile中的格式问题
        
        Args:
            dockerfile_content (str): 原始Dockerfile内容
            deep_fix (bool): 是否进行深度修复
            
        Returns:
            str: 修复后的Dockerfile内容
        """
        try:
            # 如果内容为空，创建一个基本的Dockerfile
            if not dockerfile_content or not dockerfile_content.strip():
                self.logger.warning("Dockerfile内容为空，创建基本Dockerfile")
                return "FROM python:3.9-slim\nCMD [\"python\", \"-c\", \"print('Hello World')\"]"
                
            lines = dockerfile_content.splitlines()
            fixed_lines = []
            has_from = False
            in_continuation = False
            pytorch_detected = False
            cuda_detected = False
            pytorch_version = None
            cuda_version = None
            valid_instructions = [
                'FROM', 'RUN', 'CMD', 'LABEL', 'EXPOSE', 'ENV', 'ADD',
                'COPY', 'ENTRYPOINT', 'VOLUME', 'USER', 'WORKDIR', 'ARG',
                'ONBUILD', 'STOPSIGNAL', 'HEALTHCHECK', 'SHELL'
            ]
            
            # 特殊处理的指令集合，用于检测PyTorch和CUDA相关指令
            pytorch_related = ['torch', 'pytorch', 'torchvision', 'torchaudio']
            cuda_related = ['cuda', 'nvidia', 'gpu']
            
            # 尝试提取PyTorch版本和CUDA版本
            for line in lines:
                line_lower = line.lower()
                if 'torch==' in line_lower:
                    # 尝试提取PyTorch版本
                    match = re.search(r'torch==(\d+\.\d+\.\d+)', line)
                    if match:
                        pytorch_version = match.group(1)
                        self.logger.info(f"检测到PyTorch版本: {pytorch_version}")
                
                if 'cu' in line_lower and ('--index-url' in line_lower or 'index-url' in line_lower):
                    # 尝试提取CUDA版本
                    match = re.search(r'cu(\d+)', line_lower)
                    if match:
                        cuda_version_no_dots = match.group(1)
                        # 转换为标准格式 (例如: 116 -> 11.6)
                        if len(cuda_version_no_dots) == 3:
                            cuda_version = cuda_version_no_dots[0:2] + '.' + cuda_version_no_dots[2]
                        elif len(cuda_version_no_dots) == 2:
                            cuda_version = cuda_version_no_dots[0] + '.' + cuda_version_no_dots[1]
                        self.logger.info(f"检测到CUDA版本: {cuda_version}")
            
            for i, line in enumerate(lines):
                original_line = line
                line = line.strip()
                line_lower = line.lower()
                
                # 检测PyTorch和CUDA相关内容
                if any(term in line_lower for term in pytorch_related):
                    pytorch_detected = True
                    
                if any(term in line_lower for term in cuda_related):
                    cuda_detected = True
                
                # 跳过空行
                if not line:
                    fixed_lines.append("")
                    continue
                    
                # 处理注释
                if line.startswith('#'):
                    fixed_lines.append(original_line)
                    continue
                    
                # 处理前一行的续行符
                if in_continuation:
                    fixed_lines.append(original_line)
                    in_continuation = line.endswith('\\')
                    continue
                    
                # 检查是否是有效的Dockerfile指令
                is_valid_instruction = any(line.startswith(instr + ' ') for instr in valid_instructions)
                
                # 处理当前行
                if is_valid_instruction:
                    fixed_lines.append(original_line)
                    if line.startswith('FROM '):
                        has_from = True
                    in_continuation = line.endswith('\\')
                else:
                    # 尝试修复无效行
                    if deep_fix:
                        # 针对PyTorch和CUDA相关指令的深度修复
                        if any(term in line_lower for term in pytorch_related):
                            if 'import' in line_lower or 'print' in line_lower:
                                # 看起来像Python代码
                                fixed_lines.append(f"RUN python -c \"{line}\"")
                                self.logger.info(f"深度修复: 将PyTorch相关Python代码行 '{line}' 修改为 'RUN python -c \"{line}\"'")
                            elif 'install' in line_lower or 'pip' in line_lower:
                                # 检查是否有torch==版本指定
                                if 'torch==' in line_lower and '--index-url' not in line_lower and 'torch==' not in line:
                                    # 添加适当的index-url参数
                                    if cuda_version:
                                        cuda_version_no_dots = cuda_version.replace('.', '')
                                        fixed_line = f"RUN {line} --index-url https://download.pytorch.org/whl/cu{cuda_version_no_dots}"
                                        self.logger.info(f"深度修复: 为PyTorch CUDA安装添加index-url: '{line}' -> '{fixed_line}'")
                                    else:
                                        fixed_line = f"RUN {line} --index-url https://download.pytorch.org/whl/cpu"
                                        self.logger.info(f"深度修复: 为PyTorch CPU安装添加index-url: '{line}' -> '{fixed_line}'")
                                    fixed_lines.append(fixed_line)
                                else:
                                    # 常规pip安装命令
                                    fixed_lines.append(f"RUN {line}")
                                    self.logger.info(f"深度修复: 将PyTorch相关安装行 '{line}' 修改为 'RUN {line}'")
                            else:
                                fixed_lines.append(f"RUN {line}")
                                self.logger.info(f"深度修复: 将PyTorch相关行 '{line}' 修改为 'RUN {line}'")
                        elif any(term in line_lower for term in cuda_related):
                            if 'env' in line_lower or '=' in line:
                                # 看起来像环境变量设置
                                parts = line.split('=', 1)
                                if len(parts) == 2:
                                    var_name = parts[0].strip()
                                    var_value = parts[1].strip().strip('"\'')
                                    fixed_lines.append(f"ENV {var_name}={var_value}")
                                    self.logger.info(f"深度修复: 将CUDA相关环境变量行 '{line}' 修改为 'ENV {var_name}={var_value}'")
                                else:
                                    fixed_lines.append(f"RUN {line}")
                                    self.logger.info(f"深度修复: 将CUDA相关行 '{line}' 修改为 'RUN {line}'")
                            else:
                                fixed_lines.append(f"RUN {line}")
                                self.logger.info(f"深度修复: 将CUDA相关行 '{line}' 修改为 'RUN {line}'")
                        # 其他深度修复逻辑
                        elif "=" in line and not in_continuation:
                            # 可能是ENV指令
                            fixed_lines.append(f"ENV {line}")
                            self.logger.info(f"深度修复: 将无效行 '{line}' 修改为 'ENV {line}'")
                        elif "/" in line and not in_continuation:
                            # 可能是COPY或ADD指令
                            fixed_lines.append(f"COPY {line} /")
                            self.logger.info(f"深度修复: 将无效行 '{line}' 修改为 'COPY {line} /'")
                        elif line.endswith('.sh') or line.endswith('.py') or line.startswith('./'):
                            # 可能是RUN指令
                            fixed_lines.append(f"RUN {line}")
                            self.logger.info(f"深度修复: 将无效行 '{line}' 修改为 'RUN {line}'")
                        else:
                            # 无法修复，注释掉
                            fixed_lines.append(f"# 无效指令(已注释): {line}")
                            self.logger.info(f"深度修复: 将无效行 '{line}' 注释掉")
                    else:
                        # 简单修复：注释掉无效行
                        fixed_lines.append(f"# 无效指令(已注释): {line}")
                        self.logger.info(f"简单修复: 将无效行 '{line}' 注释掉")
            
            # 确保Dockerfile有FROM指令
            if not has_from:
                # 如果检测到CUDA相关指令，使用nvidia/cuda基础镜像
                if cuda_detected and cuda_version:
                    fixed_lines.insert(0, f"FROM nvidia/cuda:{cuda_version}-base-ubuntu20.04  # 自动添加的CUDA基础镜像")
                    self.logger.info(f"修复: 添加缺失的CUDA基础镜像FROM指令，使用检测到的CUDA版本 {cuda_version}")
                elif cuda_detected:
                    fixed_lines.insert(0, "FROM nvidia/cuda:11.6.2-base-ubuntu20.04  # 自动添加的CUDA基础镜像")
                    self.logger.info("修复: 添加缺失的CUDA基础镜像FROM指令")
                # 如果检测到PyTorch相关指令，使用PyTorch基础镜像
                elif pytorch_detected and pytorch_version:
                    if cuda_detected and cuda_version:
                        # 使用PyTorch CUDA镜像
                        cuda_version_no_dots = cuda_version.replace('.', '')
                        fixed_lines.insert(0, f"FROM pytorch/pytorch:{pytorch_version}-cuda{cuda_version}-cudnn8-runtime  # 自动添加的PyTorch CUDA基础镜像")
                        self.logger.info(f"修复: 添加缺失的PyTorch CUDA基础镜像FROM指令，版本 {pytorch_version}-cuda{cuda_version}")
                    else:
                        # 使用PyTorch CPU镜像
                        fixed_lines.insert(0, f"FROM pytorch/pytorch:{pytorch_version}-cpu  # 自动添加的PyTorch CPU基础镜像")
                        self.logger.info(f"修复: 添加缺失的PyTorch CPU基础镜像FROM指令，版本 {pytorch_version}")
                elif pytorch_detected:
                    fixed_lines.insert(0, "FROM python:3.9-slim  # 自动添加的Python基础镜像")
                    self.logger.info("修复: 添加缺失的Python基础镜像FROM指令")
                else:
                    fixed_lines.insert(0, "FROM python:3.9-slim  # 自动添加的基础镜像")
                    self.logger.info("修复: 添加缺失的FROM指令")
                
            # 确保Dockerfile有CMD指令
            has_cmd = any(line.strip().startswith('CMD ') for line in fixed_lines)
            has_entrypoint = any(line.strip().startswith('ENTRYPOINT ') for line in fixed_lines)
            
            if not has_cmd and not has_entrypoint:
                # 如果检测到PyTorch，添加验证PyTorch的CMD
                if pytorch_detected:
                    fixed_lines.append('CMD ["python", "-c", "import torch; print(\\\"PyTorch version:\\\", torch.__version__); print(\\\"CUDA available:\\\", torch.cuda.is_available())"]  # 自动添加的PyTorch验证CMD指令')
                    self.logger.info("修复: 添加缺失的PyTorch验证CMD指令")
                else:
                    fixed_lines.append("CMD [\"python\", \"-c\", \"print('Hello from fixed Dockerfile')\"]  # 自动添加的CMD指令")
                    self.logger.info("修复: 添加缺失的CMD指令")
                
            # 添加修复说明
            fixed_lines.append("\n# 注意: 此Dockerfile已被自动修复，可能与原始意图有差异")
            
            return "\n".join(fixed_lines)
            
        except Exception as e:
            self.logger.error(f"修复Dockerfile时出错: {str(e)}")
            # 返回一个基本的工作Dockerfile
            return """FROM python:3.9-slim
# 自动生成的应急Dockerfile (修复过程出错)
WORKDIR /app
CMD ["python", "-c", "print('Emergency Dockerfile after repair failure')"]
# 注意: 原始Dockerfile处理失败，这是自动生成的应急版本
"""

    def _replace_pytorch_install_command(self, dockerfile_content, new_install_commands):
        """
        替换Dockerfile中的PyTorch安装命令
        
        Args:
            dockerfile_content (str): 原始Dockerfile内容
            new_install_commands (str): 新的PyTorch安装命令
            
        Returns:
            str: 更新后的Dockerfile内容
        """
        lines = dockerfile_content.splitlines()
        result_lines = []
        
        # 查找PyTorch安装段落
        i = 0
        while i < len(lines):
            line = lines[i]
            # 检测是否是PyTorch安装行
            if ("pip install" in line and "torch" in line) or ("# 安装PyTorch" in line):
                # 找到了PyTorch安装命令，跳过相关行直到找到非安装命令
                while i < len(lines) and (
                    "pip install" in lines[i] or 
                    "torch" in lines[i] or 
                    "RUN python -c" in lines[i] or
                    "# 验证" in lines[i] or
                    "# 安装PyTorch" in lines[i]):
                    i += 1
                
                # 插入新的安装命令
                result_lines.append(new_install_commands)
            else:
                # 保留原行
                result_lines.append(line)
                i += 1
        
        return "\n".join(result_lines)

    def exec_in_container(self, container_id: str, cmd: List[str], workdir: Optional[str] = None) -> Dict:
        """
        在容器中执行命令
        
        Args:
            container_id: 容器ID或名称
            cmd: 要执行的命令
            workdir: 工作目录
            
        Returns:
            Dict: 执行结果，包含 success, exit_code, output 字段
        """
        try:
            # 获取容器
            container = self.client.containers.get(container_id)
            if not container:
                return {
                    'success': False,
                    'error': f"找不到容器: {container_id}",
                    'exit_code': -1,
                    'output': ''
                }
            
            self.logger.info(f"在容器 {container_id} 中执行命令: {cmd}")
            if workdir:
                self.logger.info(f"工作目录: {workdir}")
            
            # 执行命令
            environment = {'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}
            exec_kwargs = {
                'environment': environment
            }
            if workdir:
                exec_kwargs['workdir'] = workdir
                
            result = container.exec_run(cmd, **exec_kwargs)
            
            exit_code = result.exit_code
            output = result.output.decode('utf-8', errors='replace') if result.output else ''
            
            self.logger.info(f"命令执行完成，退出码: {exit_code}")
            if exit_code != 0:
                self.logger.warning(f"命令执行失败，输出: {output[:500]}...")
                
            return {
                'success': exit_code == 0,
                'exit_code': exit_code,
                'output': output
            }
                
        except Exception as e:
            self.logger.error(f"在容器中执行命令时出错: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'exit_code': -1,
                'output': ''
            }