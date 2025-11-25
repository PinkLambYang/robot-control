# 机器人控制系统 - React Web 客户端 (Socket.IO)

基于 React + Vite + Socket.IO 的现代化 Web 客户端，用于远程控制机器人系统。

## ✨ 特性

- ⚛️ **React 18** - 使用最新的 React 版本
- ⚡️ **Vite** - 极速的开发服务器和构建工具
- 🎨 **组件化架构** - 模块化的组件设计
- 🔌 **Socket.IO 支持** - 实时双向通信，自动重连
- 📱 **响应式设计** - 适配各种屏幕尺寸
- 🔄 **自动重连** - 网络断开自动恢复连接
- 💓 **心跳检测** - 内置连接保活机制
- 🔄 **状态同步** - 断开重连后自动同步前后端状态

## 📦 安装

```bash
# 使用 npm
npm install

# 或使用 yarn
yarn install

# 或使用 pnpm
pnpm install
```

这将安装所有依赖，包括：
- React 18
- socket.io-client 4.7
- Vite 5.0

## 🚀 启动

### 开发模式

```bash
npm run dev
```

服务将在 `http://localhost:3000` 启动

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 📁 项目结构

```
robot-control-web/
├── src/
│   ├── main.jsx              # 应用入口
│   ├── App.jsx               # 主应用组件
│   ├── components/           # React 组件
│   │   ├── ConnectionPanel.jsx   # 连接面板
│   │   ├── UploadPanel.jsx       # 上传面板
│   │   ├── CommandPanel.jsx      # 指令面板
│   │   └── LogPanel.jsx          # 日志面板
│   ├── hooks/               # 自定义 Hooks
│   │   └── useSocketIO.js        # Socket.IO Hook ⭐
│   └── styles/              # 样式文件
│       └── App.css
├── index.html               # HTML 模板
├── vite.config.js          # Vite 配置
└── package.json            # 依赖配置（含 socket.io-client）
```

## 🔧 配置

### Socket.IO 地址

默认连接到 `http://localhost:8000`，可以在界面上修改。

### 端口配置

在 `vite.config.js` 中修改端口：

```js
export default defineConfig({
  server: {
    port: 3000,  // 修改为你想要的端口
    host: '0.0.0.0'
  }
})
```

## 🎯 使用流程

### 快速开始（推荐）

1. **启动后端服务**
   ```bash
   cd backend
   python main.py
   ```

2. **启动 React 客户端**
   ```bash
   cd frontend
   npm run dev
   ```

3. **连接并直接使用**
   - 打开 `http://localhost:3000`
   - 点击"连接"按钮
   - 🚀 **直接执行 PROCESS 指令！**系统会自动加载默认项目

4. **执行指令**
   - 输入对象名和方法名（默认：`robot_controller.prepare_mode`）
   - 点击"执行指令"或使用快速命令按钮
   - 查看日志面板获取执行结果

### 上传自定义项目（可选）

如需使用自定义项目：

1. **准备项目 ZIP 包**
2. **点击"上传项目"**
   - 选择 ZIP 文件
   - 点击"上传项目"
   - Worker 会自动重启
3. **执行指令**
   - 直接使用 PROCESS，无需手动 START

## 🔍 主要组件

### `useSocketIO` Hook ⭐

管理 Socket.IO 连接状态、消息发送和接收。

```jsx
const {
  isConnected,
  logs,
  connect,
  disconnect,
  sendMessage,
  addLog,
  clearLogs,
  socket  // Socket.IO 实例，用于自定义事件监听
} = useSocketIO()

// 连接时传入 URL
connect('http://localhost:8000')
```

**特性**:
- ✅ 动态 URL 连接
- ✅ 自动重连机制
- ✅ 心跳检测
- ✅ 连接状态管理
- ✅ 事件驱动通信
- ✅ 智能日志去重（避免重复记录）
- ✅ 错误处理

**日志记录策略**:
- 如果提供了 `callback` 参数，由 callback 负责记录日志（避免重复）
- 如果没有 callback，`sendMessage` 自动记录响应日志
- 组件可以通过 callback 自定义日志内容和格式

