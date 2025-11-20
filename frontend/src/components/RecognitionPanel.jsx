import React, { useState, useEffect } from 'react'

export const RecognitionPanel = ({ isConnected, onSendCommand, socket, addLog }) => {
  const [isRecognizing, setIsRecognizing] = useState(false)
  const [recognitionResults, setRecognitionResults] = useState([])
  const [latestResult, setLatestResult] = useState(null)

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
      setRecognitionResults(prev => [result, ...prev].slice(0, 50)) // 只保留最近50条
    }

    socket.on('recognition_result', handleRecognitionResult)

    return () => {
      socket.off('recognition_result', handleRecognitionResult)
    }
  }, [socket])

  const handleStartRecognition = () => {
    const data = {
      params: {
        object: 'robot_controller',
        method: 'start_recognition',
        args: {}
      }
    }

    onSendCommand('process', data, (response) => {
      if (response.status === 'success') {
        setIsRecognizing(true)
        setRecognitionResults([])
        setLatestResult(null)
        addLog(`✓ ${response.message}`, 'success')
      } else {
        addLog(`✗ ${response.message}`, 'error')
      }
    })
  }

  const handleStopRecognition = () => {
    const data = {
      params: {
        object: 'robot_controller',
        method: 'stop_recognition',
        args: {}
      }
    }

    onSendCommand('process', data, (response) => {
      if (response.status === 'success') {
        setIsRecognizing(false)
        addLog(`✓ ${response.message}`, 'warning')
      } else {
        addLog(`✗ ${response.message}`, 'error')
      }
    })
  }

  const handleClearResults = () => {
    setRecognitionResults([])
    setLatestResult(null)
    addLog('识别结果已清空', 'info')
  }

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
        <button
          className="btn btn-secondary"
          onClick={handleClearResults}
          disabled={!isConnected || recognitionResults.length === 0}
        >
          清空结果
        </button>
      </div>

      {/* 识别状态 */}
      <div style={{ marginBottom: '15px' }}>
        <div style={{
          padding: '12px',
          borderRadius: '6px',
          backgroundColor: isRecognizing ? '#e8f5e9' : '#f5f5f5',
          border: `2px solid ${isRecognizing ? '#4caf50' : '#ddd'}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <span style={{ 
              fontSize: '14px', 
              fontWeight: 'bold',
              color: isRecognizing ? '#2e7d32' : '#666'
            }}>
              {isRecognizing ? '● 识别中...' : '○ 未启动'}
            </span>
            {recognitionResults.length > 0 && (
              <span style={{ fontSize: '13px', color: '#666', marginLeft: '10px' }}>
                已识别 {recognitionResults.length} 次
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
          <div style={{
            padding: '15px',
            borderRadius: '8px',
            backgroundColor: '#e3f2fd',
            border: '2px solid #2196f3',
            animation: 'fadeIn 0.3s ease-in'
          }}>
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

      {/* 识别历史记录 */}
      {recognitionResults.length > 0 && (
        <div>
          <div style={{ fontSize: '13px', color: '#666', marginBottom: '8px', fontWeight: 'bold' }}>
            识别历史 (最近 {Math.min(recognitionResults.length, 10)} 条)：
          </div>
          <div style={{
            maxHeight: '300px',
            overflowY: 'auto',
            border: '1px solid #ddd',
            borderRadius: '6px',
            backgroundColor: '#fafafa'
          }}>
            {recognitionResults.slice(0, 10).map((result) => (
              <div
                key={result.id}
                style={{
                  padding: '10px',
                  borderBottom: '1px solid #eee',
                  fontSize: '13px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  transition: 'background-color 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f0f0f0'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <div style={{ flex: 1 }}>
                  <span style={{ fontWeight: 'bold', color: '#1976d2' }}>#{result.count}</span>
                  <span style={{ marginLeft: '10px', color: '#333' }}>{result.object}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                  <span style={{ 
                    color: result.confidence >= 0.9 ? '#4caf50' : result.confidence >= 0.8 ? '#ff9800' : '#f44336',
                    fontWeight: 'bold'
                  }}>
                    {(result.confidence * 100).toFixed(0)}%
                  </span>
                  <span style={{ color: '#999', fontSize: '12px' }}>
                    {result.timestamp}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 空状态提示 */}
      {!isRecognizing && recognitionResults.length === 0 && (
        <div style={{
          padding: '30px',
          textAlign: 'center',
          color: '#999',
          fontSize: '14px',
          border: '2px dashed #ddd',
          borderRadius: '8px',
          backgroundColor: '#fafafa'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '10px' }}>🔍</div>
          <div>点击"开始识别"按钮启动实时识别</div>
        </div>
      )}
    </div>
  )
}

