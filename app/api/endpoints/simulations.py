from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from typing import List, Optional
from datetime import datetime
import uuid
import re
from pathlib import Path

from app.models.simulation import (
    SimulationCreate, SimulationUpdate, SimulationResponse, 
    SimulationList, SimulationLog, SimulationResults,
    SimulationQuery, SimulationStatus
)
from app.services.lammps_service import LAMMPSService
from app.tasks.simulation_tasks import (
    run_lammps_simulation, cleanup_simulation_task, get_simulation_status_task
)
from app.core.config import get_settings

settings = get_settings()
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()

# 简单的内存存储，生产环境应使用数据库
simulations_db = {}

def validate_simulation_id(simulation_id: str) -> str:
    """验证模拟ID的安全性"""
    if not simulation_id or not isinstance(simulation_id, str):
        raise HTTPException(status_code=400, detail="Invalid simulation ID")
    
    # 检查ID格式（UUID格式）
    try:
        uuid.UUID(simulation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid simulation ID format")
    
    return simulation_id

def validate_input_limits(simulation: SimulationCreate):
    """验证输入数据的限制"""
    # 检查脚本大小
    if len(simulation.input_script) > settings.MAX_SCRIPT_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"Input script too large. Maximum size: {settings.MAX_SCRIPT_SIZE} bytes"
        )
    
    # 检查MPI进程数
    if simulation.mpi_processes < 1 or simulation.mpi_processes > 16:
        raise HTTPException(
            status_code=400,
            detail="MPI processes must be between 1 and 16"
        )
    
    # 检查名称长度
    if len(simulation.name) > 100:
        raise HTTPException(status_code=400, detail="Name too long (max 100 characters)")
    
    # 检查描述长度
    if simulation.description and len(simulation.description) > 1000:
        raise HTTPException(status_code=400, detail="Description too long (max 1000 characters)")
    
    # 检查标签数量和长度
    if simulation.tags and len(simulation.tags) > 10:
        raise HTTPException(status_code=400, detail="Too many tags (max 10)")
    
    for tag in simulation.tags or []:
        if len(tag) > 50:
            raise HTTPException(status_code=400, detail="Tag too long (max 50 characters)")
    
    # 检查势函数文件名安全性
    if simulation.potential_files:
        for filename in simulation.potential_files:
            if not re.match(r'^[a-zA-Z0-9._\-]+$', filename):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid potential file name: {filename}"
                )

@router.post("/", response_model=SimulationResponse)
async def create_simulation(simulation: SimulationCreate):
    """创建新的模拟任务"""
    
    try:
        # 验证输入限制
        validate_input_limits(simulation)
        
        simulation_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # 创建模拟记录
        simulation_record = SimulationResponse(
            id=simulation_id,
            name=simulation.name,
            description=simulation.description,
            status=SimulationStatus.PENDING,
            input_script=simulation.input_script,
            potential_files=simulation.potential_files,
            mpi_processes=simulation.mpi_processes,
            tags=simulation.tags,
            created_at=now,
            updated_at=now,
            workspace_path=str(Path(settings.DATA_DIR) / simulation_id)
        )
        
        # 保存到"数据库"
        simulations_db[simulation_id] = simulation_record.dict()
        
        logger.info("Created new simulation", simulation_id=simulation_id)
        
        return simulation_record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create simulation", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=SimulationList)
