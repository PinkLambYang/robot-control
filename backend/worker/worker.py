"""Worker主进程"""
from __future__ import annotations
import logging
import signal
import sys
from typing import Dict, Any, Optional
import yaml

from .project_manager import ProjectManager
from .python_executor import PythonExecutor
from ipc.zmq_manager import ZMQManager

logger = logging.getLogger(__name__)


class Worker:
    """Worker进程：接收指令、管理项目、执行代码"""
    
    def __init__(self, config: Dict[str, Any], zmq_manager: ZMQManager):
        """初始化Worker
        
        Args:
            config: 配置字典
            zmq_manager: ZMQ通信管理器
        """
        self.config = config
        self.zmq = zmq_manager
        self.project_mgr = ProjectManager(config['worker']['storage_dir'])
        
        self.python_executor: Optional[PythonExecutor] = None
        self.current_project_type: Optional[str] = None
        self.current_project_path: Optional[str] = None
        
        self.running = True
        self._should_restart = False  # 重启标志
        self._has_loaded_project = False  # 是否已加载过项目
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # 尝试加载默认项目
        self._try_load_default_project_on_init()
    
    def _signal_handler(self, signum, frame):
        """处理终止信号"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _try_load_default_project_on_init(self):
        """Worker 初始化时尝试加载默认项目"""
        try:
            from pathlib import Path
            import shutil
            
            storage_dir = Path(self.project_mgr.storage_dir)
            current_dir = storage_dir / 'current'
            default_dir = storage_dir / 'default'
            
            # 检查 current 目录是否为空
            is_current_empty = not current_dir.exists() or not any(current_dir.iterdir())
            
            if is_current_empty and default_dir.exists():
                logger.info("Loading default project...")
                
                # 确保 current 目录存在
                current_dir.mkdir(parents=True, exist_ok=True)
                
                # 复制 default 项目到 current
                for item in default_dir.iterdir():
                    if item.is_file():
                        shutil.copy2(item, current_dir / item.name)
                    elif item.is_dir() and item.name not in ['__pycache__']:
                        shutil.copytree(item, current_dir / item.name, dirs_exist_ok=True)
            
            # 如果 current 目录现在有内容，尝试加载
            if current_dir.exists() and any(current_dir.iterdir()):
                try:
                    # 检测项目类型
                    project_type = self.project_mgr.detect_project_type(str(current_dir))
                    
                    if project_type == 'python':
                        self.current_project_path = str(current_dir)
                        self.current_project_type = project_type
                        
                        # 加载 Python 项目
                        self.python_executor = PythonExecutor(
                            self.current_project_path,
                            push_callback=self._handle_push_message
                        )
                        self.python_executor.load()
                        
                        logger.info("✓ Project loaded successfully")
                        self._has_loaded_project = True
                    else:
                        logger.warning(f"Unsupported project type: {project_type}")
                
                except Exception as e:
                    logger.warning(f"Failed to load project: {e}")
                    # 不抛出异常，允许 Worker 继续运行
                
        except Exception as e:
            logger.error(f"Error in _try_load_default_project_on_init: {e}", exc_info=True)
            # 不抛出异常，允许 Worker 继续运行
    
    def run(self):
        """运行Worker主循环"""
        logger.info("✓ Worker ready")
        
        try:
            while self.running:
                # 接收指令
                msg = self.zmq.receive_command()
                
                # 处理指令
                response = self._handle_command(msg)
                
                # 发送响应
                self.zmq.send_response(response)
                
                # 检查是否需要重启
                if self._should_restart:
                    logger.info("Exiting Worker to trigger restart (exit code 0)")
                    break  # 正常退出，触发重启
                    
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            raise  # 异常退出，exit code != 0
        finally:
            self._cleanup()
    
    def _handle_command(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """处理指令
        
        Args:
            msg: 指令消息
            
        Returns:
            响应消息
        """
        cmd_type = msg.get('type')
        data = msg.get('data', {})
        
        try:
            if cmd_type == 'update':
                return self._handle_update(data)
            elif cmd_type == 'start':
                return self._handle_start(data)
            elif cmd_type == 'process':
                return self._handle_process(data)
            else:
                return {
                    'status': 'error',
                    'message': f'Unknown command type: {cmd_type}'
                }
        except Exception as e:
            logger.error(f"Error handling command: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _handle_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理UPDATE指令：解压项目文件
        
        Args:
            data: {'zip_data': 'base64_encoded_zip'}
            
        Returns:
            响应消息
        """
        try:
            # 检查是否需要重启（已加载过项目）
            need_restart = self._has_loaded_project
            
            # 清理旧的执行器
            self._cleanup_executors()
            
            # 解压项目
            zip_data = data.get('zip_data')
            if not zip_data:
                return {
                    'status': 'error',
                    'message': 'Missing zip_data field'
                }
            
            project_path, project_type = self.project_mgr.extract_project(zip_data)
            
            self.current_project_path = project_path
            self.current_project_type = project_type
            
            logger.info(f"✓ Project extracted: {project_type}")
            
            # 构造响应
            response = {
                'status': 'success',
                'message': 'Project extracted successfully',
                'data': {
                    'project_type': project_type,
                    'project_path': project_path,
                    'worker_will_restart': need_restart  # 标识 Worker 是否将重启
                }
            }
            
            # 如果需要重启，设置标志并更新消息
            if need_restart:
                logger.info("Worker will restart to clear module cache")
                self._should_restart = True
                response['message'] = 'Project extracted successfully. Worker will restart to clear module cache.'
            
            return response
            
        except Exception as e:
            logger.error(f"Update failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Failed to update project: {str(e)}'
            }
    
    def _handle_start(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理START指令：启动项目
        
        Returns:
            响应消息
        """
        try:
            # 如果没有项目信息，尝试从磁盘恢复
            if not self.current_project_path or not self.current_project_type:
                from pathlib import Path
                current_path = Path(self.project_mgr.storage_dir) / 'current'
                
                if current_path.exists() and any(current_path.iterdir()):
                    # 检测项目类型
                    project_type = self.project_mgr.detect_project_type(str(current_path))
                    self.current_project_path = str(current_path)
                    self.current_project_type = project_type
                    logger.info(f"✓ Project recovered: {project_type}")
                else:
                    return {
                        'status': 'error',
                        'message': 'No project loaded. Please upload a project first (UPDATE command)'
                    }
            
            # 启动 Python 项目
            if self.current_project_type == 'python':
                result = self._start_python_project()
                # 如果启动成功，标记已加载项目
                if result.get('status') == 'success':
                    self._has_loaded_project = True
                return result
            else:
                return {
                    'status': 'error',
                    'message': f'Unsupported project type: {self.current_project_type}. Only Python projects are supported.'
                }
                
        except Exception as e:
            logger.error(f"Start failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Failed to start project: {str(e)}'
            }
    
    def _start_python_project(self) -> Dict[str, Any]:
        """启动Python项目"""
        try:
            self.python_executor = PythonExecutor(
                self.current_project_path,
                push_callback=self._handle_push_message
            )
            self.python_executor.load()
            
            logger.info("✓ Project started")
            
            return {
                'status': 'success',
                'message': 'Python project started successfully',
                'data': {
                    'project_type': 'python'
                }
            }
        except Exception as e:
            self.python_executor = None
            raise
    
    def _handle_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理PROCESS指令：执行函数调用
        
        Args:
            data: {'object': str, 'method': str, 'args': dict}
            
        Returns:
            响应消息
        """
        try:
            # 如果没有加载项目，尝试加载默认项目
            if not self.python_executor:
                self._try_load_default_project_on_init()
                
                # 如果还是没有加载成功，返回错误
                if not self.python_executor:
                    return {
                        'status': 'error',
                        'message': 'No project loaded'
                    }
            
            # 只有Python项目支持process指令
            if self.current_project_type != 'python':
                return {
                    'status': 'error',
                    'message': 'Only Python projects supported'
                }
            
            # 解析参数
            obj_name = data.get('object')
            method_name = data.get('method')
            args = data.get('args', {})
            
            if not obj_name or not method_name:
                return {
                    'status': 'error',
                    'message': 'Missing object or method'
                }
            
            # 调用函数并直接返回结果（同步响应）
            result = self.python_executor.call_function(obj_name, method_name, args)
            
            # 返回响应（不需要额外的异步回调，因为 process 本身是同步的）
            return {
                'status': 'success',
                'message': f'{method_name} executed',
                'data': result
            }
            
        except Exception as e:
            logger.error(f"Process failed: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _handle_push_message(self, event: str, data: Any):
        """处理来自用户代码的推送消息
        
        Args:
            event: 事件名称
            data: 消息数据
        """
        try:
            callback_msg = {
                'type': 'push',
                'event': event,
                'data': data
            }
            self.zmq.send_callback(callback_msg)
        except Exception as e:
            logger.error(f"Failed to push message: {e}")
    
    def _cleanup_executors(self):
        """清理执行器"""
        if self.python_executor:
            self.python_executor.cleanup()
            self.python_executor = None
    
    def _cleanup(self):
        """清理资源"""
        self._cleanup_executors()
        self.zmq.close()


def start_worker(config_path: str = 'config.yaml'):
    """启动Worker进程"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # 创建ZMQ管理器
    zmq_manager = ZMQManager(
        role='worker',
        command_socket=config['ipc']['command_socket'],
        callback_socket=config['ipc']['callback_socket']
    )
    
    # 创建并运行Worker
    worker = Worker(config, zmq_manager)
    worker.run()

