#!/usr/bin/env python
"""
Docker连接辅助工具

用于Windows环境下检测和修复Docker连接问题
"""

import os
import sys
import platform
import subprocess
import time
import logging
import docker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("docker_helper")

def is_windows():
    """检查是否为Windows环境"""
    return platform.system().lower() == 'windows'

def check_docker_running():
    """检查Docker是否正在运行"""
    logger.info("检查Docker运行状态...")
    
    if not is_windows():
        logger.info("非Windows环境，尝试使用docker info命令检查")
        try:
            subprocess.run(['docker', 'info'], capture_output=True, check=True)
            logger.info("Docker正在运行")
            return True
        except Exception as e:
            logger.error(f"Docker可能未运行: {str(e)}")
            return False
    
    # Windows特定检查
    docker_running = False
    
    # 检查Docker Desktop进程
    try:
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Docker Desktop.exe'], 
                              capture_output=True, text=True, check=False)
        if 'Docker Desktop.exe' in result.stdout:
            docker_running = True
            logger.info("Docker Desktop进程正在运行")
    except Exception as e:
        logger.warning(f"检查Docker Desktop进程失败: {str(e)}")
    
    # 检查Docker Engine服务
    if not docker_running:
        try:
            result = subprocess.run(['sc', 'query', 'docker'], 
                                  capture_output=True, text=True, check=False)
            if 'RUNNING' in result.stdout:
                docker_running = True
                logger.info("Docker Engine服务正在运行")
        except Exception as e:
            logger.warning(f"检查Docker服务失败: {str(e)}")
    
    return docker_running

def get_docker_context():
    """获取Docker Context信息"""
    logger.info("获取Docker Context信息...")
    
    try:
        result = subprocess.run(['docker', 'context', 'inspect'], 
                               capture_output=True, text=True, check=False)
        if result.returncode == 0:
            context_info = result.stdout
            logger.info(f"Docker Context信息: {context_info[:200]}...")
            
            # 检查是否是WSL模式
            if "wsl" in context_info.lower():
                logger.info("检测到Docker可能运行在WSL环境中")
                return "wsl"
            else:
                logger.info("Docker可能运行在Windows原生环境中")
                return "windows"
    except Exception as e:
        logger.warning(f"获取Docker Context信息失败: {str(e)}")
    
    return "unknown"

def try_connect_docker():
    """尝试多种方式连接Docker"""
    logger.info("尝试多种方式连接Docker...")
    
    # 可能的Docker连接方式
    connection_methods = []
    
    # 优先使用环境变量
    docker_host = os.environ.get('DOCKER_HOST')
    if docker_host:
        connection_methods.append(('环境变量DOCKER_HOST', {'base_url': docker_host}))
    
    # Windows专用连接方式
    if is_windows():
        connection_methods.extend([
            ('Windows默认命名管道', {'base_url': 'npipe:////./pipe/docker_engine'}),
            ('Docker CLI命名管道', {'base_url': 'npipe:////./pipe/docker_cli'}),
            ('Windows本地TCP', {'base_url': 'tcp://localhost:2375'}),
            ('备用命名管道', {'base_url': 'npipe:////./pipe/com.docker.docker'}),
            ('WSL 2 TCP', {'base_url': 'tcp://localhost:2375'})
        ])
    
    # 通用连接方式
    connection_methods.extend([
        ('默认设置', {}),
        ('Unix套接字', {'base_url': 'unix://var/run/docker.sock'})
    ])
    
    # 尝试每种连接方式
    for method_name, params in connection_methods:
        logger.info(f"尝试使用 {method_name} 连接Docker...")
        
        try:
            client = docker.DockerClient(**params)
            version_info = client.version()
            
            logger.info(f"成功连接Docker! 版本: {version_info.get('Version', 'unknown')}")
            logger.info(f"连接方式: {method_name}, 参数: {params}")
            
            # 对于Windows，建议设置环境变量
            if is_windows() and 'base_url' in params and params['base_url']:
                logger.info(f"\n===推荐操作===\n在命令行设置环境变量: set DOCKER_HOST={params['base_url']}\n")
            
            return client, params
        except Exception as e:
            logger.warning(f"使用 {method_name} 连接失败: {str(e)}")
    
    logger.error("所有连接方式均失败!")
    return None, None

