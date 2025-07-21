import os
import secrets
from typing import List
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "LAMMPS MCP Service"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # 服务器配置
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 18000

    # CORS配置
    ALLOWED_HOSTS: List[str] = ["*"]

    # Redis配置
    REDIS_URL: str

    # LAMMPS配置
    LAMMPS_POTENTIALS: str = "/app/lammps/potentials"
    LAMMPS_EXECUTABLE: str = "lmp"

    # 目录配置
    UPLOAD_DIR: str = "/app/uploads"
    SIMULATION_DIR: str = "/app/simulations"
    LOG_DIR: str = "/app/logs"

    # 资源限制
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_SIMULATION_TIME: int = 3600  # 1小时

    # Celery配置
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # 安全配置
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 监控配置
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 18000

    @validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        if not v:
            raise ValueError("SECRET_KEY must be set")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @validator('ALLOWED_HOSTS')
    def validate_allowed_hosts(cls, v):
        if "*" in v and len(v) > 1:
            raise ValueError("Cannot mix '*' with specific hosts")
        return v

    @validator('UPLOAD_DIR', 'SIMULATION_DIR', 'LOG_DIR', 'LAMMPS_POTENTIALS')
    def ensure_dir_exists(cls, v):
        if not os.path.isabs(v):
            raise ValueError(f"Path must be absolute: {v}")
        os.makedirs(v, exist_ok=True)
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()