"""单客户端连接管理器"""
from __future__ import annotations
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ClientSession:
    """客户端会话信息"""
    
    def __init__(self, sid: str, user_id: str = "anonymous", auth_data: Optional[Dict[str, Any]] = None):
        """初始化客户端会话
        
        Args:
            sid: Socket.IO 会话ID
            user_id: 用户ID（可选，仅用于日志）
            auth_data: 认证数据（来自JWT payload）
        """
        self.sid = sid
        self.user_id = user_id or "anonymous"
        self.auth_data = auth_data or {}
    
    def __repr__(self):
        return f"ClientSession(sid={self.sid}, user_id={self.user_id})"


class ConnectionManager:
    """管理 Socket.IO 客户端连接，确保同一时刻只有一个客户端连接"""
    
    def __init__(self):
        self.active_client: Optional[ClientSession] = None
    
    def can_connect(self) -> bool:
        """检查是否可以接受新连接
        
        Returns:
            如果可以连接返回True
        """
        return self.active_client is None
    
    def connect_socketio(self, sid: str, user_id: str = "anonymous", auth_data: Optional[Dict[str, Any]] = None) -> bool:
        """尝试连接客户端（Socket.IO）
        
        Args:
            sid: Socket.IO 会话ID
            user_id: 用户ID（可选，仅用于日志）
            auth_data: 认证数据
            
        Returns:
            True表示连接成功，False表示拒绝连接
        """
        if self.active_client is not None:
            return False
        
        self.active_client = ClientSession(sid, user_id, auth_data)
        logger.info(f"✓ Client connected: {self.active_client}")
        return True
    
    def disconnect(self):
        """断开当前客户端连接"""
        if self.active_client is not None:
            logger.info(f"✗ Client disconnected: {self.active_client}")
            self.active_client = None
    
    def is_connected(self) -> bool:
        """检查是否有活跃连接"""
        return self.active_client is not None
    
    def get_current_sid(self) -> Optional[str]:
        """获取当前连接的客户端ID"""
        return self.active_client.sid if self.active_client else None
    
    def get_current_user_id(self) -> Optional[str]:
        """获取当前连接的用户ID"""
        return self.active_client.user_id if self.active_client else None
    
    def get_current_session(self) -> Optional[ClientSession]:
        """获取当前会话对象"""
        return self.active_client
    
    def verify_connection(self, sid: str, user_id: str) -> bool:
        """验证连接是否有效
        
        Args:
            sid: Socket.IO 会话ID
            user_id: 用户ID
            
        Returns:
            是否为当前有效连接
        """
        return (self.active_client is not None and 
                self.active_client.sid == sid and 
                self.active_client.user_id == user_id)
