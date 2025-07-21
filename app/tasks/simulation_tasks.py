import time
import signal
from typing import Dict, Any, List, Optional

import structlog
from celery import current_task
from celery.exceptions import Ignore

from app.celery_app import celery_app
from app.services.lammps_service import LAMMPSService


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_lammps_simulation(self, simulation_id: str, input_script: str, 
                         potential_files: Optional[List[str]] = None,
                         mpi_processes: int = 1) -> Dict[str, Any]:
    """运行LAMMPS模拟任务"""
    
    task_logger = structlog.get_logger("celery_task").bind(
        task_id=self.request.id,
        simulation_id=simulation_id
    )
    
    try:
        # 输入验证
        if not simulation_id or not isinstance(simulation_id, str):
            raise ValueError("Invalid simulation_id")
        
        if not input_script or not isinstance(input_script, str):
            raise ValueError("Invalid input_script")
        
        if len(input_script) > 1024 * 1024:  # 1MB限制
            raise ValueError("Input script too large")
        
        if mpi_processes < 1 or mpi_processes > 16:
            raise ValueError("Invalid MPI processes count")
        
        task_logger.info("Starting LAMMPS simulation task")
        
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 100,
                'status': 'Initializing simulation...'
            }
        )
        
        # 创建LAMMPS服务实例
        lammps_service = LAMMPSService()
        
        # 验证输入脚本
        task_logger.info("Validating input script")
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 10,
                'total': 100,
                'status': 'Validating input script...'
            }
        )
        
        validation_result = lammps_service.validate_input_script(input_script)
        if not validation_result.get("valid", False):
            error_msg = validation_result.get("error", "Script validation failed")
            task_logger.error("Script validation failed", error=error_msg)
            raise ValueError(f"Script validation failed: {error_msg}")
        
        # 启动模拟
        task_logger.info("Starting simulation")
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 20,
                'total': 100,
                'status': 'Starting simulation...'
            }
        )
        
        result = lammps_service.run_simulation(
            simulation_id=simulation_id,
            input_script=input_script,
            potential_files=potential_files,
            mpi_processes=mpi_processes
        )
        
        if not result.get("success", False):
            error_msg = result.get("error", "Failed to start simulation")
            task_logger.error("Failed to start simulation", error=error_msg)
            raise RuntimeError(error_msg)
        
        # 监控模拟进度
        task_logger.info("Monitoring simulation progress")
        max_wait_time = 3600  # 1小时超时
        check_interval = 10   # 10秒检查一次
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            # 检查任务是否被撤销
            if self.request.called_directly is False:
                # 在Celery环境中检查撤销状态
                try:
                    # 这里可以添加撤销检查逻辑
                    pass
                except Exception:
                    pass
            
            status = lammps_service.get_simulation_status(simulation_id)
            
            if status.get("status") == "completed":
                task_logger.info("Simulation completed successfully")
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': 100,
                        'total': 100,
                        'status': 'Simulation completed'
                    }
                )
                break
            elif status.get("status") == "failed":
                error_msg = status.get("message", "Simulation failed")
                task_logger.error("Simulation failed", error=error_msg)
                raise RuntimeError(f"Simulation failed: {error_msg}")
            elif status.get("status") in ["running", "starting"]:
                # 计算进度（简单的时间基础估算）
                progress = min(20 + (elapsed_time / max_wait_time) * 70, 90)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': int(progress),
                        'total': 100,
                        'status': f'Simulation running... ({elapsed_time}s)'
                    }
                )
            
            time.sleep(check_interval)
            elapsed_time += check_interval
        
        if elapsed_time >= max_wait_time:
            task_logger.error("Simulation timeout")
            raise RuntimeError("Simulation timeout")
        
        # 收集结果
        task_logger.info("Collecting simulation results")
        results = lammps_service.get_simulation_results(simulation_id)
        
        task_logger.info("Simulation task completed successfully")
        return {
            "success": True,
            "simulation_id": simulation_id,
            "results": results,
            "message": "Simulation completed successfully"
        }
        
    except Exception as e:
        task_logger.error("Simulation task failed", error=str(e))
        
        # 尝试清理资源
        try:
            lammps_service = LAMMPSService()
            lammps_service.cleanup_simulation(simulation_id)
        except Exception as cleanup_error:
            task_logger.warning("Failed to cleanup after error", error=str(cleanup_error))
        
        # 重试逻辑
        if self.request.retries < self.max_retries:
            task_logger.info("Retrying task", retry_count=self.request.retries + 1)
            raise self.retry(countdown=60, exc=e)
        
        # 最终失败
        return {
            "success": False,
            "error": str(e),
            "simulation_id": simulation_id
        }

