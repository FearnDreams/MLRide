"""
数据输入和预处理组件执行器

该模块实现了数据输入和预处理相关的组件执行器，如数据加载、清洗、转换和特征工程等。
"""

import logging
import json
import traceback
import pandas as pd
import numpy as np
import os
from typing import Dict, Any, List
from .executors import BaseComponentExecutor, ExecutionResult

logger = logging.getLogger(__name__)

class CSVDataLoader(BaseComponentExecutor):
    """CSV数据加载器
    
    加载CSV格式的数据文件，并转换为数据集对象。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        加载CSV数据文件
        
        Args:
            inputs: 输入数据 (此组件通常无输入)
            parameters: 参数，包括:
                - file_path: 文件路径 (相对于项目工作区根目录, 例如: uploads/yourfile.csv)
                - separator: 分隔符 (例如: ',', ';')
                - has_header: 布尔值，指示CSV文件是否包含表头
                - index_col: (可选) 作为行索引的列号或列名
                
        Returns:
            ExecutionResult: 执行结果，包含加载的数据集
        """
        try:
            # 获取参数，与前端 componentDefinitions.ts 中的参数名对应
            file_path = parameters.get('file_path')  # 由文件上传API填充，或用户直接提供路径
            
            # 详细记录传入的参数值，协助调试
            logger.info(f"CSVDataLoader接收到的参数: {parameters}")
            logger.info(f"CSVDataLoader接收到的file_path: {file_path}, 类型: {type(file_path)}")
            
            # 尝试从多个可能的来源获取文件路径
            if file_path is None or (isinstance(file_path, dict) and not file_path):
                # 尝试从_file_info中获取serverPath
                if '_file_info' in parameters and parameters['_file_info']:
                    file_info = parameters['_file_info']
                    if isinstance(file_info, dict) and 'serverPath' in file_info:
                        file_path = file_info['serverPath']
                        logger.info(f"从_file_info.serverPath恢复file_path: {file_path}")
            
            # 最终检查文件路径
            if not file_path or not isinstance(file_path, str) or not file_path.strip():
                return ExecutionResult(
                    success=False,
                    error_message="未能找到有效的CSV文件路径。请确保已上传文件并重试。"
                )
                
            # 规范化文件路径：
            # 1. 将Windows反斜杠替换为正斜杠
            sanitized_file_path = file_path.replace('\\', '/')
            
            # 2. 移除开头多余的斜杠(如果存在)，防止路径被解释为绝对路径
            while sanitized_file_path.startswith('/'):
                sanitized_file_path = sanitized_file_path[1:]
                
            # 3. 移除重复的斜杠
            while '//' in sanitized_file_path:
                sanitized_file_path = sanitized_file_path.replace('//', '/')
            
            logger.info(f"准备加载CSV文件: {file_path} (清理后: {sanitized_file_path})")
            
            # 获取其他参数
            separator = parameters.get('separator', ',')  # 对应前端的 'separator'
            has_header = parameters.get('has_header', True)
            index_col_param = parameters.get('index_col', None)  # 如果前端未来支持此参数
            
            logger.info(f"分隔符: {separator}, 包含表头: {has_header}")
            
            # Pandas read_csv 的 header 参数：0表示第一行为表头，None表示无表头
            pandas_header_arg = 0 if has_header else None
            
            # 在执行容器代码前，尝试检查文件是否实际存在于上传目录
            workspace_path = os.environ.get('WORKSPACE_PATH', '/workspace')
            potential_abs_path = os.path.join(workspace_path, sanitized_file_path)
            
            # 记录环境信息，协助调试
            logger.info(f"当前工作空间路径: {workspace_path}")
            logger.info(f"尝试检查文件是否存在: {potential_abs_path}")
            
            # 检查容器对象是否可用
            container_id = None
            if hasattr(self, '_container') and self._container and hasattr(self._container, 'id'):
                container_id = self._container.id
                logger.info(f"使用容器ID: {container_id}")
            
            # 首先检查文件是否存在于宿主机
            file_exists = os.path.exists(potential_abs_path)
            if file_exists:
                logger.info(f"文件存在于宿主机，大小: {os.path.getsize(potential_abs_path)} 字节")
            else:
                # 检查当前目录结构
                try:
                    current_dir = os.path.dirname(potential_abs_path) or '.'
                    if os.path.exists(current_dir):
                        logger.info(f"目录 {current_dir} 存在，内容: {os.listdir(current_dir)}")
                    else:
                        logger.info(f"目录 {current_dir} 不存在")
                except Exception as dir_err:
                    logger.error(f"检查目录时出错: {str(dir_err)}")
            
            # 如果有容器，检查文件在容器中是否存在
            container_file_exists = False
            if container_id:
                try:
                    from container.docker_ops import DockerClient
                    docker_client = DockerClient()
                    
                    # 先检查容器中的文件目录结构
                    container_workspace = '/workspace'
                    exit_code, ls_output = docker_client.exec_command_in_container(
                        container_id, 
                        f"ls -la {container_workspace}"
                    )
                    logger.info(f"容器中/workspace目录内容: {ls_output[:200]}")
                    
                    # 检查uploads目录
                    uploads_dir = '/workspace/uploads'
                    exit_code, ls_output = docker_client.exec_command_in_container(
                        container_id, 
                        f"ls -la {uploads_dir} 2>/dev/null || echo '目录不存在'"
                    )
                    logger.info(f"容器中uploads目录内容: {ls_output[:200]}")
                    
                    # 检查容器中的文件是否存在
                    container_file_path = f"/workspace/{sanitized_file_path}"
                    exit_code, file_check = docker_client.exec_command_in_container(
                        container_id, 
                        f"test -f {container_file_path} && echo '文件存在' || echo '文件不存在'"
                    )
                    container_file_exists = "文件存在" in file_check
                    logger.info(f"容器中文件检查: {container_file_path}, 结果: {file_check.strip()}")
                    
                    # 如果文件不存在于容器，但存在于宿主机，则尝试复制
                    if not container_file_exists and file_exists:
                        # 确保容器中目标目录存在
                        container_dir = os.path.dirname(container_file_path)
                        if container_dir:
                            docker_client.exec_command_in_container(
                                container_id, 
                                f"mkdir -p {container_dir}"
                            )
                        
                        # 复制文件内容到容器
                        with open(potential_abs_path, 'rb') as local_file:
                            file_content = local_file.read()
                            success = docker_client.copy_content_to_container(
                                container_id, 
                                file_content, 
                                container_file_path
                            )
                            if success:
                                logger.info(f"已将文件从宿主机复制到容器: {container_file_path}, 大小: {len(file_content)} 字节")
                                container_file_exists = True
                                
                                # 验证文件是否成功复制
                                exit_code, file_check = docker_client.exec_command_in_container(
                                    container_id, 
                                    f"ls -la {container_file_path}"
                                )
                                logger.info(f"容器中文件验证: {container_file_path}, 结果: {file_check.strip()}")
                            else:
                                logger.error(f"复制文件到容器失败")
                                
                except Exception as check_err:
                    logger.error(f"检查容器中的文件时出错: {str(check_err)}")
                    logger.error(traceback.format_exc())
            
            # 构建在容器内执行的Python代码
            # /workspace/ 是容器内映射到宿主机项目工作区的路径
            code = f"""
import json
import traceback
import sys
import os
import pandas as pd

try:
    # 用户代码开始
    
    # 构建容器内的文件路径
    file_path = '{sanitized_file_path}'
    full_path = f'/workspace/{file_path}'
    
    print(f"尝试读取CSV文件：{{{{full_path}}}}")
    
    # 检查文件是否存在
    if not os.path.exists(full_path):
        # 尝试查看当前路径结构
        base_dir = os.path.dirname(full_path) or '/workspace'
        if os.path.exists(base_dir):
            print(f"目录 {{{{base_dir}}}} 存在，内容:")
            try:
                for item in os.listdir(base_dir):
                    print(f"  - {{{{item}}}}")
            except Exception as dir_err:
                print(f"无法列出目录内容: {{{{str(dir_err)}}}}")
        else:
            print(f"目录 {{{{base_dir}}}} 不存在")
            
        raise FileNotFoundError(f"文件不存在: {{{{full_path}}}}")
        
    # 获取文件大小
    file_size = os.path.getsize(full_path)
    print(f"文件大小: {{{{file_size}}}} 字节")
    
    # 如果文件存在但大小为0，报错
    if file_size == 0:
        raise ValueError(f"文件存在但为空: {{{{full_path}}}}")
        
    # 尝试读取文件前几行
    print("文件前5行预览:")
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 5: break
                print(f"行 {{{{i+1}}}}: {{{{line[:100].strip()}}}}...")
    except Exception as preview_err:
        print(f"预览文件内容失败: {{{{str(preview_err)}}}}")
        
    # 加载CSV文件
    df = pd.read_csv(
        full_path,
        sep='{separator}',
        header={pandas_header_arg if pandas_header_arg is not None else 'None'}
    )
    
    # 获取数据信息
    info = {{
        'columns': df.columns.tolist(),
        'shape': df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}},
        'head_json': df.head(5).to_json(orient='records')
    }}
    
    # 设置结果
    result = {{
        'data': df.to_json(orient='split'),
        'info': info
    }}
    
    # 输出结果
    print("\\n----数据集JSON开始----")
    # 限制json输出大小，只保留前5行数据用于显示
    display_df = df.head(5)
    display_result = {{
        'data': display_df.to_json(orient='split'),
        'info': info
    }}
    print(json.dumps({{'dataset': display_result}}))
    print("----数据集JSON结束----\\n")
    print(f"成功加载CSV数据: {{{{df.shape[0]}}}} 行, {{{{df.shape[1]}}}} 列")

except FileNotFoundError as e:
    error_msg = f"错误：无法找到文件 {{{{full_path}}}}。请确保文件已正确上传。"
    print(json.dumps({{'error': error_msg, 'traceback': traceback.format_exc()}}))
except Exception as e:
    error_msg = f"处理CSV文件时出错: {{{{str(e)}}}}"
    print(json.dumps({{'error': error_msg, 'traceback': traceback.format_exc()}}))
"""
            
            # 在容器中执行代码
            # 假设 execute_in_container 返回一个字典，其中 'result' 键包含容器脚本的stdout
            container_exec_result = self.execute_in_container(code)
            
            # 记录容器执行返回的原始结果
            success = container_exec_result.get('success', False)
            logger.info(f"容器执行完成，success: {success}")
            
            if 'result' in container_exec_result:
                # 如果result是字符串，尝试解析里面的JSON部分
                if isinstance(container_exec_result['result'], str):
                    stdout_content = container_exec_result['result']
                    # 查找特定标记之间的JSON
                    json_start = "----数据集JSON开始----"
                    json_end = "----数据集JSON结束----"
                    
                    if json_start in stdout_content and json_end in stdout_content:
                        start_idx = stdout_content.find(json_start) + len(json_start)
                        end_idx = stdout_content.find(json_end)
                        if start_idx > 0 and end_idx > start_idx:
                            json_str = stdout_content[start_idx:end_idx].strip()
                            try:
                                json_data = json.loads(json_str)
                                logger.info(f"找到并解析了标记之间的JSON数据")
                                
                                if 'dataset' in json_data:
                                    return ExecutionResult(
                                        success=True,
                                        outputs={'dataset': json_data['dataset']},
                                        logs=["成功加载CSV数据"]
                                    )
                            except json.JSONDecodeError as e:
                                logger.error(f"解析标记间的JSON失败: {str(e)}")
                    
                    # 如果找不到标记，尝试查找任何有效的JSON对象
                    stdout_lines = stdout_content.strip().split('\n')
                    for line in stdout_lines:
                        line = line.strip()
                        if line.startswith('{') and line.endswith('}'):
                            try:
                                parsed = json.loads(line)
                                if 'error' in parsed:
                                    logger.error(f"找到错误JSON: {parsed['error']}")
                                    return ExecutionResult(
                                        success=False,
                                        error_message=parsed.get('error', 'CSV加载失败'),
                                        logs=[parsed.get('traceback', '未知错误')] + ["容器输出内容：" + stdout_content[:200]]
                                    )
                                elif 'dataset' in parsed:
                                    logger.info(f"找到dataset JSON")
                                    return ExecutionResult(
                                        success=True,
                                        outputs={'dataset': parsed['dataset']},
                                        logs=["成功加载CSV数据"]
                                    )
                            except json.JSONDecodeError:
                                # 尝试修复常见的JSON格式错误，例如单引号替换为双引号
                                try:
                                    # 尝试处理可能是Python字符串形式的输出 
                                    if line.startswith("{'") and line.endswith("'}"):
                                        import ast
                                        # 使用ast.literal_eval安全地评估Python字面量表达式
                                        python_dict = ast.literal_eval(line)
                                        if 'error' in python_dict:
                                            logger.error(f"修复并解析出错误信息: {python_dict['error']}")
                                            return ExecutionResult(
                                                success=False,
                                                error_message=python_dict.get('error', 'CSV加载失败'),
                                                logs=[python_dict.get('traceback', '未知错误')] + ["容器输出内容：" + stdout_content[:200]]
                                            )
                                except Exception as ast_err:
                                    logger.warning(f"尝试使用ast解析JSON失败: {str(ast_err)}")
                                continue
                
                # 如果result已经是字典并且包含dataset字段，直接使用
                elif isinstance(container_exec_result['result'], dict):
                    logger.info(f"容器执行返回了结构化结果")
                    
                    result_dict = container_exec_result['result']
                    if 'dataset' in result_dict:
                        return ExecutionResult(
                            success=True,
                            outputs={'dataset': result_dict['dataset']},
                            logs=["成功加载CSV数据"]
                        )
                    elif 'error' in result_dict:
                        return ExecutionResult(
                            success=False,
                            error_message=result_dict.get('error', 'CSV加载出错'),
                            logs=[result_dict.get('traceback', '未知错误')]
                        )
                    # 特殊处理初始化状态的返回结果
                    elif success and 'result' in result_dict and result_dict['result'] is None:
                        # 这说明文件已成功创建上传目录，但尚未加载数据
                        
                        # 添加详细的容器文件状态信息
                        error_logs = ["文件未找到或无法访问", f"文件路径: {sanitized_file_path}"]
                        
                        if container_id:
                            try:
                                from container.docker_ops import DockerClient
                                docker_client = DockerClient()
                                
                                # 获取容器的工作目录结构
                                exit_code, ls_output = docker_client.exec_command_in_container(
                                    container_id, 
                                    "ls -la /workspace/"
                                )
                                error_logs.append(f"容器中/workspace目录内容: {ls_output[:200]}")
                                
                                # 检查上传目录
                                exit_code, ls_output = docker_client.exec_command_in_container(
                                    container_id, 
                                    "ls -la /workspace/uploads/ 2>/dev/null || echo '目录不存在'"
                                )
                                error_logs.append(f"容器中uploads目录内容: {ls_output[:200]}")
                                
                            except Exception as check_err:
                                error_logs.append(f"获取容器文件信息时出错: {str(check_err)}")
                        
                        error_logs.append("请检查项目工作区中是否存在该文件，以及文件权限是否正确")
                        
                        return ExecutionResult(
                            success=False,
                            error_message="CSV文件未成功加载，可能文件路径不正确或文件不存在。请检查文件路径并确保文件已正确上传。",
                            logs=error_logs
                        )
            
            if success:
                # 尝试从容器的stdout解析JSON输出
                try:
                    # 获取输出内容
                    stdout_content = container_exec_result.get('result', '')
                    if not stdout_content and 'output' in container_exec_result:
                        stdout_content = container_exec_result.get('output', '')
                    
                    # 输出日志帮助诊断
                    logger.info(f"容器输出内容类型: {type(stdout_content)}, 长度: {len(str(stdout_content))}")
                    
                    # 对于空的或无效的结果，提供更详细的错误信息
                    if stdout_content is None or (isinstance(stdout_content, dict) and not stdout_content):
                        error_logs = ["容器返回了空结果", f"原始返回: {container_exec_result}"]
                        
                        # 添加文件和容器状态信息
                        if container_id:
                            try:
                                from container.docker_ops import DockerClient
                                docker_client = DockerClient()
                                
                                # 获取容器内文件系统信息
                                exit_code, ls_output = docker_client.exec_command_in_container(
                                    container_id, 
                                    f"ls -la /workspace/ && echo '===UPLOADS===' && ls -la /workspace/uploads/ 2>/dev/null || echo '目录不存在'"
                                )
                                error_logs.append(f"容器文件系统: {ls_output[:300]}")
                                
                            except Exception as check_err:
                                error_logs.append(f"检查容器文件系统出错: {str(check_err)}")
                        
                        return ExecutionResult(
                            success=False,
                            error_message="文件未找到或格式不支持，请尝试重新上传CSV文件",
                            logs=error_logs
                        )
                    
                    # 检查输出中是否包含文件不存在的错误
                    if isinstance(stdout_content, str) and ("文件不存在" in stdout_content or "File not found" in stdout_content or "No such file or directory" in stdout_content):
                        error_logs = [f"文件未找到: {sanitized_file_path}", "请重新上传文件"]
                        
                        # 添加目录内容信息
                        if "目录 " in stdout_content and " 存在，内容:" in stdout_content:
                            dir_content_start = stdout_content.find("目录 ") 
                            dir_content_end = stdout_content.find("\n{")
                            if dir_content_end > dir_content_start:
                                dir_content = stdout_content[dir_content_start:dir_content_end]
                                error_logs.append(f"容器中的目录内容: {dir_content}")
                        
                        return ExecutionResult(
                            success=False,
                            error_message=(
                                f"找不到CSV文件: {sanitized_file_path}. "
                                f"请尝试重新上传文件，或检查文件名是否正确。"
                            ),
                            logs=error_logs
                        )
                    
                    # 直接检查是否有error信息对象
                    if isinstance(stdout_content, dict) and 'error' in stdout_content:
                        error_msg = stdout_content['error']
                        if "File not found" in error_msg or "文件不存在" in error_msg:
                            return ExecutionResult(
                                success=False,
                                error_message="CSV文件未找到，请重新上传文件",
                                logs=[error_msg]
                            )
                        else:
                            return ExecutionResult(
                                success=False,
                                error_message=f"CSV读取错误: {error_msg[:100]}...",
                                logs=[error_msg]
                            )
                    
                    # 如果stdout_content已经是字典类型，检查是否包含正确的数据
                    if isinstance(stdout_content, dict):
                        if 'dataset' in stdout_content:
                            logger.info(f"容器直接返回了dataset数据")
                            return ExecutionResult(
                                success=True,
                                outputs={'dataset': stdout_content['dataset']},
                                logs=["成功加载CSV数据"]
                            )
                        elif 'error' in stdout_content:
                            logger.error(f"容器返回了错误: {stdout_content['error']}")
                            return ExecutionResult(
                                success=False,
                                error_message=stdout_content['error'],
                                logs=[stdout_content.get('traceback', '未知错误')]
                            )
                    
                    # 将stdout_content转换为字符串类型进行处理
                    if not isinstance(stdout_content, str):
                        stdout_content = str(stdout_content)
                    
                    # 容器脚本会将包含数据或错误的JSON打印到stdout
                    # 我们需要找到实际的结果JSON，它可能混杂在其他print输出中
                    stdout_lines = stdout_content.strip().split('\n')
                    if isinstance(stdout_lines, str):
                        stdout_lines = [stdout_lines]  # 确保它是一个列表
                        
                    # 输出所有行的第一部分，以助诊断
                    for i, line in enumerate(stdout_lines[:10]):  # 输出前10行
                        logger.info(f"容器输出行 {i}: {line[:100]}...")
                    
                    # 查找JSON结构
                    json_output_str = None
                    for line in reversed(stdout_lines):  # 从最后一行开始查找
                        line = line.strip()
                        if not line:
                            continue
                            
                        if line.startswith('{') and line.endswith('}'):
                            try:
                                parsed_json = json.loads(line)
                                logger.info(f"找到可能的JSON结构: {str(parsed_json)[:50]}...")
                                
                                # 检查这个JSON是否是我们期望的格式 (包含 dataset 或 error)
                                if 'dataset' in parsed_json:
                                    json_output_str = line
                                    logger.info(f"找到有效的dataset JSON")
                                    break
                                elif 'error' in parsed_json:
                                    json_output_str = line
                                    logger.info(f"找到错误JSON: {parsed_json['error'][:100]}")
                                    break
                            except json.JSONDecodeError as e:
                                logger.warning(f"JSON解析失败: {e}")
                                continue  # 不是有效的JSON行，继续找
                    
                    if not json_output_str:
                        # 如果找不到任何有效JSON，尝试检查容器文件系统
                        error_logs = ["CSV加载组件执行完成，但未能从容器输出中解析到预期的JSON结果。"]
                        log_details = f"容器原始输出: {stdout_lines[:10]}..." if stdout_lines else "容器未输出内容"
                        error_logs.append(log_details)
                        
                        # 尝试获取容器中的文件系统信息
                        if container_id:
                            try:
                                from container.docker_ops import DockerClient
                                docker_client = DockerClient()
                                
                                # 检查容器中的文件
                                exit_code, file_check = docker_client.exec_command_in_container(
                                    container_id, 
                                    f"test -f /workspace/{sanitized_file_path} && echo '文件存在' || echo '文件不存在'"
                                )
                                error_logs.append(f"容器中文件检查: {file_check.strip()}")
                                
                                # 获取目录结构
                                exit_code, ls_output = docker_client.exec_command_in_container(
                                    container_id, 
                                    "ls -la /workspace/uploads/ 2>/dev/null || echo '目录不存在'"
                                )
                                error_logs.append(f"容器中uploads目录内容: {ls_output[:200]}")
                            except Exception as check_err:
                                error_logs.append(f"检查容器文件系统出错: {str(check_err)}")
                        
                        logger.warning(f"{error_logs[0]} {log_details}")
                        return ExecutionResult(success=False, error_message="CSV文件解析失败，请检查文件格式和路径", logs=error_logs)
                except json.JSONDecodeError as json_err:
                    error_msg = f"解析CSV加载组件的容器输出为JSON时失败: {json_err}"
                    log_details = f"容器原始输出: {container_exec_result.get('result', '')}"
                    logger.error(f"{error_msg} {log_details}")
                    return ExecutionResult(success=False, error_message=error_msg, logs=[log_details])
            else:
                # execute_in_container 本身失败 (例如，Docker命令失败)
                error_logs = [container_exec_result.get('traceback', 'No traceback from container execution.')]
                
                # 尝试提供更详细的错误信息
                if hasattr(self, '_container') and self._container:
                    container_id = getattr(self._container, 'id', None) or getattr(self._container, 'container_id', None)
                    if container_id:
                        try:
                            from container.docker_ops import DockerClient
                            docker_client = DockerClient()
                            
                            # 获取容器状态
                            exit_code, status = docker_client.exec_command_in_container(
                                container_id, 
                                "echo '容器状态: 正常'"
                            )
                            error_logs.append(f"容器状态检查: {status.strip()}")
                            
                            # 检查文件访问权限
                            exit_code, perm_check = docker_client.exec_command_in_container(
                                container_id, 
                                f"ls -la /workspace/ && echo '===UPLOADS===' && mkdir -p /workspace/uploads && ls -la /workspace/uploads/"
                            )
                            error_logs.append(f"容器目录权限检查: {perm_check[:200]}")
                            
                        except Exception as check_err:
                            error_logs.append(f"检查容器状态时出错: {str(check_err)}")
                
                return ExecutionResult(
                    success=False,
                    error_message=container_exec_result.get('error', '执行CSV加载的容器命令失败。'),
                    logs=error_logs
                )
                
        except Exception as e:
            logger.error(f"执行CSV数据加载器 (CSVDataLoader) 外部逻辑时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=f"CSVDataLoader组件执行失败: {str(e)}"
            )


