import { useState, useEffect, useRef, useCallback } from 'react'
import { io } from 'socket.io-client'
import { AESCrypto } from '../utils/crypto'


const encryptionEnabled = true
const encryptionKey = 'ROBOT_CONTROL_SYSTEM'

export const getTokenFromURL = () => {
  try {
    const params = new URLSearchParams(window.location.search)
    return params.get('token')
  } catch (e) {
    console.error('Failed to get token from URL:', e)
    return null
  }
}

export const useSocketIO = () => {
  const [isConnected, setIsConnected] = useState(false)
  const [logs, setLogs] = useState([])
  const socketRef = useRef(null)
  const cryptoRef = useRef(null)

  const addLog = useCallback((message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    setLogs(prev => [...prev, { timestamp, message, type }])
  }, [])

  const connect = useCallback(async (url) => {
    if (!url) {
      addLog('✗ 请输入服务器地址', 'error')
      return
    }

    if (socketRef.current?.connected) {
      addLog('已经连接', 'warning')
      return
    }

    addLog(`正在连接到 ${url}...`, 'info')
    
    try {
      let authToken = getTokenFromURL()
      
      if (!authToken) {
        addLog('✗ 未找到 Token', 'error')
        return
      }
      
      addLog('✓ Token 已加载', 'success')

      // 2. 初始化加密（固定启用）
      if (encryptionEnabled) {
        cryptoRef.current = new AESCrypto(encryptionKey)
        addLog('✓ 消息加密已启用 (AES-256-GCM)', 'success')
      }

      // 3. 建立 Socket.IO 连接（推荐使用 auth 对象传递 token）
      const socket = io(url, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 3,
        auth: {
          token: authToken  // 使用 auth 对象（推荐方式）
        }
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

      // 监听识别结果（实时推送）
      socket.on('recognition_result', (data) => {
        addLog(`📊 识别结果 #${data.count}: ${data.object} (置信度: ${data.confidence})`, 'success')
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
  }, [addLog])

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect()
      addLog('主动断开连接', 'info')
      socketRef.current = null
    }
  }, [addLog])

  const sendMessage = useCallback(async (eventName, data, callback) => {
    if (!socketRef.current || !socketRef.current.connected) {
      addLog('✗ Socket.IO 未连接', 'error')
      return false
    }

    try {
      // 如果启用加密，将数据加密为 base64 字符串
      let messageData = data
      if (encryptionEnabled && cryptoRef.current) {
        const encryptResult = await cryptoRef.current.encrypt(data)
        if (encryptResult.success) {
          messageData = encryptResult.encrypted  // 直接发送 base64 字符串
        } else {
          console.warn('Encryption failed, sending unencrypted:', encryptResult.error)
        }
      } else {
        console.log('Sending unencrypted object')
      }

      socketRef.current.emit(eventName, messageData, async (response) => {
        if (response) {
          let actualResponse = response
          
          // 如果响应是字符串 = 加密数据，需要解密
          if (typeof response === 'string' && encryptionEnabled && cryptoRef.current) {
            const decryptResult = await cryptoRef.current.decrypt(response)
            
            if (decryptResult.success) {
              actualResponse = decryptResult.data
              console.log(decryptResult,'解密响应成功:', actualResponse)
            } else {
              addLog(`✗ 解密响应失败: ${decryptResult.error}`, 'error')
              return
            }
          }

          if (callback) {
            callback(actualResponse)
          } else {
            if (actualResponse.status === 'success' && actualResponse.data && 'status' in actualResponse.data) {
              addLog(`回调结果: ${JSON.stringify(actualResponse.data)}`, actualResponse.data.status)
              return
            } 
            addLog(`回调结果: ${actualResponse.message}`, actualResponse.status)
          }
        }
      })
      return true
    } catch (e) {
      addLog(`✗ 发送失败: ${e.message}`, 'error')
      return false
    }
  }, [addLog, encryptionEnabled, cryptoRef])

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
    clearLogs,
    socket: socketRef.current
  }
}

