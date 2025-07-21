import os
import json
import shutil
import subprocess
import tempfile
import signal
import psutil
import re
import time
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, List, Optional

import structlog

from app.core.config import get_settings

settings = get_settings()

logger = structlog.get_logger()

class LAMMPSService:
    """LAMMPS模拟服务封装类"""
    
    def __init__(self):
        self.potentials_path = Path(settings.LAMMPS_POTENTIALS_PATH)
        self.data_dir = Path(settings.DATA_DIR)
        self.logger = structlog.get_logger(__name__)
        
        # 确保目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def _validate_simulation_id(self, simulation_id: str) -> bool:
        """验证模拟ID的安全性"""
        # 只允许字母数字和连字符，防止路径遍历
        import re
        return bool(re.match(r'^[a-zA-Z0-9\-_]+$', simulation_id))
    
    def _sanitize_path(self, path: Path, base_path: Path) -> Path:
        """确保路径在基础目录内，防止路径遍历攻击"""
        try:
            resolved_path = path.resolve()
            base_resolved = base_path.resolve()
            resolved_path.relative_to(base_resolved)
            return resolved_path
        except ValueError:
            raise ValueError(f"Path {path} is outside base directory {base_path}")
    
    @contextmanager
    def _secure_temp_file(self, suffix='.in'):
        """安全的临时文件管理"""
        temp_file = None
        try:
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix=suffix, 
                delete=False,
                dir=tempfile.gettempdir()
            )
            yield temp_file
        finally:
            if temp_file:
                temp_file.close()
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    pass
        
    def create_simulation_workspace(self, simulation_id: str) -> Path:
        """创建模拟工作目录"""
        if not self._validate_simulation_id(simulation_id):
            raise ValueError(f"Invalid simulation ID: {simulation_id}")
            
        workspace = self.data_dir / simulation_id
        workspace = self._sanitize_path(workspace, self.data_dir)
        workspace.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (workspace / "input").mkdir(exist_ok=True)
        (workspace / "output").mkdir(exist_ok=True)
        (workspace / "logs").mkdir(exist_ok=True)
        
        self.logger.info("Created simulation workspace", 
                        simulation_id=simulation_id, 
                        workspace=str(workspace))
        return workspace
    
    def validate_input_script(self, script_content: str) -> Dict[str, Any]:
        """验证LAMMPS输入脚本的语法"""
        # 检查脚本长度
        if len(script_content) > settings.MAX_SCRIPT_SIZE:
            return {
                "valid": False,
                "message": "Script too large",
                "error": f"Script size exceeds {settings.MAX_SCRIPT_SIZE} bytes"
            }
        
        # 检查危险命令
        dangerous_commands = ['shell', 'python', 'variable', 'include']
        lines = script_content.lower().split('\n')
        for line in lines:
            line = line.strip()
            if any(cmd in line for cmd in dangerous_commands):
                self.logger.warning("Potentially dangerous command detected", line=line)
        
        try:
            with self._secure_temp_file() as temp_file:
                temp_file.write(script_content)
                temp_file.flush()
                
                # 使用LAMMPS进行语法检查（不执行模拟）
                cmd = [settings.LAMMPS_EXECUTABLE, "-in", temp_file.name, "-screen", "none", "-log", "none"]
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=30,
                    cwd=tempfile.gettempdir()
                )
                
                if result.returncode == 0:
                    return {
                        "valid": True,
                        "message": "Input script is valid"
                    }
                else:
                    return {
                        "valid": False,
                        "message": "Input script validation failed",
                        "error": result.stderr
                    }
                    
        except subprocess.TimeoutExpired:
            return {
                "valid": False,
                "message": "Validation timeout",
                "error": "Script validation took too long"
            }
        except Exception as e:
            self.logger.error("Script validation error", error=str(e))
            return {
                "valid": False,
                "message": "Validation error",
                "error": str(e)
            }
    
    def run_simulation(self, simulation_id: str, input_script: str, 
                      potential_files: Optional[List[str]] = None,
                      mpi_processes: int = 1) -> Dict[str, Any]:
        """运行LAMMPS模拟"""
        
        if not self._validate_simulation_id(simulation_id):
            raise ValueError(f"Invalid simulation ID: {simulation_id}")
        
        # 验证MPI进程数
        if mpi_processes < 1 or mpi_processes > 16:  # 限制最大进程数
            raise ValueError("MPI processes must be between 1 and 16")
        
        workspace = self.create_simulation_workspace(simulation_id)
        sim_logger = structlog.get_logger("simulation").bind(simulation_id=simulation_id)
        
        try:
            # 保存输入脚本
            input_file = workspace / "input" / "lammps.in"
            with open(input_file, 'w', encoding='utf-8') as f:
                f.write(input_script)
            
            # 复制势函数文件（安全检查）
            if potential_files:
                for potential_file in potential_files:
                    # 验证文件名安全性
                    if not re.match(r'^[a-zA-Z0-9._\-]+$', potential_file):
                        sim_logger.warning("Skipping unsafe potential file", file=potential_file)
                        continue
                        
                    src = self.potentials_path / potential_file
                    src = self._sanitize_path(src, self.potentials_path)
                    
                    if src.exists():
                        dst = workspace / "input" / potential_file
                        shutil.copy2(src, dst)
                        sim_logger.info("Copied potential file", file=potential_file)
                    else:
                        sim_logger.warning("Potential file not found", file=potential_file)
            
            # 构建运行命令
            log_file = workspace / "logs" / "lammps.log"
            output_file = workspace / "output" / "lammps.out"
            
            if mpi_processes > 1:
                cmd = ["mpirun", "-np", str(mpi_processes), 
                       settings.LAMMPS_EXECUTABLE, 
                       "-in", str(input_file), 
                       "-log", str(log_file),
                       "-screen", str(output_file)]
            else:
                cmd = [settings.LAMMPS_EXECUTABLE, 
                       "-in", str(input_file), 
                       "-log", str(log_file),
                       "-screen", str(output_file)]
            
            sim_logger.info("Starting LAMMPS simulation", 
                          command=" ".join(cmd),
                          mpi_processes=mpi_processes)
            
            # 运行模拟（使用更安全的进程管理）
            process = subprocess.Popen(
                cmd,
                cwd=workspace,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid  # 创建新的进程组
            )
            
            # 保存进程信息到文件
            process_info_file = workspace / "process.json"
            with open(process_info_file, 'w') as f:
                json.dump({
                    "pid": process.pid,
                    "command": " ".join(cmd),
                    "started_at": datetime.utcnow().isoformat(),
                    "mpi_processes": mpi_processes
                }, f)
            
            return {
                "success": True,
                "simulation_id": simulation_id,
                "workspace": str(workspace),
                "process_id": process.pid,
                "command": " ".join(cmd)
            }
            
        except Exception as e:
            sim_logger.error("Failed to start simulation", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_simulation_status(self, simulation_id: str) -> Dict[str, Any]:
        """获取模拟状态"""
        
        if not self._validate_simulation_id(simulation_id):
            raise ValueError(f"Invalid simulation ID: {simulation_id}")
        
        workspace = self.data_dir / simulation_id
        workspace = self._sanitize_path(workspace, self.data_dir)
        
        if not workspace.exists():
            return {
                "status": "not_found",
                "error": "Simulation workspace not found"
            }
        
        sim_logger = structlog.get_logger("simulation").bind(simulation_id=simulation_id)
        
        try:
            # 检查进程信息文件
            process_info_file = workspace / "process.json"
            if process_info_file.exists():
                try:
                    with open(process_info_file, 'r') as f:
                        process_info = json.load(f)
                
                    pid = process_info.get("pid")
                    if pid:
                        # 检查进程是否还在运行
                        try:
                            os.kill(pid, 0)  # 不发送信号，只检查进程是否存在
                            process_running = True
                        except (OSError, ProcessLookupError):
                            process_running = False
                    else:
                        process_running = False
                except (json.JSONDecodeError, KeyError) as e:
                    sim_logger.warning("Failed to read process info", error=str(e))
                    process_running = False
            else:
                process_running = False
            
            # 检查日志文件
            log_file = workspace / "logs" / "lammps.log"
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        log_content = f.read()
                
                    # 检查是否有错误
                    if "ERROR" in log_content.upper():
                        return {
                            "status": "failed",
                            "message": "Simulation failed with errors",
                            "process_running": process_running
                        }
                
                    # 检查是否完成
                    if "Total wall time:" in log_content or "Loop time of" in log_content:
                        return {
                            "status": "completed",
                            "message": "Simulation completed successfully",
                            "process_running": process_running
                        }
                
                    # 如果进程不在运行但没有完成标志，可能是异常终止
                    if not process_running:
                        return {
                            "status": "failed",
                            "message": "Simulation process terminated unexpectedly",
                            "process_running": False
                        }
                
                    # 进程在运行且没有错误，认为是运行中
                    return {
                        "status": "running",
                        "message": "Simulation is running",
                        "process_running": process_running
                    }
                    
                except Exception as e:
                    sim_logger.warning("Failed to read log file", error=str(e))
                    return {
                        "status": "unknown",
                        "error": f"Failed to read log file: {str(e)}",
                        "process_running": process_running
                    }
            else:
                # 没有日志文件
                if process_running:
                    return {
                        "status": "starting",
                        "message": "Simulation is starting",
                        "process_running": True
                    }
                else:
                    return {
                        "status": "pending",
                        "message": "Simulation not started",
                        "process_running": False
                    }
                    
        except Exception as e:
            sim_logger.error("Failed to get simulation status", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_simulation_logs(self, simulation_id: str, tail_lines: int = 100) -> Dict[str, Any]:
        """获取模拟日志"""
        
        if not self._validate_simulation_id(simulation_id):
            raise ValueError(f"Invalid simulation ID: {simulation_id}")
        
        # 限制tail_lines的范围
        tail_lines = max(1, min(tail_lines, 10000))  # 限制在1-10000行之间
        
        workspace = self.data_dir / simulation_id
        workspace = self._sanitize_path(workspace, self.data_dir)
        
        if not workspace.exists():
            return {
                "success": False,
                "error": "Simulation workspace not found"
            }
        
        log_file = workspace / "logs" / "lammps.log"
        sim_logger = structlog.get_logger("simulation").bind(simulation_id=simulation_id)
        
        try:
            if not log_file.exists():
                return {
                    "success": True,
                    "logs": "",
                    "lines": 0,
                    "message": "Log file not found"
                }
            
            # 检查文件大小，防止读取过大的文件
            file_size = log_file.stat().st_size
            max_file_size = 50 * 1024 * 1024  # 50MB
            
            if file_size > max_file_size:
                sim_logger.warning("Log file too large", size=file_size)
                return {
                    "success": False,
                    "error": f"Log file too large ({file_size} bytes). Maximum allowed: {max_file_size} bytes"
                }
            
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                if tail_lines > 0:
                    # 读取最后N行
                    lines = f.readlines()
                    if len(lines) > tail_lines:
                        lines = lines[-tail_lines:]
                    log_content = ''.join(lines)
                else:
                    # 读取全部内容
                    log_content = f.read()
            
            return {
                "success": True,
                "logs": log_content,
                "lines": len(log_content.splitlines()),
                "file_size": file_size,
                "tail_lines": tail_lines if tail_lines > 0 else "all"
            }
            
        except Exception as e:
            sim_logger.error("Failed to read simulation logs", error=str(e))
            return {
                "success": False,
                "error": f"Failed to read logs: {str(e)}"
            }
    
    def get_simulation_results(self, simulation_id: str) -> Dict[str, Any]:
        """获取模拟结果文件列表"""
        
        if not self._validate_simulation_id(simulation_id):
            raise ValueError(f"Invalid simulation ID: {simulation_id}")
        
        workspace = self.data_dir / simulation_id
        workspace = self._sanitize_path(workspace, self.data_dir)
        
        if not workspace.exists():
            return {
                "success": False,
                "error": "Simulation workspace not found"
            }
        
        output_dir = workspace / "output"
        sim_logger = structlog.get_logger("simulation").bind(simulation_id=simulation_id)
        
        try:
            if not output_dir.exists():
                return {
                    "success": True,
                    "files": [],
                    "message": "Output directory not found"
                }
            
            files = []
            for file_path in output_dir.iterdir():
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        files.append({
                            "name": file_path.name,
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                            "path": str(file_path.relative_to(workspace))
                        })
                    except Exception as e:
                        sim_logger.warning("Failed to get file info", file=file_path.name, error=str(e))
                        continue
            
            # 按修改时间排序
            files.sort(key=lambda x: x["modified"], reverse=True)
            
            return {
                "success": True,
                "files": files,
                "count": len(files)
            }
            
        except Exception as e:
            sim_logger.error("Failed to get simulation results", error=str(e))
            return {
                "success": False,
                "error": f"Failed to get results: {str(e)}"
            }
    
    def cleanup_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """清理模拟工作目录"""
        
        if not self._validate_simulation_id(simulation_id):
            raise ValueError(f"Invalid simulation ID: {simulation_id}")
        
        workspace = self.data_dir / simulation_id
        workspace = self._sanitize_path(workspace, self.data_dir)
        
        sim_logger = structlog.get_logger("simulation").bind(simulation_id=simulation_id)
        
        try:
            if not workspace.exists():
                return {
                    "success": True,
                    "message": "Workspace already cleaned or not found"
                }
            
            # 首先尝试终止可能还在运行的进程
            process_info_file = workspace / "process.json"
            if process_info_file.exists():
                try:
                    with open(process_info_file, 'r') as f:
                        process_info = json.load(f)
                    
                    pid = process_info.get("pid")
                    if pid:
                        try:
                            # 尝试优雅地终止进程组
                            os.killpg(os.getpgid(pid), signal.SIGTERM)
                            time.sleep(2)  # 等待进程终止
                            
                            # 检查进程是否还在运行
                            try:
                                os.kill(pid, 0)
                                # 如果还在运行，强制终止
                                os.killpg(os.getpgid(pid), signal.SIGKILL)
                                sim_logger.info("Forcefully terminated simulation process", pid=pid)
                            except (OSError, ProcessLookupError):
                                sim_logger.info("Simulation process already terminated", pid=pid)
                                
                        except (OSError, ProcessLookupError):
                            sim_logger.info("Process not found during cleanup", pid=pid)
                            
                except Exception as e:
                    sim_logger.warning("Failed to terminate process during cleanup", error=str(e))
            
            # 删除工作目录
            shutil.rmtree(workspace)
            sim_logger.info("Cleaned up simulation workspace")
            
            return {
                "success": True,
                "message": "Simulation workspace cleaned up successfully"
            }
            
        except Exception as e:
            sim_logger.error("Failed to cleanup simulation", error=str(e))
            return {
                "success": False,
                "error": f"Failed to cleanup: {str(e)}"
            }