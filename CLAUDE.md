# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

## 语言规则

**重要：在此仓库中与用户交流时，始终使用中文回复。**

## 项目概述

一个具有双进程 Python 后端和 React Web 前端的远程机器人控制系统。系统通过 Socket.IO 实现 Web 客户端与机器人控制器之间的实时双向通信，内部进程间通信使用 ZeroMQ。

## 架构

### 多进程设计

后端采用三层架构：

1. **主进程** ([main.py](backend/main.py))
   - 启动并监控 Socket.IO Server 和 Worker 进程
   - 处理 UPDATE 命令时的 Worker 自动重启
   - 管理优雅关闭

2. **Socket.IO 服务器进程** ([ws_server/](backend/ws_server/))
   - FastAPI + Python-SocketIO + Uvicorn 服务器
   - 处理客户端连接（强制单客户端限制）
   - 通过协议层验证命令
   - 监听来自 Worker 的异步回调（通过 ZMQ PUB-SUB）

3. **Worker 进程** ([worker/](backend/worker/))
   - 通过 ZMQ REQ-REP 接收命令
   - 管理 Python 项目生命周期（解压、加载、执行）
   - 启动时自动加载默认项目
   - UPDATE 后重启以清除 Python 模块缓存

### IPC 通信

使用 ZeroMQ 和 Unix Domain Socket：
- **命令通道**（REQ-REP）：同步命令/响应
- **回调通道**（PUB-SUB）：异步推送通知
- Socket 路径在 [config.yaml](backend/config.yaml) 中配置

### 前端

React 18 + Vite 5 + Socket.IO 客户端：
- [useSocketIO.js](frontend/src/hooks/useSocketIO.js)：核心 Socket.IO Hook，支持自动重连
- 组件：ConnectionPanel、UploadPanel、CommandPanel、LogPanel

## 开发命令

### 后端

```bash
# 安装依赖（使用阿里云镜像加速）
cd backend
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 运行服务器（同时启动 Socket.IO 服务器和 Worker）
python main.py
# 服务器运行在 http://0.0.0.0:8000

# 运行测试
python tests/test_client.py          # Socket.IO 客户端测试
python tests/create_test_project.py  # 生成测试项目 ZIP
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 开发服务器（http://localhost:3000）
npm run dev

# 生产构建
npm run build

# 预览生产构建
npm run preview
```

## 核心概念

### 默认项目行为

- 系统内置默认机器人控制器，位于 `backend/storage/projects/default/`
- 启动时，Worker 自动加载默认项目（如果 `current/` 为空则复制过去）
- 客户端可以直接执行 PROCESS 命令，无需 UPDATE/START
- UPDATE 命令会覆盖 `current/` 目录，但不影响 `default/`

### Python 项目结构

用户项目必须遵循此约定：

```
my_robot_project/
├── main.py              # 必需：必须导出全局实例
└── requirements.txt     # 可选
```

`main.py` 示例：
```python
class RobotController:
    def prepare_mode(self):
        return {"status": "success", "message": "Ready"}

# 全局实例（必需）
robot_controller = RobotController()
```

### 异步操作

对于长时间运行的操作（5 秒以上），使用线程配合 `push_message`：

```python
import threading

# push_message 由系统注入
def start_long_task(self):
    threading.Thread(target=self._worker, daemon=True).start()
    return {"status": "success", "message": "Task started"}

def _worker(self):
    # 执行工作...
    if push_message:
        push_message('task_completed', {"result": "done"})
```

客户端监听：
```javascript
socket.on('task_completed', (data) => {
  console.log('结果:', data.result)
})
```

### Socket.IO 协议

**事件（客户端 → 服务器）：**
- `update`：上传 Python 项目（base64 编码的 ZIP）
- `start`：加载项目（可选，首次 PROCESS 时自动加载）
- `process`：执行方法，参数格式：`{params: {object, method, args}}`

**事件（服务器 → 客户端）：**
- 同步：通过 emit 回调返回响应
- 异步：从后端推送的自定义事件（例如 `recognition_result`）

## 配置

编辑 [backend/config.yaml](backend/config.yaml)：
- `websocket.port`：Socket.IO 服务器端口（默认：8000）
- `worker.max_execution_time`：超时时间（秒，默认：300）
- `ipc.*_socket`：ZMQ socket 路径

前端服务器端口：编辑 [frontend/vite.config.js](frontend/vite.config.js)

## 重要实现细节

### Worker 重启机制

- UPDATE 时 Worker 以退出码 0 退出（触发主进程自动重启）
- 重启是必要的，因为 Python 无法完全卸载已导入的模块
- 重启期间会有短暂的服务中断（约 1-2 秒）

### 单客户端强制限制

[ws_server/connection_manager.py](backend/ws_server/connection_manager.py) 中的 ConnectionManager 确保同一时间只有一个客户端连接，以防止命令冲突。

### 日志

- 应用日志：`backend/storage/logs/`
- 配置位置：[utils/logger.py](backend/utils/logger.py)
- 控制台级别：INFO，文件级别：INFO（可配置）

## 常见任务

### 添加新的 Socket.IO 事件

1. 在 [ws_server/server.py](backend/ws_server/server.py) 的 `register_handlers()` 中添加事件处理器
2. 如需要，在 [ws_server/protocol.py](backend/ws_server/protocol.py) 中添加协议验证
3. 在 [worker/worker.py](backend/worker/worker.py) 中更新 Worker 命令处理

### 修改默认项目

编辑 [backend/storage/projects/default/main.py](backend/storage/projects/default/main.py) 并重启后端。

### 调试

设置环境变量以启用详细日志：
```bash
export LOG_LEVEL=DEBUG
python backend/main.py
```

## 安全注意事项

当前实现仅用于开发/内部使用：
- 未实现身份验证
- CORS 允许所有来源（`cors_allowed_origins='*'`）
- 生产环境需要：添加身份验证、限制 CORS、实现速率限制
