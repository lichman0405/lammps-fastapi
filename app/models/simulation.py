from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SimulationCreate(BaseModel):
    """创建模拟的请求模型"""
    name: str = Field(..., description="模拟名称")
    description: Optional[str] = Field(None, description="模拟描述")
    input_script: str = Field(..., description="LAMMPS输入脚本内容")
    potential_files: Optional[List[str]] = Field(None, description="使用的势函数文件列表")
    mpi_processes: int = Field(1, ge=1, description="MPI进程数")
    tags: Optional[List[str]] = Field(None, description="标签列表")

class SimulationUpdate(BaseModel):
    """更新模拟的请求模型"""
    name: Optional[str] = Field(None, description="模拟名称")
    description: Optional[str] = Field(None, description="模拟描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")

class SimulationResponse(BaseModel):
    """模拟响应模型"""
    id: str = Field(..., description="模拟ID")
    name: str = Field(..., description="模拟名称")
    description: Optional[str] = Field(None, description="模拟描述")
    status: SimulationStatus = Field(..., description="模拟状态")
    input_script: str = Field(..., description="LAMMPS输入脚本")
    potential_files: Optional[List[str]] = Field(None, description="势函数文件列表")
    mpi_processes: int = Field(..., description="MPI进程数")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    task_id: Optional[str] = Field(None, description="Celery任务ID")
    workspace_path: Optional[str] = Field(None, description="工作目录路径")
    error_message: Optional[str] = Field(None, description="错误信息")

class SimulationList(BaseModel):
    """模拟列表响应模型"""
    simulations: List[SimulationResponse]
    total: int
    page: int
    page_size: int

class SimulationLog(BaseModel):
    """模拟日志模型"""
    simulation_id: str = Field(..., description="模拟ID")
    logs: List[str] = Field(..., description="日志内容")
    line_count: int = Field(..., description="日志行数")
    timestamp: datetime = Field(..., description="获取时间")

class SimulationFile(BaseModel):
    """模拟文件模型"""
    name: str = Field(..., description="文件名")
    size: int = Field(..., description="文件大小（字节）")
    path: str = Field(..., description="文件路径")
    last_modified: datetime = Field(..., description="最后修改时间")

class SimulationResults(BaseModel):
    """模拟结果模型"""
    simulation_id: str = Field(..., description="模拟ID")
    files: List[SimulationFile] = Field(..., description="结果文件列表")
    status: SimulationStatus = Field(..., description="模拟状态")

class ScriptValidationRequest(BaseModel):
    """脚本验证请求模型"""
    script_content: str = Field(..., description="LAMMPS脚本内容")

class ScriptValidationResponse(BaseModel):
    """脚本验证响应模型"""
    valid: bool = Field(..., description="是否有效")
    message: str = Field(..., description="验证消息")
    error: Optional[str] = Field(None, description="错误信息（如果有）")
    warnings: Optional[List[str]] = Field(None, description="警告信息")

class SimulationQuery(BaseModel):
    """模拟查询参数模型"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")
    status: Optional[SimulationStatus] = Field(None, description="按状态筛选")
    name: Optional[str] = Field(None, description="按名称模糊搜索")
    tags: Optional[List[str]] = Field(None, description="按标签筛选")
    created_after: Optional[datetime] = Field(None, description="创建时间之后")
    created_before: Optional[datetime] = Field(None, description="创建时间之前")

class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")
    progress: Optional[int] = Field(None, description="进度百分比")
    meta: Optional[Dict[str, Any]] = Field(None, description="额外元数据")