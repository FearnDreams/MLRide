"""
工作流执行引擎核心模块

该模块负责工作流的解析、执行和状态管理。
"""

import logging
import json
import time
import traceback
import os
from typing import Dict, List, Any, Tuple, Set, Optional
from threading import Thread
from queue import Queue
import networkx as nx
from django.utils import timezone
from django.conf import settings
from project.models import Workflow, WorkflowExecution, WorkflowComponentExecution
from container.docker_ops import DockerClient
from .component_registry import get_component_executor
from .executors import BaseComponentExecutor, ExecutionResult

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """工作流执行引擎
    
    负责解析工作流定义，构建执行计划，并协调各组件的执行。
    """
    
    def __init__(self, execution_id: int):
        """
        初始化工作流引擎
        
        Args:
            execution_id: 工作流执行记录ID
        """
        self.execution_id = execution_id  # 公开属性
        self._execution_id = execution_id  # 私有属性，确保这两个都被设置
        
        # 获取执行记录和相关对象
        try:
            self._execution = WorkflowExecution.objects.get(id=execution_id)
            self._workflow = self._execution.workflow
            self._project = self._workflow.project
            self._container = self._project.container
            self._definition = self._workflow.definition
        except Exception as e:
            logger.error(f"初始化工作流引擎时发生错误: {str(e)}")
            raise
            
        self._docker_client = DockerClient()
        self._execution_graph = None
        self._node_data = {}
        self._edge_data = {}
        self._component_results = {}
        self._execution_queue = Queue()
        self._execution_thread = None
        self._is_canceled = False
        
    def start(self) -> bool:
        """
        启动工作流执行
        
        Returns:
            bool: 是否成功启动
        """
        try:
            # 更新执行状态为运行中
            self._execution.status = 'running'
            self._execution.logs = f"[{timezone.now().isoformat()}] 工作流执行开始\n"
            self._execution.save()

            # 获取工作流定义（包含节点和连接）
            definition = self._definition
            if not definition:
                self._update_execution_failed("工作流定义为空，无法执行")
                return False
                
            # 解析定义中的节点和连接
            nodes = definition.get('nodes', [])
            edges = definition.get('edges', [])
            
            logger.info(f"工作流执行 #{self._execution_id}: 成功解析工作流: {len(nodes)}个节点, {len(edges)}个连接")
            
            # 获取项目工作区路径
            project_id = self._project.id
            project_workspace = f"workspaces/project_{project_id}"
            abs_workspace_path = os.path.join(os.getcwd(), project_workspace)
            logger.info(f"工作流执行 #{self._execution_id}: 项目工作区路径: {abs_workspace_path}")
            
            # 确保工作区的uploads目录存在 - 在宿主机上
            workspace_uploads_dir = os.path.join(abs_workspace_path, 'uploads')
            if not os.path.exists(workspace_uploads_dir):
                try:
                    os.makedirs(workspace_uploads_dir, exist_ok=True)
                    logger.info(f"工作流执行 #{self._execution_id}: 创建了uploads目录: {workspace_uploads_dir}")
                except Exception as e:
                    logger.warning(f"工作流执行 #{self._execution_id}: 无法创建uploads目录: {str(e)}")
            
            # 列出uploads目录中的文件
            if os.path.exists(workspace_uploads_dir):
                files = os.listdir(workspace_uploads_dir)
                logger.info(f"工作流执行 #{self._execution_id}: 宿主机上传目录中的文件: {files}")
            
            # 如果有容器ID，在容器中创建uploads目录
            if hasattr(self, '_container') and self._container and hasattr(self._container, 'container_id'):
                container_id = self._container.container_id
                logger.info(f"工作流执行 #{self._execution_id}: 尝试在容器 {container_id} 中创建目录")
                
                try:
                    # 创建容器中的uploads目录
                    exit_code, output = self._docker_client.exec_command_in_container(
                        container_id, 
                        "mkdir -p /workspace/uploads && ls -la /workspace/"
                    )
                    logger.info(f"工作流执行 #{self._execution_id}: 在容器中创建uploads目录，结果: {exit_code}, 输出: {output[:200]}")
                    
                    # 获取容器中/workspace的内容
                    exit_code, ls_output = self._docker_client.exec_command_in_container(
                        container_id,
                        "ls -la /workspace/"
                    )
                    logger.info(f"工作流执行 #{self._execution_id}: 容器中/workspace目录内容: {ls_output[:200]}")
                    
                    # 检查并复制每个节点引用的文件
                    for node in nodes:
                        node_data = node.get('data', {})
                        params = node_data.get('parameters', {})
                        node_id = node.get('id', 'unknown')
                        
                        # 如果是数据加载组件且有文件路径参数或文件信息
                        file_path = None
                        if params and isinstance(params, dict):
                            # 从file_path直接获取
                            if 'file_path' in params:
                                file_path = params['file_path']
                            
                            # 从_file_info中获取serverPath
                            elif '_file_info' in params and isinstance(params['_file_info'], dict):
                                file_info = params['_file_info']
                                if 'serverPath' in file_info:
                                    file_path = file_info['serverPath']
                        
                        if file_path and isinstance(file_path, str):
                            # 规范化路径，移除开头的uploads/如果有的话
                            clean_file_path = file_path
                            if clean_file_path.startswith('uploads/'):
                                clean_file_path = clean_file_path[8:]  # 移除'uploads/'
                            
                            # 构建本地文件路径和容器目标路径
                            host_file_path = os.path.join(workspace_uploads_dir, clean_file_path)
                            container_file_path = f"/workspace/uploads/{clean_file_path}"
                            
                            logger.info(f"工作流执行 #{self._execution_id}: 节点 {node_id} 需要文件: {file_path}")
                            logger.info(f"工作流执行 #{self._execution_id}: 尝试从 {host_file_path} 复制到容器 {container_file_path}")
                            
                            if os.path.exists(host_file_path):
                                logger.info(f"工作流执行 #{self._execution_id}: 文件 {host_file_path} 存在, 大小: {os.path.getsize(host_file_path)} 字节")
                                
                                # 确保容器中目标目录存在
                                container_dir = os.path.dirname(container_file_path)
                                if container_dir != "/workspace/uploads":
                                    self._docker_client.exec_command_in_container(
                                        container_id,
                                        f"mkdir -p {container_dir}"
                                    )
                                
                                # 直接使用复制内容的方法，可能更可靠
                                with open(host_file_path, 'rb') as f:
                                    file_content = f.read()
                                    success = self._docker_client.copy_content_to_container(
                                        container_id,
                                        file_content,
                                        container_file_path
                                    )
                                    logger.info(f"工作流执行 #{self._execution_id}: 文件内容复制结果: {success}")
                                    
                                    # 验证文件是否成功复制到容器
                                    if success:
                                        verify_cmd = f"ls -la {container_file_path}"
                                        exit_code, verify_output = self._docker_client.exec_command_in_container(
                                            container_id, 
                                            verify_cmd
                                        )
                                        logger.info(f"工作流执行 #{self._execution_id}: 文件验证结果: {exit_code}, {verify_output}")
                            else:
                                logger.warning(f"工作流执行 #{self._execution_id}: 文件 {host_file_path} 不存在，无法复制到容器")
                
                except Exception as e:
                    logger.error(f"工作流执行 #{self._execution_id}: 容器目录操作失败: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # 解析工作流定义
            success = self._parse_workflow()
            if not success:
                self._update_execution_failed("工作流解析失败")
                return False
            
            # 构建执行图
            success = self._build_execution_graph()
            if not success:
                self._update_execution_failed("构建执行计划失败")
                return False
            
            # 启动执行线程
            self._execution_thread = Thread(target=self._execute_workflow)
            self._execution_thread.daemon = True
            self._execution_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"启动工作流执行失败: {str(e)}")
            self._update_execution_failed(f"启动工作流执行失败: {str(e)}")
            traceback.print_exc()
            return False
    
    def cancel(self) -> bool:
        """
        取消工作流执行
        
        Returns:
            bool: 是否成功取消
        """
        try:
            self._is_canceled = True
            
            if self._execution.status in ['completed', 'failed', 'canceled']:
                return False
                
            self._execution.status = 'canceled'
            self._execution.end_time = timezone.now()
            self._execution.logs += f"[{timezone.now().isoformat()}] 工作流执行已取消\n"
            self._execution.save()
            
            # 将所有待执行的组件标记为已跳过
            for node_id in self._node_data:
                component_execution = WorkflowComponentExecution.objects.filter(
                    execution=self._execution,
                    node_id=node_id,
                    status='pending'
                ).first()
                
                if component_execution:
                    component_execution.status = 'skipped'
                    component_execution.save()
            
            return True
            
        except Exception as e:
            logger.error(f"取消工作流执行失败: {str(e)}")
            return False
    
    def _parse_workflow(self) -> bool:
        """
        解析工作流定义
        
        Returns:
            bool: 是否成功解析
        """
        try:
            # 解析节点数据
            if 'nodes' not in self._definition:
                self._log_error("工作流定义缺少节点信息")
                return False
                
            for node in self._definition.get('nodes', []):
                node_id = node.get('id')
                if not node_id:
                    self._log_error(f"节点缺少ID: {node}")
                    continue
                    
                self._node_data[node_id] = {
                    'id': node_id,
                    'type': node.get('type'),
                    'data': node.get('data', {}),
                    'position': node.get('position', {'x': 0, 'y': 0}),
                    'inputs': {},
                    'outputs': {},
                    'component_id': node.get('data', {}).get('component', {}).get('id'),
                    'component_type': node.get('data', {}).get('component', {}).get('type'),
                    'parameters': node.get('data', {}).get('parameters', {})
                }
            
            # 解析边数据
            if 'edges' not in self._definition:
                self._log_error("工作流定义缺少连接信息")
                return False
                
            for edge in self._definition.get('edges', []):
                edge_id = edge.get('id')
                source = edge.get('source')
                sourceHandle = edge.get('sourceHandle')
                target = edge.get('target')
                targetHandle = edge.get('targetHandle')
                
                if not all([edge_id, source, sourceHandle, target, targetHandle]):
                    self._log_error(f"边缺少必要信息: {edge}")
                    continue
                
                # 记录连接关系
                self._edge_data[edge_id] = {
                    'id': edge_id,
                    'source': source,
                    'sourceHandle': sourceHandle,
                    'target': target,
                    'targetHandle': targetHandle
                }
                
                # 更新节点的输入输出关系
                # 源节点的输出连接到了哪里
                if source in self._node_data:
                    if 'outputs' not in self._node_data[source]:
                        self._node_data[source]['outputs'] = {}
                    
                    if sourceHandle not in self._node_data[source]['outputs']:
                        self._node_data[source]['outputs'][sourceHandle] = []
                    
                    self._node_data[source]['outputs'][sourceHandle].append({
                        'edge': edge_id,
                        'target': target,
                        'targetHandle': targetHandle
                    })
                
                # 目标节点的输入来自哪里
                if target in self._node_data:
                    if 'inputs' not in self._node_data[target]:
                        self._node_data[target]['inputs'] = {}
                    
                    self._node_data[target]['inputs'][targetHandle] = {
                        'edge': edge_id,
                        'source': source,
                        'sourceHandle': sourceHandle
                    }
            
            self._log_info(f"成功解析工作流: {len(self._node_data)}个节点, {len(self._edge_data)}个连接")
            return True
            
        except Exception as e:
            self._log_error(f"解析工作流定义失败: {str(e)}")
            traceback.print_exc()
            return False
    
    def _build_execution_graph(self) -> bool:
        """
        构建执行图，确定执行顺序
        
        Returns:
            bool: 是否成功构建
        """
        try:
            # 创建有向图
            G = nx.DiGraph()
            
            # 添加所有节点
            for node_id in self._node_data:
                G.add_node(node_id)
            
            # 添加所有边
            for edge_id, edge in self._edge_data.items():
                source = edge['source']
                target = edge['target']
                G.add_edge(source, target, id=edge_id)
            
            # 检查是否有环
            if not nx.is_directed_acyclic_graph(G):
                cycles = list(nx.simple_cycles(G))
                self._log_error(f"工作流图中存在循环: {cycles}")
                return False
            
            # 获取拓扑排序
            try:
                topological_order = list(nx.topological_sort(G))
                self._log_info(f"确定执行顺序: {topological_order}")
                
                # 为每个节点创建执行记录
                for node_id in topological_order:
                    node = self._node_data[node_id]
                    component_id = node.get('component_id', '')
                    component_type = node.get('component_type', '')
                    component_name = node.get('data', {}).get('component', {}).get('label', '未命名组件')
                    
                    WorkflowComponentExecution.objects.create(
                        execution=self._execution,
                        node_id=node_id,
                        component_id=component_id,
                        component_name=component_name,
                        status='pending',
                        inputs=node.get('parameters', {})
                    )
                
                # 将执行顺序放入队列
                for node_id in topological_order:
                    self._execution_queue.put(node_id)
                
                self._execution_graph = G
                return True
                
            except nx.NetworkXUnfeasible:
                self._log_error("工作流图不是有向无环图，无法确定执行顺序")
                return False
                
        except Exception as e:
            self._log_error(f"构建执行图失败: {str(e)}")
            traceback.print_exc()
            return False
    
    def _execute_workflow(self) -> None:
        """
        执行工作流
        """
        try:
            start_time = time.time()
            success = True
            
            while not self._execution_queue.empty() and not self._is_canceled:
                # 获取下一个要执行的节点
                node_id = self._execution_queue.get()
                node = self._node_data[node_id]
                
                # 获取节点的组件执行记录
                component_execution = WorkflowComponentExecution.objects.filter(
                    execution=self._execution,
                    node_id=node_id
                ).first()
                
                if not component_execution:
                    self._log_error(f"找不到节点 {node_id} 的执行记录")
                    continue
                
                # 更新组件状态为正在执行
                component_execution.status = 'running'
                component_execution.start_time = timezone.now()
                component_execution.save()
                
                # 为节点准备输入数据
                input_data = {}
                
                # 处理来自其他节点的输入
                for input_handle, input_info in node.get('inputs', {}).items():
                    source_node_id = input_info.get('source')
                    source_handle = input_info.get('sourceHandle')
                    
                    # 检查源节点是否有结果
                    if source_node_id not in self._component_results:
                        self._log_error(f"节点 {node_id} 的输入 {input_handle} 依赖的源节点 {source_node_id} 没有执行结果")
                        success = False
                        break
                    
                    # 检查源节点的特定输出端口是否有数据
                    source_outputs = self._component_results[source_node_id].outputs
                    if source_handle not in source_outputs:
                        self._log_error(f"节点 {node_id} 的输入 {input_handle} 依赖的源节点 {source_node_id} 的输出端口 {source_handle} 没有数据")
                        success = False
                        break
                    
                    # 获取输入数据
                    input_data[input_handle] = source_outputs[source_handle]
                
                    # 记录原始输入数据的结构，便于调试
                    if isinstance(input_data[input_handle], dict):
                        keys = list(input_data[input_handle].keys())
                        self._log_info(f"DEBUG: 节点 {node_id} 的输入 {input_handle} 包含键: {keys}")
                    else:
                        self._log_info(f"DEBUG: 节点 {node_id} 的输入 {input_handle} 类型: {type(input_data[input_handle])}")
                
                    # 检查完整数据是否存在并处理
                    if isinstance(input_data[input_handle], dict) and 'full_data' in input_data[input_handle]:
                        # 记录调试信息
                        self._log_info(f"DEBUG: 节点 {node_id} 的输入 {input_handle} 接收到包含full_data的数据")
                        data_len = len(input_data[input_handle].get('data', '')) if isinstance(input_data[input_handle].get('data'), str) else 'NA'
                        full_data_len = len(input_data[input_handle].get('full_data', '')) if isinstance(input_data[input_handle].get('full_data'), str) else 'NA'
                        self._log_info(f"DEBUG: data大小: {data_len}字节, full_data大小: {full_data_len}字节")
                        
                        # 验证数据大小合理性
                        if isinstance(data_len, int) and isinstance(full_data_len, int):
                            if data_len > full_data_len:
                                self._log_info(f"警告: 预览数据({data_len})大于完整数据({full_data_len})，这可能是一个问题")
                            if full_data_len / max(data_len, 1) < 1.5 and input_data[input_handle].get('info', {}).get('shape', [0])[0] > 10:
                                self._log_info(f"警告: 完整数据与预览数据大小比例较小({full_data_len/max(data_len, 1):.2f})，但数据行数较多({input_data[input_handle].get('info', {}).get('shape', [0])[0]})")
                        
                        # 使用 full_data 替换截断的数据
                        full_data = input_data[input_handle]['full_data']
                        display_data = input_data[input_handle]['data']
                        info = input_data[input_handle].get('info', {})
                        
                        # 重构完整数据，保留原始格式但使用完整数据
                        input_data[input_handle] = {
                            'data': full_data,  # 使用完整数据
                            'display_data': display_data,  # 保留显示数据
                            'info': info  # 保留元数据
                        }
                        self._log_info(f"节点 {node_id} 的输入 {input_handle} 使用了完整数据替代截断版本")
                
                # 如果获取输入数据失败，标记该组件执行失败并继续下一个
                if not success:
                    component_execution.status = 'failed'
                    component_execution.error = f"无法获取完整的输入数据"
                    component_execution.end_time = timezone.now()
                    component_execution.save()
                    continue
                
                # 合并节点参数
                parameters = node.get('parameters', {})
                
                # 获取组件执行器
                component_id = node.get('component_id')
                component_type = node.get('component_type')
                
                try:
                    # 获取组件执行器
                    executor = get_component_executor(
                        component_id=component_id,
                        component_type=component_type,
                        container_id=self._container.container_id
                    )
                    
                    if not executor:
                        self._log_error(f"找不到组件 {component_id} ({component_type}) 的执行器")
                        component_execution.status = 'failed'
                        component_execution.error = f"找不到组件执行器"
                        component_execution.end_time = timezone.now()
                        component_execution.save()
                        continue
                    
                    # 执行组件
                    self._log_info(f"开始执行组件: {node_id} ({component_id})")
                    result = executor.execute(input_data, parameters)
                    
                    # 保存执行结果
                    self._component_results[node_id] = result
                    
                    # 添加调试信息 - 记录组件输出中是否包含完整数据
                    for key, value in result.outputs.items():
                        if isinstance(value, dict):
                            if 'data' in value and isinstance(value['data'], str):
                                data_len = len(value['data'])
                                self._log_info(f"DEBUG: 组件 {node_id} 输出端口 {key} 的data大小: {data_len}字节")
                            if 'full_data' in value and isinstance(value['full_data'], str):
                                full_data_len = len(value['full_data'])
                                self._log_info(f"DEBUG: 组件 {node_id} 输出端口 {key} 的full_data大小: {full_data_len}字节")
                    
                    # 更新组件执行记录
                    component_execution.status = 'completed' if result.success else 'failed'
                    component_execution.end_time = timezone.now()
                    
                    # 截断大型数据集结果，限制输出大小
                    # 对于数据集结果，我们保留元数据但限制actual data的大小
                    truncated_outputs = {}
                    data_too_large = False
                    
                    # 检查数据集大小并处理
                    for key, value in result.outputs.items():
                        if isinstance(value, dict) and 'data' in value and isinstance(value['data'], str) and len(value['data']) > 1000000:
                            # 保存数据集元信息，但截断实际数据
                            truncated_outputs[key] = {
                                'info': value.get('info', {}),
                                'data_truncated': True,
                                'original_size': len(value['data']),
                                'data': value['data'][:1000] + '... [数据已截断，共' + str(len(value['data'])) + '字节]'
                            }
                            
                            # 如果存在完整数据字段，保留它用于数据传递
                            if 'full_data' in value:
                                # 保存到内存中用于组件间传递，但不保存到数据库
                                # 我们将在程序内存中为该组件的结果保留一个字段，而不是保存到数据库
                                self._component_results[node_id].outputs[key]['full_data'] = value['full_data']
                            else:
                                # 将原始data保存为full_data以供数据传递使用，但仅保存在内存中
                                self._component_results[node_id].outputs[key]['full_data'] = value['data']
                                
                            data_too_large = True
                            # 记录日志
                            self._log_info(f"数据集太大，已截断 {key} 字段 (原始大小: {len(value['data'])} 字节)，但在内存中保留完整数据供后续组件使用")
                        else:
                            truncated_outputs[key] = value
                            # 如果有full_data字段，从数据库保存版本中移除，但在内存中保留
                            if isinstance(value, dict) and 'full_data' in value:
                                # 保存在内存中
                                self._component_results[node_id].outputs[key]['full_data'] = value['full_data']
                                # 从数据库版本中移除
                                truncated_outputs[key] = {k: v for k, v in value.items() if k != 'full_data'}
                    
                    # 使用截断后的输出
                    component_execution.outputs = truncated_outputs
                    
                    if not result.success:
                        component_execution.error = result.error_message
                        # 增强错误日志记录
                        error_details = f"组件 {node_id} ({component_id}) 执行失败. "
                        error_details += f"错误信息: {result.error_message}. "
                        if result.logs:
                            error_details += f"组件日志: {'; '.join(result.logs[:5])}."
                            if len(result.logs) > 5:
                                error_details += f" [日志已截断，共{len(result.logs)}条]"
                        self._log_error(error_details) # 使用 _log_error 记录详细错误
                    
                    # 如果数据太大，添加警告信息
                    if data_too_large:
                        component_execution.error = component_execution.error or ""
                        component_execution.error += "\n警告: 结果数据集太大，已被截断以便保存到数据库。完整数据仍在内存中可供后续节点使用。"
                    
                    try:
                        component_execution.save()
                    except Exception as save_err:
                        # 如果保存失败，尝试进一步截断数据
                        logger.error(f"保存组件执行结果失败: {str(save_err)}，尝试进一步截断数据")
                        try:
                            # 完全移除数据字段，只保留元数据
                            for key in truncated_outputs:
                                if isinstance(truncated_outputs[key], dict):
                                    # 保留info字段，但移除所有数据
                                    info = truncated_outputs[key].get('info', {})
                                    truncated_outputs[key] = {
                                        'truncated': True, 
                                        'info': info,
                                        'message': '数据太大，无法保存到数据库'
                                    }
                            component_execution.outputs = truncated_outputs
                            try:
                                component_execution.save()
                            except Exception as second_save_err:
                                logger.error(f"二次尝试保存组件执行结果也失败: {str(second_save_err)}，放弃保存到数据库")
                                logger.error(f"该组件执行结果将仅存在于内存中，不会保存到数据库")
                                # 不抛出异常，让工作流继续执行
                        except Exception as truncate_err:
                            logger.error(f"处理数据截断时出错: {str(truncate_err)}，放弃保存到数据库")
                            # 不抛出异常，让工作流继续执行
                    
                    # 保留原来的成功/失败概览日志，但详细错误已通过 _log_error 记录
                    self._log_info(f"组件 {node_id} ({component_id}) 执行状态: {'成功' if result.success else '失败'}")
                    
                except Exception as e:
                    self._log_error(f"执行组件 {node_id} ({component_id}) 时发生严重异常: {str(e)}")
                    traceback.print_exc()
                    
                    # 更新组件执行记录
                    component_execution.status = 'failed'
                    component_execution.error = str(e)
                    component_execution.end_time = timezone.now()
                    component_execution.save()
                    
                    # 继续执行其他组件
                    continue
            
            # 检查整体执行状态
            execution_time = time.time() - start_time
            if self._is_canceled:
                self._log_info(f"工作流执行已取消，耗时 {execution_time:.2f} 秒")
                return
            
            # 检查是否所有组件都执行成功
            all_components = WorkflowComponentExecution.objects.filter(execution=self._execution)
            failed_components = all_components.filter(status='failed').count()
            
            if failed_components > 0:
                self._update_execution_failed(f"工作流执行完成，但有 {failed_components} 个组件执行失败")
            else:
                # 更新整体执行状态为成功
                self._execution.status = 'completed'
                self._execution.end_time = timezone.now()
                self._execution.logs += f"[{timezone.now().isoformat()}] 工作流执行成功，耗时 {execution_time:.2f} 秒\n"
                
                # 将最终结果汇总 - 但不要包含大型数据集
                final_results = {}
                for node_id, result in self._component_results.items():
                    if result.success:
                        # 创建结果摘要，避免复制大数据
                        result_summary = {}
                        for key, value in result.outputs.items():
                            # 完全移除full_data字段
                            if isinstance(value, dict) and 'full_data' in value:
                                # 创建不包含full_data的副本
                                filtered_value = {k: v for k, v in value.items() if k != 'full_data'}
                                value = filtered_value
                                
                            # 处理大型数据集
                            if isinstance(value, dict) and 'data' in value and isinstance(value['data'], str) and len(value['data']) > 10000:
                                # 只保留数据集元信息
                                result_summary[key] = {
                                    'info': value.get('info', {}),
                                    'data_truncated': True,
                                    'original_size': len(value['data']),
                                    # 只保留极小的数据预览
                                    'data_preview': value['data'][:200] + '...' if len(value['data']) > 200 else value['data']
                                }
                            else:
                                result_summary[key] = value
                                
                        final_results[node_id] = {
                            'outputs': result_summary,
                            'component_id': self._node_data[node_id].get('component_id'),
                            'component_type': self._node_data[node_id].get('component_type'),
                        }
                
                try:
                    self._execution.result = {'results': final_results}
                    self._execution.save()
                except Exception as save_err:
                    # 如果保存失败，尝试进一步截断数据
                    logger.error(f"保存工作流执行结果失败: {str(save_err)}，进一步截断结果数据")
                    for node_id in final_results:
                        if 'outputs' in final_results[node_id]:
                            for key in list(final_results[node_id]['outputs'].keys()):
                                final_results[node_id]['outputs'][key] = {
                                    'truncated': True, 
                                    'message': '数据太大，无法保存到数据库'
                                }
                    self._execution.result = {'results': final_results}
                    self._execution.save()
                
                self._log_info(f"工作流执行成功，耗时 {execution_time:.2f} 秒")
            
        except Exception as e:
            self._log_error(f"执行工作流过程中发生异常: {str(e)}")
            traceback.print_exc()
            self._update_execution_failed(f"执行工作流过程中发生异常: {str(e)}")
    
    def _update_execution_failed(self, message: str) -> None:
        """
        更新执行状态为失败
        
        Args:
            message: 失败信息
        """
        self._execution.status = 'failed'
        self._execution.end_time = timezone.now()
        self._execution.logs += f"[{timezone.now().isoformat()}] {message}\n"
        self._execution.save()
        self._log_error(message)
    
    def _log_info(self, message: str) -> None:
        """
        记录信息日志
        
        Args:
            message: 日志消息
        """
        try:
            self._execution.logs += f"[{timezone.now().isoformat()}] {message}\n"
            try:
                self._execution.save(update_fields=['logs'])
            except Exception as e:
                # 如果数据库保存失败，只记录到控制台但不抛出异常
                logger.warning(f"保存日志到数据库失败: {str(e)}")
            logger.info(f"工作流执行 #{self.execution_id}: {message}")
        except Exception as e:
            # 确保即使日志记录失败也不影响工作流执行
            logger.error(f"日志记录失败: {str(e)}")
    
    def _log_error(self, message: str) -> None:
        """
        记录错误日志
        
        Args:
            message: 日志消息
        """
        try:
            self._execution.logs += f"[{timezone.now().isoformat()}] 错误: {message}\n"
            try:
                self._execution.save(update_fields=['logs'])
            except Exception as e:
                # 如果数据库保存失败，只记录到控制台但不抛出异常
                logger.warning(f"保存错误日志到数据库失败: {str(e)}")
            logger.error(f"工作流执行 #{self.execution_id}: {message}")
        except Exception as e:
            # 确保即使日志记录失败也不影响工作流执行
            logger.error(f"错误日志记录失败: {str(e)}")

    def execute_workflow(self):
        """执行工作流
        
        解析工作流定义，构建执行计划，并协调各个组件的执行
        """
        try:
            # 获取工作流定义（包含节点和连接）
            definition = self._definition
            if not definition:
                raise ValueError("工作流定义为空，无法执行")
                
            # 解析定义中的节点和连接
            nodes = definition.get('nodes', [])
            edges = definition.get('edges', [])
            
            logger.info(f"工作流执行 #{self._execution_id}: 成功解析工作流: {len(nodes)}个节点, {len(edges)}个连接")
            
            # 获取项目工作区路径
            project_id = self._project.id
            project_workspace = f"workspaces/project_{project_id}"
            abs_workspace_path = os.path.join(os.getcwd(), project_workspace)
            logger.info(f"工作流执行 #{self._execution_id}: 项目工作区路径: {abs_workspace_path}")
            
            # 确保工作区的uploads目录存在 - 在宿主机上
            workspace_uploads_dir = os.path.join(abs_workspace_path, 'uploads')
            if not os.path.exists(workspace_uploads_dir):
                try:
                    os.makedirs(workspace_uploads_dir, exist_ok=True)
                    logger.info(f"工作流执行 #{self._execution_id}: 创建了uploads目录: {workspace_uploads_dir}")
                except Exception as e:
                    logger.warning(f"工作流执行 #{self._execution_id}: 无法创建uploads目录: {str(e)}")
            
            # 列出uploads目录中的文件
            if os.path.exists(workspace_uploads_dir):
                files = os.listdir(workspace_uploads_dir)
                logger.info(f"工作流执行 #{self._execution_id}: 宿主机上传目录中的文件: {files}")
            
            # 如果有容器ID，在容器中创建uploads目录
            if hasattr(self, '_container') and self._container and hasattr(self._container, 'container_id'):
                container_id = self._container.container_id
                logger.info(f"工作流执行 #{self._execution_id}: 尝试在容器 {container_id} 中创建目录")
                
                try:
                    # 创建容器中的uploads目录
                    exit_code, output = self._docker_client.exec_command_in_container(
                        container_id, 
                        "mkdir -p /workspace/uploads && ls -la /workspace/"
                    )
                    logger.info(f"工作流执行 #{self._execution_id}: 在容器中创建uploads目录，结果: {exit_code}, 输出: {output[:200]}")
                    
                    # 获取容器中/workspace的内容
                    exit_code, ls_output = self._docker_client.exec_command_in_container(
                        container_id,
                        "ls -la /workspace/"
                    )
                    logger.info(f"工作流执行 #{self._execution_id}: 容器中/workspace目录内容: {ls_output[:200]}")
                    
                    # 检查并复制每个节点引用的文件
                    for node in nodes:
                        node_data = node.get('data', {})
                        params = node_data.get('parameters', {})
                        node_id = node.get('id', 'unknown')
                        
                        # 如果是数据加载组件且有文件路径参数或文件信息
                        file_path = None
                        if params and isinstance(params, dict):
                            # 从file_path直接获取
                            if 'file_path' in params:
                                file_path = params['file_path']
                            
                            # 从_file_info中获取serverPath
                            elif '_file_info' in params and isinstance(params['_file_info'], dict):
                                file_info = params['_file_info']
                                if 'serverPath' in file_info:
                                    file_path = file_info['serverPath']
                        
                        if file_path and isinstance(file_path, str):
                            # 规范化路径，移除开头的uploads/如果有的话
                            clean_file_path = file_path
                            if clean_file_path.startswith('uploads/'):
                                clean_file_path = clean_file_path[8:]  # 移除'uploads/'
                            
                            # 构建本地文件路径和容器目标路径
                            host_file_path = os.path.join(workspace_uploads_dir, clean_file_path)
                            container_file_path = f"/workspace/uploads/{clean_file_path}"
                            
                            logger.info(f"工作流执行 #{self._execution_id}: 节点 {node_id} 需要文件: {file_path}")
                            logger.info(f"工作流执行 #{self._execution_id}: 尝试从 {host_file_path} 复制到容器 {container_file_path}")
                            
                            if os.path.exists(host_file_path):
                                logger.info(f"工作流执行 #{self._execution_id}: 文件 {host_file_path} 存在, 大小: {os.path.getsize(host_file_path)} 字节")
                                
                                # 确保容器中目标目录存在
                                container_dir = os.path.dirname(container_file_path)
                                if container_dir != "/workspace/uploads":
                                    self._docker_client.exec_command_in_container(
                                        container_id,
                                        f"mkdir -p {container_dir}"
                                    )
                                
                                # 直接使用复制内容的方法，可能更可靠
                                with open(host_file_path, 'rb') as f:
                                    file_content = f.read()
                                    success = self._docker_client.copy_content_to_container(
                                        container_id,
                                        file_content,
                                        container_file_path
                                    )
                                    logger.info(f"工作流执行 #{self._execution_id}: 文件内容复制结果: {success}")
                                    
                                    # 验证文件是否成功复制到容器
                                    if success:
                                        verify_cmd = f"ls -la {container_file_path}"
                                        exit_code, verify_output = self._docker_client.exec_command_in_container(
                                            container_id, 
                                            verify_cmd
                                        )
                                        logger.info(f"工作流执行 #{self._execution_id}: 文件验证结果: {exit_code}, {verify_output}")
                            else:
                                logger.warning(f"工作流执行 #{self._execution_id}: 文件 {host_file_path} 不存在，无法复制到容器")
                
                except Exception as e:
                    logger.error(f"工作流执行 #{self._execution_id}: 容器目录操作失败: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # 解析工作流定义
            success = self._parse_workflow()
            if not success:
                self._update_execution_failed("工作流解析失败")
                return False
            
            # 构建执行图
            success = self._build_execution_graph()
            if not success:
                self._update_execution_failed("构建执行计划失败")
                return False
            
            # 启动执行线程
            self._execution_thread = Thread(target=self._execute_workflow)
            self._execution_thread.daemon = True
            self._execution_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"执行工作流失败: {str(e)}")
            self._update_execution_failed(f"执行工作流失败: {str(e)}")
            traceback.print_exc()
            return False

class WorkflowEngineManager:
    """工作流引擎管理器
    
    管理所有工作流引擎实例
    """
    
    _instances = {}
    
    @classmethod
    def get_engine(cls, execution_id: int) -> Optional[WorkflowEngine]:
        """
        获取工作流引擎实例
        
        Args:
            execution_id: 工作流执行记录ID
            
        Returns:
            WorkflowEngine: 工作流引擎实例
        """
        return cls._instances.get(execution_id)
    
    @classmethod
    def create_engine(cls, execution_id: int) -> WorkflowEngine:
        """
        创建工作流引擎实例
        
        Args:
            execution_id: 工作流执行记录ID
            
        Returns:
            WorkflowEngine: 工作流引擎实例
        """
        engine = WorkflowEngine(execution_id)
        cls._instances[execution_id] = engine
        return engine
    
    @classmethod
    def remove_engine(cls, execution_id: int) -> None:
        """
        移除工作流引擎实例
        
        Args:
            execution_id: 工作流执行记录ID
        """
        if execution_id in cls._instances:
            del cls._instances[execution_id]
