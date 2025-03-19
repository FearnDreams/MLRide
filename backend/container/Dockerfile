# 使用官方Python镜像作为基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /workspace

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
RUN pip install --no-cache-dir \
    jupyter \
    notebook \
    numpy \
    pandas \
    matplotlib \
    scikit-learn \
    torch \
    transformers \
    mlflow \
    dvc

# 创建jupyter配置目录
RUN mkdir -p /root/.jupyter

# 配置Jupyter
RUN jupyter notebook --generate-config && \
    echo "c.NotebookApp.ip = '0.0.0.0'" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.port = 8888" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.token = ''" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.password = ''" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_root = True" >> /root/.jupyter/jupyter_notebook_config.py

# 创建工作目录
RUN mkdir -p /workspace && \
    chmod 777 /workspace

# 设置环境变量
ENV JUPYTER_CONFIG_DIR=/root/.jupyter \
    JUPYTER_DATA_DIR=/root/.local/share/jupyter \
    JUPYTER_RUNTIME_DIR=/root/.local/share/jupyter/runtime \
    PYTHONPATH=/workspace

# 暴露端口
EXPOSE 8888

# 设置默认命令
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''", "--notebook-dir=/workspace"]
