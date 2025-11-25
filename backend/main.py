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
from utils.logger import setup_logging, get_logger

# 常量定义
WORKER_STARTUP_WAIT = 2  # Worker 启动等待时间（秒）
WORKER_RESTART_WAIT = 1  # Worker 重启前等待时间（秒）
PROCESS_SHUTDOWN_TIMEOUT = 5  # 进程关闭超时时间（秒）

logger = get_logger(__name__)


def cleanup_ipc_sockets(socket_files):
    """清理旧的IPC socket文件
    
    Args:
        socket_files: socket文件路径列表
    """
    for socket_file in socket_files:
        if os.path.exists(socket_file):
            try:
                os.remove(socket_file)
                logger.debug(f"Removed old socket file: {socket_file}")
            except OSError as e:
                logger.warning(f"Failed to remove socket file {socket_file}: {e}")


def main():
    """主函数：启动WebSocket Server和Worker进程"""
    # 配置日志系统
    setup_logging(
        name="main",
        log_dir="./storage/logs",
        console_level="INFO",  # 控制台显示 INFO 及以上
        file_level="INFO",     # 文件记录 INFO 及以上
        backup_count=3
    )
    
    print("=" * 60)
    print("机器人远程控制系统")
    print("Robot Control System")
    print("=" * 60)
    
    logger.info("System starting...")
    
    # 检查配置文件
    config_path = Path('config.yaml')
    if not config_path.exists():
        logger.error("config.yaml not found!")
        print("ERROR: config.yaml not found!")
        sys.exit(1)
    
    # 加载配置以获取socket路径
    import yaml
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # 清理旧的IPC socket文件
    socket_files = [
        config['ipc']['command_socket'].replace('ipc://', ''),
        config['ipc']['callback_socket'].replace('ipc://', '')
    ]
    cleanup_ipc_sockets(socket_files)
    
    # Worker 进程引用
    worker_process = None
    
    def start_worker_process():
        """启动 Worker 进程"""
        nonlocal worker_process
        logger.info("Starting Worker process...")
        print("Starting Worker process...")
        worker_process = multiprocessing.Process(target=start_worker, name="Worker")
        worker_process.start()
        logger.info(f"Worker process started (PID: {worker_process.pid})")
        print(f"✓ Worker process started (PID: {worker_process.pid})")
        return worker_process.pid
    
    # 启动初始 Worker
    start_worker_process()
    time.sleep(WORKER_STARTUP_WAIT)  # 等待 Worker 完全启动
    
    logger.info("Starting WebSocket Server process...")
    print("Starting WebSocket Server process...")
    ws_process = multiprocessing.Process(target=start_ws_server, name="WSServer")
    ws_process.start()
    
    logger.info("All processes started successfully")
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
                    logger.info("Worker exited normally, restarting...")
                    print(f"\n{'='*60}")
                    print("[INFO] Worker exited normally (UPDATE command)")
                    print("[INFO] Restarting Worker to clear module cache...")
                    print(f"{'='*60}\n")
                    
                    time.sleep(WORKER_RESTART_WAIT)  # 等待资源释放
                    start_worker_process()
                    time.sleep(WORKER_STARTUP_WAIT)  # 等待 Worker 完全启动
                    
                    logger.info("Worker restarted successfully")
                    print(f"\n{'='*60}")
                    print("✓ Worker restarted successfully")
                    print("✓ Module cache cleared")
                    print("✓ Ready to accept START command")
                    print(f"{'='*60}\n")
                else:
                    # 异常退出
                    logger.error(f"Worker crashed with exit code {exit_code}")
                    print(f"\n{'='*60}")
                    print(f"[ERROR] Worker crashed with exit code {exit_code}")
                    print("[ERROR] System will exit. Please check logs.")
                    print(f"{'='*60}\n")
                    break
            
            # 检查 WS Server 进程状态
            if not ws_process.is_alive():
                logger.error("Socket.IO Server process died unexpectedly")
                print("\n[ERROR] Socket.IO Server process died unexpectedly")
                break
            
            # 短暂休眠，避免 CPU 占用
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        print("\n\nShutting down...")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        print(f"\n\n[ERROR] Unexpected error: {e}")
    finally:
        # 终止进程
        logger.info("Terminating processes...")
        print("  ├─ Terminating Socket.IO Server...")
        ws_process.terminate()
        
        if worker_process:
            print("  ├─ Terminating Worker...")
            worker_process.terminate()
        
        # 等待进程结束
        ws_process.join(timeout=PROCESS_SHUTDOWN_TIMEOUT)
        if worker_process:
            worker_process.join(timeout=PROCESS_SHUTDOWN_TIMEOUT)
        
        # 强制终止未结束的进程
        if ws_process.is_alive():
            logger.warning("Killing Socket.IO Server process")
            print("  ├─ Killing Socket.IO Server process")
            ws_process.kill()
        
        if worker_process and worker_process.is_alive():
            logger.warning("Killing Worker process")
            print("  ├─ Killing Worker process")
            worker_process.kill()
        
        logger.info("Shutdown complete")
        print("  └─ Shutdown complete\n")


if __name__ == '__main__':
    # 设置启动方法（macOS需要）
    multiprocessing.set_start_method('spawn', force=True)
    main()

