from fastapi import APIRouter, HTTPException
import structlog

from app.models.simulation import ScriptValidationRequest, ScriptValidationResponse
from app.tasks.simulation_tasks import validate_lammps_script
from app.core.config import get_settings

settings = get_settings()

logger = structlog.get_logger(__name__)
router = APIRouter()

def validate_script_request(validation: ScriptValidationRequest):
    """验证脚本验证请求"""
    if not validation.script_content or not validation.script_content.strip():
        raise HTTPException(status_code=400, detail="Script content cannot be empty")
    
    if len(validation.script_content) > settings.MAX_SCRIPT_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"Script too large. Maximum size: {settings.MAX_SCRIPT_SIZE} bytes"
        )

@router.post("/lammps", response_model=ScriptValidationResponse)
async def validate_lammps_script_endpoint(validation: ScriptValidationRequest):
    """验证LAMMPS脚本"""
    
    try:
        # 验证请求
        validate_script_request(validation)
        
        # 异步验证脚本
        task = validate_lammps_script.delay(validation.script_content)
        
        # 等待结果（简单实现，生产环境应使用轮询）
        try:
            result = task.get(timeout=30)
            return ScriptValidationResponse(**result)
        except Exception as e:
            logger.error("Script validation failed", error=str(e))
            return ScriptValidationResponse(
                valid=False,
                message="Validation failed",
                error=str(e)
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to validate script", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/lammps/async")
async def validate_lammps_script_async(validation: ScriptValidationRequest):
    """异步验证LAMMPS脚本"""
    
    try:
        # 验证请求
        validate_script_request(validation)
        
        # 启动异步验证任务
        task = validate_lammps_script.delay(validation.script_content)
        
        logger.info("Started async script validation", task_id=task.id)
        
        return {
            "message": "Validation task started",
            "task_id": task.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start async validation", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")