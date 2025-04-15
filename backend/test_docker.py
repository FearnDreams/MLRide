import docker
import platform
import sys

print(f"Python版本: {platform.python_version()}")
print(f"操作系统: {platform.system()} {platform.release()}")
print(f"Docker-py版本: {docker.__version__}")
print("尝试连接Docker...\n")

# 尝试多种连接方式
connection_methods = [
    ('默认设置', {}),
    ('Windows命名管道1', {'base_url': 'npipe:////./pipe/docker_engine'}),
    ('Windows命名管道2', {'base_url': 'npipe:////./pipe/docker_cli'}),
    ('TCP连接', {'base_url': 'tcp://localhost:2375'})
]

success = False

for name, params in connection_methods:
    try:
        print(f"尝试使用 {name}...")
        client = docker.DockerClient(**params)
        version = client.version()
        print(f"成功! Docker版本: {version.get('Version', 'unknown')}")
        
        if 'base_url' in params:
            print(f"推荐设置环境变量: DOCKER_HOST={params['base_url']}")
        
        # 测试列出容器
        containers = client.containers.list(all=True)
        print(f"找到 {len(containers)} 个容器")
        
        success = True
        break
    except Exception as e:
        print(f"失败: {str(e)}\n")

if not success:
    print("\n所有连接方式均失败。请确保Docker Desktop正在运行。")
    sys.exit(1)

print("\nDocker连接测试成功!") 