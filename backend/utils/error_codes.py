"""统一错误码定义

错误码格式: 模块代码(2位) + 序号(3位)
- 00xxx: 连接层错误 (WebSocket 连接阶段)
- 01xxx: 协议层错误 (命令验证)
- 02xxx: 项目管理错误 (上传/加载/启动)
- 03xxx: 执行层错误 (方法调用/模块加载)
- 99xxx: 系统级错误

设计原则:
1. 用户可自定义项目,不对业务逻辑(如DDS)定义具体错误码
2. 仅定义框架层面的通用错误
3. 区分连接阶段(00xxx)和命令执行阶段(01-03xxx)
"""
from __future__ import annotations
from typing import Dict, Any, Optional
from enum import Enum


class ErrorCode(str, Enum):
    """错误码枚举 - 格式: 模块(2位) + 序号(3位)"""

    # === 00xxx: 连接层错误 (Socket.IO 连接阶段) ===
    CONNECTION_REJECTED = "00001"              # 连接被拒绝(已有其他客户端)
    CONNECTION_LIMIT_REACHED = "00002"         # 达到连接数限制
    
    # 认证相关错误
    AUTH_TOKEN_MISSING = "00010"               # 缺少认证 Token
    AUTH_TOKEN_INVALID = "00011"               # Token 无效或格式错误
    AUTH_TOKEN_EXPIRED = "00012"               # Token 已过期

    # === 01xxx: 协议层错误 ===
    PROTOCOL_INVALID_FORMAT = "01001"          # 请求格式无效
    PROTOCOL_MISSING_FIELD = "01002"           # 缺少必需字段
    PROTOCOL_UNKNOWN_COMMAND = "01003"         # 未知命令类型
    PROTOCOL_INVALID_PARAMS = "01004"          # 参数格式错误

    # === 02xxx: 项目管理错误 ===
    PROJECT_UPLOAD_FAILED = "02001"            # 项目上传失败
    PROJECT_INVALID_FORMAT = "02002"           # 项目格式无效
    PROJECT_LOAD_FAILED = "02003"              # 项目加载失败
    PROJECT_NOT_FOUND = "02004"                # 项目未加载
    PROJECT_SECURITY_VIOLATION = "02005"       # 安全违规(路径遍历等)

    # === 03xxx: 执行层错误 ===
    EXECUTION_FAILED = "03001"                 # 执行失败(通用)
    METHOD_NOT_FOUND = "03002"                 # 方法不存在
    OBJECT_NOT_FOUND = "03003"                 # 对象不存在
    MODULE_LOAD_ERROR = "03004"                # 模块加载错误

    # === 99xxx: 系统级错误 ===
    INTERNAL_ERROR = "99001"                   # 内部错误
    UNKNOWN_ERROR = "99999"                    # 未知错误


# 错误码到用户友好消息的映射
ERROR_MESSAGES: Dict[str, str] = {
    # 00xxx: 连接层
    ErrorCode.CONNECTION_REJECTED: "连接被拒绝,已有其他客户端连接",
    ErrorCode.CONNECTION_LIMIT_REACHED: "达到最大连接数限制",
    ErrorCode.AUTH_TOKEN_MISSING: "缺少认证 Token",
    ErrorCode.AUTH_TOKEN_INVALID: "Token 无效",
    ErrorCode.AUTH_TOKEN_EXPIRED: "Token 已过期",

    # 01xxx: 协议层
    ErrorCode.PROTOCOL_INVALID_FORMAT: "请求格式错误",
    ErrorCode.PROTOCOL_MISSING_FIELD: "缺少必需字段",
    ErrorCode.PROTOCOL_UNKNOWN_COMMAND: "未知命令",
    ErrorCode.PROTOCOL_INVALID_PARAMS: "参数格式错误",

    # 02xxx: 项目管理
    ErrorCode.PROJECT_UPLOAD_FAILED: "项目上传失败",
    ErrorCode.PROJECT_INVALID_FORMAT: "项目格式无效",
    ErrorCode.PROJECT_LOAD_FAILED: "项目加载失败",
    ErrorCode.PROJECT_NOT_FOUND: "项目未加载",
    ErrorCode.PROJECT_SECURITY_VIOLATION: "检测到不安全的操作",

    # 03xxx: 执行层
    ErrorCode.EXECUTION_FAILED: "执行失败",
    ErrorCode.METHOD_NOT_FOUND: "方法不存在",
    ErrorCode.OBJECT_NOT_FOUND: "对象不存在",
    ErrorCode.MODULE_LOAD_ERROR: "模块加载失败",

    # 99xxx: 系统级
    ErrorCode.INTERNAL_ERROR: "系统内部错误",
    ErrorCode.UNKNOWN_ERROR: "未知错误",
}


def create_error_response(
    error_code: ErrorCode,
    custom_message: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """创建标准错误响应

    Args:
        error_code: 错误码枚举
        custom_message: 自定义消息(可选,覆盖默认消息)
        data: 附加数据(可选)

    Returns:
        标准错误响应字典

    Example:
        >>> create_error_response(ErrorCode.DDS_START_FAILED)
        {'status': 'error', 'error_code': 'E0401', 'message': 'DDS Client 启动失败', 'data': {}}
    """
    return {
        'status': 'error',
        'error_code': error_code.value,
        'message': custom_message or ERROR_MESSAGES.get(error_code, '未知错误'),
        'data': data or {}
    }


def create_success_response(
    message: str = '',
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """创建标准成功响应

    Args:
        message: 成功消息
        data: 响应数据

    Returns:
        标准成功响应字典
    """
    return {
        'status': 'success',
        'message': message,
        'data': data or {}
    }
