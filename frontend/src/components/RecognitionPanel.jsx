import React, { useState, useEffect, useCallback, useRef } from 'react'

// 样式常量
const STYLES = {
  statusBox: (isActive) => ({
    padding: '12px',
    borderRadius: '6px',
    backgroundColor: isActive ? '#e8f5e9' : '#f5f5f5',
    border: `2px solid ${isActive ? '#4caf50' : '#ddd'}`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between'
  }),
  latestResultCard: {
    padding: '15px',
    borderRadius: '8px',
    backgroundColor: '#e3f2fd',
    border: '2px solid #2196f3',
    animation: 'fadeIn 0.3s ease-in'
  },
  emptyState: {
    padding: '30px',
    textAlign: 'center',
    color: '#999',
    fontSize: '14px',
    border: '2px dashed #ddd',
    borderRadius: '8px',
    backgroundColor: '#fafafa'
  }
}

export const RecognitionPanel = ({ isConnected, onSendCommand, socket, addLog }) => {
  const [isRecognizing, setIsRecognizing] = useState(false)
  const [latestResult, setLatestResult] = useState(null)
  const [recognitionCount, setRecognitionCount] = useState(0)
  
  // 使用 ref 避免 useEffect 重复订阅
  const isRecognizingRef = useRef(isRecognizing)
  const addLogRef = useRef(addLog)
  const onSendCommandRef = useRef(onSendCommand)
  
  // 同步 ref
  useEffect(() => {
    isRecognizingRef.current = isRecognizing
    addLogRef.current = addLog
    onSendCommandRef.current = onSendCommand
  }, [isRecognizing, addLog, onSendCommand])

  useEffect(() => {
    if (!socket) return

    // 监听识别结果
    const handleRecognitionResult = (data) => {
      const result = {
        id: Date.now(),
        count: data.count,
        timestamp: new Date(data.timestamp * 1000).toLocaleTimeString('zh-CN', { hour12: false }),
        object: data.object,
        confidence: data.confidence,
        position: data.position
      }
      
      setLatestResult(result)
      setRecognitionCount(data.count)
    }

    // 监听断开连接事件 - 重置识别状态
    const handleDisconnect = () => {
      if (isRecognizingRef.current) {
        setIsRecognizing(false)
        addLogRef.current('⚠ 连接断开，识别已自动停止', 'warning')
      }
    }

    // 监听重新连接事件 - 同步状态
    const handleConnect = () => {
      // 只在之前正在识别时才查询状态
      if (isRecognizingRef.current) {
        const data = {
          params: {
            object: 'robot_controller',
            method: 'get_status',
            args: {}
          }
        }

        onSendCommandRef.current('process', data, (response) => {
          if (response.status === 'success' && response.data?.result) {
            const backendRecognitionRunning = response.data.result.recognition_running
            if (!backendRecognitionRunning) {
              setIsRecognizing(false)
              addLogRef.current('✓ 状态已同步：识别已停止', 'info')
            }
          }
        })
      }
    }

    socket.on('recognition_result', handleRecognitionResult)
    socket.on('disconnect', handleDisconnect)
    socket.on('connect', handleConnect)

    return () => {
      socket.off('recognition_result', handleRecognitionResult)
      socket.off('disconnect', handleDisconnect)
      socket.off('connect', handleConnect)
    }
  }, [socket])

  const handleStartRecognition = useCallback(() => {
    const data = {
      params: {
        object: 'robot_controller',
        method: 'start_recognition',
        args: {}
      }
    }

    onSendCommand('process', data, (response) => {
      if (response.status === 'success' && response.data?.status === 'success') {
        setIsRecognizing(true)
        setLatestResult(null)
        setRecognitionCount(0)
        addLog(`回调结果: ${response.message}`, 'success')
      } else {
        addLog(`✗ ${response.status === 'error' ? response.message : response.data?.status === 'error' ? response.data?.message : 'Unknown error'}`, 'error')
      }
    })
  }, [onSendCommand, addLog])

  const handleStopRecognition = useCallback(() => {
    const data = {
      params: {
        object: 'robot_controller',
        method: 'stop_recognition',
        args: {}
      }
    }

    onSendCommand('process', data, (response) => {
      if (response.status === 'success' && response.data?.status === 'success') {
        setIsRecognizing(false)
        addLog(`✓ ${response.message}`, 'info')
      } else {
        addLog(`✗ ${response.status === 'error' ? response.message : response.data?.status === 'error' ? response.data?.message : 'Unknown error'}`, 'error')
      }
    })
  }, [onSendCommand, addLog])


  return (
    <div className="section">
      <div className="section-title">🔍 实时识别</div>
      
      {/* 控制按钮 */}
      <div className="command-section" style={{ marginBottom: '15px' }}>
        <button
          className={`btn ${isRecognizing ? 'btn-danger' : 'btn-success'}`}
          onClick={isRecognizing ? handleStopRecognition : handleStartRecognition}
          disabled={!isConnected}
          style={{ minWidth: '120px' }}
        >
          {isRecognizing ? '⏹ 停止识别' : '▶️ 开始识别'}
        </button>
      </div>

      {/* 识别状态 */}
      <div style={{ marginBottom: '15px' }}>
        <div style={STYLES.statusBox(isRecognizing)}>
          <div>
            <span style={{ 
              fontSize: '14px', 
              fontWeight: 'bold',
              color: isRecognizing ? '#2e7d32' : '#666'
            }}>
              {isRecognizing ? '● 识别中...' : '○ 未启动'}
            </span>
            {recognitionCount > 0 && (
              <span style={{ fontSize: '13px', color: '#666', marginLeft: '10px' }}>
                已识别 {recognitionCount} 次
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 最新识别结果 */}
      {latestResult && (
        <div style={{ marginBottom: '15px' }}>
          <div style={{ fontSize: '13px', color: '#666', marginBottom: '8px', fontWeight: 'bold' }}>
            最新识别结果：
          </div>
          <div style={STYLES.latestResultCard}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <div style={{ fontSize: '12px', color: '#666' }}>对象</div>
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#1976d2' }}>
                  {latestResult.object}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#666' }}>置信度</div>
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#1976d2' }}>
                  {(latestResult.confidence * 100).toFixed(0)}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#666' }}>位置</div>
                <div style={{ fontSize: '14px', color: '#333' }}>
                  X: {latestResult.position.x}, Y: {latestResult.position.y}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#666' }}>时间</div>
                <div style={{ fontSize: '14px', color: '#333' }}>
                  {latestResult.timestamp}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 空状态提示 */}
      {!isRecognizing && !latestResult && (
        <div style={STYLES.emptyState}>
          <div style={{ fontSize: '48px', marginBottom: '10px' }}>🔍</div>
          <div>点击"开始识别"按钮启动实时识别</div>
        </div>
      )}
    </div>
  )
}