@celery_app.task(bind=True, max_retries=2)
def validate_lammps_script(self, script_content: str) -> Dict[str, Any]:
    """异步验证LAMMPS脚本"""
    
    task_logger = structlog.get_logger("celery_task").bind(
        task_id=self.request.id,
        task_type="validate_script"
    )
    
    try:
        # 输入验证
        if not script_content or not isinstance(script_content, str):
            raise ValueError("Invalid script content")
        
        if len(script_content) > 1024 * 1024:  # 1MB限制
            raise ValueError("Script too large")
        
        task_logger.info("Starting script validation task")
        
        lammps_service = LAMMPSService()
        result = lammps_service.validate_input_script(script_content)
        
        task_logger.info("Script validation completed", valid=result.get("valid", False))
        return result
        
    except Exception as e:
        task_logger.error("Script validation task failed", error=str(e))
        
        # 重试逻辑
        if self.request.retries < self.max_retries:
            task_logger.info("Retrying validation task", retry_count=self.request.retries + 1)
            raise self.retry(countdown=30, exc=e)
        
        return {
            "valid": False,
            "error": str(e)
        }


@celery_app.task(bind=True, max_retries=2)
def cleanup_simulation_task(self, simulation_id: str) -> Dict[str, Any]:
    """异步清理模拟数据"""
    
    task_logger = structlog.get_logger("celery_task").bind(
        task_id=self.request.id,
        simulation_id=simulation_id,
        task_type="cleanup"
    )
    
    try:
        # 输入验证
        if not simulation_id or not isinstance(simulation_id, str):
            raise ValueError("Invalid simulation_id")
        
        task_logger.info("Starting cleanup task")
        
        lammps_service = LAMMPSService()
        result = lammps_service.cleanup_simulation(simulation_id)
        
        task_logger.info("Cleanup task completed", success=result.get("success", False))
        return result
        
    except Exception as e:
        task_logger.error("Cleanup task failed", error=str(e))
        
        # 重试逻辑
        if self.request.retries < self.max_retries:
            task_logger.info("Retrying cleanup task", retry_count=self.request.retries + 1)
            raise self.retry(countdown=30, exc=e)
        
        return {
            "success": False,
            "error": str(e)
        }


@celery_app.task(bind=True, max_retries=2)
def get_simulation_status_task(self, simulation_id: str) -> Dict[str, Any]:
    """异步获取模拟状态"""
    
    task_logger = structlog.get_logger("celery_task").bind(
        task_id=self.request.id,
        simulation_id=simulation_id,
        task_type="get_status"
    )
    
    try:
        # 输入验证
        if not simulation_id or not isinstance(simulation_id, str):
            raise ValueError("Invalid simulation_id")
        
        task_logger.debug("Getting simulation status")
        
        lammps_service = LAMMPSService()
        result = lammps_service.get_simulation_status(simulation_id)
        
        return result
        
    except Exception as e:
        task_logger.error("Get status task failed", error=str(e))
        
        # 重试逻辑
        if self.request.retries < self.max_retries:
            task_logger.info("Retrying get status task", retry_count=self.request.retries + 1)
            raise self.retry(countdown=10, exc=e)
        
        return {
            "status": "error",
            "error": str(e)
        }