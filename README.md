# 机器人远程控制系统

基于 Socket.IO 的远程控制系统，支持动态部署Python/C++项目，实现单客户端连接管理、动态代码加载、函数调用和异步回调机制。

## 系统架构

- **双进程架构**：Socket.IO 进程 + Worker 进程
- **Socket.IO 通信**：支持自动重连、心跳检测的实时通信
- **IPC通信**：使用ZeroMQ的Unix Domain Socket
- **单客户端限制**：同一时刻只允许一个客户端连接
- **动态加载**：Python项目动态导入模块，C++项目启动可执行文件

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

### 启动后端服务

```bash
python main.py
```

服务将在 `http://0.0.0.0:8000` 启动 Socket.IO 服务。

### 启动 Web 客户端

```bash
cd robot-control-web
npm install  # 首次运行（安装依赖，包括 socket.io-client）
npm run dev
```

访问：**http://localhost:3000**

## 客户端协议 (Socket.IO 事件)

### UPDATE 事件
```javascript
socket.emit('update', {
  data: "base64_encoded_zip_data"
}, (response) => {
  console.log(response) // {status: 'success', message: '...'}
})
```

### START 事件
```javascript
socket.emit('start', {}, (response) => {
  console.log(response)
})
```

### PROCESS 事件
```javascript
socket.emit('process', {
  params: {
    object: "sport_client",
    method: "StandUp",
    args: {}
  }
}, (response) => {
  console.log(response)
})
```

### CALLBACK 事件（服务器推送）
```javascript
socket.on('callback', (data) => {
  console.log('收到回调:', data)
})
```

## 项目类型支持

### Python 项目 ✅
- **动态加载**: 使用 `importlib` 动态加载 Python 模块
- **函数调用**: 支持 `PROCESS` 指令调用对象方法
- **示例**: `sport_client.StandUp()`
- **要求**: 包含 `main.py` 或 `__init__.py`

### C++ 项目 ✅ (已验证)
- **进程启动**: 启动预编译的可执行文件为子进程
- **命令支持**: 支持 `UPDATE` 和 `START` 指令（不支持 `PROCESS`）
- **要求**: 
  - 提供预编译的二进制可执行文件
  - 文件需要有可执行权限（`chmod +x`）
  - zip 文件会自动保留和恢复文件权限
- **验证报告**: 参见 `docs/CPP_EXECUTOR_TEST_REPORT.md`

## 文档

- 📖 [快速启动指南](docs/QUICKSTART.md) - 快速开始使用系统
- 🏗️ [架构设计文档](docs/ARCHITECTURE.md) - 详细的系统架构说明
- ⚛️ [React 客户端文档](robot-control-web/README.md) - Web 客户端使用指南
- 🔌 [Socket.IO 快速指南](docs/SOCKETIO_QUICKSTART.md) - Socket.IO 使用和示例

## 项目结构

```
robot-control-system/
├── main.py                     # 启动入口（Socket.IO）
├── config.yaml                 # 系统配置
├── requirements.txt            # Python依赖
├── robot-control-web/          # React Web 客户端 ⭐
│   ├── src/
│   │   ├── hooks/
│   │   │   └── useSocketIO.js # Socket.IO Hook
│   │   ├── components/        # React 组件
│   │   └── App.jsx           # 主应用
│   ├── package.json           # Node 依赖 (含 socket.io-client)
│   └── README.md              # 客户端文档
├── docs/                       # 文档目录
│   ├── QUICKSTART.md          # 快速启动指南
│   ├── ARCHITECTURE.md        # 架构设计文档
│   └── TEST_REPORT.md         # 测试报告
├── ws_server/                  # Socket.IO 服务进程
│   ├── server.py              # Socket.IO 服务器
│   ├── connection_manager.py  # 连接管理
│   └── protocol.py            # 协议定义
├── worker/                     # Worker执行进程
├── ipc/                        # 进程间通信
├── tests/                      # 测试文件
└── storage/                    # 运行时目录
    └── projects/              # 项目文件
```

