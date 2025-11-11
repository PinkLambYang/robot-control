import { useState, useEffect, useRef, useCallback } from 'react'
import { io } from 'socket.io-client'

export const useSocketIO = (url) => {
  const [isConnected, setIsConnected] = useState(false)
  const [logs, setLogs] = useState([])
  const socketRef = useRef(null)

  const addLog = useCallback((message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    setLogs(prev => [...prev, { timestamp, message, type }])
  }, [])

  const connect = useCallback(() => {
    if (socketRef.current?.connected) {
      addLog('已经连接', 'warning')
      return
    }

    addLog(`正在连接到 ${url}...`, 'info')
    
    try {
      const socket = io(url, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 5
      })
      
      socketRef.current = socket

      socket.on('connect', () => {
        addLog('✓ Socket.IO 连接成功', 'success')
        setIsConnected(true)
      })

      socket.on('connected', (data) => {
        addLog(`✓ ${data.message}`, 'success')
      })

      socket.on('disconnect', (reason) => {
        addLog(`连接已断开: ${reason}`, 'warning')
        setIsConnected(false)
      })

      socket.on('error', (data) => {
        addLog(`✗ 错误: ${data.message}`, 'error')
      })

      socket.on('callback', (data) => {
        addLog(`↩ 回调: ${JSON.stringify(data)}`, 'warning')
      })

      socket.on('connect_error', (error) => {
        addLog(`✗ 连接错误: ${error.message}`, 'error')
      })

      socket.on('reconnect', (attemptNumber) => {
        addLog(`✓ 重新连接成功 (第 ${attemptNumber} 次尝试)`, 'success')
      })

      socket.on('reconnect_attempt', () => {
        addLog('正在尝试重新连接...', 'info')
      })

      socket.on('reconnect_failed', () => {
        addLog('✗ 重连失败，请检查网络连接', 'error')
      })
    } catch (e) {
      addLog(`✗ 连接失败: ${e.message}`, 'error')
    }
  }, [url, addLog])

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect()
      addLog('主动断开连接', 'info')
      socketRef.current = null
    }
  }, [addLog])

  const sendMessage = useCallback((eventName, data, callback) => {
    if (!socketRef.current || !socketRef.current.connected) {
      addLog('✗ Socket.IO 未连接', 'error')
      return false
    }

    try {
      socketRef.current.emit(eventName, data, (response) => {
        if (response) {
          console.log(response)
          if (response.status === 'success') {
            addLog(`✓ ${response.message}`, 'success')
            if (response.data) {
              if ('status' in response.data) {
                addLog(`数据: ${JSON.stringify(response.data)}`, response.data.status)
              } else {
                addLog(`数据: ${JSON.stringify(response.data)}`, 'info')
              }
            }
          } else if (response.status === 'error') {
            addLog(`✗ 错误: ${response.message}`, 'error')
            if (response.data) {
              addLog(`错误详情: ${JSON.stringify(response.data)}`, 'error')
            }
          }
          
          if (callback) {
            callback(response)
          }
        }
      })
      return true
    } catch (e) {
      addLog(`✗ 发送失败: ${e.message}`, 'error')
      return false
    }
  }, [addLog])

  const clearLogs = useCallback(() => {
    setLogs([])
    addLog('日志已清空', 'info')
  }, [addLog])

  // 清理函数
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect()
      }
    }
  }, [])

  return {
    isConnected,
    logs,
    connect,
    disconnect,
    sendMessage,
    addLog,
    clearLogs
  }
}

