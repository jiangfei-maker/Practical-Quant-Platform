import os
import sys
import subprocess
from pathlib import Path

def main():
    project_root = Path(__file__).parent
    app_dir = project_root / "实战量化交易平台"
    
    if not app_dir.exists():
        print(f"错误: 找不到项目目录 {app_dir}")
        sys.exit(1)
    
    main_py = app_dir / "app" / "首页.py"
    if not main_py.exists():
        print(f"错误: 找不到主程序文件 {main_py}")
        sys.exit(1)
    
    os.chdir(app_dir)
    
    print("=" * 60)
    print("🚀 实战量化交易平台启动中...")
    print("=" * 60)
    print(f"项目目录: {app_dir}")
    print(f"主程序: {main_py}")
    print("=" * 60)
    print()
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(main_py),
            "--server.port=8501",
            "--server.address=localhost",
            "--theme.base=dark"
        ], check=True)
    except KeyboardInterrupt:
        print("\n\n👋 程序已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
