from fastapi import APIRouter, HTTPException, Depends
from celery.result import AsyncResult
import uuid
import structlog

from app.models.simulation import TaskStatus
from app.tasks.simulation_tasks import run_lammps_simulation

logger = structlog.get_logger(__name__)
router = APIRouter()

def validate_task_id(task_id: str) -> str:
    """验证任务ID的安全性"""
    if not task_id or not isinstance(task_id, str):
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    # 检查ID格式（UUID格式）
    try:
        uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    
    return task_id

@router.get("/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str = Depends(validate_task_id)):
    """获取任务状态"""
    
    try:
        task = AsyncResult(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # 构建响应
        response = TaskStatus(
            task_id=task_id,
            status=task.status,
            result=task.result if task.ready() else None,
            error=str(task.result) if task.failed() else None,
            progress=None,
            meta=None
        )
        
        # 如果任务正在进行，获取进度信息
        if task.status == 'PROGRESS' and task.info:
            response.progress = task.info.get('progress', 0)
            response.meta = task.info
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{task_id}/revoke")
async def revoke_task(
    task_id: str = Depends(validate_task_id), 
    terminate: bool = False
):
    """撤销任务"""
    
    try:
        task = AsyncResult(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # 检查任务状态
        if task.ready():
            raise HTTPException(status_code=400, detail="Task is already completed")
        
        # 撤销任务
        task.revoke(terminate=terminate)
        
        logger.info("Task revoked", task_id=task_id, terminate=terminate)
        
        return {"message": "Task revoked successfully", "terminated": terminate}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to revoke task", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{task_id}/result")
async def get_task_result(task_id: str = Depends(validate_task_id)):
    """获取任务结果"""
    
    try:
        task = AsyncResult(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if not task.ready():
            raise HTTPException(status_code=202, detail="Task is still running")
        
        if task.failed():
            raise HTTPException(status_code=500, detail=f"Task failed: {str(task.result)}")
        
        return {"result": task.result, "status": task.status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task result", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")