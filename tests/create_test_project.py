"""创建测试项目zip文件"""
import zipfile
from pathlib import Path


def create_python_test_project():
    """创建Python测试项目"""
    output_path = Path('test_python_project.zip')
    
    with zipfile.ZipFile(output_path, 'w') as zf:
        # main.py
        main_py = """
# 机器人控制器示例

class SportClient:
    def __init__(self):
        self.status = "initialized"
        print("SportClient initialized")
    
    def StandUp(self):
        print("Executing StandUp command...")
        self.status = "standing"
        return {"action": "stand_up", "status": "success"}
    
    def Damp(self):
        print("Executing Damp command...")
        self.status = "damping"
        return {"action": "damp", "status": "success"}
    
    def Walk(self, speed=1.0, direction="forward"):
        print(f"Walking {direction} at speed {speed}...")
        return {"action": "walk", "speed": speed, "direction": direction}

# 创建全局实例
sport_client = SportClient()

def init():
    print("Project initialized!")
"""
        zf.writestr('main.py', main_py)
    
    print(f"Created: {output_path}")
    return output_path


def create_cpp_test_project():
    """创建C++测试项目（需要预编译的可执行文件）"""
    output_path = Path('test_cpp_project.zip')
    
    # 注意：这里只是示例，实际需要真实的可执行文件
    print("Note: C++ project needs pre-compiled executable file")
    print("Please compile your C++ project first and add the executable to the zip")
    
    # 示例C++代码
    cpp_code = """
#include <iostream>
#include <thread>
#include <chrono>

int main() {
    std::cout << "Robot C++ Controller Started" << std::endl;
    
    // 模拟机器人控制循环
    for (int i = 0; i < 10; i++) {
        std::cout << "Step " << i << std::endl;
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
    
    std::cout << "Robot Controller Stopped" << std::endl;
    return 0;
}
"""
    
    print("\nExample C++ code:")
    print(cpp_code)
    print("\nCompile with: g++ -o robot_controller main.cpp -pthread")
    
    return None


if __name__ == '__main__':
    print("Creating test projects...\n")
    
    # 创建Python测试项目
    python_zip = create_python_test_project()
    
    print("\n" + "="*60)
    print("Test projects created!")
    print("="*60)
    print(f"\nPython project: {python_zip}")
    print("\nYou can use these files with the test_client.py script")

