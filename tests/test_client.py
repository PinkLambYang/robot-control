"""WebSocket客户端测试"""
import asyncio
import json
import base64
import zipfile
import io
from pathlib import Path
import websockets


async def test_client():
    """测试WebSocket客户端"""
    uri = "ws://localhost:8000/ws"
    
    print(f"Connecting to {uri}...")
    
    async with websockets.connect(uri) as websocket:
        print("Connected!")
        
        # 测试1: 发送UPDATE指令
        print("\n--- Test 1: UPDATE command ---")
        
        # 创建一个简单的Python项目zip
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            # 添加main.py
            main_py = """
class RobotController:
    def __init__(self):
        self.name = "TestRobot"
        print("RobotController initialized")
    
    def stand_up(self):
        print("Robot standing up...")
        return {"status": "standing", "message": "Successfully stood up"}
    
    def sit_down(self):
        print("Robot sitting down...")
        return {"status": "sitting", "message": "Successfully sat down"}

# 创建全局实例
robot_controller = RobotController()
"""
            zf.writestr('main.py', main_py)
        
        zip_data = zip_buffer.getvalue()
        zip_b64 = base64.b64encode(zip_data).decode('utf-8')
        
        update_cmd = {
            "command": "update",
            "data": zip_b64
        }
        
        await websocket.send(json.dumps(update_cmd))
        response = await websocket.recv()
        print(f"Response: {response}")
        
        # 测试2: 发送START指令
        print("\n--- Test 2: START command ---")
        start_cmd = {
            "command": "start"
        }
        
        await websocket.send(json.dumps(start_cmd))
        response = await websocket.recv()
        print(f"Response: {response}")
        
        # 测试3: 发送PROCESS指令
        print("\n--- Test 3: PROCESS command (stand_up) ---")
        process_cmd = {
            "command": "process",
            "params": {
                "object": "robot_controller",
                "method": "stand_up",
                "args": {}
            }
        }
        
        await websocket.send(json.dumps(process_cmd))
        response = await websocket.recv()
        print(f"Response: {response}")
        
        # 等待回调
        print("Waiting for callback...")
        try:
            callback = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Callback: {callback}")
        except asyncio.TimeoutError:
            print("No callback received (timeout)")
        
        # 测试4: 再次调用process
        print("\n--- Test 4: PROCESS command (sit_down) ---")
        process_cmd = {
            "command": "process",
            "params": {
                "object": "robot_controller",
                "method": "sit_down",
                "args": {}
            }
        }
        
        await websocket.send(json.dumps(process_cmd))
        response = await websocket.recv()
        print(f"Response: {response}")
        
        # 等待回调
        try:
            callback = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Callback: {callback}")
        except asyncio.TimeoutError:
            print("No callback received (timeout)")
        
        print("\n--- All tests completed ---")


if __name__ == '__main__':
    asyncio.run(test_client())

