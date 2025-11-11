# 机器人远程控制系统架构文档

## 1. 系统概述

这是一个基于WebSocket的远程控制系统，支持动态部署Python/C++项目，实现单客户端连接管理、动态代码加载、函数调用和异步回调机制。

### 核心特性

- **双进程架构**：WebSocket进程 + Worker进程，通过IPC通信
- **单客户端限制**：同一时刻只允许一个客户端连接
- **动态加载**：Python项目动态导入模块，C++项目启动可执行文件
- **异步回调**：Worker执行完成后通过IPC返回结果到WS进程
- **进程级隔离**：Worker崩溃不影响WS Server

## 2. 架构图

```
┌─────────────────────┐         IPC (ZMQ)        ┌──────────────────────┐
│  WebSocket Server   │ ◄──────────────────────► │   Worker Process     │
│  - 接收客户端连接    │   REQ-REP (指令)         │   - Python Executor  │
│  - 单连接管理        │   PUB-SUB (回调)         │   - C++ Executor     │
│  - 指令路由          │                          │   - 项目管理         │
└─────────────────────┘                          └──────────────────────┘
         ▲                                                  │
         │                                                  │
    WebSocket                                         调用机器人SDK
         │                                          (unitree_sdk2py等)
         │                                                  │
    ┌────┴────┐                                      ┌─────▼─────┐
    │ Client  │                                      │  Robot    │
    └─────────┘                                      └───────────┘
```

## 3. 模块说明

### 3.1 WebSocket Server (`ws_server/`)

负责接收客户端WebSocket连接和指令处理。

- **server.py**: WebSocket服务器主程序（FastAPI + uvicorn）
- **connection_manager.py**: 单客户端连接管理，确保同时只有一个连接
- **protocol.py**: 协议定义和验证

### 3.2 Worker进程 (`worker/`)

负责项目管理和代码执行。

- **worker.py**: Worker主进程，接收和分发指令
- **project_manager.py**: 处理zip解压、项目类型识别
- **python_executor.py**: Python项目动态加载和函数调用
- **cpp_executor.py**: C++可执行文件管理和进程控制

### 3.3 IPC通信 (`ipc/`)

进程间通信模块。

- **zmq_manager.py**: ZeroMQ封装，使用Unix Domain Socket
- **messages.py**: 消息格式定义

## 4. 通信协议

### 客户端 → 服务器

#### UPDATE指令
```json
{
  "command": "update",
  "data": "base64_encoded_zip_data"
}
```

#### START指令
```json
{
  "command": "start"
}
```

#### PROCESS指令
```json
{
  "command": "process",
  "params": {
    "object": "sport_client",
    "method": "StandUp",
    "args": {}
  }
}
```

### 服务器 → 客户端

```json
{
  "status": "success|error|callback",
  "message": "...",
  "data": {}
}
```

## 5. 数据流

### UPDATE流程
1. 客户端发送zip文件（base64编码）
2. WS Server转发到Worker
3. Worker解压并识别项目类型
4. 返回成功/失败响应

### START流程
1. 客户端发送start指令
2. WS Server转发到Worker
3. Worker根据项目类型加载：
   - Python: 动态导入模块
   - C++: 启动可执行文件
4. 返回启动状态

### PROCESS流程
1. 客户端发送函数调用请求
2. WS Server转发到Worker
3. Worker立即返回ACK
4. Worker执行Python函数
5. 执行完成后通过PUB-SUB发送回调
6. WS Server推送回调给客户端

## 6. 技术栈

- **WebSocket**: FastAPI + websockets + uvicorn
- **IPC**: ZeroMQ (pyzmq) with Unix Domain Socket
- **动态加载**: importlib (Python), subprocess (C++)
- **配置**: PyYAML
- **日志**: Python logging

## 7. 目录结构

```
robot-control-system/
├── main.py                     # 启动入口
├── config.yaml                 # 系统配置
├── requirements.txt            # Python依赖
├── ws_server/                  # WebSocket服务模块
│   ├── server.py
│   ├── connection_manager.py
│   └── protocol.py
├── worker/                     # Worker执行模块
│   ├── worker.py
│   ├── project_manager.py
│   ├── python_executor.py
│   └── cpp_executor.py
├── ipc/                        # 进程间通信
│   ├── zmq_manager.py
│   └── messages.py
├── storage/                    # 运行时目录
│   ├── projects/              # 解压的项目
│   └── logs/                  # 日志
└── tests/                      # 测试代码
    ├── test_client.py
    └── create_test_project.py
```

## 8. 部署

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

### Docker部署

```bash
# 构建镜像
docker build -t robot-control-system .

# 运行容器
docker run -p 8000:8000 robot-control-system
```

## 9. 设计亮点

### 9.1 低耦合

- WS Server和Worker通过消息队列通信，互不依赖
- 每个模块职责单一，可独立测试

### 9.2 可扩展

- **新语言支持**：添加新的Executor子类
- **新通信方式**：替换ZMQManager实现
- **多Worker**：改为任务队列+Worker池

### 9.3 稳定性

- 进程隔离：Worker崩溃不影响WS连接
- 单连接限制：避免并发冲突
- 完善的错误处理和日志

### 9.4 性能

- Unix Domain Socket：本地IPC性能优异
- 异步架构：支持高并发连接
- REQ-REP + PUB-SUB：同步响应+异步回调

## 10. 限制和注意事项

1. **Python模块卸载**：Python无法完全卸载已导入模块，需重启Worker来切换项目
2. **单客户端限制**：不支持多客户端同时连接
3. **C++项目要求**：必须是预编译的可执行文件
4. **依赖隔离**：用户项目依赖可能与系统冲突

## 11. 未来改进

- [ ] 支持多Worker池和负载均衡
- [ ] 添加项目版本管理
- [ ] 支持Web管理界面
- [ ] 使用虚拟环境隔离Python依赖
- [ ] 添加认证和安全机制
- [ ] 支持项目热重载

