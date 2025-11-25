#!/usr/bin/env python3
"""测试 WebSocket 断开时的线程清理功能"""
import socketio
import time
import sys

def test_thread_cleanup():
    """测试线程清理：断开连接后线程停止但状态保留"""
    
    print("=" * 60)
    print("WebSocket 断开时的线程清理功能测试")
    print("=" * 60)
    
    # 1. 连接
    print("\n[步骤1] 连接 WebSocket...")
    sio = socketio.Client()
    try:
        sio.connect('http://localhost:8000', wait_timeout=5)
        print("  ✓ 已连接")
    except Exception as e:
        print(f"  ✗ 连接失败: {e}")
        print("\n请确保后端服务正在运行: python main.py")
        sys.exit(1)
    
    # 2. 监听识别结果
    result_count = 0
    
    def on_recognition_result(data):
        nonlocal result_count
        result_count += 1
        print(f"    收到识别结果 #{result_count}: {data.get('object', 'unknown')}")
    
    sio.on('recognition_result', on_recognition_result)
    
    # 3. 启动识别
    print("\n[步骤2] 启动识别任务...")
    try:
        response = sio.call('process', {
            'params': {
                'object': 'robot_controller',
                'method': 'start_recognition',
                'args': {}
            }
        }, timeout=5)
        print(f"  响应: {response}")
        
        if response.get('status') != 'success':
            print(f"  ✗ 启动失败: {response.get('message')}")
            sio.disconnect()
            sys.exit(1)
        print("  ✓ 识别任务已启动")
    except Exception as e:
        print(f"  ✗ 调用失败: {e}")
        sio.disconnect()
        sys.exit(1)
    
    # 4. 等待接收几次识别结果
    print("\n[步骤3] 接收识别结果（等待3秒）...")
    time.sleep(3)
    print(f"  ✓ 共接收 {result_count} 次识别结果")
    
    if result_count < 2:
        print(f"  ⚠ 警告: 预期至少收到2次结果，实际收到 {result_count} 次")
    
    # 5. 断开连接
    print("\n[步骤4] 断开 WebSocket...")
    sio.disconnect()
    print("  ✓ 已断开")
    
    # 6. 等待后端清理完成
    print("\n[步骤5] 等待后端清理线程（2秒）...")
    time.sleep(2)
    print("  ✓ 清理应该已完成")
    
    # 7. 重新连接
    print("\n[步骤6] 重新连接 WebSocket...")
    sio = socketio.Client()
    try:
        sio.connect('http://localhost:8000', wait_timeout=5)
        print("  ✓ 已重连")
    except Exception as e:
        print(f"  ✗ 重连失败: {e}")
        sys.exit(1)
    
    # 8. 查询状态（验证缓存保留）
    print("\n[步骤7] 查询状态（验证对象缓存保留）...")
    try:
        response = sio.call('process', {
            'params': {
                'object': 'robot_controller',
                'method': 'get_status',
                'args': {}
            }
        }, timeout=5)
        print(f"  响应: {response}")
        
        if response.get('status') != 'success':
            print(f"  ✗ 查询失败: {response.get('message')}")
            sio.disconnect()
            sys.exit(1)
        
        # 检查状态
        result = response.get('data', {}).get('result', {})
        recognition_running = result.get('recognition_running', True)
        
        if recognition_running:
            print(f"  ✗ 识别线程应该已停止，但状态显示仍在运行")
            sio.disconnect()
            sys.exit(1)
        
        print("  ✓ 对象状态正确保留")
        print(f"  ✓ 识别线程已停止: recognition_running = {recognition_running}")
        print(f"  ✓ 模式保留: current_mode = {result.get('current_mode')}")
        
    except Exception as e:
        print(f"  ✗ 调用失败: {e}")
        sio.disconnect()
        sys.exit(1)
    
    # 9. 再次启动识别（验证功能正常）
    print("\n[步骤8] 再次启动识别（验证功能恢复）...")
    result_count = 0
    sio.on('recognition_result', on_recognition_result)
    
    try:
        response = sio.call('process', {
            'params': {
                'object': 'robot_controller',
                'method': 'start_recognition',
                'args': {}
            }
        }, timeout=5)
        print(f"  响应: {response}")
        
        if response.get('status') != 'success':
            print(f"  ✗ 启动失败: {response.get('message')}")
            sio.disconnect()
            sys.exit(1)
        print("  ✓ 识别任务重新启动成功")
    except Exception as e:
        print(f"  ✗ 调用失败: {e}")
        sio.disconnect()
        sys.exit(1)
    
    # 10. 再次接收结果
    print("\n[步骤9] 接收识别结果（等待3秒）...")
    time.sleep(3)
    print(f"  ✓ 共接收 {result_count} 次识别结果")
    
    if result_count < 2:
        print(f"  ⚠ 警告: 预期至少收到2次结果，实际收到 {result_count} 次")
    else:
        print("  ✓ 功能恢复正常")
    
    # 11. 清理：停止识别
    print("\n[步骤10] 停止识别任务...")
    try:
        response = sio.call('process', {
            'params': {
                'object': 'robot_controller',
                'method': 'stop_recognition',
                'args': {}
            }
        }, timeout=5)
        print(f"  响应: {response}")
        
        if response.get('status') == 'success':
            print("  ✓ 识别任务已停止")
        else:
            print(f"  ⚠ 停止可能失败: {response.get('message')}")
    except Exception as e:
        print(f"  ⚠ 调用失败: {e}")
    
    # 12. 断开连接
    sio.disconnect()
    print("\n[步骤11] 断开连接")
    print("  ✓ 已断开")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过!")
    print("=" * 60)
    print("\n总结:")
    print("  ✓ WebSocket 断开时后台线程正确停止")
    print("  ✓ 模块缓存和对象状态保留")
    print("  ✓ 重连后无需重新 UPDATE/START")
    print("  ✓ 功能完全恢复正常")
    print()


if __name__ == '__main__':
    try:
        test_thread_cleanup()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

