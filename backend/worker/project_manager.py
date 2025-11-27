"""项目管理器：处理zip解压和项目类型识别"""
from __future__ import annotations
import os
import shutil
import zipfile
import base64
import logging
from typing import Optional, List, Tuple
from pathlib import Path

from utils.error_codes import ErrorCode

logger = logging.getLogger(__name__)


class ProjectError(Exception):
    """项目管理错误基类
    
    Attributes:
        error_code: 错误码
        message: 错误消息
    """
    def __init__(self, error_code: ErrorCode, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(message)


class ProjectManager:
    """管理项目的解压、存储和类型识别"""

    # 安全配置
    MAX_ZIP_SIZE = 20 * 1024 * 1024  # 20MB
    MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_FILES = 10  # 最多 10 个文件

    # 允许的文件扩展名白名单
    ALLOWED_EXTENSIONS = {'.py', '.txt', '.md', '.json', '.yaml', '.yml', '.ini', '.cfg', '.toml'}

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
            ValueError: 安全检查失败
            Exception: 解压或识别失败
        """
        try:
            # 解码base64
            zip_data = base64.b64decode(zip_data_b64)
            logger.info(f"Decoded zip data: {len(zip_data)} bytes")

            # 1. 检查 ZIP 文件大小
            if len(zip_data) > self.MAX_ZIP_SIZE:
                raise ProjectError(
                    ErrorCode.PROJECT_INVALID_FORMAT,
                    f"ZIP 文件过大: {len(zip_data)} 字节 "
                    f"(最大允许: {self.MAX_ZIP_SIZE} 字节)"
                )

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

            # 2. 执行安全检查并解压
            logger.info(f"Validating and extracting zip to {self.current_project_dir}")
            self._safe_extract(zip_path, self.current_project_dir)

            # 删除zip文件
            zip_path.unlink()

            # 识别项目类型
            project_type = self._detect_project_type(self.current_project_dir)
            logger.info(f"Project type detected: {project_type}")

            return str(self.current_project_dir), project_type

        except ProjectError:
            # 项目错误（包含错误码），直接抛出
            raise
        except Exception as e:
            logger.error(f"Failed to extract project: {e}", exc_info=True)
            # 其他未知错误，包装为项目上传失败
            raise ProjectError(
                ErrorCode.PROJECT_UPLOAD_FAILED,
                f"项目上传失败: {str(e)}"
            )
    
    def detect_project_type(self, project_path: str) -> str:
        """公开的项目类型检测方法"""
        return self._detect_project_type(Path(project_path))

    def _safe_extract(self, zip_path: Path, extract_to: Path) -> None:
        """安全解压 ZIP 文件，防止路径遍历和炸弹攻击

        Args:
            zip_path: ZIP 文件路径
            extract_to: 目标解压目录

        Raises:
            ValueError: 如果检测到安全问题
        """
        extract_to = extract_to.resolve()
        errors: List[str] = []

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 1. 检查文件数量
            file_count = len(zip_ref.namelist())
            if file_count > self.MAX_FILES:
                raise ProjectError(
                    ErrorCode.PROJECT_INVALID_FORMAT,
                    f"ZIP 文件数量过多: {file_count} 个文件 "
                    f"(最大允许: {self.MAX_FILES} 个)"
                )

            # 2. 检查解压后总大小（防止 Zip 炸弹）
            total_size = sum(info.file_size for info in zip_ref.infolist())
            if total_size > self.MAX_UNCOMPRESSED_SIZE:
                raise ProjectError(
                    ErrorCode.PROJECT_INVALID_FORMAT,
                    f"解压后大小过大: {total_size} 字节 "
                    f"(最大允许: {self.MAX_UNCOMPRESSED_SIZE} 字节)"
                )

            # 3. 逐个文件验证
            for info in zip_ref.infolist():
                # 跳过目录
                if info.is_dir():
                    continue

                member = info.filename

                # 3.1 检查文件扩展名
                file_ext = Path(member).suffix.lower()
                if file_ext and file_ext not in self.ALLOWED_EXTENSIONS:
                    errors.append(f"{member}: 不允许的文件类型 ({file_ext})")
                    continue

                # 3.2 检查路径安全性
                if not self._is_safe_path(member, extract_to):
                    errors.append(f"{member}: 不安全的路径")
                    continue

                # 3.3 检查压缩比（防止压缩炸弹）
                if info.compress_size > 0:
                    ratio = info.file_size / info.compress_size
                    if ratio > 100:  # 压缩比超过 100:1
                        errors.append(f"{member}: 压缩比异常 ({ratio:.1f}:1)")
                        continue

            # 4. 如果有错误，抛出异常
            if errors:
                raise ProjectError(
                    ErrorCode.PROJECT_SECURITY_VIOLATION,
                    f"发现 {len(errors)} 个安全问题:\n" +
                    "\n".join(f"  - {err}" for err in errors)
                )

            # 5. 安全解压
            logger.info(f"安全检查通过，开始解压 {file_count} 个文件")
            for info in zip_ref.infolist():
                member = info.filename

                # 跳过目录
                if info.is_dir():
                    continue

                # 构造目标路径
                target_path = (extract_to / member).resolve()

                # 再次验证路径（双重保险）
                # Python 3.8 兼容：使用 relative_to() 替代 is_relative_to()
                try:
                    target_path.relative_to(extract_to)
                except ValueError:
                    raise ProjectError(
                        ErrorCode.PROJECT_SECURITY_VIOLATION,
                        f"路径遍历攻击检测: {member}"
                    )

                # 确保目标目录存在
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # 解压文件
                with zip_ref.open(member) as source:
                    with open(target_path, 'wb') as target:
                        # 分块读取，避免内存溢出
                        while True:
                            chunk = source.read(8192)
                            if not chunk:
                                break
                            target.write(chunk)

                # 恢复 Unix 文件权限（如果有）
                unix_mode = info.external_attr >> 16
                if unix_mode:
                    try:
                        os.chmod(target_path, unix_mode)
                        logger.debug(f"Set permissions {oct(unix_mode)} for {member}")
                    except Exception as e:
                        logger.warning(f"Failed to set permissions for {member}: {e}")

        logger.info("安全解压完成")

    def _is_safe_path(self, member: str, extract_to: Path) -> bool:
        """检查路径是否安全

        Args:
            member: ZIP 文件内的路径
            extract_to: 目标解压目录

        Returns:
            如果路径安全返回 True，否则返回 False
        """
        # 1. 拒绝绝对路径
        if member.startswith('/') or member.startswith('\\'):
            logger.warning(f"拒绝绝对路径: {member}")
            return False

        # 2. 检查危险模式
        dangerous_patterns = ['..', '~', '$']
        for pattern in dangerous_patterns:
            if pattern in member:
                logger.warning(f"路径包含危险字符 '{pattern}': {member}")
                return False

        # 3. 检查路径组件
        parts = Path(member).parts
        for part in parts:
            if part in ['.', '..'] or part.startswith('~'):
                logger.warning(f"路径包含危险组件 '{part}': {member}")
                return False

        # 4. 验证解压后的路径
        try:
            target_path = (extract_to / member).resolve()
            # Python 3.8 兼容：使用 relative_to() 验证路径
            target_path.relative_to(extract_to)
        except ValueError:
            logger.warning(f"路径遍历检测: {member}")
            return False

        return True
    
    def _detect_project_type(self, project_path: Path) -> str:
        """识别项目类型
        
        Args:
            project_path: 项目路径
            
        Returns:
            'python'
            
        Raises:
            ValueError: 无法识别项目类型
        """
        # 递归查找所有文件
        all_files = list(project_path.rglob('*'))
        
        # 检查是否有Python文件
        has_python = any(f.suffix == '.py' for f in all_files if f.is_file())
        
        if has_python:
            logger.info("Python files found")
            return 'python'
        else:
            raise ProjectError(
                ErrorCode.PROJECT_INVALID_FORMAT,
                "无法识别项目类型: 未找到 Python 文件。仅支持 Python 项目。"
            )
    
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