class ExcelDataLoader(BaseComponentExecutor):
    """Excel数据加载器
    
    加载Excel格式的数据文件，并转换为数据集对象。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        加载Excel数据文件
        
        Args:
            inputs: 输入数据
            parameters: 参数，包括:
                - file_path: 文件路径（相对于工作区）
                - sheet_name: 工作表名称
                - header: 是否有标题行
                
        Returns:
            ExecutionResult: 执行结果，包含加载的数据集
        """
        try:
            # 获取参数
            file_path = parameters.get('file_path', '')
            sheet_name = parameters.get('sheet_name', 0)
            header = parameters.get('header', 'true') == 'true'
            
            if not file_path:
                return ExecutionResult(
                    success=False,
                    error_message="未指定文件路径"
                )
            
            # 转换为Python代码
            code = f"""
try:
    # 加载Excel文件
    df = pd.read_excel('/workspace/{file_path}', 
                      sheet_name={repr(sheet_name)}, 
                      header={0 if header else None})
    
    # 获取数据信息
    info = {{
        'columns': df.columns.tolist(),
        'shape': df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}},
        'head': df.head(5).to_dict(orient='records')
    }}
    
    # 设置结果
    result = {{
        'data': df.to_json(orient='split'),
        'info': info
    }}
except Exception as e:
    raise Exception(f"加载Excel文件失败: {{str(e)}}")
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                data_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'dataset': data_result
                    },
                    logs=["成功加载Excel数据"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '加载Excel文件失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行Excel数据加载器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class JSONDataLoader(BaseComponentExecutor):
    """JSON数据加载器
    
    加载JSON格式的数据文件，并转换为数据集对象。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        加载JSON数据文件
        
        Args:
            inputs: 输入数据
            parameters: 参数，包括:
                - file_path: 文件路径（相对于工作区）
                - orient: JSON格式（records, split, index等）
                
        Returns:
            ExecutionResult: 执行结果，包含加载的数据集
        """
        try:
            # 获取参数
            file_path = parameters.get('file_path', '')
            orient = parameters.get('orient', 'records')
            
            if not file_path:
                return ExecutionResult(
                    success=False,
                    error_message="未指定文件路径"
                )
            
            # 转换为Python代码
            code = f"""
