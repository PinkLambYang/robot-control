"""ZeroMQ进程间通信管理器"""
from __future__ import annotations
import zmq
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ZMQManager:
    """ZeroMQ通信管理器
    
    使用Unix Domain Socket进行进程间通信：
    - REQ-REP模式：用于指令请求和同步响应
    - PUB-SUB模式：用于异步回调通知
    """
    
    def __init__(self, role: str, command_socket: str, callback_socket: str):
        """初始化ZMQ管理器
        
        Args:
            role: 'server' (WS Server) 或 'worker' (Worker进程)
            command_socket: 命令通信socket地址
            callback_socket: 回调通信socket地址
        """
        self.role = role
        self.context = zmq.Context()
        self.command_socket_addr = command_socket
        self.callback_socket_addr = callback_socket
        
        if role == 'server':
            self._init_server_sockets()
        elif role == 'worker':
            self._init_worker_sockets()
        else:
            raise ValueError(f"Invalid role: {role}")
        
        logger.info(f"ZMQManager initialized (role={role})")
    
    def _init_server_sockets(self):
        """初始化WS Server的socket"""
        # REQ socket用于发送指令
        self.req_socket = self.context.socket(zmq.REQ)
        self.req_socket.connect(self.command_socket_addr)
        logger.debug(f"REQ socket connected to {self.command_socket_addr}")
        
        # SUB socket用于接收回调
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(self.callback_socket_addr)
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        logger.debug(f"SUB socket connected to {self.callback_socket_addr}")
    
    def _init_worker_sockets(self):
        """初始化Worker的socket"""
        # REP socket用于接收指令
        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind(self.command_socket_addr)
        logger.debug(f"REP socket bound to {self.command_socket_addr}")
        
        # PUB socket用于发布回调
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(self.callback_socket_addr)
        logger.debug(f"PUB socket bound to {self.callback_socket_addr}")
    
    def send_command(self, msg: Dict[str, Any], timeout: Optional[int] = None) -> Dict[str, Any]:
        """WS Server发送指令到Worker
        
        Args:
            msg: 指令消息字典
            timeout: 可选的接收超时时间（毫秒），None表示阻塞等待
            
        Returns:
            Worker的响应消息
            
        Raises:
            TimeoutError: 如果设置了timeout且接收超时
        """
        if self.role != 'server':
            raise RuntimeError("Only server can send commands")
        
        logger.debug(f"Sending command: {msg}")
        self.req_socket.send_json(msg)
        
        # 如果指定了超时，使用poll检查
        if timeout is not None:
            if self.req_socket.poll(timeout):
                response = self.req_socket.recv_json()
                logger.debug(f"Received response: {response}")
                return response
            else:
                logger.warning(f"Command timeout after {timeout}ms: {msg.get('type')}")
                raise TimeoutError(f"No response received within {timeout}ms")
        else:
            response = self.req_socket.recv_json()
            logger.debug(f"Received response: {response}")
            return response
    
    def receive_command(self) -> Dict[str, Any]:
        """Worker接收来自WS Server的指令
        
        Returns:
            指令消息字典
        """
        if self.role != 'worker':
            raise RuntimeError("Only worker can receive commands")
        
        msg = self.rep_socket.recv_json()
        logger.debug(f"Received command: {msg}")
        return msg
    
    def send_response(self, msg: Dict[str, Any]):
        """Worker发送响应到WS Server
        
        Args:
            msg: 响应消息字典
        """
        if self.role != 'worker':
            raise RuntimeError("Only worker can send responses")
        
        logger.debug(f"Sending response: {msg}")
        self.rep_socket.send_json(msg)
    
    def send_callback(self, msg: Dict[str, Any]):
        """Worker发送异步回调到WS Server
        
        Args:
            msg: 回调消息字典
        """
        if self.role != 'worker':
            raise RuntimeError("Only worker can send callbacks")
        
        logger.debug(f"Publishing callback: {msg}")
        self.pub_socket.send_json(msg)
    
    def receive_callback(self, timeout: int = 100) -> Optional[Dict[str, Any]]:
        """WS Server接收来自Worker的回调
        
        Args:
            timeout: 超时时间（毫秒）
            
        Returns:
            回调消息字典，如果超时则返回None
        """
        if self.role != 'server':
            raise RuntimeError("Only server can receive callbacks")
        
        if self.sub_socket.poll(timeout):
            msg = self.sub_socket.recv_json()
            logger.debug(f"Received callback: {msg}")
            return msg
        return None
    
    def close(self) -> None:
        """关闭所有socket和context"""
        logger.debug("Closing ZMQ sockets")
        errors = []

        # 尝试关闭所有socket，收集错误但不中断
        try:
            if self.role == 'server':
                if hasattr(self, 'req_socket'):
                    try:
                        self.req_socket.close()
                    except Exception as e:
                        errors.append(f"req_socket: {e}")

                if hasattr(self, 'sub_socket'):
                    try:
                        self.sub_socket.close()
                    except Exception as e:
                        errors.append(f"sub_socket: {e}")
            else:
                if hasattr(self, 'rep_socket'):
                    try:
                        self.rep_socket.close()
                    except Exception as e:
                        errors.append(f"rep_socket: {e}")

                if hasattr(self, 'pub_socket'):
                    try:
                        self.pub_socket.close()
                    except Exception as e:
                        errors.append(f"pub_socket: {e}")
        finally:
            # 无论socket关闭是否成功，都尝试终止context
            try:
                self.context.term()
            except Exception as e:
                errors.append(f"context: {e}")

        # 记录所有错误
        if errors:
            logger.error(f"Errors during ZMQ cleanup: {'; '.join(errors)}")
        else:
            logger.debug("ZMQ sockets closed successfully")

