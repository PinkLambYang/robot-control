import React, { useEffect } from 'react'
import { useSocketIO } from './hooks/useSocketIO'
import { ConnectionPanel } from './components/ConnectionPanel'
import { UploadPanel } from './components/UploadPanel'
import { CommandPanel } from './components/CommandPanel'
import { RecognitionPanel } from './components/RecognitionPanel'
import { LogPanel } from './components/LogPanel'

function App() {
  const {
    isConnected,
    logs,
    connect,
    disconnect,
    sendMessage,
    addLog,
    clearLogs,
    socket
  } = useSocketIO()

  useEffect(() => {
    addLog('欢迎使用机器人控制系统 Web 客户端 (Socket.IO)', 'info')
    addLog('请先连接 Socket.IO 服务器', 'info')
    addLog('💡 提示：连接后可直接执行 PROCESS 指令，无需上传项目', 'info')
  }, [addLog])

  return (
    <div className="container">
      <div className="header">
        <h1>🤖 机器人控制系统</h1>
        <p>Robot Control System - Web Client (Socket.IO)</p>
      </div>

      <div className="content">
        <div className="left-panel">
          <ConnectionPanel
            isConnected={isConnected}
            onConnect={connect}
            onDisconnect={disconnect}
          />

          <RecognitionPanel
            isConnected={isConnected}
            onSendCommand={sendMessage}
            socket={socket}
            addLog={addLog}
          />

          <CommandPanel
            isConnected={isConnected}
            onSendCommand={sendMessage}
            addLog={addLog}
          />

          <UploadPanel
            isConnected={isConnected}
            onUpload={sendMessage}
            addLog={addLog}
          />
        </div>

        <div className="right-panel">
          <LogPanel logs={logs} onClear={clearLogs} />
        </div>
      </div>
    </div>
  )
}

export default App

