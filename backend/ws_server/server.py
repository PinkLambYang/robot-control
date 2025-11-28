"""Socket.IO 服务器"""
from __future__ import annotations
import socketio
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx

from .connection_manager import ConnectionManager
from .protocol import (
    validate_command,
    ProtocolError
)
from ipc.zmq_manager import ZMQManager
from utils.error_codes import ErrorCode, create_error_response
from utils.logger import setup_logging
from utils.auth import TokenExtractor
from utils.crypto_js_compat import CryptoJSAES

logger = logging.getLogger(__name__)


class SocketIOServer:
    """Socket.IO 服务器"""
    
    def __init__(self, config: Dict[str, Any], zmq_manager: ZMQManager):
        """初始化 Socket.IO 服务器
        
        Args:
            config: 配置字典
            zmq_manager: ZMQ通信管理器
        """
        # 创建 Socket.IO 服务器
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins='*',  # 允许跨域
            logger=False,
            engineio_logger=False
        )
        
        self.config = config
        self.zmq = zmq_manager
        self.conn_mgr = ConnectionManager()
        self.callback_tasks = {}  # 存储每个客户端的回调监听任务
        
        # 初始化安全模块
        security_config = config.get('websocket', {}).get('security', {})
        
        # Auth Service 远程验证
        self.auth_service_url = security_config.get('auth_service_url', 'http://localhost:3124')
        logger.info("✓ Token Verification: Remote auth_service at %s", self.auth_service_url)
        
        # 消息加密（使用 crypto-js 兼容格式）
        self.encryption_enabled = security_config.get('encryption_enabled', False)
        if self.encryption_enabled:
            crypto_key = security_config.get('encryption_key')
            if not crypto_key:
                raise ValueError("encryption_key is required when encryption_enabled=true")
            self.crypto = CryptoJSAES(crypto_key)
        else:
            self.crypto = None
        
        encryption_status = 'enabled' if self.encryption_enabled else 'disabled'
        logger.info("✓ Message encryption: %s", encryption_status)
        
        # 注册事件处理器
        self.register_handlers()
    
    def register_handlers(self):
        """注册 Socket.IO 事件处理器"""
        
        @self.sio.event
        async def connect(sid, environ, auth=None):
            """客户端连接（需要身份验证）"""
            try:
                # 1. 从请求中提取 token（支持 auth 对象、query string、headers）
                token = TokenExtractor.extract_from_environ(environ, auth)
                
                if not token:
                    logger.warning("⚠ Connection rejected: no token provided")
                    error_msg = f"{ErrorCode.AUTH_TOKEN_MISSING.value}:缺少认证 Token"
                    raise socketio.exceptions.ConnectionRefusedError(error_msg)
                
                # 2. 调用 auth_service 验证 token
                payload = await self._verify_token_remote(token)
                
                if not payload:
                    raise socketio.exceptions.ConnectionRefusedError(f"{ErrorCode.AUTH_TOKEN_INVALID.value}:Token非法或者过期")
                
                user_id = payload.get('user_id', 'anonymous')
                logger.debug(f"Token verified for user: {user_id}")
                
                # 3. 检查是否已有连接
                if not self.conn_mgr.can_connect():
                    logger.warning(f"⚠ Connection rejected: another client connected")
                    error_response = create_error_response(ErrorCode.CONNECTION_REJECTED)
                    raise socketio.exceptions.ConnectionRefusedError(f"{error_response['error_code']}:{error_response['message']}")
                
                # 4. 接受连接
                self.conn_mgr.connect_socketio(sid, user_id, payload)
                logger.info(f"✓ Client connected: {sid} (user: {user_id})")

                # 5. 启动回调监听任务
                self.callback_tasks[sid] = asyncio.create_task(
                    self._listen_callbacks(sid)
                )
                
                # 6. 发送连接成功消息
                return True
            
            except socketio.exceptions.ConnectionRefusedError:
                raise
            except Exception as e:
                logger.error(f"Connection error: {e}", exc_info=True)
                raise socketio.exceptions.ConnectionRefusedError("Internal server error")
        
        @self.sio.event
        async def disconnect(sid):
            """客户端断开"""
            logger.info(f"✗ Client disconnected: {sid}")
            
            # 取消回调监听任务
            if sid in self.callback_tasks:
                self.callback_tasks[sid].cancel()
                try:
                    await self.callback_tasks[sid]
                except asyncio.CancelledError:
                    pass
                del self.callback_tasks[sid]
            
            # 只有断开的客户端是当前活跃客户端时，才清除连接状态并通知 Worker
            if self.conn_mgr.get_current_sid() == sid:
                self.conn_mgr.disconnect()
                
                # 通知 Worker 停止用户线程（不清理缓存）
                try:
                    logger.debug(f"Notifying worker about disconnect [{sid}]")
                    disconnect_msg = {
                        'type': 'client_disconnected',
                        'data': {'sid': sid}
                    }
                    # 在后台线程中发送（避免阻塞异步事件循环）
                    await asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: self.zmq.send_command(disconnect_msg, timeout=1000)
                    )
                    logger.debug("Worker notified successfully")
                except Exception as e:
                    logger.warning(f"Failed to notify worker about disconnect: {e}")
        
        @self.sio.event
        async def update(sid, data):
            """UPDATE 指令"""
            logger.info(f"→ UPDATE [{sid}]")
            response = await self._handle_command(sid, 'update', data)
            return self._wrap_response(response)
        
        @self.sio.event
        async def start(sid, data=None):
            """START 指令"""
            logger.info(f"→ START [{sid}]")
            response = await self._handle_command(sid, 'start', data or {})
            return self._wrap_response(response)
        
        @self.sio.event
        async def process(sid, data):
            """PROCESS 指令"""
            logger.info(f"→ PROCESS [{sid}]")
            response = await self._handle_command(sid, 'process', data)
            return self._wrap_response(response)
        
    
    async def _verify_token_remote(self, token: str) -> Optional[Dict[str, Any]]:
        """调用 auth_service 远程验证 token
        
        Args:
            token: JWT token
            
        Returns:
            验证成功返回负载数据，失败返回 None
        """
        try:
            # 禁用代理，避免 SOCKS 代理相关错误
            async with httpx.AsyncClient(proxy=None, trust_env=False) as client:
                # 构造请求头
                headers = {'Authorization': f'Bearer {token}'}
                
                # 调用 auth_service 的验证端点
                response = await client.post(
                    f'{self.auth_service_url}/auth/verify',
                    headers=headers,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    error_detail = response.text if hasattr(response, 'text') else 'Unknown error'
                    logger.warning(f"Token verification failed with status {response.status_code}: {error_detail}")
                    return None
        except Exception as e:
            logger.error(f"Remote token verification error: {e}", exc_info=True)
            return None
    
    def _decrypt_data(self, data) -> Dict[str, Any]:
        """解密数据（如果是加密字符串）
        
        Args:
            data: 可能是加密字符串或原始字典
            
        Returns:
            解密后的数据字典
        """
        # 如果是字符串，说明是加密数据
        if isinstance(data, str):
            if not self.crypto:
                logger.error("Received encrypted data but crypto not available")
                return {}
            
            logger.debug(f"Decrypting base64 string (length: {len(data)})")
            success, decrypted_data, error = self.crypto.decrypt(data)
            
            if success:
                logger.debug("Data decrypted successfully")
                return decrypted_data
            else:
                logger.error(f"Failed to decrypt data: {error}")
                return {}
        
        # 如果是字典，直接返回
        elif isinstance(data, dict):
            logger.debug("Data is unencrypted dict")
            return data
        
        # 其他类型（空数据等）
        else:
            logger.debug(f"Data is type: {type(data)}")
            return {}
    
    def _wrap_response(self, response: Dict[str, Any]):
        """包装响应（加密或明文）
        
        Args:
            response: 响应数据
            
        Returns:
            - 加密模式：返回 base64 字符串
            - 明文模式：返回原始对象
        """
        if not self.encryption_enabled or not self.crypto:
            logger.debug("Sending unencrypted response")
            return response  # 直接返回原始对象
        
        logger.debug("Encrypting response...")
        success, encrypted, error = self.crypto.encrypt(response)
        
        if not success:
            logger.error(f"Failed to encrypt response: {error}, sending unencrypted")
            return response
        
        logger.debug(f"Response encrypted: {len(encrypted)} chars")
        return encrypted  # 返回 base64 字符串
    
    async def _handle_command(self, sid: str, command: str, data) -> Dict[str, Any]:
        """处理客户端指令
        
        Args:
            sid: 客户端会话ID
            command: 指令类型 ('update', 'start', 'process')
            data: 指令数据（可能是加密字符串或原始字典）
            
        Returns:
            响应字典
        """
        try:
            # 1. 解密数据（如果需要）
            decrypted_data = self._decrypt_data(data)
            
            # 2. 添加 command 字段
            full_data = {
                'command': command,
                **decrypted_data
            }
            
            # 3. 验证指令
            command_type, parsed_data = validate_command(full_data)
            
            # 构造发送给Worker的消息
            worker_msg = {
                'type': command_type,
                'data': parsed_data
            }
            
            # 发送到Worker并等待响应
            response = self.zmq.send_command(worker_msg)
            
            # 返回响应（Worker 已经返回标准格式）
            return response
        
        except ProtocolError as e:
            logger.error("Protocol error: %s", str(e))
            return create_error_response(e.error_code, e.message)
        except Exception as e:
            logger.error("Error handling command: %s", str(e), exc_info=True)
            return create_error_response(
                ErrorCode.INTERNAL_ERROR,
                '操作失败，请稍后重试'
            )
    
    async def _listen_callbacks(self, sid: str):
        """监听Worker的异步回调
        
        Args:
            sid: 客户端会话ID
        """
        try:
            while True:
                # 检查回调（非阻塞，100ms超时）
                callback = await asyncio.get_event_loop().run_in_executor(
                    None, self.zmq.receive_callback, 100
                )
                
                if callback:
                    # 根据回调类型发送不同的事件
                    callback_type = callback.get('type', 'callback')
                    
                    if callback_type == 'push':
                        # 主动推送消息：使用自定义事件名
                        event_name = callback.get('event', 'message')
                        data = callback.get('data', {})
                        await self.sio.emit(event_name, data, room=sid)
                    else:
                        # 普通回调：使用 'callback' 事件
                        await self.sio.emit('callback', callback, room=sid)
                
                # 短暂休眠，避免CPU占用过高
                await asyncio.sleep(0.01)
        
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error in callback listener: {e}", exc_info=True)
    
    def get_asgi_app(self):
        """获取 ASGI 应用"""
        # 创建 FastAPI 应用
        app = FastAPI(title="Robot Control System - Socket.IO")
        
        @app.get("/")
        async def root():
            return JSONResponse({
                "service": "Robot Control System",
                "protocol": "Socket.IO",
                "status": "running"
            })
        
        # 挂载 Socket.IO
        socket_app = socketio.ASGIApp(
            self.sio,
            other_asgi_app=app
        )
        
        return socket_app
    
    def run(self):
        """运行服务器"""
        import uvicorn
        
        host = self.config['websocket']['host']
        port = self.config['websocket']['port']
        
        logger.info(f"✓ Socket.IO server listening on {host}:{port}")
        
        # 获取ASGI应用
        app = self.get_asgi_app()
        
        # 运行服务器
        uvicorn.run(app, host=host, port=port, log_level="info")


def start_ws_server(config_path: str = 'config.yaml'):
    """启动 Socket.IO 服务器进程"""
    import yaml
    
    # 在子进程中重新配置日志
    setup_logging(
        name="ws_server",
        console_level="INFO",
        file_level="INFO"
    )
    
    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # 创建ZMQ管理器
    zmq_manager = ZMQManager(
        role='server',
        command_socket=config['ipc']['command_socket'],
        callback_socket=config['ipc']['callback_socket']
    )
    
    # 创建并运行服务器
    server = SocketIOServer(config, zmq_manager)
    server.run()
