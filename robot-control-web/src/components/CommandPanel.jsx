import React, { useState } from 'react'

export const CommandPanel = ({ isConnected, onSendCommand, addLog }) => {
  const [objectName, setObjectName] = useState('robot_controller')
  const [methodName, setMethodName] = useState('stand_up')

  const handleStart = () => {
    const success = onSendCommand('start', {})
    if (success) {
      addLog('✓ START 指令已发送', 'success')
    }
  }

  const handleProcess = () => {
    if (!objectName || !methodName) {
      addLog('✗ 请输入对象名称和方法名称', 'error')
      return
    }

    const data = {
      params: {
        object: objectName,
        method: methodName,
        args: {}
      }
    }

    const success = onSendCommand('process', data)
    if (success) {
      addLog(`✓ PROCESS 指令已发送: ${objectName}.${methodName}()`, 'success')
    }
  }

  const handleQuickCommand = (obj, method) => {
    setObjectName(obj)
    setMethodName(method)
    const data = {
      params: {
        object: obj,
        method: method,
        args: {}
      }
    }
    const success = onSendCommand('process', data)
    if (success) {
      addLog(`✓ PROCESS 指令已发送: ${obj}.${method}()`, 'success')
    }
  }

  return (
    <>
      {/* 启动项目 */}
      <div className="section">
        <div className="section-title">2. 启动项目 (START)</div>
        <button
          className="btn btn-warning"
          onClick={handleStart}
          disabled={!isConnected}
        >
          启动项目
        </button>
      </div>

      {/* 执行指令 */}
      <div className="section">
        <div className="section-title">3. 执行指令 (PROCESS)</div>
        <div className="command-group">
          <div className="command-inputs">
            <input
              type="text"
              value={objectName}
              onChange={(e) => setObjectName(e.target.value)}
              placeholder="对象名称 (如: sport_client)"
            />
            <input
              type="text"
              value={methodName}
              onChange={(e) => setMethodName(e.target.value)}
              placeholder="方法名称 (如: StandUp)"
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
        
        <div className="command-section" style={{ marginTop: '15px' }}>
          <button
            className="btn btn-secondary"
            onClick={() => handleQuickCommand('robot_controller', 'stand_up')}
            disabled={!isConnected}
          >
            站立
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => handleQuickCommand('robot_controller', 'sit_down')}
            disabled={!isConnected}
          >
            坐下
          </button>
        </div>
      </div>
    </>
  )
}

