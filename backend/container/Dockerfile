# 使用官方Python镜像作为基础镜像
FROM python:3.9-slim

# 安装必要的包
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装jupyter
RUN pip install notebook==6.5.5

# 创建工作目录
RUN mkdir -p /workspace && chmod 777 /workspace
WORKDIR /workspace

# 创建启动脚本
RUN echo '#!/bin/bash\n\
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token="" --NotebookApp.password="" & \n\
# 保持容器运行\n\
tail -f /dev/null\n\
' > /start.sh && chmod +x /start.sh

# 暴露端口
EXPOSE 8888

# 启动命令
CMD ["/bin/bash", "/start.sh"]
