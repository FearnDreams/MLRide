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
            image = self.client.images.pull(image_name, tag=tag)
            return {
                'id': image.id,
                'tags': image.tags,
                'size': image.attrs['Size'],
                'created': image.attrs['Created']
            }
        except DockerException as e:
            logger.error(f"Failed to pull image {image_name}:{tag}: {str(e)}")
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
            
    def start_container(self, container_id: str) -> bool:
        """
        启动Docker容器
        
        Args:
            container_id: 容器ID
            
        Returns:
            bool: 启动是否成功
        """
        try:
            container = self.client.containers.get(container_id)
            container.start()
            return True
        except DockerException as e:
            logger.error(f"Failed to start container {container_id}: {str(e)}")
            raise
            
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
            logger.error(f"Failed to get stats for container {container_id}: {str(e)}")
            raise 