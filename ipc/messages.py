"""消息格式定义"""
from typing import Dict, Any, Literal
from dataclasses import dataclass, asdict
import json


@dataclass
class Message:
    """基础消息类"""
    type: str
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        return cls.from_dict(json.loads(json_str))


@dataclass
class CommandMessage(Message):
    """指令消息"""
    pass


@dataclass
class ResponseMessage(Message):
    """响应消息"""
    status: Literal['success', 'error', 'callback'] = 'success'
    message: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['status'] = self.status
        result['message'] = self.message
        return result


@dataclass
class CallbackMessage(Message):
    """回调消息"""
    pass


def create_update_command(zip_data: bytes) -> Dict[str, Any]:
    """创建UPDATE指令消息"""
    import base64
    return {
        'type': 'update',
        'data': {
            'zip_data': base64.b64encode(zip_data).decode('utf-8')
        }
    }


def create_start_command() -> Dict[str, Any]:
    """创建START指令消息"""
    return {
        'type': 'start',
        'data': {}
    }


def create_process_command(obj: str, method: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """创建PROCESS指令消息"""
    return {
        'type': 'process',
        'data': {
            'object': obj,
            'method': method,
            'args': args
        }
    }


def create_response(status: str, message: str = '', data: Dict[str, Any] = None) -> Dict[str, Any]:
    """创建响应消息"""
    return {
        'status': status,
        'message': message,
        'data': data or {}
    }