### ConnectionPanel

处理 Socket.IO 连接和断开。

### UploadPanel

处理文件上传和 Base64 编码（UPDATE 事件）。

### CommandPanel

发送 START 和 PROCESS 事件。

### LogPanel

显示实时日志信息和回调。

## 🔌 Socket.IO vs WebSocket

| 特性 | Socket.IO | WebSocket |
|------|-----------|-----------|
| 自动重连 | ✅ 内置 | ❌ 需手动实现 |
| 心跳检测 | ✅ 内置 | ❌ 需手动实现 |
| 事件系统 | ✅ 基于事件 | ❌ 基于消息 |
| 降级支持 | ✅ 自动降级 | ❌ 不支持 |
| 房间/命名空间 | ✅ 支持 | ❌ 不支持 |
| 易用性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

## 🐛 常见问题

### Q: 为什么选择 Socket.IO？

A: Socket.IO 提供了更可靠的实时通信，包括自动重连、心跳检测、事件驱动 API 等功能，比原生 WebSocket 更适合生产环境。

### Q: Socket.IO 如何实现自动重连？

A: Socket.IO 客户端会在连接断开后自动尝试重连，你可以配置重连延迟和尝试次数：

```js
const socket = io('http://localhost:8000', {
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: 5
})
```

### Q: 如何修改服务器地址？

A: 在界面的"Socket.IO 连接"区域直接修改即可。

### Q: 构建后如何部署？

A: 运行 `npm run build` 后，将 `dist` 目录部署到任何静态文件服务器即可。

## 📝 Socket.IO API 示例

### 1-3 秒操作（等待响应即可）

```javascript
// 发送指令，等待同步响应
socket.emit('process', {
  params: {
    object: 'robot_controller',
    method: 'prepare_mode',
    args: {}
  }
}, (response) => {
  console.log(response) // 等待 1-3 秒后获得结果
})
```

### 5 秒以上操作（监听异步推送）

```javascript
// 1. 启动任务（立即返回）
socket.emit('process', {
  params: {
    object: 'robot_controller',
    method: 'start_long_task',
    args: {}
  }
}, (response) => {
  console.log(response.message) // "任务已启动"
})

// 2. 监听任务完成
socket.on('task_completed', (data) => {
  console.log('任务完成:', data.result)
})

// 3. 监听任务错误
socket.on('task_error', (data) => {
  console.error('任务失败:', data.message)
})
```

### 持续性任务（实时数据流）

```javascript
// 启动识别
socket.emit('process', {
  params: {
    object: 'robot_controller',
    method: 'start_recognition',
    args: {}
  }
})

// 监听实时结果（持续推送）
socket.on('recognition_result', (data) => {
  console.log('识别到:', data.object, data.confidence)
})

// 停止识别
socket.emit('process', {
  params: {
    object: 'robot_controller',
    method: 'stop_recognition',
    args: {}
  }
})
```

### 系统事件

```javascript
socket.on('connect', () => console.log('已连接'))
socket.on('disconnect', (reason) => console.log('已断开:', reason))
socket.on('error', (data) => console.error('错误:', data.message))
```

## 📚 相关文档

- [Vite 文档](https://vitejs.dev/)
- [React 文档](https://react.dev/)
- [Socket.IO 客户端文档](https://socket.io/docs/v4/client-api/)
- [Socket.IO 中文文档](https://socket.io/zh-CN/docs/v4/)

## 🎉 优势对比

| 特性 | React + Socket.IO | 纯 HTML + WebSocket |
|------|-------------------|---------------------|
| 组件化 | ✅ | ❌ |
| 状态管理 | ✅ | ❌ |
| 代码复用 | ✅ | ❌ |
| 自动重连 | ✅ | ❌ |
| 心跳检测 | ✅ | ❌ |
| 开发体验 | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| 热更新 | ✅ | ❌ |
| 构建优化 | ✅ | ❌ |
| 维护性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 可靠性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

## 📄 License

MIT