try:
    # 加载JSON文件
    df = pd.read_json('/workspace/{file_path}', orient='{orient}')
    
    # 获取数据信息
    info = {{
        'columns': df.columns.tolist(),
        'shape': df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}},
        'head': df.head(5).to_dict(orient='records')
    }}
    
    # 设置结果
    result = {{
        'data': df.to_json(orient='split'),
        'info': info
    }}
except Exception as e:
    raise Exception(f"加载JSON文件失败: {{str(e)}}")
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                data_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'dataset': data_result
                    },
                    logs=["成功加载JSON数据"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '加载JSON文件失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行JSON数据加载器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class RandomDataGenerator(BaseComponentExecutor):
    """随机数据生成器
    
    生成随机数据集，用于测试和原型设计。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        生成随机数据集
        
        Args:
            inputs: 输入数据
            parameters: 参数，包括:
                - rows: 行数
                - columns: 列数
                - column_type: 数据类型（数值、分类等）
                
        Returns:
            ExecutionResult: 执行结果，包含生成的数据集
        """
        try:
            # 获取参数
            rows = int(parameters.get('rows', 100))
            columns = int(parameters.get('columns', 5))
            column_type = parameters.get('column_type', 'numeric')
            include_target = parameters.get('include_target', 'true') == 'true'
            
            # 转换为Python代码
            code = f"""
try:
    import numpy as np
    import pandas as pd
    
    # 生成随机数据
    np.random.seed(42)  # 固定随机种子
    
    if '{column_type}' == 'numeric':
        # 生成数值型数据
        data = np.random.randn({rows}, {columns})
        columns = [f'feature_{{i+1}}' for i in range({columns})]
        df = pd.DataFrame(data, columns=columns)
        
        # 如果需要目标变量
        if {include_target}:
            # 生成连续型目标变量
            df['target'] = df.sum(axis=1) + np.random.randn({rows}) * 0.5
    
    elif '{column_type}' == 'categorical':
        # 生成分类型数据
        categories = ['A', 'B', 'C', 'D', 'E']
        data = np.random.choice(categories, size=({rows}, {columns}))
        columns = [f'cat_feature_{{i+1}}' for i in range({columns})]
        df = pd.DataFrame(data, columns=columns)
        
        # 如果需要目标变量
        if {include_target}:
            # 生成分类型目标变量
            df['target'] = np.random.choice(['Class1', 'Class2', 'Class3'], size={rows})
    
    elif '{column_type}' == 'mixed':
        # 生成混合型数据
        df = pd.DataFrame()
        
        # 数值型列
        for i in range({columns} // 2):
            df[f'num_feature_{{i+1}}'] = np.random.randn({rows})
        
        # 分类型列
        categories = ['A', 'B', 'C', 'D', 'E']
        for i in range({columns} // 2, {columns}):
            df[f'cat_feature_{{i+1}}'] = np.random.choice(categories, size={rows})
        
        # 如果需要目标变量
        if {include_target}:
            # 随机选择连续型或分类型目标
            if np.random.random() > 0.5:
                df['target'] = df.select_dtypes(include='number').sum(axis=1) + np.random.randn({rows}) * 0.5
            else:
                df['target'] = np.random.choice(['Class1', 'Class2', 'Class3'], size={rows})
    
    # 获取数据信息
    info = {{
        'columns': df.columns.tolist(),
        'shape': df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}},
        'head': df.head(5).to_dict(orient='records')
    }}
    
    # 设置结果
    result = {{
        'data': df.to_json(orient='split'),
        'info': info
    }}
except Exception as e:
    raise Exception(f"生成随机数据失败: {{str(e)}}")
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                data_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'dataset': data_result
                    },
                    logs=[f"成功生成随机数据集: {rows}行 x {columns}列"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '生成随机数据失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行随机数据生成器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )


class DataCleaner(BaseComponentExecutor):
    """数据清洗器
    
    清洗数据集中的缺失值、异常值等。
    可处理数字数据和文本数据。
    """
    
    def execute(self, inputs: Dict[str, Any], parameters: Dict[str, Any]) -> ExecutionResult:
        """
        清洗数据集
        
        Args:
            inputs: 输入数据，包括:
                - dataset: 输入数据集
            parameters: 参数，包括:
                - data_type: 数据类型（'numeric' 或 'text'）
                - handle_missing: 缺失值处理方式（删除、填充等）
                - fill_value: 用于填充的值
                - handle_outliers: 是否处理异常值
                - columns: 要处理的列
                - text_operations: 文本处理操作列表
                - lowercase: 是否转换为小写
                - remove_html: 是否移除HTML标签
                - remove_special_chars: 是否移除特殊字符
                - remove_extra_spaces: 是否移除多余空格
                - remove_stopwords: 是否移除停用词
                - stemming: 是否进行词干提取
                - lemmatization: 是否进行词形还原
                
        Returns:
            ExecutionResult: 执行结果，包含清洗后的数据集
        """
        try:
            # 获取输入数据
            if 'dataset' not in inputs:
                return ExecutionResult(
                    success=False,
                    error_message="缺少输入数据集"
                )
            
            dataset = inputs['dataset']
            
            # 检查数据集是否为空或无效
            if not dataset or not isinstance(dataset, dict) or 'data' not in dataset:
                return ExecutionResult(
                    success=False,
                    error_message="输入数据集无效或为空"
                )
                
            # 检查数据内容是否为空
            data_json = dataset.get('data', '{"columns":[],"data":[]}')
            try:
                # 尝试解析数据JSON
                data_obj = json.loads(data_json) if isinstance(data_json, str) else data_json
                if (not data_obj.get('columns') or len(data_obj.get('columns', [])) == 0) and \
                   (not data_obj.get('data') or len(data_obj.get('data', [])) == 0):
                    return ExecutionResult(
                        success=False,
                        error_message="输入数据集为空，无法进行数据清洗。请确保CSV文件已正确上传并包含数据。"
                    )
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error_message=f"数据格式错误: {str(e)}"
                )
            
            # 获取参数
            data_type = parameters.get('data_type', 'numeric')
            columns = parameters.get('columns', [])
            if columns and isinstance(columns, str):
                columns = columns.split(',')
            
            # 根据数据类型选择清洗策略
            if data_type == 'numeric':
                # 数值型数据清洗
                handle_missing = parameters.get('handle_missing', 'drop')
                fill_value = parameters.get('fill_value', '')
                handle_outliers = parameters.get('handle_outliers', False)
                if isinstance(handle_outliers, str):
                    handle_outliers = handle_outliers.lower() == 'true'
                
                # 转换为Python代码
                code = f"""
try:
    # 设置静默模式，减少输出
    silent_mode = True
    
    # 解析输入数据集
    df = pd.read_json('''{json.dumps(dataset.get('data', '{}'))}''', orient='split')
    
    # 选择要处理的列
    columns_to_process = {repr(columns)} if {repr(columns)} else df.columns.tolist()
    
    # 处理缺失值
    if '{handle_missing}' == 'drop':
        # 删除缺失值
        df = df.dropna(subset=columns_to_process)
    elif '{handle_missing}' == 'fill_mean':
        # 用均值填充数值型列的缺失值
        for col in columns_to_process:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].mean())
    elif '{handle_missing}' == 'fill_median':
        # 用中位数填充数值型列的缺失值
        for col in columns_to_process:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].median())
    elif '{handle_missing}' == 'fill_mode':
        # 用众数填充缺失值
        for col in columns_to_process:
            df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else None)
    elif '{handle_missing}' == 'fill_value':
        # 用指定值填充缺失值
        fill_value = '{fill_value}'
        for col in columns_to_process:
            # 根据列类型转换填充值
            if pd.api.types.is_numeric_dtype(df[col]):
                try:
                    val = float(fill_value)
                except:
                    val = 0
                df[col] = df[col].fillna(val)
            else:
                df[col] = df[col].fillna(fill_value)
    
    # 处理异常值
    if {handle_outliers}:
        for col in columns_to_process:
            if pd.api.types.is_numeric_dtype(df[col]):
                # 使用IQR方法检测和处理异常值
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # 异常值替换为边界值
                df[col] = df[col].apply(lambda x: lower_bound if x < lower_bound else (upper_bound if x > upper_bound else x))
    
    # 获取数据信息
    info = {{
        'columns': df.columns.tolist(),
        'shape': df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}},
        'head': df.head(5).to_dict(orient='records'),
        'cleaned_records': len(df)
    }}
    
    # 设置结果
    result = {{
        'data': df.to_json(orient='split'),
        'info': info
    }}

    # 只输出最终结果的JSON，减少终端输出
    print("----数据集JSON开始----")
    # 限制json输出大小，只保留前5行数据用于显示
    display_df = df.head(5)
    display_result = {{
        'data': display_df.to_json(orient='split'),
        'info': info
    }}
    print(json.dumps({{'dataset': display_result}}))
    print("----数据集JSON结束----")
