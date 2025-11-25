import React, { useState } from 'react'

export const UploadPanel = ({ isConnected, onUpload, addLog }) => {
  const [selectedFile, setSelectedFile] = useState(null)

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
      addLog(`已选择文件: ${file.name}`, 'info')
    } else {
      setSelectedFile(null)
    }
  }

  const handleStart = () => {
    // sendMessage 会自动记录响应日志（因为没有 callback）
    onUpload('start', {})
  }

  const handleUpload = () => {
    if (!selectedFile) {
      addLog('✗ 请先选择文件', 'error')
      return
    }

    addLog(`正在上传项目: ${selectedFile.name}...`, 'info')

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        addLog(`[DEBUG] 文件读取完成，大小: ${e.target.result.byteLength} 字节`, 'info')
        
        const bytes = new Uint8Array(e.target.result)
        let binary = ''
        const chunkSize = 8192
        
        for (let i = 0; i < bytes.length; i += chunkSize) {
          const chunk = bytes.subarray(i, Math.min(i + chunkSize, bytes.length))
          binary += String.fromCharCode.apply(null, chunk)
        }
        
        const base64Data = btoa(binary)
        addLog(`[DEBUG] Base64编码完成，长度: ${base64Data.length} 字符`, 'info')

        // Socket.IO 使用事件名和数据分离，sendMessage 会自动记录响应日志
        onUpload('update', { data: base64Data })
      } catch (err) {
        addLog('✗ 处理失败: ' + err.message, 'error')
        console.error('Upload error:', err)
      }
    }

    reader.onerror = (err) => {
      addLog('✗ 文件读取失败: ' + err, 'error')
      console.error('FileReader error:', err)
    }

    try {
      reader.readAsArrayBuffer(selectedFile)
    } catch (err) {
      addLog('✗ 启动文件读取失败: ' + err.message, 'error')
      console.error('ReadAsArrayBuffer error:', err)
    }
  }

  return (
    <div className="section" style={{ opacity: 0.8 }}>
      <div className="section-title">项目管理 (UPDATE & START) - 可选</div>
      <p style={{ fontSize: '13px', color: '#666', marginBottom: '10px' }}>
        💡 系统已有默认项目可直接使用。上传新项目会替换默认项目，Worker 会自动重启
      </p>
      
      {/* UPDATE - 上传项目 */}
      <div style={{ marginBottom: '15px' }}>
        <div style={{ fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>上传项目 (UPDATE)</div>
        <div className="file-input-wrapper">
          <input
            type="file"
            id="zipFile"
            accept=".zip"
            onChange={handleFileSelect}
          />
          <label
            htmlFor="zipFile"
            className={`file-input-label ${selectedFile ? 'has-file' : ''}`}
          >
            {selectedFile
              ? `📦 ${selectedFile.name} (${(selectedFile.size / 1024).toFixed(2)} KB)`
              : '📦 选择 ZIP 文件'}
          </label>
        </div>
        <button
          className="btn btn-success"
          onClick={handleUpload}
          disabled={!isConnected || !selectedFile}
          style={{ marginTop: '8px', width: '100%' }}
        >
          上传项目
        </button>
      </div>

      {/* START - 启动项目 */}
      <div>
        <div style={{ fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>手动启动 (START)</div>
        <p style={{ fontSize: '12px', color: '#999', marginBottom: '8px' }}>
          通常不需要手动启动，仅在特殊情况下使用
        </p>
        <button
          className="btn btn-warning"
          onClick={handleStart}
          disabled={!isConnected}
          style={{ width: '100%', opacity: 0.7 }}
        >
          启动项目
        </button>
      </div>
    </div>
  )
}

