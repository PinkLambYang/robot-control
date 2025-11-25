import React, { useState } from 'react'

export const CommandPanel = ({ isConnected, onSendCommand, addLog }) => {
  const [methodName, setMethodName] = useState('prepare_mode')
  const [ddsStarted, setDdsStarted] = useState(false) // DDS 启动状态
  const OBJECT_NAME = 'robot_controller' // 固定对象名

  const handleProcess = () => {
    if (!methodName) {
      addLog('✗ 请输入方法名称', 'error')
      return
    }

    const data = {
      params: {
        object: OBJECT_NAME,
        method: methodName,
        args: {}
      }
    }

    // sendMessage 会自动记录响应日志（因为没有 callback）
    onSendCommand('process', data)
  }

  const handleQuickCommand = (method) => {
    setMethodName(method)
    const data = {
      params: {
        object: OBJECT_NAME,
        method: method,
        args: {}
      }
    }
    // sendMessage 会自动记录响应日志（因为没有 callback）
    onSendCommand('process', data)
  }

  const handleStartDDS = () => {
    const data = {
      params: {
        object: OBJECT_NAME,
        method: 'start_dds_client',
        args: {}
      }
    }
    onSendCommand('process', data, (response) => {
      console.log('response', response)
      if (response.status === 'success') {
        addLog('DDS Client 启动成功', 'success')
        setDdsStarted(true)
      } else {
        addLog('DDS Client 启动失败', 'error')
      }
    })
  }

  const handleStopDDS = () => {
    const data = {
      params: {
        object: OBJECT_NAME,
        method: 'stop_dds_client',
        args: {}
      }
    }
    onSendCommand('process', data, (response) => {
      if (response.status === 'success') {
        addLog('DDS Client 停止成功', 'success')
      } else {
        addLog(`DDS Client 停止: ${response.message}`, 'warning')
      }
      // 无论成功还是失败，都标记为已停止，让用户能重试
      setDdsStarted(false)
    })
  }

  return (
    <>
      {/* DDS Client 控制 - 必须先启动 */}
      <div className="section" style={{ 
        background: ddsStarted ? '#e7f9f0' : '#fff5e1', 
        padding: '15px', 
        borderRadius: '10px',
        border: `2px solid ${ddsStarted ? '#48bb78' : '#ed8936'}`
      }}>
        <div className="section-title" style={{ marginBottom: '10px' }}>
          🔌 DDS Client 控制
          <span style={{ 
            fontSize: '12px', 
            fontWeight: 'normal',
            color: ddsStarted ? '#48bb78' : '#ed8936',
            marginLeft: '10px'
          }}>
            {ddsStarted ? '● 已启动' : '○ 未启动'}
          </span>
        </div>
        <p style={{ fontSize: '13px', color: '#666', marginBottom: '10px' }}>
          ⚠️ <strong>必须先启动 DDS Client 才能控制机器人</strong>
        </p>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            className="btn btn-success"
            onClick={handleStartDDS}
            disabled={!isConnected || ddsStarted}
            style={{ flex: 1 }}
          >
            🚀 启动 DDS
          </button>
          <button
            className="btn btn-danger"
            onClick={handleStopDDS}
            disabled={!isConnected || !ddsStarted}
            style={{ flex: 1 }}
          >
            🛑 停止 DDS
          </button>
        </div>
      </div>

      {/* 执行指令 */}
      <div className="section">
        <div className="section-title">执行指令 (PROCESS)</div>
        <p style={{ fontSize: '13px', color: '#666', marginBottom: '10px' }}>
          {ddsStarted ? (
            <>✅ DDS 已启动，可以控制机器人</>
          ) : (
            <>⚠️ 请先启动 DDS Client 才能执行控制指令</>
          )}
        </p>
        <div className="command-group">
          <div className="command-inputs">
            <input
              type="text"
              value={methodName}
              onChange={(e) => setMethodName(e.target.value)}
              placeholder="方法名称 (如: prepare_mode, get_status)"
              style={{ flex: 1 }}
            />
          </div>
          <button
            className="btn btn-primary"
            onClick={handleProcess}
            disabled={!isConnected}
          >
            执行指令
          </button>
        </div>
        
        <div className="quick-commands" style={{ marginTop: '15px' }}>
          <div style={{ fontSize: '13px', color: '#666', marginBottom: '8px' }}>模式控制：</div>
          <div className="command-section">
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('prepare_mode')}
              disabled={!isConnected || !ddsStarted}
            >
              准备模式
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('walk_mode')}
              disabled={!isConnected || !ddsStarted}
            >
              走路模式
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('run_mode')}
              disabled={!isConnected || !ddsStarted}
            >
              跑步模式
            </button>
          </div>

          <div style={{ fontSize: '13px', color: '#666', marginTop: '12px', marginBottom: '8px' }}>动作指令：</div>
          <div className="command-section">
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('wave_hand')}
              disabled={!isConnected || !ddsStarted}
            >
              打招呼
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('shake_hand')}
              disabled={!isConnected || !ddsStarted}
            >
              握手
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('cheer')}
              disabled={!isConnected || !ddsStarted}
            >
              欢呼
            </button>
          </div>

          <div style={{ fontSize: '13px', color: '#666', marginTop: '12px', marginBottom: '8px' }}>移动控制：</div>
          <div className="gamepad-container">
            <div className="dpad">
              {/* 上 */}
              <button
                className="dpad-btn dpad-up"
                onClick={() => handleQuickCommand('move_up')}
                disabled={!isConnected || !ddsStarted}
                title="向前移动"
              >
                <span className="dpad-arrow">▲</span>
              </button>
              
              {/* 左 */}
              <button
                className="dpad-btn dpad-left"
                onClick={() => handleQuickCommand('move_left')}
                disabled={!isConnected || !ddsStarted}
                title="向左移动"
              >
                <span className="dpad-arrow">◀</span>
              </button>
              
              {/* 中心圆 */}
              <div className="dpad-center"></div>
              
              {/* 右 */}
              <button
                className="dpad-btn dpad-right"
                onClick={() => handleQuickCommand('move_right')}
                disabled={!isConnected || !ddsStarted}
                title="向右移动"
              >
                <span className="dpad-arrow">▶</span>
              </button>
              
              {/* 下 */}
              <button
                className="dpad-btn dpad-down"
                onClick={() => handleQuickCommand('move_down')}
                disabled={!isConnected || !ddsStarted}
                title="向后移动"
              >
                <span className="dpad-arrow">▼</span>
              </button>
            </div>
          </div>
        </div>
      </div>

    </>
  )
}

