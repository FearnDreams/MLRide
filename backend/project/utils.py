"""
项目工具函数模块

提供项目管理相关的工具函数
"""

import os
import re
import logging

logger = logging.getLogger(__name__)

def fix_jupyter_config_syntax(config_file_path):
    """
    修复Jupyter配置文件中的语法错误
    
    Args:
        config_file_path (str): 配置文件路径
        
    Returns:
        bool: 修复是否成功
    """
    try:
        if not os.path.exists(config_file_path):
            logger.warning(f"配置文件不存在: {config_file_path}")
            return False
            
        # 尝试多种编码方式读取配置文件内容
        content = None
        encoding_used = None
        
        for encoding in ['utf-8', 'gbk', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                with open(config_file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                encoding_used = encoding
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            logger.error(f"无法读取配置文件，所有编码尝试均失败: {config_file_path}")
            return False
        
        original_content = content
        
        # 修复P3P头中的双引号语法错误
        # 模式1: "P3P": "CP="ALL DSP COR PSAa PSDa OUR NOR ONL UNI COM NAV""
        pattern1 = r'"P3P":\s*"CP="([^"]+)""'
        replacement1 = r'"P3P": "CP=\'\1\'"'
        content = re.sub(pattern1, replacement1, content)
        
        # 模式2: "P3P": "CP=\"ALL DSP COR PSAa PSDa OUR NOR ONL UNI COM NAV\""
        pattern2 = r'"P3P":\s*"CP=\\"([^"]+)\\""'
        replacement2 = r'"P3P": "CP=\'\1\'"'
        content = re.sub(pattern2, replacement2, content)
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(config_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"已修复Jupyter配置文件语法错误: {config_file_path} (使用编码: {encoding_used})")
            return True
        else:
            logger.info(f"Jupyter配置文件无需修复: {config_file_path}")
            return True
            
    except Exception as e:
        logger.error(f"修复Jupyter配置文件时出错: {str(e)}")
        return False

def cleanup_workspace_jupyter_configs(workspace_dir):
    """
    清理工作空间中所有Jupyter配置文件的语法错误
    
    Args:
        workspace_dir (str): 工作空间目录路径
        
    Returns:
        int: 修复的文件数量
    """
    fixed_count = 0
    
    try:
        # 查找所有jupyter_notebook_config.py文件
        for root, dirs, files in os.walk(workspace_dir):
            for file in files:
                if file == 'jupyter_notebook_config.py':
                    config_path = os.path.join(root, file)
                    if fix_jupyter_config_syntax(config_path):
                        fixed_count += 1
                        
        logger.info(f"在工作空间 {workspace_dir} 中修复了 {fixed_count} 个Jupyter配置文件")
        return fixed_count
        
    except Exception as e:
        logger.error(f"清理工作空间Jupyter配置时出错: {str(e)}")
        return fixed_count

def force_kill_jupyter_processes():
    """
    强制终止所有Jupyter进程
    
    Returns:
        bool: 操作是否成功
    """
    try:
        import subprocess
        
        if os.name == 'nt':  # Windows
            # 查找并终止所有jupyter进程
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'jupyter' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            pid = parts[1]
                            try:
                                subprocess.run(['taskkill', '/F', '/PID', pid], 
                                             capture_output=True)
                                logger.info(f"强制终止Jupyter进程: PID={pid}")
                            except Exception as e:
                                logger.warning(f"终止进程失败: PID={pid}, 错误: {str(e)}")
        else:  # Unix-like
            # 使用pkill终止jupyter进程
            subprocess.run(['pkill', '-f', 'jupyter'], capture_output=True)
            logger.info("已尝试终止所有Jupyter进程")
            
        return True
        
    except Exception as e:
        logger.error(f"强制终止Jupyter进程时出错: {str(e)}")
        return False 