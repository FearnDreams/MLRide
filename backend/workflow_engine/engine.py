"""
工作流执行引擎核心模块

该模块负责工作流的解析、执行和状态管理。
"""

import logging
import json
import time
import traceback
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
        self.execution_id = execution_id
        self._execution = WorkflowExecution.objects.get(id=execution_id)
        self._workflow = self._execution.workflow
        self._project = self._workflow.project
        self._container = self._project.container
        self._definition = self._workflow.definition
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
                    
                    # 更新组件执行记录
                    component_execution.status = 'completed' if result.success else 'failed'
                    component_execution.end_time = timezone.now()
                    component_execution.outputs = result.outputs
                    if not result.success:
                        component_execution.error = result.error_message
                    component_execution.save()
                    
                    self._log_info(f"组件 {node_id} ({component_id}) 执行{'成功' if result.success else '失败'}")
                    
                except Exception as e:
                    self._log_error(f"执行组件 {node_id} ({component_id}) 时出错: {str(e)}")
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
                
                # 将最终结果汇总
                final_results = {}
                for node_id, result in self._component_results.items():
                    if result.success:
                        final_results[node_id] = {
                            'outputs': result.outputs,
                            'component_id': self._node_data[node_id].get('component_id'),
                            'component_type': self._node_data[node_id].get('component_type'),
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
            message: 日志信息
        """
        logger.info(f"工作流执行 #{self._execution_id}: {message}")
        self._execution.logs += f"[{timezone.now().isoformat()}] {message}\n"
        self._execution.save()
    
    def _log_error(self, message: str) -> None:
        """
        记录错误日志
        
        Args:
            message: 错误信息
        """
        logger.error(f"工作流执行 #{self._execution_id}: {message}")
        self._execution.logs += f"[{timezone.now().isoformat()}] 错误: {message}\n"
        self._execution.save()


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
