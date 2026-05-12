@echo off
chcp 65001 > nul

rem 设置窗口标题
title KOOK Image Compression Client

rem 显示启动信息
echo =======================================
echo KOOK Image Compression Client 启动器
echo =======================================
echo.
echo 正在启动图片压缩客户端...
echo.

rem 检查Python是否可用
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python环境!
    echo 请确保已正确安装Python 3.x
    echo.
    pause
    exit /b 1
)

rem 检查client.py是否存在
if not exist "client.py" (
    echo 错误: 未找到client.py文件!
    echo 请确保在正确的目录中运行此脚本
    echo.
    pause
    exit /b 1
)

rem 启动客户端
echo 启动中...
python client.py

rem 检查启动是否成功
if %errorlevel% neq 0 (
    echo.
    echo 错误: 客户端启动失败!
    echo 请检查是否安装了所有依赖项
    echo 可尝试运行: python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

rem 启动成功
echo.
echo 客户端已关闭
pause
