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
import time

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
        
        # 初始化容器引用
        self._container = None
        try:
            if container_id:
                self._container = self.docker_client.get_container(container_id)
                logger.info(f"组件 {component_id} 成功获取到容器引用: {container_id[:12]}")
        except Exception as e:
            logger.warning(f"获取容器对象失败: {str(e)}")
    
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
            # 对注入的代码进行缩进处理，确保在try块内正确缩进
            indented_code = ""
            for line in code.splitlines():
                indented_code += "    " + line + "\n"  # 添加4个空格的缩进
            
            # 将代码包装在一个临时文件中，确保不会干扰用户代码中的result变量
            wrapped_code = f"""
import json
import traceback
import sys

try:
    # 重定向标准输出到字符串IO，抑制中间过程的打印输出
    import io
    import sys
    original_stdout = sys.stdout
    sys.stdout = io.StringIO()
    
    # 用户代码开始
{indented_code}
    # 用户代码结束
    
    # 获取包含所有print输出的缓冲区内容
    buffer_content = sys.stdout.getvalue()
    
    # 恢复标准输出
    sys.stdout = original_stdout
    
    # 寻找输出中的JSON标记部分
    json_content = None
    for marker_pair in [
        ("----数据集JSON开始----", "----数据集JSON结束----"),
        ("----DEFAULT_JSON_RESULT----", "----DEFAULT_JSON_END----")
    ]:
        start_marker, end_marker = marker_pair
        if start_marker in buffer_content and end_marker in buffer_content:
            start_idx = buffer_content.find(start_marker) + len(start_marker)
            end_idx = buffer_content.find(end_marker, start_idx)
            if start_idx > 0 and end_idx > start_idx:
                json_content = buffer_content[start_idx:end_idx].strip()
                # 只输出找到的JSON数据
                print(json_content)
                break
    
    # 如果没有找到有效的JSON数据输出，则尝试查找其他有效JSON
    if not json_content:
        # 寻找输出中任何有效的JSON对象
        for line in buffer_content.split('\\n'):
            if line.strip().startswith('{') and line.strip().endswith('}'):
                try:
                    json.loads(line.strip())  # 验证是否为有效JSON
                    print(line.strip())  # 有效则输出
                    break
                except:
                    pass
    
    # 打印结果 - 只有在未在用户代码中处理输出时使用
    if 'result' not in locals() and '_result_output' not in locals() and not json_content:
        print(json.dumps({{'success': True, 'result': None}}))

except Exception as e:
    error_message = str(e)
    error_traceback = traceback.format_exc()
    print(json.dumps({{'success': False, 'error': error_message, 'traceback': error_traceback}}))
"""
            
            # 检查容器状态，如果未运行则启动
            try:
                container = self.docker_client.get_container(self.container_id)
                if container.status != 'running':
                    logger.info(f"容器 {self.container_id} 未运行，当前状态: {container.status}，尝试启动容器")
                    start_result = self.docker_client.start_container(self.container_id)
                    if not start_result.get('status') == 'running':
                        return {
                            'success': False,
                            'error': f"无法启动容器，状态: {container.status}",
                            'traceback': "容器未运行且无法启动"
                        }
                    logger.info(f"容器 {self.container_id} 已成功启动")
                    # 短暂等待容器初始化
                    time.sleep(2)
            except Exception as e:
                logger.error(f"检查或启动容器时出错: {str(e)}")
                return {
                    'success': False,
                    'error': f"检查或启动容器时出错: {str(e)}",
                    'traceback': traceback.format_exc()
                }
            
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
                logger.info(f"容器命令执行成功，输出长度: {len(output)}")
                
                # 调试级别的日志，不会输出到控制台
                if output and logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"容器输出前50字符: {output[:50]}")
                    
                # 尝试从输出中提取JSON
                json_output = None
                # 初始化json_candidates变量，避免后续使用前未定义的错误
                json_candidates = []
                
                # 直接尝试解析容器输出的内容
                try:
                    json_output = json.loads(output.strip())
                    logger.info("成功直接解析容器输出的JSON")
                    return {
                        'success': True,
                        'result': json_output
                    }
                except json.JSONDecodeError:
                    # 如果不是单个JSON对象，则继续尝试提取
                    pass
                
                # 首先尝试从标记中提取JSON
                start_markers = ["----数据集JSON开始----", "----DEFAULT_JSON_RESULT----"]
                end_markers = ["----数据集JSON结束----", "----DEFAULT_JSON_END----"]
                
                json_between_markers = None
                for start_marker in start_markers:
                    if start_marker in output:
                        start_index = output.find(start_marker) + len(start_marker)
                        # 找到对应的结束标记
                        for end_marker in end_markers:
                            if end_marker in output[start_index:]:
                                end_index = output.find(end_marker, start_index)
                                if end_index > start_index:
                                    json_between_markers = output[start_index:end_index].strip()
                                    logger.debug(f"从标记中提取到JSON: {json_between_markers[:50]}...")
                                    try:
                                        json_output = json.loads(json_between_markers)
                                        logger.info(f"成功解析标记间的JSON数据, keys: {list(json_output.keys())}")
                                        break
                                    except json.JSONDecodeError:
                                        logger.warning(f"从标记中提取的内容不是有效的JSON: {json_between_markers[:100]}")
                                        json_between_markers = None
                        if json_output:
                            break
                
                # 如果没有从标记中找到JSON，则尝试从行中查找JSON
                if not json_output:
                    # 从输出中查找JSON结构
                    json_candidates = []
                    for line in output.split('\n'):
                        line = line.strip()
                        if line and line.startswith('{') and line.endswith('}'):
                            try:
                                json_obj = json.loads(line)
                                logger.debug(f"找到JSON候选行: {line[:50]}...")
                                json_candidates.append((line, json_obj))
                            except json.JSONDecodeError:
                                continue
                
                # 记录找到的JSON候选项
                if json_candidates:
                    logger.debug(f"从容器输出中找到 {len(json_candidates)} 个JSON候选项")
                    
                    # 优先选择包含dataset、result或特定数据结构的JSON
                    for candidate, obj in json_candidates:
                        if 'dataset' in obj or 'result' in obj or ('success' in obj and obj['success'] is True):
                            logger.debug(f"选择了合适的JSON: {candidate[:50]}...")
                            json_output = obj
                            break
                    
                    # 如果没找到特定格式，使用最后一个JSON
                    if not json_output and json_candidates:
                        json_output = json_candidates[-1][1]
                        logger.debug(f"使用最后一个JSON: {json_candidates[-1][0][:50]}...")
                
                # 如果找到有效JSON，返回它
                if json_output:
                    logger.info(f"返回有效JSON结果: {str(json_output)[:100]}...")
                    
                    # 限制返回的dataset数据大小
                    if isinstance(json_output, dict) and 'dataset' in json_output:
                        # 保持完整result用于内部处理，但限制返回的数据大小
                        return {
                            'success': True,
                            'result': json_output,
                            'truncated': True
                        }
                    elif isinstance(json_output, dict) and 'error' in json_output:
                        # 返回错误信息
                        return {
                            'success': False,
                            'error': json_output.get('error', '未知错误'),
                            'traceback': json_output.get('traceback', '')
                        }
                    
                    return {
                        'success': True,
                        'result': json_output
                    }
                
                # 如果没有找到JSON但命令成功执行
                if exec_result.get('exit_code', 0) == 0:
                    # 没有JSON输出但命令执行成功的情况下
                    logger.warning("容器命令执行成功，但未找到有效的JSON输出")
                    
                    # 检查是否有其他输出
                    if output and output.strip():
                        # 有文本输出但不是有效JSON
                        return {
                            'success': True,
                            'result': {'text_output': output[:1000]},  # 返回前1000个字符
                            'raw_output': output
                        }
                    else:
                        # 完全没有输出
                        logger.error("容器执行成功但没有任何输出")
                        return {
                            'success': False,
                            'error': '组件未产生任何输出',
                            'traceback': '检查组件代码是否正确输出JSON格式结果'
                        }
                        
                return {
                    'success': False,
                    'error': '无法从容器输出中解析JSON',
                    'traceback': output[:1000]  # 包含部分stdout协助调试
                }
            else:
                # 记录错误详情
                error_output = exec_result.get('output', '')
                logger.error(f"容器命令执行失败，退出码: {exec_result.get('exit_code')}")
                logger.error(f"错误输出: {error_output[:500]}")  # 只记录前500字符
                
                return {
                    'success': False,
                    'error': f"执行失败，退出码: {exec_result.get('exit_code')}",
                    'output': error_output
                }
                
        except Exception as e:
            logger.error(f"在容器中执行代码时出错: {str(e)}")
            return {
                'success': False,
                'error': f"执行容器代码时发生异常: {str(e)}",
                'traceback': traceback.format_exc()
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
