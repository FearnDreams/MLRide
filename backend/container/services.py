# """
# This module contains the service classes for container management.
# 包含容器管理的服务类。
# """

# import docker
# from docker.errors import DockerException
# import psutil
# from django.conf import settings
# import logging

# logger = logging.getLogger(__name__)

# class DockerService:
#     """Docker服务类
    
#     处理Docker容器的创建、启动、停止等操作
    
#     Attributes:
#         client: Docker客户端实例
#     """
    
#     def __init__(self):
#         """初始化Docker客户端"""
#         try:
#             self.client = docker.from_env()
#         except DockerException as e:
#             logger.error(f"Docker客户端初始化失败: {str(e)}")
#             raise
    
#     def create_container(self, image_name, container_name, cpu_limit, memory_limit, gpu_limit=0):
#         """创建Docker容器
        
#         Args:
#             image_name (str): 镜像名称
#             container_name (str): 容器名称
#             cpu_limit (int): CPU核心数限制
#             memory_limit (int): 内存限制(MB)
#             gpu_limit (int): GPU数量限制
            
#         Returns:
#             container: 创建的容器实例
            
#         Raises:
#             DockerException: 当容器创建失败时抛出
#         """
#         try:
#             # 转换资源限制
#             mem_limit = f"{memory_limit}m"  # 转换为MB格式
#             cpu_count = float(cpu_limit)
            
#             # 设置设备请求（用于GPU）
#             device_requests = []
#             if gpu_limit > 0:
#                 device_requests.append(
#                     docker.types.DeviceRequest(
#                         count=gpu_limit,
#                         capabilities=[['gpu']]
#                     )
#                 )
            
#             # 创建容器
#             container = self.client.containers.create(
#                 image=image_name,
#                 name=container_name,
#                 mem_limit=mem_limit,
#                 cpu_count=cpu_count,
#                 device_requests=device_requests,
#                 detach=True
#             )
            
#             return container
            
#         except DockerException as e:
#             logger.error(f"容器创建失败: {str(e)}")
#             raise
    
#     def start_container(self, container_id):
#         """启动容器
        
#         Args:
#             container_id (str): 容器ID
            
#         Raises:
#             DockerException: 当容器启动失败时抛出
#         """
#         try:
#             container = self.client.containers.get(container_id)
#             container.start()
#         except DockerException as e:
#             logger.error(f"容器启动失败: {str(e)}")
#             raise
    
#     def stop_container(self, container_id):
#         """停止容器
        
#         Args:
#             container_id (str): 容器ID
            
#         Raises:
#             DockerException: 当容器停止失败时抛出
#         """
#         try:
#             container = self.client.containers.get(container_id)
#             container.stop()
#         except DockerException as e:
#             logger.error(f"容器停止失败: {str(e)}")
#             raise
    
#     def remove_container(self, container_id):
#         """删除容器
        
#         Args:
#             container_id (str): 容器ID
            
#         Raises:
#             DockerException: 当容器删除失败时抛出
#         """
#         try:
#             container = self.client.containers.get(container_id)
#             container.remove(force=True)
#         except DockerException as e:
#             logger.error(f"容器删除失败: {str(e)}")
#             raise
    
#     def get_container_stats(self, container_id):
#         """获取容器资源使用统计
        
#         Args:
#             container_id (str): 容器ID
            
#         Returns:
#             dict: 包含CPU、内存使用情况的字典
            
#         Raises:
#             DockerException: 当获取统计信息失败时抛出
#         """
#         try:
#             container = self.client.containers.get(container_id)
#             stats = container.stats(stream=False)
            
#             # 计算CPU使用率
#             cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
#                        stats['precpu_stats']['cpu_usage']['total_usage']
#             system_delta = stats['cpu_stats']['system_cpu_usage'] - \
#                           stats['precpu_stats']['system_cpu_usage']
#             cpu_usage = (cpu_delta / system_delta) * 100.0
            
#             # 计算内存使用率
#             mem_usage = stats['memory_stats']['usage']
#             mem_limit = stats['memory_stats']['limit']
#             mem_percent = (mem_usage / mem_limit) * 100.0
            
#             return {
#                 'cpu_usage': round(cpu_usage, 2),
#                 'memory_usage': round(mem_usage / (1024 * 1024), 2),  # 转换为MB
#                 'memory_percent': round(mem_percent, 2)
#             }
            
#         except DockerException as e:
#             logger.error(f"获取容器统计信息失败: {str(e)}")
#             raise
    
#     def get_system_resources(self):
#         """获取系统资源使用情况
        
#         Returns:
#             dict: 包含系统CPU、内存使用情况的字典
#         """
#         try:
#             cpu_percent = psutil.cpu_percent(interval=1)
#             memory = psutil.virtual_memory()
            
#             return {
#                 'cpu_percent': cpu_percent,
#                 'memory_total': round(memory.total / (1024 * 1024), 2),  # MB
#                 'memory_used': round(memory.used / (1024 * 1024), 2),  # MB
#                 'memory_percent': memory.percent
#             }
#         except Exception as e:
#             logger.error(f"获取系统资源信息失败: {str(e)}")
#             raise 