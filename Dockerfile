# Dockerfile
FROM python:3.11-slim

WORKDIR /app

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

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/

RUN mkdir -p /app/data /app/logs /app/static /app/examples /app/lammps/potentials
COPY examples/ /app/examples/
RUN chmod -R 755 /app/examples && \
    chmod -R 777 /app/data /app/logs

RUN groupadd -r lammps && useradd -r -g lammps lammps && \
    chown -R lammps:lammps /app

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:18000/health || exit 1

EXPOSE 18000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18000"]

ENV PYTHONPATH=/app
ENV LAMMPS_POTENTIALS=/app/lammps/potentials