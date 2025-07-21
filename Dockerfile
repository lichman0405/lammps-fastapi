FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖 - 分为构建依赖和运行时依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    libfftw3-dev \
    libjpeg-dev \
    libpng-dev \
    libopenmpi-dev \
    openmpi-bin \
    openmpi-common \
    pkg-config \
    libblas-dev \
    liblapack-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装LAMMPS
RUN git clone https://github.com/lammps/lammps.git /tmp/lammps \
    && cd /tmp/lammps \
    && mkdir build \
    && cd build \
    && cmake ../cmake \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
        -DPKG_PYTHON=ON \
        -DPKG_MPI=ON \
        -DPKG_MOLECULE=ON \
        -DPKG_RIGID=ON \
        -DPKG_KSPACE=ON \
        -DPKG_MANYBODY=ON \
        -DBUILD_SHARED_LIBS=ON \
        -DPKG_PYTHON=ON \
    && make -j$(nproc) \
    && make install \
    && cd / && rm -rf /tmp/lammps

# 设置Python环境
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 创建必要的目录
RUN mkdir -p /app/data /app/logs /app/static /app/examples

# 复制示例文件
COPY examples/ /app/examples/

# 设置权限
RUN chmod -R 755 /app/examples && \
    chmod -R 777 /app/data /app/logs

# 创建非root用户
RUN groupadd -r lammps && useradd -r -g lammps lammps && \
    chown -R lammps:lammps /app

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 切换到非root用户
USER lammps

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# 设置环境变量
ENV PYTHONPATH=/app
ENV LAMMPS_POTENTIALS=/usr/local/share/lammps/potentials

# 暴露端口
EXPOSE 8000

# 默认命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]