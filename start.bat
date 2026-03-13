@echo off
chcp 65001 >nul
title 实战量化交易平台

echo ============================================================
echo 🚀 实战量化交易平台启动中...
echo ============================================================
echo.

cd /d "%~dp0实战量化交易平台"

if not exist "app\首页.py" (
    echo ❌ 错误: 找不到主程序文件 app\首页.py
    pause
    exit /b 1
)

echo 项目目录: %CD%
echo 主程序: app\首页.py
echo ============================================================
echo.

python -m streamlit run app\首页.py --server.port=8501 --server.address=localhost

if errorlevel 1 (
    echo.
    echo ❌ 启动失败，请检查是否已安装所需依赖
    echo 运行: pip install -r requirements.txt
    pause
)
