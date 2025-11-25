"""日志配置模块"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


# 日志级别定义
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,      # 详细的调试信息
    'INFO': logging.INFO,        # 一般信息
    'WARNING': logging.WARNING,  # 警告信息
    'ERROR': logging.ERROR,      # 错误信息
    'CRITICAL': logging.CRITICAL # 严重错误
}

# 日志格式
CONSOLE_FORMAT = '%(levelname)-8s %(name)-15s %(message)s'
FILE_FORMAT = '%(asctime)s - %(name)-15s - %(levelname)-8s - %(filename)s:%(lineno)d - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logging(
    name: str = "robot_control",
    log_dir: str = "./storage/logs",
    console_level: str = "INFO",
    file_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 3
):
    """配置日志系统
    
    Args:
        name: 日志记录器名称
        log_dir: 日志文件目录
        console_level: 控制台日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        file_level: 文件日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份日志文件数量
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 获取根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # 设置为最低级别，让各个handler自己控制
    
    # 清除已有的handlers，避免重复
    logger.handlers.clear()
    
    # 控制台处理器 - 简洁格式
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVELS.get(console_level.upper(), logging.INFO))
    console_formatter = logging.Formatter(CONSOLE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器 - 详细格式（INFO及以上）
    today = datetime.now().strftime('%Y-%m-%d')
    info_log_file = log_path / f'robot_control_{today}.log'
    file_handler = RotatingFileHandler(
        info_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(LOG_LEVELS.get(file_level.upper(), logging.INFO))
    file_formatter = logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # 错误日志单独记录
    error_log_file = log_path / f'error_{today}.log'
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    # 记录初始化信息
    logging.info(f"Logging initialized: console={console_level}, file={file_level}")


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器
    
    Args:
        name: 日志记录器名称（通常是模块名 __name__）
        
    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)

