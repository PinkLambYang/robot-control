# 快速启动指南

## 1. 安装依赖

```bash
cd robot-control-system
pip install -r requirements.txt
```

## 2. 启动系统

```bash
python main.py
```

你将看到：

```
============================================================
机器人远程控制系统
Robot Control System
============================================================

============================================================
✓ WebSocket Server: ws://0.0.0.0:8000/ws
✓ Worker Process: Running
============================================================

Press Ctrl+C to stop...
```

## 3. 测试系统

### 方法1：使用测试脚本

在另一个终端：

```bash
# 安装websockets库
pip install websockets

# 运行测试客户端
python tests/test_client.py
```

### 方法2：手动测试

#### 3.1 创建测试项目

```bash
python tests/create_test_project.py
```

这将生成 `test_python_project.zip`。

#### 3.2 使用WebSocket客户端

你可以使用任何WebSocket客户端（如wscat、浏览器JavaScript等）连接到 `ws://localhost:8000/ws`。

## 4. 协议示例

### 4.1 上传项目（UPDATE）

```json
{
  "command": "update",
  "data": "<base64_encoded_zip_data>"
}
```

响应：
```json
{
  "status": "success",
  "message": "Project extracted successfully",
  "data": {
    "project_type": "python",
    "project_path": "./storage/projects/current"
  }
}
```

### 4.2 启动项目（START）

```json
{
  "command": "start"
}
```

响应：
```json
{
  "status": "success",
  "message": "Python project started successfully",
  "data": {
    "project_type": "python"
  }
}
```

### 4.3 调用函数（PROCESS）

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

立即响应（ACK）：
```json
{
  "status": "success",
  "message": "Command executed",
  "data": {
    "status": "success",
    "result": {"action": "stand_up", "status": "success"}
  }
}
```

异步回调：
```json
{
  "status": "callback",
  "message": "",
  "data": {
    "type": "callback",
    "data": {
      "object": "sport_client",
      "method": "StandUp",
      "result": {"action": "stand_up", "status": "success"}
    }
  }
}
```

## 5. Python项目结构

你的Python项目应该有一个 `main.py` 文件：

```python
# main.py

class SportClient:
    def __init__(self):
        print("SportClient initialized")
    
    def StandUp(self):
        # 你的机器人控制代码
        return {"status": "success"}
    
    def Walk(self, speed=1.0):
        # 你的机器人控制代码
        return {"status": "walking", "speed": speed}

# 创建全局实例
sport_client = SportClient()

# 可选的初始化函数
def init():
    print("Project initialized!")
```

打包：
```bash
zip -r my_robot_project.zip main.py
```

## 6. 常见问题

### Q: 连接被拒绝？
A: 检查是否已有其他客户端连接。系统同时只允许一个客户端连接。

### Q: Python项目加载失败？
A: 确保zip文件中包含 `main.py` 或 `__init__.py`。

### Q: 函数调用失败？
A: 检查：
- 是否已执行START指令
- object名称是否正确（在main.py中定义的变量或类）
- method名称是否正确

### Q: 如何停止系统？
A: 按 `Ctrl+C`，系统会优雅地关闭所有进程。

## 7. 日志查看

日志文件位于：`storage/logs/app.log`

```bash
tail -f storage/logs/app.log
```

## 8. Docker部署

```bash
# 构建镜像
docker build -t robot-control-system .

# 运行
docker run -d -p 8000:8000 --name robot-control robot-control-system

# 查看日志
docker logs -f robot-control

# 停止
docker stop robot-control
```

## 9. 下一步

- 阅读 `ARCHITECTURE.md` 了解系统架构
- 查看 `tests/test_client.py` 学习完整的使用流程
- 根据需要修改 `config.yaml` 配置

