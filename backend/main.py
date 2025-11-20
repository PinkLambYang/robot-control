"""机器人控制系统主启动脚本"""
import multiprocessing
import sys
import os
import time
from pathlib import Path

# 确保当前目录在sys.path中
sys.path.insert(0, str(Path(__file__).parent))

from ws_server.server import start_ws_server
from worker.worker import start_worker


def main():
    """主函数：启动WebSocket Server和Worker进程"""
    print("=" * 60)
    print("机器人远程控制系统")
    print("Robot Control System")
    print("=" * 60)
    
    # 检查配置文件
    if not Path('config.yaml').exists():
        print("ERROR: config.yaml not found!")
        sys.exit(1)
    
    # 清理旧的IPC socket文件
    for socket_file in ['/tmp/robot-control-cmd.ipc', '/tmp/robot-control-callback.ipc']:
        if os.path.exists(socket_file):
            print(f"Removing old socket file: {socket_file}")
            os.remove(socket_file)
    
    # Worker 进程引用
    worker_process = None
    
    def start_worker_process():
        """启动 Worker 进程"""
        nonlocal worker_process
        print("Starting Worker process...")
        worker_process = multiprocessing.Process(target=start_worker, name="Worker")
        worker_process.start()
        print(f"✓ Worker process started (PID: {worker_process.pid})")
        return worker_process.pid
    
    # 启动初始 Worker
    start_worker_process()
    time.sleep(2)  # 等待 Worker 完全启动
    
    print("Starting WebSocket Server process...")
    ws_process = multiprocessing.Process(target=start_ws_server, name="WSServer")
    ws_process.start()
    
    print("All processes started successfully")
    print("\n" + "=" * 60)
    print("✓ Socket.IO Server: http://0.0.0.0:8000")
    print("✓ Worker Process: Running")
    print("=" * 60)
    print("\n[INFO] Worker will auto-restart on UPDATE command")
    print("Press Ctrl+C to stop...\n")
    
    try:
        while True:
            # 检查 Worker 进程状态
            if worker_process and not worker_process.is_alive():
                exit_code = worker_process.exitcode
                
                if exit_code == 0:
                    # 正常退出，说明是 UPDATE 触发的重启
                    print(f"\n{'='*60}")
                    print("[INFO] Worker exited normally (UPDATE command)")
                    print("[INFO] Restarting Worker to clear module cache...")
                    print(f"{'='*60}\n")
                    
                    time.sleep(1)  # 等待资源释放
                    start_worker_process()
                    time.sleep(2)  # 等待 Worker 完全启动
                    
                    print(f"\n{'='*60}")
                    print("✓ Worker restarted successfully")
                    print("✓ Module cache cleared")
                    print("✓ Ready to accept START command")
                    print(f"{'='*60}\n")
                else:
                    # 异常退出
                    print(f"\n{'='*60}")
                    print(f"[ERROR] Worker crashed with exit code {exit_code}")
                    print("[ERROR] System will exit. Please check logs.")
                    print(f"{'='*60}\n")
                    break
            
            # 检查 WS Server 进程状态
            if not ws_process.is_alive():
                print("\n[ERROR] Socket.IO Server process died unexpectedly")
                break
            
            # 短暂休眠，避免 CPU 占用
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        
        # 终止进程
        print("  ├─ Terminating Socket.IO Server...")
        ws_process.terminate()
        
        if worker_process:
            print("  ├─ Terminating Worker...")
            worker_process.terminate()
        
        # 等待进程结束
        ws_process.join(timeout=5)
        if worker_process:
            worker_process.join(timeout=5)
        
        # 强制终止未结束的进程
        if ws_process.is_alive():
            print("  ├─ Killing Socket.IO Server process")
            ws_process.kill()
        
        if worker_process and worker_process.is_alive():
            print("  ├─ Killing Worker process")
            worker_process.kill()
        
        print("  └─ Shutdown complete\n")


if __name__ == '__main__':
    # 设置启动方法（macOS需要）
    multiprocessing.set_start_method('spawn', force=True)
    main()

