from fastapi import APIRouter

from app.api.endpoints import simulations, tasks, validation

api_router = APIRouter()

# 注册路由
api_router.include_router(simulations.router, prefix="/simulations", tags=["simulations"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(validation.router, prefix="/validation", tags=["validation"])