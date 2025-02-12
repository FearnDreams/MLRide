#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """
    Django 命令行工具的入口函数。

    此函数负责配置 Django 环境并执行命令行管理任务。
    """
    # 设置 Django 的 settings 模块环境变量。
    # 'DJANGO_SETTINGS_MODULE' 环境变量告诉 Django 使用哪个 settings 文件。
    # 在这里，我们设置为 'mlride.settings'，即项目 mlride 目录下的 settings.py 文件。
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mlride.settings")
    try:
        # 尝试导入 Django 的命令行执行工具函数 execute_from_command_line。
        # 这个函数负责解析命令行参数并执行相应的 Django 管理命令，例如 runserver, migrate 等。
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # 如果 ImportError 异常被捕获，说明 Django 库没有被正确安装或添加到 Python 路径中。
        # 抛出一个更友好的 ImportError 异常，提示用户检查 Django 是否已安装，
        # 以及是否激活了虚拟环境或者 PYTHONPATH 环境变量是否配置正确。
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # 执行 Django 命令行工具。
    # sys.argv 是 Python 解释器接收到的命令行参数列表，
    # execute_from_command_line 函数会解析这些参数并执行相应的 Django 命令。
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
