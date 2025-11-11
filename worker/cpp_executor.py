"""C++可执行文件管理器"""
from __future__ import annotations
import os
import subprocess
import logging
from typing import Optional
from pathlib import Path
import signal

logger = logging.getLogger(__name__)


class CppExecutor:
    """C++可执行文件执行器"""
    
    def __init__(self, project_path: str):
        """初始化C++执行器
        
        Args:
            project_path: C++项目路径
        """
        self.project_path = Path(project_path)
        self.process: Optional[subprocess.Popen] = None
        self.executable_path: Optional[Path] = None
        
        logger.info(f"CppExecutor initialized for {project_path}")
    
    def find_executable(self) -> Path:
        """查找可执行文件
        
        Returns:
            可执行文件路径
            
        Raises:
            FileNotFoundError: 未找到可执行文件
        """
        logger.info("Searching for executable files...")
        
        # 遍历项目目录
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                file_path = Path(root) / file
                
                # 检查是否是可执行文件
                # 1. 有可执行权限
                # 2. 不是脚本文件（.sh, .py等）
                if file_path.is_file() and os.access(file_path, os.X_OK):
                    # 排除脚本文件
                    if file_path.suffix not in ['.sh', '.py', '.rb', '.pl']:
                        logger.info(f"Found executable: {file_path}")
                        return file_path
        
        raise FileNotFoundError("No executable file found in project")
    
    def start(self) -> dict:
        """启动C++可执行文件
        
        Returns:
            启动结果字典
        """
        try:
            # 查找可执行文件
            self.executable_path = self.find_executable()
            
            # 确保使用绝对路径
            exec_absolute_path = self.executable_path.resolve()
            project_absolute_path = self.project_path.resolve()
            
            # 启动进程
            logger.info(f"Starting executable: {exec_absolute_path}")
            logger.info(f"Working directory: {project_absolute_path}")
            self.process = subprocess.Popen(
                [str(exec_absolute_path)],
                cwd=str(project_absolute_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            logger.info(f"Process started with PID: {self.process.pid}")
            
            return {
                'status': 'success',
                'pid': self.process.pid,
                'executable': str(self.executable_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to start executable: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def stop(self, timeout: int = 5) -> dict:
        """停止C++进程
        
        Args:
            timeout: 终止超时时间（秒）
            
        Returns:
            停止结果字典
        """
        if self.process is None:
            return {'status': 'success', 'message': 'No process running'}
        
        try:
            logger.info(f"Stopping process {self.process.pid}")
            
            # 先尝试优雅终止
            self.process.terminate()
            
            try:
                # 等待进程结束
                self.process.wait(timeout=timeout)
                logger.info("Process terminated gracefully")
            except subprocess.TimeoutExpired:
                # 超时后强制终止
                logger.warning(f"Process did not terminate within {timeout}s, killing...")
                self.process.kill()
                self.process.wait()
                logger.info("Process killed")
            
            return {'status': 'success', 'message': 'Process stopped'}
            
        except Exception as e:
            logger.error(f"Failed to stop process: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
        finally:
            self.process = None
    
    def is_running(self) -> bool:
        """检查进程是否正在运行"""
        if self.process is None:
            return False
        
        # 检查进程状态
        return self.process.poll() is None
    
    def get_output(self) -> tuple[str, str]:
        """获取进程的输出
        
        Returns:
            (stdout, stderr) 元组
        """
        if self.process is None:
            return '', ''
        
        try:
            # 非阻塞读取
            import select
            
            stdout_data = ''
            stderr_data = ''
            
            # 读取stdout
            if self.process.stdout:
                # 设置为非阻塞模式
                import fcntl
                flags = fcntl.fcntl(self.process.stdout, fcntl.F_GETFL)
                fcntl.fcntl(self.process.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                
                try:
                    stdout_data = self.process.stdout.read()
                except:
                    pass
            
            # 读取stderr
            if self.process.stderr:
                flags = fcntl.fcntl(self.process.stderr, fcntl.F_GETFL)
                fcntl.fcntl(self.process.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                
                try:
                    stderr_data = self.process.stderr.read()
                except:
                    pass
            
            return stdout_data, stderr_data
            
        except Exception as e:
            logger.error(f"Failed to get output: {e}")
            return '', ''
    
    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up CppExecutor")
        self.stop()

