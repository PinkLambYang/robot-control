"""Socket.IO 服务器"""
from __future__ import annotations
import socketio
import asyncio
import logging
from typing import Dict, Any
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .connection_manager import ConnectionManager
from .protocol import (
    validate_command,
    create_success_response,
    create_error_response,
    create_callback_response,
    ProtocolError
)
from ipc.zmq_manager import ZMQManager

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
        
        # 注册事件处理器
        self.register_handlers()
    
    def register_handlers(self):
        """注册 Socket.IO 事件处理器"""
        
        @self.sio.event
        async def connect(sid, environ):
            """客户端连接"""
            # 检查是否已有连接
            if not self.conn_mgr.can_connect():
                logger.warning(f"⚠ Connection rejected (another client connected)")
                await self.sio.emit('error', {
                    'message': 'Another client is already connected'
                }, room=sid)
                return False
            
            # 接受连接
            self.conn_mgr.connect_socketio(sid)
            logger.info(f"✓ Client connected: {sid}")
            
            # 启动回调监听任务
            self.callback_tasks[sid] = asyncio.create_task(
                self._listen_callbacks(sid)
            )
            
            # 发送连接成功消息
            await self.sio.emit('connected', {'message': 'Connected successfully'}, room=sid)
            
            return True
        
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
            
            # 只有断开的客户端是当前活跃客户端时，才清除连接状态
            if self.conn_mgr.get_current_sid() == sid:
                self.conn_mgr.disconnect()
        
        @self.sio.event
        async def update(sid, data):
            """UPDATE 指令"""
            logger.info(f"→ UPDATE [{sid}]")
            response = await self._handle_command(sid, {
                'command': 'update',
                **data
            })
            return response
        
        @self.sio.event
        async def start(sid, data=None):
            """START 指令"""
            logger.info(f"→ START [{sid}]")
            response = await self._handle_command(sid, {
                'command': 'start'
            })
            return response
        
        @self.sio.event
        async def process(sid, data):
            """PROCESS 指令"""
            response = await self._handle_command(sid, {
                'command': 'process',
                **data
            })
            return response
    
    async def _handle_command(self, sid: str, data: Dict[str, Any]) -> Dict:
        """处理客户端指令
        
        Args:
            sid: 客户端会话ID
            data: 指令数据
            
        Returns:
            响应字典
        """
        try:
            # 验证指令
            command_type, parsed_data = validate_command(data)
            
            # 构造发送给Worker的消息
            worker_msg = {
                'type': command_type,
                'data': parsed_data
            }
            
            # 发送到Worker并等待响应
            response = self.zmq.send_command(worker_msg)
            
            # 返回响应
            if response.get('status') == 'success':
                return {
                    'status': 'success',
                    'message': response.get('message', ''),
                    'data': response.get('data', {})
                }
            else:
                return {
                    'status': 'error',
                    'message': response.get('message', 'Unknown error'),
                    'data': response.get('data', {})
                }
        
        except ProtocolError as e:
            logger.error(f"Protocol error: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
        except Exception as e:
            logger.error(f"Error handling command: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f"Internal error: {str(e)}"
            }
    
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
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
