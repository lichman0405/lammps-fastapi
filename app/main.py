from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import structlog
import redis

from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()
from app.core.logging import setup_logging

# 设置日志
setup_logging()
logger = structlog.get_logger()

# 创建FastAPI应用
app = FastAPI(
    title="LAMMPS MCP Service",
    description="A modern RESTful API service for LAMMPS molecular dynamics simulations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册路由
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    logger.info("LAMMPS MCP Service starting up", version="1.0.0")
    # 这里可以添加数据库连接、Redis连接等初始化操作

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    logger.info("LAMMPS MCP Service shutting down")

@app.get("/")
async def root():
    """根路由"""
    return {
        "message": "LAMMPS MCP Service is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "lammps-mcp"}

@app.get("/health")
async def health_check():
    """健康检查端点"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "services": {
            "api": "ok",
            "redis": "unknown",
            "system": {}
        }
    }
    
    try:
        # 检查Redis连接
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        health_status["services"]["redis"] = "ok"
    except Exception as e:
        health_status["services"]["redis"] = "error"
        health_status["status"] = "unhealthy"
    
    # 系统信息
    try:
        health_status["services"]["system"] = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        }
    except Exception as e:
        health_status["services"]["system"] = "error"
    
    if health_status["status"] == "healthy":
        return JSONResponse(content=health_status, status_code=200)
    else:
        return JSONResponse(content=health_status, status_code=503)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)