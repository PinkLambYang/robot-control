import React, { useEffect, useRef } from 'react'

export const LogPanel = ({ logs, onClear }) => {
  const logContainerRef = useRef(null)

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  return (
    <div className="section">
      <div className="section-title">
        日志输出
        <button className="btn btn-secondary clear-log-btn" onClick={onClear}>
          清空日志
        </button>
      </div>
      <div className="log-container" ref={logContainerRef}>
        {logs.map((log, index) => (
          <div key={index} className={`log-entry log-${log.type}`}>
            <span className="log-time">[{log.timestamp}]</span>
            {log.message}
          </div>
        ))}
      </div>
    </div>
  )
}

