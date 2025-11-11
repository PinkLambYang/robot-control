"""Worker主进程"""
import logging
import signal
import sys
from typing import Dict, Any, Optional
import yaml

from .project_manager import ProjectManager
from .python_executor import PythonExecutor
from .cpp_executor import CppExecutor
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
        self.cpp_executor: Optional[CppExecutor] = None
        self.current_project_type: Optional[str] = None
        self.current_project_path: Optional[str] = None
        
        self.running = True
        self._should_restart = False  # 重启标志
        self._has_loaded_project = False  # 是否已加载过项目
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Worker initialized")
    
    def _signal_handler(self, signum, frame):
        """处理终止信号"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def run(self):
        """运行Worker主循环"""
        logger.info("Worker started, waiting for commands...")
        
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
        
        logger.info(f"Handling command: {cmd_type}")
        
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
            
            logger.info(f"Project updated: type={project_type}, path={project_path}, need_restart={need_restart}")
            
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
                logger.info("No project loaded, checking for existing project...")
                current_path = Path(self.project_mgr.storage_dir) / 'current'
                
                if current_path.exists() and any(current_path.iterdir()):
                    # 检测项目类型
                    project_type = self.project_mgr.detect_project_type(str(current_path))
                    self.current_project_path = str(current_path)
                    self.current_project_type = project_type
                    logger.info(f"Recovered project from disk: type={project_type}, path={current_path}")
                else:
                    return {
                        'status': 'error',
                        'message': 'No project loaded. Please upload a project first (UPDATE command)'
                    }
            
            # 根据项目类型启动
            if self.current_project_type == 'python':
                result = self._start_python_project()
                # 如果启动成功，标记已加载项目
                if result.get('status') == 'success':
                    self._has_loaded_project = True
                return result
            elif self.current_project_type == 'cpp':
                result = self._start_cpp_project()
                # C++ 项目不需要重启（无模块缓存问题）
                return result
            else:
                return {
                    'status': 'error',
                    'message': f'Unknown project type: {self.current_project_type}'
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
            logger.info("Starting Python project...")
            
            self.python_executor = PythonExecutor(self.current_project_path)
            self.python_executor.load()
            
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
    
    def _start_cpp_project(self) -> Dict[str, Any]:
        """启动C++项目"""
        try:
            logger.info("Starting C++ project...")
            
            self.cpp_executor = CppExecutor(self.current_project_path)
            result = self.cpp_executor.start()
            
            if result['status'] == 'error':
                self.cpp_executor = None
                return result
            
            return {
                'status': 'success',
                'message': 'C++ project started successfully',
                'data': result
            }
        except Exception as e:
            self.cpp_executor = None
            raise
    
    def _handle_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理PROCESS指令：执行函数调用
        
        Args:
            data: {'object': str, 'method': str, 'args': dict}
            
        Returns:
            响应消息
        """
        try:
            # 只有Python项目支持process指令
            if self.current_project_type != 'python':
                return {
                    'status': 'error',
                    'message': 'PROCESS command is only supported for Python projects'
                }
            
            if not self.python_executor:
                return {
                    'status': 'error',
                    'message': 'Python project not started. Please use START command first'
                }
            
            # 解析参数
            obj_name = data.get('object')
            method_name = data.get('method')
            args = data.get('args', {})
            
            if not obj_name or not method_name:
                return {
                    'status': 'error',
                    'message': 'Missing object or method field'
                }
            
            # 调用函数
            logger.info(f"Calling {obj_name}.{method_name}({args})")
            result = self.python_executor.call_function(obj_name, method_name, args)
            
            # 如果执行成功，发送异步回调
            if result.get('status') == 'success':
                callback_msg = {
                    'type': 'callback',
                    'data': {
                        'object': obj_name,
                        'method': method_name,
                        'result': result.get('result')
                    }
                }
                self.zmq.send_callback(callback_msg)
            
            # 返回立即响应（ACK）
            return {
                'status': 'success',
                'message': 'Command executed',
                'data': result
            }
            
        except Exception as e:
            logger.error(f"Process failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Failed to execute command: {str(e)}'
            }
    
    def _cleanup_executors(self):
        """清理执行器"""
        if self.python_executor:
            logger.info("Cleaning up Python executor")
            self.python_executor.cleanup()
            self.python_executor = None
        
        if self.cpp_executor:
            logger.info("Cleaning up C++ executor")
            self.cpp_executor.cleanup()
            self.cpp_executor = None
    
    def _cleanup(self):
        """清理资源"""
        logger.info("Cleaning up Worker")
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

