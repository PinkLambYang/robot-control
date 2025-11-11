import React, { useEffect } from 'react'
import { useSocketIO } from './hooks/useSocketIO'
import { ConnectionPanel } from './components/ConnectionPanel'
import { UploadPanel } from './components/UploadPanel'
import { CommandPanel } from './components/CommandPanel'
import { LogPanel } from './components/LogPanel'

function App() {
  const {
    isConnected,
    logs,
    connect,
    disconnect,
    sendMessage,
    addLog,
    clearLogs
  } = useSocketIO('http://localhost:8000')

  useEffect(() => {
    addLog('欢迎使用机器人控制系统 Web 客户端 (Socket.IO)', 'info')
    addLog('请先连接 Socket.IO 服务器', 'info')
  }, [addLog])

  return (
    <div className="container">
      <div className="header">
        <h1>🤖 机器人控制系统</h1>
        <p>Robot Control System - Web Client (Socket.IO)</p>
      </div>

      <div className="content">
        <ConnectionPanel
          isConnected={isConnected}
          onConnect={connect}
          onDisconnect={disconnect}
        />

        <UploadPanel
          isConnected={isConnected}
          onUpload={sendMessage}
          addLog={addLog}
        />

        <CommandPanel
          isConnected={isConnected}
          onSendCommand={sendMessage}
          addLog={addLog}
        />

        <LogPanel logs={logs} onClear={clearLogs} />
      </div>
    </div>
  )
}

export default App