except Exception as e:
    raise Exception(f"清洗数据失败: {{str(e)}}")
"""
            else:  # data_type == 'text'
                # 文本数据清洗参数
                lowercase = parameters.get('lowercase', True)
                if isinstance(lowercase, str):
                    lowercase = lowercase.lower() == 'true'
                    
                remove_html = parameters.get('remove_html', True)
                if isinstance(remove_html, str):
                    remove_html = remove_html.lower() == 'true'
                    
                remove_special_chars = parameters.get('remove_special_chars', True)
                if isinstance(remove_special_chars, str):
                    remove_special_chars = remove_special_chars.lower() == 'true'
                    
                remove_extra_spaces = parameters.get('remove_extra_spaces', True)
                if isinstance(remove_extra_spaces, str):
                    remove_extra_spaces = remove_extra_spaces.lower() == 'true'
                    
                remove_stopwords = parameters.get('remove_stopwords', False)
                if isinstance(remove_stopwords, str):
                    remove_stopwords = remove_stopwords.lower() == 'true'
                    
                stemming = parameters.get('stemming', False)
                if isinstance(stemming, str):
                    stemming = stemming.lower() == 'true'
                    
                lemmatization = parameters.get('lemmatization', False)
                if isinstance(lemmatization, str):
                    lemmatization = lemmatization.lower() == 'true'
                
                # 构建文本清洗代码
                code = f"""
