"""WebSocket协议定义和验证"""
from __future__ import annotations
from typing import Dict, Any, Optional, Tuple
import json
import logging

logger = logging.getLogger(__name__)


class ProtocolError(Exception):
    """协议错误"""
    pass


def validate_command(data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """验证并解析客户端指令
    
    Args:
        data: 客户端发送的消息字典
        
    Returns:
        (command_type, parsed_data) 元组
        
    Raises:
        ProtocolError: 协议格式错误
    """
    if not isinstance(data, dict):
        raise ProtocolError("Message must be a JSON object")
    
    if 'command' not in data:
        raise ProtocolError("Missing 'command' field")
    
    command = data['command']
    
    if command == 'update':
        return validate_update_command(data)
    elif command == 'start':
        return validate_start_command(data)
    elif command == 'process':
        return validate_process_command(data)
    else:
        raise ProtocolError(f"Unknown command: {command}")


def validate_update_command(data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """验证UPDATE指令
    
    格式:
    {
        "command": "update",
        "data": "base64_encoded_zip_data"
    }
    """
    if 'data' not in data:
        raise ProtocolError("UPDATE command requires 'data' field")
    
    if not isinstance(data['data'], str):
        raise ProtocolError("'data' field must be a base64 string")
    
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
    if 'params' not in data:
        raise ProtocolError("PROCESS command requires 'params' field")
    
    params = data['params']
    
    if not isinstance(params, dict):
        raise ProtocolError("'params' must be an object")
    
    if 'object' not in params:
        raise ProtocolError("'params' must contain 'object' field")
    
    if 'method' not in params:
        raise ProtocolError("'params' must contain 'method' field")
    
    # args是可选的
    args = params.get('args', {})
    if not isinstance(args, dict):
        raise ProtocolError("'args' must be an object")
    
    return 'process', {
        'object': params['object'],
        'method': params['method'],
        'args': args
    }


def create_success_response(message: str = '', data: Optional[Dict[str, Any]] = None) -> str:
    """创建成功响应"""
    response = {
        'status': 'success',
        'message': message,
        'data': data or {}
    }
    return json.dumps(response)


def create_error_response(message: str, data: Optional[Dict[str, Any]] = None) -> str:
    """创建错误响应"""
    response = {
        'status': 'error',
        'message': message,
        'data': data or {}
    }
    return json.dumps(response)


def create_callback_response(data: Dict[str, Any]) -> str:
    """创建回调响应"""
    response = {
        'status': 'callback',
        'message': '',
        'data': data
    }
    return json.dumps(response)

