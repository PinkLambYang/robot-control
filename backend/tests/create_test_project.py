"""创建测试项目zip文件"""
import zipfile
from pathlib import Path


def create_python_test_project():
    """创建Python测试项目"""
    output_path = Path('test_python_project.zip')
    
    with zipfile.ZipFile(output_path, 'w') as zf:
        # main.py
        main_py = f"""
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


if __name__ == '__main__':
    print("Creating test projects...\n")
    
    # 创建Python测试项目
    python_zip = create_python_test_project()
    
    print("\n" + "="*60)
    print("Test projects created!")
    print("="*60)
    print(f"\nPython project: {python_zip}")
    print("\nYou can use these files with the test_client.py script")

