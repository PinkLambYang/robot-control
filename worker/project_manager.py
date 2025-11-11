"""项目管理器：处理zip解压和项目类型识别"""
import os
import shutil
import zipfile
import base64
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class ProjectManager:
    """管理项目的解压、存储和类型识别"""
    
    def __init__(self, storage_dir: str = './storage/projects'):
        """初始化项目管理器
        
        Args:
            storage_dir: 项目存储根目录
        """
        self.storage_dir = Path(storage_dir)
        self.current_project_dir = self.storage_dir / 'current'
        
        # 确保存储目录存在
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ProjectManager initialized with storage: {self.storage_dir}")
    
    def extract_project(self, zip_data_b64: str) -> Tuple[str, str]:
        """解压项目文件
        
        Args:
            zip_data_b64: Base64编码的zip文件数据
            
        Returns:
            (project_path, project_type) 元组
            
        Raises:
            Exception: 解压或识别失败
        """
        try:
            # 解码base64
            zip_data = base64.b64decode(zip_data_b64)
            logger.info(f"Decoded zip data: {len(zip_data)} bytes")
            
            # 清理旧项目
            if self.current_project_dir.exists():
                logger.info("Cleaning old project")
                shutil.rmtree(self.current_project_dir)
            
            # 创建当前项目目录
            self.current_project_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存zip文件
            zip_path = self.current_project_dir / 'project.zip'
            with open(zip_path, 'wb') as f:
                f.write(zip_data)
            
            # 解压（保留文件权限）
            logger.info(f"Extracting zip to {self.current_project_dir}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 解压所有文件
                zip_ref.extractall(self.current_project_dir)
                
                # 恢复Unix文件权限
                for info in zip_ref.infolist():
                    extracted_path = self.current_project_dir / info.filename
                    
                    # 获取Unix权限（如果有）
                    unix_mode = info.external_attr >> 16
                    if unix_mode:
                        try:
                            os.chmod(extracted_path, unix_mode)
                            logger.debug(f"Set permissions {oct(unix_mode)} for {info.filename}")
                        except Exception as e:
                            logger.warning(f"Failed to set permissions for {info.filename}: {e}")
            
            # 删除zip文件
            zip_path.unlink()
            
            # 识别项目类型
            project_type = self._detect_project_type(self.current_project_dir)
            logger.info(f"Project type detected: {project_type}")
            
            return str(self.current_project_dir), project_type
            
        except Exception as e:
            logger.error(f"Failed to extract project: {e}", exc_info=True)
            raise
    
    def detect_project_type(self, project_path: str) -> str:
        """公开的项目类型检测方法"""
        return self._detect_project_type(Path(project_path))
    
    def _detect_project_type(self, project_path: Path) -> str:
        """识别项目类型
        
        Args:
            project_path: 项目路径
            
        Returns:
            'python' 或 'cpp'
            
        Raises:
            ValueError: 无法识别项目类型
        """
        # 递归查找所有文件
        all_files = list(project_path.rglob('*'))
        
        # 检查是否有Python文件
        has_python = any(f.suffix == '.py' for f in all_files if f.is_file())
        
        # 检查是否有可执行文件
        has_executable = any(
            f.is_file() and os.access(f, os.X_OK) and not f.suffix
            for f in all_files
        )
        
        if has_python:
            logger.info("Python files found")
            return 'python'
        elif has_executable:
            logger.info("Executable files found")
            return 'cpp'
        else:
            # 检查是否有C++源文件但没有可执行文件
            has_cpp_source = any(
                f.suffix in ['.cpp', '.cc', '.cxx', '.c', '.h', '.hpp']
                for f in all_files if f.is_file()
            )
            if has_cpp_source:
                raise ValueError("C++ source files found but no executable. Please upload pre-compiled binaries.")
            else:
                raise ValueError("Cannot detect project type: no Python or executable files found")
    
    def get_current_project_path(self) -> Optional[str]:
        """获取当前项目路径
        
        Returns:
            项目路径，如果不存在则返回None
        """
        if self.current_project_dir.exists():
            return str(self.current_project_dir)
        return None
    
    def cleanup(self):
        """清理当前项目"""
        if self.current_project_dir.exists():
            logger.info("Cleaning up current project")
            shutil.rmtree(self.current_project_dir)

