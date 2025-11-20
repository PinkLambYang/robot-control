FROM ubuntu:20.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 安装Python、pip、git和构建工具（Ubuntu 20.04 默认 Python 3.8）
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    git \
    cmake \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 编译安装 CycloneDDS C 库（使用 releases/0.10.x 分支）
WORKDIR /root
RUN git clone https://github.com/eclipse-cyclonedds/cyclonedds.git -b releases/0.10.x && \
    cd cyclonedds && \
    mkdir build install && \
    cd build && \
    cmake .. -DCMAKE_INSTALL_PREFIX=/root/cyclonedds/install && \
    cmake --build . --target install

# 设置 CYCLONEDDS_HOME 环境变量
ENV CYCLONEDDS_HOME=/root/cyclonedds/install

# 设置工作目录
WORKDIR /app/backend

# 升级 pip 并配置镜像源
RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip3 install --no-cache-dir --upgrade pip setuptools wheel

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖（不包括 Unitree SDK）
RUN pip3 install --no-cache-dir -r requirements.txt

# 克隆 Unitree SDK 到独立目录
RUN git clone https://github.com/unitreerobotics/unitree_sdk2_python.git /app/unitree_sdk2_python

# 以可编辑模式安装 Unitree SDK
RUN pip3 install -e /app/unitree_sdk2_python

# 复制后端项目文件
COPY . .

# 创建存储目录
RUN mkdir -p storage/projects storage/logs

# 暴露WebSocket端口
EXPOSE 8000

# 启动服务
CMD ["python3", "main.py"]