async def list_simulations(
    page: int = Query(1, ge=1, le=1000, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[SimulationStatus] = Query(None, description="按状态筛选")
):
    """获取模拟列表"""
    
    try:
        # 筛选模拟
        filtered_simulations = list(simulations_db.values())
        if status:
            filtered_simulations = [
                sim for sim in filtered_simulations 
                if sim['status'] == status.value
            ]
        
        # 按创建时间排序（最新的在前）
        filtered_simulations.sort(
            key=lambda x: x.get('created_at', datetime.min), 
            reverse=True
        )
        
        # 分页
        total = len(filtered_simulations)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_simulations = filtered_simulations[start:end]
        
        # 转换为响应模型
        simulations = [SimulationResponse(**sim) for sim in paginated_simulations]
        
        return SimulationList(
            simulations=simulations,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error("Failed to list simulations", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(simulation_id: str = Depends(validate_simulation_id)):
    """获取单个模拟详情"""
    
    try:
        if simulation_id not in simulations_db:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        return SimulationResponse(**simulations_db[simulation_id])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get simulation", simulation_id=simulation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{simulation_id}", response_model=SimulationResponse)
async def update_simulation(
    simulation: SimulationUpdate, 
    simulation_id: str = Depends(validate_simulation_id)
):
    """更新模拟信息"""
    
    try:
        if simulation_id not in simulations_db:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        sim_data = simulations_db[simulation_id]
        
        # 检查是否可以更新（只有PENDING状态的模拟可以更新）
        if sim_data['status'] not in [SimulationStatus.PENDING.value, SimulationStatus.FAILED.value]:
            raise HTTPException(
                status_code=400, 
                detail="Cannot update simulation in current state"
            )
        
        # 验证更新数据
        update_data = simulation.dict(exclude_unset=True)
        if 'name' in update_data and len(update_data['name']) > 100:
            raise HTTPException(status_code=400, detail="Name too long")
        
        if 'description' in update_data and len(update_data['description']) > 1000:
            raise HTTPException(status_code=400, detail="Description too long")
        
        if 'tags' in update_data:
            if len(update_data['tags']) > 10:
                raise HTTPException(status_code=400, detail="Too many tags")
            for tag in update_data['tags']:
                if len(tag) > 50:
                    raise HTTPException(status_code=400, detail="Tag too long")
        
        # 更新记录
        sim_data.update(update_data)
        sim_data['updated_at'] = datetime.utcnow()
        
        simulations_db[simulation_id] = sim_data
        
        logger.info("Updated simulation", simulation_id=simulation_id)
        
        return SimulationResponse(**sim_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update simulation", simulation_id=simulation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{simulation_id}")
async def delete_simulation(
    background_tasks: BackgroundTasks,
    simulation_id: str = Depends(validate_simulation_id)
):
    """删除模拟"""
    
    try:
        if simulation_id not in simulations_db:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        sim_data = simulations_db[simulation_id]
        
        # 检查是否可以删除（正在运行的模拟需要先取消）
        if sim_data['status'] == SimulationStatus.RUNNING.value:
            # 尝试取消任务
            if sim_data.get('task_id'):
                from celery.result import AsyncResult
                task = AsyncResult(sim_data['task_id'])
                task.revoke(terminate=True)
                logger.info("Cancelled running task before deletion", 
                           simulation_id=simulation_id, task_id=sim_data['task_id'])
        
        # 异步清理数据
        cleanup_task = cleanup_simulation_task.delay(simulation_id)
        logger.info("Started cleanup task", simulation_id=simulation_id, cleanup_task_id=cleanup_task.id)
        
        # 从数据库中移除
        del simulations_db[simulation_id]
        
        logger.info("Deleted simulation", simulation_id=simulation_id)
        
        return {"message": "Simulation deleted successfully", "cleanup_task_id": cleanup_task.id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete simulation", simulation_id=simulation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{simulation_id}/start")
async def start_simulation(simulation_id: str = Depends(validate_simulation_id)):
    """启动模拟"""
    
    try:
        if simulation_id not in simulations_db:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        sim_data = simulations_db[simulation_id]
        
        if sim_data['status'] not in [SimulationStatus.PENDING.value, SimulationStatus.FAILED.value]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot start simulation in {sim_data['status']} state"
            )
        
        # 启动异步任务
        task = run_lammps_simulation.delay(
            simulation_id=simulation_id,
            input_script=sim_data['input_script'],
            potential_files=sim_data.get('potential_files'),
            mpi_processes=sim_data['mpi_processes']
        )
        
        # 更新状态
        sim_data['status'] = SimulationStatus.RUNNING.value
        sim_data['started_at'] = datetime.utcnow()
        sim_data['task_id'] = task.id
        sim_data['updated_at'] = datetime.utcnow()
        sim_data['error_message'] = None  # 清除之前的错误信息
        
        simulations_db[simulation_id] = sim_data
        
        logger.info("Started simulation", simulation_id=simulation_id, task_id=task.id)
        
        return {"message": "Simulation started", "task_id": task.id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start simulation", simulation_id=simulation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{simulation_id}/cancel")
async def cancel_simulation(simulation_id: str = Depends(validate_simulation_id)):
    """取消模拟"""
    
    try:
        if simulation_id not in simulations_db:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        sim_data = simulations_db[simulation_id]
        
        if sim_data['status'] not in [SimulationStatus.RUNNING.value, SimulationStatus.PENDING.value]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel simulation in {sim_data['status']} state"
            )
        
        # 取消Celery任务（如果存在）
        if sim_data.get('task_id'):
            from celery.result import AsyncResult
            task = AsyncResult(sim_data['task_id'])
            task.revoke(terminate=True)
            logger.info("Revoked Celery task", simulation_id=simulation_id, task_id=sim_data['task_id'])
        
        # 更新状态
        sim_data['status'] = SimulationStatus.CANCELLED.value
        sim_data['updated_at'] = datetime.utcnow()
        sim_data['completed_at'] = datetime.utcnow()
        
        simulations_db[simulation_id] = sim_data
        
        logger.info("Cancelled simulation", simulation_id=simulation_id)
        
        return {"message": "Simulation cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel simulation", simulation_id=simulation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{simulation_id}/logs", response_model=SimulationLog)
async def get_simulation_logs(
    simulation_id: str = Depends(validate_simulation_id), 
    tail_lines: int = Query(100, ge=1, le=1000, description="获取日志的行数")
):
    """获取模拟日志"""
    
    try:
        if simulation_id not in simulations_db:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        lammps_service = LAMMPSService()
        logs = lammps_service.get_simulation_logs(simulation_id, tail_lines)
        
        if not logs['exists']:
            raise HTTPException(status_code=404, detail="Logs not found")
        
        return SimulationLog(
            simulation_id=simulation_id,
            logs=logs.get('logs', []),
            line_count=logs.get('line_count', 0),
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get simulation logs", simulation_id=simulation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{simulation_id}/results", response_model=SimulationResults)
async def get_simulation_results(simulation_id: str = Depends(validate_simulation_id)):
    """获取模拟结果"""
    
    try:
        if simulation_id not in simulations_db:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        lammps_service = LAMMPSService()
        results = lammps_service.get_simulation_results(simulation_id)
        sim_data = simulations_db[simulation_id]
        
        if not results['exists']:
            raise HTTPException(status_code=404, detail="Results not found")
        
        # 转换为文件模型
        files = []
        for file_info in results.get('files', []):
            try:
                file_path = Path(file_info['path'])
                files.append(SimulationFile(
                    name=file_info['name'],
                    size=file_info['size'],
                    path=file_info['path'],
                    last_modified=datetime.fromtimestamp(file_path.stat().st_mtime)
                ))
            except (OSError, ValueError) as e:
                logger.warning("Failed to get file info", 
                             simulation_id=simulation_id, 
                             file_path=file_info['path'], 
                             error=str(e))
                continue
        
        return SimulationResults(
            simulation_id=simulation_id,
            files=files,
            status=SimulationStatus(sim_data['status'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get simulation results", simulation_id=simulation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")