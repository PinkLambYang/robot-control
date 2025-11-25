"""Python动态执行器"""
from __future__ import annotations
import sys
import importlib
import importlib.util
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PythonExecutor:
    """Python项目动态加载和执行器"""
    
    def __init__(self, project_path: str, push_callback=None):
        """初始化Python执行器

        Args:
            project_path: Python项目路径
            push_callback: 可选的推送回调函数，用于主动向前端推送消息
        """
        self.project_path = Path(project_path)
        self.module = None
        self.context: Dict[str, Any] = {}  # 存储已创建的对象实例
        self.original_sys_path = sys.path.copy()
        self.push_callback = push_callback
        self.loaded_modules = set()  # 记录加载前的模块列表
    
    def load(self):
        """加载Python模块"""
        try:
            # 记录加载前的模块列表
            self.loaded_modules = set(sys.modules.keys())

            # 将项目路径添加到sys.path
            if str(self.project_path) not in sys.path:
                sys.path.insert(0, str(self.project_path))
            
            # 查找入口文件
            entry_file = self._find_entry_file()
            if not entry_file:
                raise FileNotFoundError("No entry file found (main.py or __init__.py)")
            
            # 导入模块
            if entry_file.name == 'main.py':
                self.module = importlib.import_module('main')
            elif entry_file.name == '__init__.py':
                # 如果是__init__.py，导入包
                package_name = self.project_path.name
                self.module = importlib.import_module(package_name)
            
            # 注入推送函数到模块
            if self.push_callback:
                self._inject_push_function()
            
            # 如果模块有init函数，调用它
            if hasattr(self.module, 'init'):
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
            
            return {
                'status': 'success',
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error calling {obj_name}.{method_name}(): {e}")
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
            
        except Exception as e:
            logger.error(f"Failed to create instance: {e}", exc_info=True)
            raise
    
    def _camel_to_snake(self, name: str) -> str:
        """将CamelCase转换为snake_case"""
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    
    def _inject_push_function(self):
        """注入推送函数到用户模块（全局函数方式）
        
        将 push_message 函数注入到模块的全局命名空间，
        让用户代码可以直接调用 push_message(event, data)
        """
        def push_message(event: str, data: Any):
            """推送消息到前端
            
            Args:
                event: 事件名称（如 'recognition_result'）
                data: 消息数据（可JSON序列化的对象）
            """
            if self.push_callback:
                try:
                    self.push_callback(event, data)
                except Exception as e:
                    logger.error(f"Failed to push message: {e}", exc_info=True)
            else:
                logger.warning("No push callback available")
        
        # 注入到模块的全局命名空间
        if self.module:
            setattr(self.module, 'push_message', push_message)
            logger.debug("Injected push_message function into module")
    
    def stop_threads(self):
        """停止用户代码中运行的线程（不清理缓存）
        
        调用用户代码的约定 stop() 方法：
        1. 模块级别的 stop() 函数
        2. context 中每个对象的 stop() 方法
        """
        logger.info("Stopping user threads...")
        stopped_count = 0
        
        try:
            # 1. 尝试调用模块级别的 stop() 函数
            if self.module and hasattr(self.module, 'stop'):
                try:
                    logger.debug("Calling module.stop()")
                    self.module.stop()
                    stopped_count += 1
                except Exception as e:
                    logger.warning(f"Module stop() failed: {e}")
            
            # 2. 遍历 context 中的对象，调用它们的 stop() 方法
            for obj_name, obj in self.context.items():
                try:
                    if hasattr(obj, 'stop') and callable(getattr(obj, 'stop')):
                        logger.debug(f"Calling {obj_name}.stop()")
                        obj.stop()
                        stopped_count += 1
                except Exception as e:
                    logger.warning(f"Failed to stop {obj_name}: {e}")
            
            logger.info(f"Thread stop completed (called {stopped_count} stop method(s))")
            
        except Exception as e:
            logger.error(f"Error stopping threads: {e}", exc_info=True)
    
    def cleanup(self):
        """清理资源"""
        logger.debug("Starting Python executor cleanup")

        # 1. 清理注入的函数
        if self.module and hasattr(self.module, 'push_message'):
            try:
                delattr(self.module, 'push_message')
                logger.debug("Removed injected push_message function")
            except Exception as e:
                logger.warning(f"Failed to remove push_message: {e}")

        # 2. 清理context中的对象
        self.context.clear()

        # 3. 清理 sys.modules 中新加载的模块
        if self.loaded_modules:
            current_modules = set(sys.modules.keys())
            new_modules = current_modules - self.loaded_modules

            for mod_name in new_modules:
                # 只删除项目相关的模块（main 及其子模块）
                if mod_name == 'main' or mod_name.startswith('main.'):
                    logger.debug(f"Removing module from sys.modules: {mod_name}")
                    try:
                        sys.modules.pop(mod_name, None)
                    except Exception as e:
                        logger.warning(f"Failed to remove module {mod_name}: {e}")

        # 4. 恢复sys.path
        sys.path = self.original_sys_path.copy()

        # 5. 清理模块引用
        self.module = None

        logger.debug("Python executor cleanup completed")