import re
import pandas as pd
import json
try:
    # 设置静默模式，减少输出
    silent_mode = True
    
    # 解析输入数据集
    df = pd.read_json('''{json.dumps(dataset.get('data', '{}'))}''', orient='split')
    
    # 选择要处理的列
    columns_to_process = {repr(columns)} if {repr(columns)} else df.columns.tolist()
    
    # 文本清洗函数
    def clean_text(text):
        if not isinstance(text, str):
            return text
            
        # 转换为小写
        if {lowercase}:
            text = text.lower()
            
        # 移除HTML标签
        if {remove_html}:
            text = re.sub(r'<.*?>', '', text)
            
        # 移除特殊字符
        if {remove_special_chars}:
            text = re.sub(r'[^\\w\\s]', '', text)
            
        # 移除多余空格
        if {remove_extra_spaces}:
            text = re.sub(r'\\s+', ' ', text).strip()
            
        # 移除停用词
        if {remove_stopwords}:
            try:
                import nltk
                from nltk.corpus import stopwords
                try:
                    nltk.data.find('corpora/stopwords')
                except LookupError:
                    nltk.download('stopwords', quiet=True)
                stop_words = set(stopwords.words('english'))
                words = text.split()
                text = ' '.join([word for word in words if word.lower() not in stop_words])
            except Exception as e:
                if not silent_mode:
                    print("Warning: Could not remove stopwords: " + str(e))
                
        # 词干提取
        if {stemming}:
            try:
                import nltk
                from nltk.stem import PorterStemmer
                stemmer = PorterStemmer()
                words = text.split()
                text = ' '.join([stemmer.stem(word) for word in words])
            except Exception as e:
                if not silent_mode:
                    print("Warning: Could not perform stemming: " + str(e))
                
        # 词形还原
        if {lemmatization}:
            try:
                import nltk
                from nltk.stem import WordNetLemmatizer
                try:
                    nltk.data.find('corpora/wordnet')
                except LookupError:
                    nltk.download('wordnet', quiet=True)
                    nltk.download('omw-1.4', quiet=True)
                lemmatizer = WordNetLemmatizer()
                words = text.split()
                text = ' '.join([lemmatizer.lemmatize(word) for word in words])
            except Exception as e:
                if not silent_mode:
                    print("Warning: Could not perform lemmatization: " + str(e))
                
        return text
    
    # 应用文本清洗函数到选定的列
    original_shapes = {{}}
    for col in columns_to_process:
        if df[col].dtype == 'object':  # 只处理可能是文本的列
            original_shapes[col] = (
                df[col].str.len().mean() if df[col].str.len().mean() > 0 else 0, 
                df[col].str.len().max() if df[col].str.len().max() > 0 else 0
            )
            df[col] = df[col].apply(clean_text)
    
    # 获取数据信息
    text_stats = {{}}
    for col in original_shapes.keys():
        new_mean = df[col].str.len().mean() if df[col].str.len().mean() > 0 else 0
        new_max = df[col].str.len().max() if df[col].str.len().max() > 0 else 0
        reduction = (1 - new_mean / original_shapes[col][0]) * 100 if original_shapes[col][0] > 0 else 0
        text_stats[col] = {{
            'original_mean_length': original_shapes[col][0],
            'original_max_length': original_shapes[col][1],
            'new_mean_length': new_mean,
            'new_max_length': new_max,
            'length_reduction_percent': reduction
        }}
    
    info = {{
        'columns': df.columns.tolist(),
        'shape': df.shape,
        'dtypes': {{col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}},
        'head': df.head(5).to_dict(orient='records'),
        'text_stats': text_stats,
        'cleaned_records': len(df)
    }}
    
    # 设置结果
    result = {{
        'data': df.to_json(orient='split'),
        'info': info
    }}
    
    # 只输出最终结果JSON
    print("----数据集JSON开始----")
    # 限制json输出大小，只保留前5行数据用于显示
    display_df = df.head(5)
    display_result = {{
        'data': display_df.to_json(orient='split'),
        'info': info
    }}
    print(json.dumps({{'dataset': display_result}}))
    print("----数据集JSON结束----")
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    print("----数据集JSON开始----")
    print(json.dumps({{'error': "清洗文本数据失败: " + str(e), 'traceback': error_details}}))
    print("----数据集JSON结束----")
"""
            
            # 在容器中执行
            result = self.execute_in_container(code)
            
            if result.get('success', False):
                data_result = result.get('result', {})
                return ExecutionResult(
                    success=True,
                    outputs={
                        'dataset': data_result
                    },
                    logs=[f"数据清洗完成 (类型: {data_type})"]
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get('error', '数据清洗失败'),
                    logs=[result.get('traceback', '')]
                )
                
        except Exception as e:
            logger.error(f"执行数据清洗器时出错: {str(e)}")
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
