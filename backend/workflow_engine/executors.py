"""
工作流组件执行器

该模块定义了组件执行器的基类和执行结果类，用于执行工作流中的各类组件。
"""

import logging
import json
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from container.docker_ops import DockerClient

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """组件执行结果
    
    表示组件执行的结果，包括执行是否成功、输出数据、错误信息等。
    """
    success: bool = False
    outputs: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    logs: List[str] = field(default_factory=list)


class BaseComponentExecutor(ABC):
    """组件执行器基类
    
    所有组件执行器必须继承此类并实现execute方法。
    """
    
    def __init__(self, component_id: str, component_type: str, container_id: str):
        """
        初始化组件执行器
        
        Args:
            component_id: 组件ID
            component_type: 组件类型
            container_id: 容器ID
        """
        self.component_id = component_id
        self.component_type = component_type
        self.container_id = container_id
        self.docker_client = DockerClient()
    
    @abstractmethod
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        执行组件
        
        Args:
            inputs: 输入数据，格式为 {端口ID: 数据}
            parameters: 组件参数
            
        Returns:
            ExecutionResult: 执行结果
        """
        pass
    
    def execute_in_container(self, code: str) -> Dict[str, Any]:
        """
        在容器中执行代码
        
        Args:
            code: 要执行的Python代码
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            # 将代码包装在一个临时文件中
            wrapped_code = f"""
import json
import traceback
import sys

try:
    # 用户代码开始
{code}
    # 用户代码结束
    
    # 打印结果
    if 'result' in locals():
        print(json.dumps({{'success': True, 'result': result}}))
    else:
        print(json.dumps({{'success': True, 'result': None}}))
except Exception as e:
    error_message = str(e)
    error_traceback = traceback.format_exc()
    print(json.dumps({{'success': False, 'error': error_message, 'traceback': error_traceback}}))
"""
            
            # 在容器中执行代码
            exec_result = self.docker_client.exec_in_container(
                container_id=self.container_id,
                cmd=['python', '-c', wrapped_code],
                workdir='/workspace'
            )
            
            # 解析执行结果
            if exec_result.get('exit_code') == 0:
                # 尝试解析输出为JSON
                output = exec_result.get('output', '')
                try:
                    result = json.loads(output)
                    return result
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'error': '无法解析执行结果',
                        'output': output
                    }
            else:
                return {
                    'success': False,
                    'error': f"执行失败，退出码: {exec_result.get('exit_code')}",
                    'output': exec_result.get('output', '')
                }
                
        except Exception as e:
            logger.error(f"在容器中执行代码时出错: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }


class PythonScriptExecutor(BaseComponentExecutor):
    """Python脚本执行器
    
    执行自定义Python脚本，用于实现自定义逻辑。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        执行Python脚本
        
        Args:
            inputs: 输入数据
            parameters: 组件参数，必须包含'script'字段
            
        Returns:
            ExecutionResult: 执行结果
        """
        try:
            # 获取脚本代码
            script = parameters.get('script', '')
            if not script:
                return ExecutionResult(
                    success=False,
                    error_message="脚本代码为空"
                )
            
            # 将输入数据转换为变量定义代码
            input_code = ""
            for port_id, value in inputs.items():
                # 将变量转换为JSON字符串，然后在Python中加载
                input_code += f"{port_id} = json.loads('''{json.dumps(value)}''')\n"
            
            # 组合代码
            code = f"""
# 导入库
import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from sklearn import preprocessing, model_selection, metrics
import io
import base64

# 定义输入变量
{input_code}

# 用户脚本
{script}
"""
            
            # 在容器中执行代码
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                return ExecutionResult(
                    success=True,
                    outputs={'result': result.get('result')},
                    logs=["脚本执行成功"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '未知错误'),
                    logs=[result.get('output', ''), result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行Python脚本时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e),
                logs=[traceback.format_exc()]
            )
