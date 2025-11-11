import React, { useState } from 'react'

export const ConnectionPanel = ({ isConnected, onConnect, onDisconnect }) => {
  const [wsUrl, setWsUrl] = useState('http://localhost:8000')

  const handleConnect = () => {
    onConnect(wsUrl)
  }

  return (
    <div className="section">
      <div className="status-bar">
        <div className={`status-item ${isConnected ? 'status-connected' : 'status-disconnected'}`}>
          <strong>Socket.IO:</strong> <span>{isConnected ? '已连接' : '未连接'}</span>
        </div>
      </div>

      <div className="section-title">Socket.IO 连接</div>
      <div className="input-group">
        <label>服务器地址</label>
        <input
          type="text"
          value={wsUrl}
          onChange={(e) => setWsUrl(e.target.value)}
          placeholder="http://localhost:8000"
        />
      </div>
      <button className="btn btn-primary" onClick={handleConnect} disabled={isConnected}>
        连接
      </button>
      <button className="btn btn-danger" onClick={onDisconnect} disabled={!isConnected}>
        断开连接
      </button>
    </div>
  )
}

