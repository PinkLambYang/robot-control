"""单客户端连接管理器"""
from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ConnectionManager:
    """管理 Socket.IO 客户端连接，确保同一时刻只有一个客户端连接"""
    
    def __init__(self):
        self.active_client_sid: Optional[str] = None
    
    def can_connect(self) -> bool:
        """检查是否可以接受新连接
        
        Returns:
            如果可以连接返回True
        """
        return self.active_client_sid is None
    
    def connect_socketio(self, sid: str) -> bool:
        """尝试连接客户端（Socket.IO）
        
        Args:
            sid: Socket.IO 会话ID
            
        Returns:
            True表示连接成功，False表示拒绝连接
        """
        if self.active_client_sid is not None:
            return False
        
        self.active_client_sid = sid
        return True
    
    def disconnect(self):
        """断开当前客户端连接"""
        if self.active_client_sid is not None:
            self.active_client_sid = None
    
    def is_connected(self) -> bool:
        """检查是否有活跃连接"""
        return self.active_client_sid is not None
    
    def get_current_sid(self) -> Optional[str]:
        """获取当前连接的客户端ID"""
        return self.active_client_sid