def fix_docker_connection():
    """修复Docker连接问题"""
    logger.info("开始Docker连接修复流程...")
    
    # 步骤1: 检查Docker是否运行
    if not check_docker_running():
        logger.error("Docker未运行! 请启动Docker Desktop后重试")
        return False
    
    # 步骤2: 获取Docker Context信息
    context = get_docker_context()
    
    # 步骤3: 尝试连接Docker
    client, params = try_connect_docker()
    
    if client:
        logger.info("Docker连接修复成功!")
        
        # 输出推荐操作
        if context == "wsl" and is_windows():
            logger.info("\n===环境信息===")
            logger.info("检测到Docker运行在WSL 2中")
            logger.info("建议操作:")
            logger.info("1. 设置环境变量: set DOCKER_HOST=tcp://localhost:2375")
            logger.info("2. 在Docker Desktop设置中确保暴露了2375端口")
        elif is_windows():
            logger.info("\n===环境信息===")
            logger.info("检测到Docker运行在Windows原生环境中")
            logger.info("建议操作:")
            logger.info("1. 设置环境变量: set DOCKER_HOST=npipe:////./pipe/docker_engine")
        
        # 测试列出容器
        try:
            containers = client.containers.list()
            logger.info(f"当前运行的容器数量: {len(containers)}")
            for container in containers:
                logger.info(f"- {container.name} (ID: {container.short_id})")
        except Exception as e:
            logger.warning(f"列出容器失败: {str(e)}")
        
        return True
    else:
        logger.error("Docker连接修复失败!")
        
        if is_windows():
            logger.info("\n===故障排除===")
            logger.info("1. 确保Docker Desktop已经完全启动")
            logger.info("2. 尝试重启Docker Desktop")
            logger.info("3. 检查Docker Desktop设置:")
            logger.info("   - General -> 'Use the WSL 2 based engine'状态")
            logger.info("   - Docker Engine -> 检查配置是否正确")
            logger.info("4. 如果Docker运行在WSL 2中，确保已暴露API端口:")
            logger.info("   - 在Docker Desktop设置中启用'Expose daemon on tcp://localhost:2375 without TLS'")
        
        return False

def main():
    """主函数"""
    logger.info("=== Docker连接辅助工具 ===")
    logger.info(f"操作系统: {platform.system()} {platform.release()}")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--auto-fix":
        # 自动修复模式
        if fix_docker_connection():
            logger.info("Docker连接问题修复成功!")
        else:
            logger.error("Docker连接问题修复失败，请参考上述建议手动解决")
    else:
        # 诊断模式
        logger.info("正在检查Docker连接...")
        
        # 检查Docker是否运行
        if not check_docker_running():
            logger.error("Docker未运行! 请启动Docker Desktop后重试")
            return
        
        # 尝试连接Docker
        client, params = try_connect_docker()
        
        if client:
            logger.info("Docker连接正常!")
            
            # 测试Docker功能
            try:
                logger.info("获取Docker信息...")
                info = client.info()
                logger.info(f"Docker运行状态:")
                logger.info(f"- 容器数量: {info.get('Containers', 'unknown')}")
                logger.info(f"- 镜像数量: {info.get('Images', 'unknown')}")
                logger.info(f"- Docker根目录: {info.get('DockerRootDir', 'unknown')}")
                
                logger.info("列出容器...")
                containers = client.containers.list()
                logger.info(f"当前运行的容器数量: {len(containers)}")
                for container in containers:
                    logger.info(f"- {container.name} (ID: {container.short_id})")
                
            except Exception as e:
                logger.error(f"测试Docker功能时出错: {str(e)}")
        else:
            logger.error("无法连接到Docker!")
            logger.info("请运行 'python docker_helper.py --auto-fix' 尝试自动修复")

if __name__ == "__main__":
    main() 