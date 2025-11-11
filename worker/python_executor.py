"""Python动态执行器"""
import sys
import importlib
import importlib.util
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PythonExecutor:
    """Python项目动态加载和执行器"""
    
    def __init__(self, project_path: str):
        """初始化Python执行器
        
        Args:
            project_path: Python项目路径
        """
        self.project_path = Path(project_path)
        self.module = None
        self.context: Dict[str, Any] = {}  # 存储已创建的对象实例
        self.original_sys_path = sys.path.copy()
        
        logger.info(f"PythonExecutor initialized for {project_path}")
    
    def load(self):
        """加载Python模块"""
        try:
            # 将项目路径添加到sys.path
            if str(self.project_path) not in sys.path:
                sys.path.insert(0, str(self.project_path))
                logger.info(f"Added {self.project_path} to sys.path")
            
            # 查找入口文件
            entry_file = self._find_entry_file()
            if not entry_file:
                raise FileNotFoundError("No entry file found (main.py or __init__.py)")
            
            logger.info(f"Loading entry file: {entry_file}")
            
            # 导入模块
            if entry_file.name == 'main.py':
                self.module = importlib.import_module('main')
            elif entry_file.name == '__init__.py':
                # 如果是__init__.py，导入包
                package_name = self.project_path.name
                self.module = importlib.import_module(package_name)
            
            logger.info("Module loaded successfully")
            
            # 如果模块有init函数，调用它
            if hasattr(self.module, 'init'):
                logger.info("Calling module's init() function")
                self.module.init()
            
        except Exception as e:
            logger.error(f"Failed to load module: {e}", exc_info=True)
            raise
    
    def _find_entry_file(self) -> Optional[Path]:
        """查找入口文件（main.py或__init__.py）"""
        main_py = self.project_path / 'main.py'
        if main_py.exists():
            return main_py
        
        init_py = self.project_path / '__init__.py'
        if init_py.exists():
            return init_py
        
        return None
    
    def call_function(self, obj_name: str, method_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """调用Python函数
        
        Args:
            obj_name: 对象名称（在context中或module的属性）
            method_name: 方法名称
            args: 方法参数
            
        Returns:
            执行结果字典
        """
        try:
            logger.info(f"Calling {obj_name}.{method_name}({args})")
            
            # 获取对象
            obj = self._get_object(obj_name)
            
            # 获取方法
            if not hasattr(obj, method_name):
                raise AttributeError(f"Object '{obj_name}' has no method '{method_name}'")
            
            method = getattr(obj, method_name)
            
            # 调用方法
            if callable(method):
                result = method(**args)
            else:
                raise TypeError(f"{obj_name}.{method_name} is not callable")
            
            logger.info(f"Method executed successfully, result: {result}")
            
            return {
                'status': 'success',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to call function: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _get_object(self, obj_name: str) -> Any:
        """获取对象（从context或module）
        
        Args:
            obj_name: 对象名称
            
        Returns:
            对象实例
            
        Raises:
            AttributeError: 对象不存在
        """
        # 先从context中查找
        if obj_name in self.context:
            return self.context[obj_name]
        
        # 再从module中查找
        if self.module and hasattr(self.module, obj_name):
            obj = getattr(self.module, obj_name)
            # 如果是类，实例化它并保存到context
            if isinstance(obj, type):
                logger.info(f"Instantiating class {obj_name}")
                instance = obj()
                self.context[obj_name] = instance
                return instance
            else:
                # 如果已经是实例，保存到context
                self.context[obj_name] = obj
                return obj
        
        raise AttributeError(f"Object '{obj_name}' not found in context or module")
    
    def create_instance(self, class_name: str, args: Dict[str, Any], instance_name: Optional[str] = None):
        """创建对象实例并保存到context
        
        Args:
            class_name: 类名
            args: 构造函数参数
            instance_name: 实例名称（可选，默认使用类名的snake_case）
        """
        try:
            if not self.module:
                raise RuntimeError("Module not loaded")
            
            if not hasattr(self.module, class_name):
                raise AttributeError(f"Class '{class_name}' not found in module")
            
            cls = getattr(self.module, class_name)
            instance = cls(**args)
            
            # 确定实例名称
            if instance_name is None:
                # 转换为snake_case
                instance_name = self._camel_to_snake(class_name)
            
            self.context[instance_name] = instance
            logger.info(f"Created instance '{instance_name}' of class {class_name}")
            
        except Exception as e:
            logger.error(f"Failed to create instance: {e}", exc_info=True)
            raise
    
    def _camel_to_snake(self, name: str) -> str:
        """将CamelCase转换为snake_case"""
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    
    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up PythonExecutor")
        
        # 清理context中的对象
        self.context.clear()
        
        # 恢复sys.path（注意：无法完全卸载已导入的模块）
        sys.path = self.original_sys_path.copy()
        
        self.module = None

