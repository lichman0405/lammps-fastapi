from pydantic import BaseSettings, validator
from typing import List
import os

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "LAMMPS MCP Service"
    DEBUG: bool = False
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS配置 - 生产环境应该限制具体域名
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # LAMMPS配置
    LAMMPS_POTENTIALS_PATH: str = os.getenv("LAMMPS_POTENTIALS", "/usr/local/share/lammps/potentials")
    LAMMPS_EXECUTABLE: str = "lmp"
    
    # 文件存储配置
    DATA_DIR: str = os.getenv("DATA_DIR", "/app/data")
    LOGS_DIR: str = os.getenv("LOGS_DIR", "/app/logs")
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_SCRIPT_SIZE: int = 1024 * 1024  # 1MB
    MAX_SIMULATION_TIME: int = 3600  # 1小时
    
    # 任务配置
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379")
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 监控配置
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    @validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        if not v or v == "your-secret-key-change-this":
            # 生成一个安全的随机密钥
            return secrets.token_urlsafe(32)
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator('ALLOWED_HOSTS')
    def validate_allowed_hosts(cls, v):
        if "*" in v and len(v) > 1:
            raise ValueError("Cannot mix '*' with specific hosts")
        return v
    
    @validator('DATA_DIR', 'LOGS_DIR', 'LAMMPS_POTENTIALS_PATH')
    def validate_paths(cls, v):
        # 确保路径是绝对路径，防止路径遍历攻击
        if not os.path.isabs(v):
            raise ValueError(f"Path must be absolute: {v}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建全局配置实例
settings = Settings()