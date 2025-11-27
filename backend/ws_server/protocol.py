"""WebSocket协议定义和验证"""
from __future__ import annotations
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class ProtocolError(Exception):
    """协议错误

    Attributes:
        error_code: 错误码(来自 ErrorCode 枚举)
        message: 错误消息
    """
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(message)


def validate_command(data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """验证并解析客户端指令

    Args:
        data: 客户端发送的消息字典

    Returns:
        (command_type, parsed_data) 元组

    Raises:
        ProtocolError: 协议格式错误
    """
    from utils.error_codes import ErrorCode

    if not isinstance(data, dict):
        raise ProtocolError(ErrorCode.PROTOCOL_INVALID_FORMAT, "Message must be a JSON object")

    if 'command' not in data:
        raise ProtocolError(ErrorCode.PROTOCOL_MISSING_FIELD, "Missing 'command' field")

    command = data['command']

    if command == 'update':
        return validate_update_command(data)
    elif command == 'start':
        return validate_start_command(data)
    elif command == 'process':
        return validate_process_command(data)
    else:
        raise ProtocolError(ErrorCode.PROTOCOL_UNKNOWN_COMMAND, f"Unknown command: {command}")


def validate_update_command(data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """验证UPDATE指令

    格式:
    {
        "command": "update",
        "data": "base64_encoded_zip_data"
    }
    """
    from utils.error_codes import ErrorCode

    if 'data' not in data:
        raise ProtocolError(ErrorCode.PROTOCOL_INVALID_PARAMS, "UPDATE command requires 'data' field")

    if not isinstance(data['data'], str):
        raise ProtocolError(ErrorCode.PROTOCOL_INVALID_PARAMS, "'data' field must be a base64 string")

    return 'update', {'zip_data': data['data']}


def validate_start_command(data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """验证START指令

    格式:
    {
        "command": "start"
    }
    """
    return 'start', {}


def validate_process_command(data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """验证PROCESS指令

    格式:
    {
        "command": "process",
        "params": {
            "object": "sport_client",
            "method": "StandUp",
            "args": {...}
        }
    }
    """
    from utils.error_codes import ErrorCode

    if 'params' not in data:
        raise ProtocolError(ErrorCode.PROTOCOL_INVALID_PARAMS, "PROCESS command requires 'params' field")

    params = data['params']

    if not isinstance(params, dict):
        raise ProtocolError(ErrorCode.PROTOCOL_INVALID_PARAMS, "'params' must be an object")

    if 'object' not in params:
        raise ProtocolError(ErrorCode.PROTOCOL_INVALID_PARAMS, "'params' must contain 'object' field")

    if 'method' not in params:
        raise ProtocolError(ErrorCode.PROTOCOL_INVALID_PARAMS, "'params' must contain 'method' field")

    # args是可选的
    args = params.get('args', {})
    if not isinstance(args, dict):
        raise ProtocolError(ErrorCode.PROTOCOL_INVALID_PARAMS, "'args' must be an object")

    return 'process', {
        'object': params['object'],
        'method': params['method'],
        'args': args
    }


