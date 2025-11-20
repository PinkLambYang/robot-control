import React, { useState } from 'react'

export const CommandPanel = ({ isConnected, onSendCommand, addLog }) => {
  const [methodName, setMethodName] = useState('prepare_mode')
  const OBJECT_NAME = 'robot_controller' // 固定对象名

  const handleStart = () => {
    // sendMessage 会自动记录响应日志（因为没有 callback）
    onSendCommand('start', {})
  }

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

  return (
    <>
      {/* 执行指令 */}
      <div className="section">
        <div className="section-title">执行指令 (PROCESS)</div>
        <p style={{ fontSize: '13px', color: '#666', marginBottom: '10px' }}>
          🚀 <strong>可直接执行！</strong>系统会自动加载默认项目，无需先执行 UPDATE 和 START
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
              disabled={!isConnected}
            >
              准备模式
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('walk_mode')}
              disabled={!isConnected}
            >
              走路模式
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('run_mode')}
              disabled={!isConnected}
            >
              跑步模式
            </button>
          </div>

          <div style={{ fontSize: '13px', color: '#666', marginTop: '12px', marginBottom: '8px' }}>动作指令：</div>
          <div className="command-section">
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('wave_hand')}
              disabled={!isConnected}
            >
              打招呼
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('shake_hand')}
              disabled={!isConnected}
            >
              握手
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('cheer')}
              disabled={!isConnected}
            >
              欢呼
            </button>
          </div>

          <div style={{ fontSize: '13px', color: '#666', marginTop: '12px', marginBottom: '8px' }}>移动控制：</div>
          <div className="command-section">
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('move_up')}
              disabled={!isConnected}
            >
              ⬆️ 向上
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('move_down')}
              disabled={!isConnected}
            >
              ⬇️ 向下
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('move_left')}
              disabled={!isConnected}
            >
              ⬅️ 向左
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleQuickCommand('move_right')}
              disabled={!isConnected}
            >
              ➡️ 向右
            </button>
          </div>
        </div>
      </div>

      {/* 启动项目 (可选) */}
      <div className="section" style={{ opacity: 0.8 }}>
        <div className="section-title">手动启动 (START) - 可选</div>
        <p style={{ fontSize: '13px', color: '#666', marginBottom: '10px' }}>
          💡 通常不需要手动启动，仅在特殊情况下使用
        </p>
        <button
          className="btn btn-warning"
          onClick={handleStart}
          disabled={!isConnected}
          style={{ opacity: 0.7 }}
        >
          启动项目
        </button>
      </div>
    </>
  )
}

