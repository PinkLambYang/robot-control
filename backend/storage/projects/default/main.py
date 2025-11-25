"""机器人控制器 - 内置控制方法"""
import logging
import subprocess
import time
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)

# push_message 函数将由 PythonExecutor 注入到模块的全局命名空间
# 用户代码可以通过调用 push_message(event, data) 来主动推送消息到前端
push_message = None


class RobotController:
    """机器人控制器
    
    包含所有机器人控制方法的内置实现。
    当前所有方法都是TODO占位符，待实际硬件集成时实现。
    """
    
    def __init__(self):
        """初始化机器人控制器"""
        self.current_mode = "idle"
        self.recognition_thread = None
        self.recognition_running = False
        self._lock = threading.Lock()  # 线程锁，保护共享状态
        
        # DDS Client 管理
        self.dds_process = None
        self.dds_running = False
        self.dds_path = "/home/noetix/work/dds_client_release/dds_bridge"
    
    def start_dds_client(self) -> Dict[str, Any]:
        """启动 DDS Client
        
        Returns:
            执行结果
        """
        try:
            # 检查是否已经在运行
            if self.dds_running and self.dds_process and self.dds_process.poll() is None:
                return {
                    "status": "warning",
                    "message": "DDS Client 已经在运行",
                    "pid": self.dds_process.pid
                }
            
            # 检查系统中是否有其他 dds_bridge 进程
            check_result = subprocess.run(
                ['pgrep', '-f', 'dds_bridge'],
                capture_output=True
            )
            
            if check_result.returncode == 0:
                self.dds_running = True
                pid = check_result.stdout.decode().strip()
                return {
                    "status": "success",
                    "message": "DDS Client 已在系统中运行",
                    "pid": pid
                }
            
            # 检查文件是否存在
            import os
            if not os.path.exists(self.dds_path):
                return {
                    "status": "error",
                    "message": f"DDS Bridge 文件不存在: {self.dds_path}"
                }
            
            # 启动 DDS bridge
            logger.info(f"Starting DDS bridge: {self.dds_path}")
            self.dds_process = subprocess.Popen(
                ['sudo', self.dds_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 等待启动
            time.sleep(1)
            
            # 检查是否成功启动
            if self.dds_process.poll() is not None:
                stderr = self.dds_process.stderr.read().decode()
                return {
                    "status": "error",
                    "message": "DDS Client 启动失败",
                    "error": stderr
                }
            
            self.dds_running = True
            logger.info(f"DDS bridge started (PID: {self.dds_process.pid})")
            
            return {
                "status": "success",
                "message": "DDS Client 启动成功",
                "pid": self.dds_process.pid
            }
            
        except Exception as e:
            logger.error(f"Failed to start DDS client: {e}")
            return {
                "status": "error",
                "message": f"启动 DDS Client 失败: {str(e)}"
            }
    
    def stop_dds_client(self) -> Dict[str, Any]:
        """停止 DDS Client
        
        Returns:
            执行结果
        """
        try:
            # 先尝试用 SIGTERM 优雅停止
            try:
                result = subprocess.run(
                    ['sudo', 'pkill', '-f', 'dds_bridge'],
                    capture_output=True,
                    timeout=5
                )
                logger.info(f"sudo pkill (SIGTERM) result: return code {result.returncode}")
            except subprocess.TimeoutExpired:
                logger.warning("sudo pkill timeout")
            except Exception as e:
                logger.error(f"sudo pkill failed: {e}")
            
            # 等待一下让进程有时间退出
            time.sleep(0.5)
            
            # 再用 SIGKILL 强制终止所有残留进程
            try:
                result = subprocess.run(
                    ['sudo', 'pkill', '-9', '-f', 'dds_bridge'],
                    capture_output=True,
                    timeout=5
                )
                logger.info(f"sudo pkill -9 (SIGKILL) result: return code {result.returncode}")
            except subprocess.TimeoutExpired:
                logger.warning("sudo pkill -9 timeout")
            except Exception as e:
                logger.error(f"sudo pkill -9 failed: {e}")
            
            # 清理本地进程对象
            if self.dds_process:
                try:
                    if self.dds_process.poll() is None:
                        self.dds_process.terminate()
                        self.dds_process.wait(timeout=1)
                except:
                    pass
                self.dds_process = None
            
            self.dds_running = False
            logger.info("DDS bridge stopped")
            
            return {
                "status": "success",
                "message": "DDS Client 已停止"
            }
                
        except Exception as e:
            logger.error(f"Failed to stop DDS client: {e}")
            self.dds_running = False  # 强制标记为已停止
            return {
                "status": "success",
                "message": "DDS Client 已停止"
            }
    
    def _check_dds_required(self) -> Dict[str, Any]:
        """检查 DDS 是否已启动（内部方法）
        
        Returns:
            如果 DDS 未启动，返回错误信息；否则返回 None
        """
        if not self.dds_running:
            return {
                "status": "error",
                "message": "请先启动 DDS Client 才能执行此操作"
            }
        return None
    
    def prepare_mode(self) -> Dict[str, Any]:
        """准备模式
        
        Returns:
            执行结果
        """
        # 检查 DDS 是否启动
        dds_check = self._check_dds_required()
        if dds_check:
            return dds_check
        
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=0 yaw=0 action=7 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        self.current_mode = "prepare"
        return {
            "status": "success",
            "message": "准备模式已激活",
            "mode": "prepare"
        }
    
    def walk_mode(self) -> Dict[str, Any]:
        """走路模式
        
        Returns:
            执行结果
        """
        # 检查 DDS 是否启动
        dds_check = self._check_dds_required()
        if dds_check:
            return dds_check
        
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=0 yaw=0 action=0 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        self.current_mode = "walk"
        return {
            "status": "success",
            "message": "走路模式已激活",
            "mode": "walk"
        }
    
    def run_mode(self) -> Dict[str, Any]:
        """跑步模式
        
        Returns:
            执行结果
        """
        # 检查 DDS 是否启动
        dds_check = self._check_dds_required()
        if dds_check:
            return dds_check
        
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=0 yaw=0 action=4 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        self.current_mode = "run"
        return {
            "status": "success",
            "message": "跑步模式已激活",
            "mode": "run"
        }
    
    def wave_hand(self) -> Dict[str, Any]:
        """打招呼动作
        
        Returns:
            执行结果
        """
        # 检查 DDS 是否启动
        dds_check = self._check_dds_required()
        if dds_check:
            return dds_check
        
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=0 yaw=0 action=1 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        return {
            "status": "success",
            "message": "打招呼动作已执行",
            "action": "wave_hand"
        }
    
    def shake_hand(self) -> Dict[str, Any]:
        """握手动作
        
        Returns:
            执行结果
        """
        # 检查 DDS 是否启动
        dds_check = self._check_dds_required()
        if dds_check:
            return dds_check
        
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=0 yaw=0 action=2 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        return {
            "status": "success",
            "message": "握手动作已执行",
            "action": "shake_hand"
        }
    
    def cheer(self) -> Dict[str, Any]:
        """欢呼动作
        
        Returns:
            执行结果
        """
        # 检查 DDS 是否启动
        dds_check = self._check_dds_required()
        if dds_check:
            return dds_check
        
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=0 yaw=0 action=3 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        return {
            "status": "success",
            "message": "欢呼动作已执行",
            "action": "cheer"
        }
    
    def move_up(self) -> Dict[str, Any]:
        """向上移动
        
        Returns:
            执行结果
        """
        # 检查 DDS 是否启动
        dds_check = self._check_dds_required()
        if dds_check:
            return dds_check
        
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=1 yaw=0 action=0 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        time.sleep(1)
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=0 yaw=0 action=0 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        return {
            "status": "success",
            "message": "向上移动已执行",
            "direction": "up"
        }
    
    def move_down(self) -> Dict[str, Any]:
        """向下移动
        
        Returns:
            执行结果
        """
        # 检查 DDS 是否启动
        dds_check = self._check_dds_required()
        if dds_check:
            return dds_check
        
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=-1 yaw=0 action=0 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        time.sleep(1)
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=0 yaw=0 action=0 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        return {
            "status": "success",
            "message": "向下移动已执行",
            "direction": "down"
        }
    
    def move_left(self) -> Dict[str, Any]:
        """向左移动
        
        Returns:
            执行结果
        """
        # 检查 DDS 是否启动
        dds_check = self._check_dds_required()
        if dds_check:
            return dds_check
        
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=0 yaw=1 action=0 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        time.sleep(1)
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=0 yaw=0 action=0 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        return {
            "status": "success",
            "message": "向左移动已执行",
            "direction": "left"
        }
    
    def move_right(self) -> Dict[str, Any]:
        """向右移动
        
        Returns:
            执行结果
        """
        # 检查 DDS 是否启动
        dds_check = self._check_dds_required()
        if dds_check:
            return dds_check
        
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=0 yaw=-1 action=0 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        time.sleep(1)
        p = subprocess.Popen(
            ["bash", "-lc", 'printf "move x=0 yaw=0 action=0 index=0\n" | nc -q 0 127.0.0.1 5566'],
            stdout=subprocess.DEVNULL,   # 不关心输出就丢掉
            stderr=subprocess.DEVNULL
        )
        return {
            "status": "success",
            "message": "向右移动已执行",
            "direction": "right"
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态
        
        Returns:
            当前状态信息
        """
        return {
            "status": "success",
            "current_mode": self.current_mode,
            "recognition_running": self.recognition_running,
            "dds_running": self.dds_running,
            "message": f"当前模式: {self.current_mode}"
        }
    
    def start_recognition(self) -> Dict[str, Any]:
        """开始识别

        启动一个后台线程，模拟持续的识别过程，实时推送识别结果到前端

        Returns:
            执行结果
        """
        with self._lock:
            if self.recognition_running:
                return {
                    "status": "error",
                    "message": "识别已经在运行中"
                }

            # 启动识别线程
            self.recognition_running = True
            self.recognition_thread = threading.Thread(target=self._recognition_worker, daemon=True)
            self.recognition_thread.start()

        return {
            "status": "success",
            "message": "识别已启动"
        }
    
    def stop_recognition(self) -> Dict[str, Any]:
        """结束识别

        停止识别线程

        Returns:
            执行结果
        """
        with self._lock:
            if not self.recognition_running:
                return {
                    "status": "error",
                    "message": "识别未在运行"
                }

            # 停止识别
            self.recognition_running = False
            thread_to_join = self.recognition_thread

        # 在锁外等待线程结束，避免死锁
        if thread_to_join:
            thread_to_join.join(timeout=2)

        with self._lock:
            self.recognition_thread = None

        return {
            "status": "success",
            "message": "识别已停止"
        }
    
    def stop(self):
        """WebSocket 断开时自动调用，停止后台线程和 DDS"""
        logger.info("Stopping background threads and DDS...")
        try:
            # 停止识别线程
            if self.recognition_running:
                self.stop_recognition()
            
            # 停止 DDS client
            if self.dds_running:
                self.stop_dds_client()
        except Exception as e:
            logger.error(f"Error stopping threads: {e}")
    
    def _recognition_worker(self):
        """识别工作线程
        
        模拟持续的识别过程，每隔一段时间推送一次识别结果
        在实际应用中，这里应该是真实的识别逻辑（如图像识别、语音识别等）
        """
        recognition_count = 0
        
        # 模拟识别对象列表
        objects = ['球', '障碍物', '目标点', '人', '墙壁']
        
        try:
            while self.recognition_running:
                recognition_count += 1
                
                # 模拟识别结果（在实际应用中，这里应该是真实的识别逻辑）
                import random
                detected_object = random.choice(objects)
                confidence = random.uniform(0.7, 0.99)
                
                # 推送识别结果
                if push_message:
                    push_message('recognition_result', {
                        'count': recognition_count,
                        'timestamp': time.time(),
                        'object': detected_object,
                        'confidence': round(confidence, 2),
                        'position': {
                            'x': random.randint(0, 100),
                            'y': random.randint(0, 100)
                        }
                    })
                
                # 每秒识别一次（实际应用中可以根据需要调整）
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Recognition worker error: {e}")


# 创建全局实例
robot_controller = RobotController()
