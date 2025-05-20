import React, { useRef, useCallback, useState, useEffect } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Background,
  Controls,
  useReactFlow,
  NodeTypes,
  Panel,
  Node
} from 'reactflow';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { ArrowLeft, FileCode, Download, ChevronLeft, ChevronRight, Sliders, Play, Save, Trash2, Eye, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import ComponentNode from '@/components/workflows/ComponentNode';
import ComponentPanel from '@/components/workflows/ComponentPanel';
import PropertiesPanel from '@/components/workflows/PropertiesPanel';
import useWorkflowStore, { ComponentDefinition } from '@/store/workflowStore';
import allComponents from '@/components/workflows/componentDefinitions';
import { cn } from '@/lib/utils';
import { getProject } from '@/services/projects';
import 'reactflow/dist/style.css';
import { Modal } from 'antd';

// Helper function to get CSRF token from cookies
function getCookie(name: string): string | null {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// 结果展示面板组件
const ResultViewPanel = ({ outputs, nodeLabel }: { outputs: any, nodeLabel: string }) => {
  // 获取要显示的图像数据
  const getImageData = () => {
    // 直接图像输出
    if (outputs.image) return outputs.image;
    
    // 标准图表格式
    if (outputs.chart) return outputs.chart;
    
    // 折线图数据
    if (outputs.roc_data && outputs.roc_data.image) return outputs.roc_data.image;
    
    // 混淆矩阵数据
    if (outputs.confusion_matrix && 
        outputs.confusion_matrix.confusion_matrix && 
        outputs.confusion_matrix.confusion_matrix.image) {
      return outputs.confusion_matrix.confusion_matrix.image;
    }
    
    // 检查嵌套输出格式
    if (typeof outputs === 'object') {
      for (const key in outputs) {
        const value = outputs[key];
        if (value && typeof value === 'object') {
          if ('chart' in value && typeof value.chart === 'string') return value.chart;
          if ('image' in value && typeof value.image === 'string') return value.image;
        }
      }
    }
    
    return '';
  };
  
  const imageData = getImageData();
  const hasImageData = imageData !== '';
  
  // 检测输出类型
  const getOutputType = () => {
    // 检查是否有DataFrame数据
    if (outputs.data && Array.isArray(outputs.data)) {
      return 'dataframe';
    }
    
    // 检查常见的图表类型
    if (outputs.roc_data) return 'chart-line';
    if (outputs.confusion_matrix) return 'chart-heatmap';
    if (outputs.chart_type) return `chart-${outputs.chart_type}`;
    
    // 检查CSV组件特有的数据结构
    if (outputs.columns && outputs.data_sample) {
      return 'csv-data';
    }
    
    // 默认为通用数据
    return 'generic';
  };
  
  // 获取精度指标
  const getAccuracy = () => {
    if (outputs.confusion_matrix && outputs.confusion_matrix.accuracy !== undefined) {
      return outputs.confusion_matrix.accuracy;
    }
    return outputs.accuracy;
  };
  
  // 获取AUC值
  const getAUC = () => {
    if (outputs.roc_data && outputs.roc_data.auc) {
      return outputs.roc_data.auc[0];
    }
    return outputs.auc;
  };
  
  const outputType = getOutputType();
  const accuracy = getAccuracy();
  const auc = getAUC();

  // 渲染DataFrame或表格数据
  const renderTableData = () => {
    // 检查是否为CSV输入组件的dataset格式
    if (outputs.dataset) {
  return (
        <div className="p-3 bg-slate-800 rounded-md">
          <p className="text-slate-300">CSV数据加载成功，信息如下：</p>
          
          {/* 数据形状信息 */}
          {outputs.dataset.info && outputs.dataset.info.shape && (
            <div className="mt-3 p-2 bg-slate-700/50 rounded-lg">
              <div className="text-sm text-white font-semibold mb-1">数据集信息:</div>
              <div className="flex gap-4">
                <div className="text-xs text-green-300">
                  <span className="text-slate-400">行数:</span> {outputs.dataset.info.shape[0]?.toLocaleString()}
                </div>
                <div className="text-xs text-green-300">
                  <span className="text-slate-400">列数:</span> {outputs.dataset.info.shape[1]?.toLocaleString()}
                </div>
              </div>
            </div>
          )}
          
          {/* 列信息 */}
          {outputs.dataset.columns && (
            <div className="mt-3 p-2 bg-slate-700/50 rounded-lg">
              <div className="text-sm text-white font-semibold mb-1">列名:</div>
              <div className="flex flex-wrap gap-2 max-h-20 overflow-y-auto custom-scrollbar">
                {outputs.dataset.columns.map((col: string, idx: number) => (
                  <div key={idx} className="text-xs px-2 py-1 bg-slate-600/50 rounded text-slate-300">{col}</div>
                ))}
              </div>
            </div>
          )}
          
          {/* 数据类型信息 */}
          {outputs.dataset.dtypes && (
            <div className="mt-3 p-2 bg-slate-700/50 rounded-lg">
              <div className="text-sm text-white font-semibold mb-1">数据类型:</div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-24 overflow-y-auto custom-scrollbar">
                {Object.entries(outputs.dataset.dtypes).map(([col, type]: [string, any], idx: number) => (
                  <div key={idx} className="text-xs flex justify-between gap-2 px-2 py-1 bg-slate-600/30 rounded">
                    <span className="text-slate-300 truncate" title={col}>{col}</span>
                    <span className="text-blue-300 text-right">{type}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* 数据样本展示 - 以缩略形式展示JSON */}
          <div className="mt-3">
            <div className="text-sm text-white font-semibold mb-1">完整数据:</div>
            <details>
              <summary className="cursor-pointer text-xs text-slate-300 mb-1 p-1 hover:bg-slate-700/50 rounded">
                &#x25BC; 展开/收起原始数据 (JSON格式)
              </summary>
              <pre className="mt-2 p-3 bg-slate-900 rounded-md overflow-auto text-xs text-slate-300 max-h-[35vh] whitespace-pre-wrap break-all custom-scrollbar">
                {JSON.stringify(outputs, null, 2)}
              </pre>
            </details>
          </div>
        </div>
      );
    }
    
    // CSV输入组件的特殊处理
    if (outputType === 'csv-data' && outputs.columns && outputs.data_sample) {
      return (
        <div className="overflow-x-auto w-full custom-scrollbar">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr className="bg-slate-700">
                {outputs.columns.map((col: string, idx: number) => (
                  <th key={idx} className="px-4 py-2 text-left text-white border border-slate-600">{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {outputs.data_sample.map((row: any[], rowIdx: number) => (
                <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-slate-800' : 'bg-slate-850'}>
                  {row.map((cell, cellIdx) => (
                    <td key={cellIdx} className="px-4 py-2 border border-slate-600 text-slate-300">
                      {String(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 text-xs text-slate-400 italic">
            {outputs.total_rows ? `显示 ${outputs.data_sample.length} 行，共 ${outputs.total_rows} 行` : ''}
          </div>
        </div>
      );
    }
    
    // 其他数据处理组件的数据展示
    if (outputType === 'dataframe' && Array.isArray(outputs.data)) {
      // 提取列名（假设第一行数据包含所有键）
      const columns = outputs.data.length > 0 ? Object.keys(outputs.data[0]) : [];
      
      return (
        <div className="overflow-x-auto w-full">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr className="bg-slate-700">
                {columns.map((col, idx) => (
                  <th key={idx} className="px-4 py-2 text-left text-white border border-slate-600">{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {outputs.data.slice(0, 10).map((row: any, rowIdx: number) => (
                <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-slate-800' : 'bg-slate-850'}>
                  {columns.map((col, cellIdx) => (
                    <td key={cellIdx} className="px-4 py-2 border border-slate-600 text-slate-300">
                      {String(row[col])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 text-xs text-slate-400 italic">
            {outputs.data.length > 10 ? `显示前 10 行，共 ${outputs.data.length} 行` : `共 ${outputs.data.length} 行`}
          </div>
        </div>
      );
    }
    
    // 默认情况：JSON显示
    return (
      <div className="p-3 bg-slate-800 rounded-md">
        <p className="text-slate-300">该组件执行成功，输出如下：</p>
        <pre className="mt-3 p-3 bg-slate-900 rounded-md overflow-x-auto whitespace-pre-wrap text-xs text-slate-300 max-h-[30vh]">
          {JSON.stringify(outputs, null, 2)}
        </pre>
      </div>
    );
  };

  return (
    <div className="w-full">
      {hasImageData ? (
        <div className="flex flex-col items-center">
          <img 
            src={`data:image/png;base64,${imageData}`} 
            alt="可视化结果" 
            className="max-w-full mb-3" 
          />
          
          <div className="flex gap-3 mt-2">
            {outputType === 'chart-line' && auc !== undefined && (
              <div className="text-sm px-3 py-1 bg-green-600/30 text-green-300 rounded-md">
                AUC值: {auc.toFixed(4)}
              </div>
            )}
            {outputType === 'chart-heatmap' && accuracy !== undefined && (
              <div className="text-sm px-3 py-1 bg-green-600/30 text-green-300 rounded-md">
                准确率: {accuracy.toFixed(4)}
              </div>
            )}
          </div>
        </div>
      ) : (
        renderTableData()
      )}
    </div>
  );
};

// 定义节点类型
const nodeTypes: NodeTypes = {
  component: ComponentNode,
};

// 工作流设计器核心组件
const WorkflowDesignerContent: React.FC = () => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect, setSelectedNode } = useWorkflowStore();
  const reactFlowInstance = useReactFlow();
  const [executing, setExecuting] = useState(false);
  const [executionId, setExecutionId] = useState<number | null>(null); // 添加执行ID状态
  const [saving, setSaving] = useState(false);
  const [workflowCompleted, setWorkflowCompleted] = useState(false);
  const [showResultsDialog, setShowResultsDialog] = useState(false);
  // 添加轮询取消标志
  const pollingCancelRef = useRef<boolean>(false);
  
  const routeParams = useParams<{ id: string; workflowId?: string }>(); 
  const navigate = useNavigate();
  const projectId = routeParams.id;
  const [workflowId, setWorkflowId] = useState<string | undefined>(routeParams.workflowId);
  
  // 增加组件挂载状态跟踪
  const [componentMounted, setComponentMounted] = useState(false);
  const [loadAttempted, setLoadAttempted] = useState(false);
  const [isLoadingWorkflow, setIsLoadingWorkflow] = useState(false); // 添加加载状态标记
  const [windowSize, setWindowSize] = useState({ width: window.innerWidth, height: window.innerHeight });
  
  // 在窗口大小改变时更新状态
  useEffect(() => {
    const handleResize = () => {
      setWindowSize({ width: window.innerWidth, height: window.innerHeight });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 在组件挂载时标记已挂载
  useEffect(() => {
    console.log('[WorkflowDesignerContent] 组件挂载');
    setComponentMounted(true);
    
    // 组件卸载时清除状态
    return () => {
      console.log('[WorkflowDesignerContent] 组件卸载');
      setComponentMounted(false);
      setLoadAttempted(false);
    };
  }, []);

  // 在useEffect中打印一次projectId确保其正确获取
  useEffect(() => {
    console.log('[WorkflowDesignerContent] Initial projectId from routeParams:', projectId);
    console.log('[WorkflowDesignerContent] Initial workflowId from routeParams:', workflowId);
  }, [projectId, workflowId]);

  // 提取工作流加载为单独函数
  const loadWorkflowDefinition = useCallback(async (id: string) => {
    if (!id) {
      console.warn('[loadWorkflowDefinition] 未提供workflowId，无法加载工作流');
      return false;
    }
      
    // 如果已经在加载中，避免重复请求
    if (isLoadingWorkflow) {
      console.log('[loadWorkflowDefinition] 已有加载请求正在进行中，跳过');
      return false;
    }

    console.log(`[loadWorkflowDefinition] 开始加载工作流 ID: ${id}`);
    setIsLoadingWorkflow(true); // 标记加载开始
          
          try {
      const response = await fetch(`/api/project/workflows/${id}/`);
      
            if (response.ok) {
              const workflowData = await response.json();
        console.log('[loadWorkflowDefinition] 加载工作流定义成功:', workflowData);
              
              // 将工作流定义加载到store中
              if (workflowData.definition && workflowData.definition.nodes && workflowData.definition.edges) {
          console.log('[loadWorkflowDefinition] 正在加载工作流节点到store, 节点数量:', workflowData.definition.nodes.length);
                
          // 预处理节点数据，确保文件路径信息和类型正确
                if (workflowData.definition.nodes.length > 0) {
                  workflowData.definition.nodes = workflowData.definition.nodes.map((node: Node) => {
              // 确保每个节点都有type属性
              if (!node.type) {
                node.type = 'component';
                console.log(`[loadWorkflowDefinition] 为节点 ${node.id} 添加缺失的type属性: component`);
              }
              
              // 如果是CSV输入组件，处理文件路径
                    if (node.data && node.data.component && node.data.component.id === 'csv-input') {
                console.log(`[loadWorkflowDefinition] 检查CSV节点参数:`, node.data.params);
                      
                      // 修复文件路径和文件信息
                      if (node.data.params) {
                        const filePathParam = node.data.params.file_path;
                        const fileInfoParam = node.data.params._file_info;
                        
                  // 同步文件路径信息
                  if (typeof filePathParam === 'string' && filePathParam) {
                          // 从路径提取文件名
                          const fileName = filePathParam.split('/').pop() || 'data.csv';
                    // 确保存在_file_info
                    if (!fileInfoParam || typeof fileInfoParam !== 'object') {
                          node.data.params._file_info = {
                            name: fileName,
                            serverPath: filePathParam
                          };
                    } else if (typeof fileInfoParam === 'object') {
                      // 更新serverPath
                      node.data.params._file_info.serverPath = filePathParam;
                      // 如果没有名称，添加名称
                      if (!node.data.params._file_info.name) {
                        node.data.params._file_info.name = fileName;
                      }
                    }
                    console.log(`[loadWorkflowDefinition] 更新文件信息:`, node.data.params._file_info);
                        }
                  // 从file_info恢复file_path
                  else if (fileInfoParam && typeof fileInfoParam === 'object' && fileInfoParam.serverPath &&
                            (!filePathParam || typeof filePathParam === 'object' || filePathParam === '')) {
                          node.data.params.file_path = fileInfoParam.serverPath;
                    console.log(`[loadWorkflowDefinition] 从_file_info恢复file_path:`, fileInfoParam.serverPath);
                        }
                  // 修复无效文件路径
                  else if (node.data.params && typeof node.data.params.file_path === 'object') {
                    console.log(`[loadWorkflowDefinition] 修复无效文件路径`);
                    if (fileInfoParam && fileInfoParam.serverPath) {
                      node.data.params.file_path = fileInfoParam.serverPath;
                          } else {
                            node.data.params.file_path = null;
                          }
                        }
                      }
                    }
                    
                    return node;
                  });
                }
                
          // 设置标志，表示已尝试加载
          setLoadAttempted(true);
          
          console.log('[loadWorkflowDefinition] 正在更新工作流到store...');
          
          // 清空现有节点，然后使用延迟加载新节点的方式
          // 这有助于ReactFlow组件正确识别节点状态变化
          useWorkflowStore.setState({ nodes: [], edges: [] });
          
          // 使用延迟确保清空操作完成后再加载新节点
                setTimeout(() => {
            // 使用store的loadWorkflow函数加载完整工作流
            useWorkflowStore.getState().loadWorkflow({
                    ...workflowData,
                    nodes: workflowData.definition.nodes,
                    edges: workflowData.definition.edges
                  });
                  
            console.log('[loadWorkflowDefinition] 工作流加载完成，节点数量:', workflowData.definition.nodes.length);
            console.log('[loadWorkflowDefinition] 节点IDs:', workflowData.definition.nodes.map((n: Node) => n.id));
            
            // 显示成功通知 - 不使用toast，因为父组件已经有加载成功的提示
            // 移除这个成功提示，由父组件统一显示
            // toast.success(`工作流 "${workflowData.name}" 加载成功`);
            
            // 从sessionStorage获取工作流名称并显示成功提示
            const lastLoadedWorkflowName = sessionStorage.getItem('last_loaded_workflow_name');
            if (lastLoadedWorkflowName) {
              toast.success(`已加载最新工作流: ${lastLoadedWorkflowName}`);
              // 显示后立即清除，避免重复显示
              sessionStorage.removeItem('last_loaded_workflow_name');
              } else {
              toast.success(`工作流 "${workflowData.name}" 加载成功`);
              }
          }, 50);
          
          return true;
            } else {
          console.warn('[loadWorkflowDefinition] 工作流定义不完整:', workflowData);
          toast.error('工作流定义不完整，无法加载');
          return false;
              }
            } else {
        console.error('[loadWorkflowDefinition] 加载工作流定义失败:', response.status);
        toast.error(`加载工作流失败: ${response.status}`);
        return false;
            }
          } catch (error) {
      console.error('[loadWorkflowDefinition] 加载工作流定义出错:', error);
      toast.error('加载工作流时发生错误');
      return false;
    } finally {
      setIsLoadingWorkflow(false); // 无论成功失败，标记加载结束
    }
  }, [isLoadingWorkflow]);

  // 检测URL变化，更新workflowId，并加载工作流
  useEffect(() => {
    const newWorkflowId = routeParams.workflowId;
    
    console.log('[WorkflowDesignerContent] 路由参数中的workflowId:', newWorkflowId);
    console.log('[WorkflowDesignerContent] 当前状态中的workflowId:', workflowId);
    
    if (newWorkflowId !== workflowId) {
      console.log('[WorkflowDesignerContent] Updating workflowId from URL:', newWorkflowId);
      setWorkflowId(newWorkflowId);
      
      // 如果URL中有workflowId，且组件已挂载，则尝试加载工作流定义
      if (newWorkflowId && componentMounted && reactFlowInstance) {
        // 加载前设置标志，防止其他useEffect重复加载
        setLoadAttempted(true);
        loadWorkflowDefinition(newWorkflowId);
      }
    }
  }, [routeParams.workflowId, workflowId, componentMounted, reactFlowInstance, loadWorkflowDefinition]);
  
  // 合并之前的两个useEffect，只保留一个备用加载逻辑
  useEffect(() => {
    // 仅在以下情况运行:
    // 1. 组件已挂载 
    // 2. ReactFlow实例已初始化
    // 3. 没有workflowId或未尝试加载过
    // 4. 没有节点 (画布是空的)
    if (componentMounted && reactFlowInstance && (!workflowId || !loadAttempted) && nodes.length === 0) {
      console.log('[WorkflowDesignerContent] 尝试备用加载流程');
      
      // 方式1: 使用已知workflowId但尚未尝试加载
      if (workflowId && !loadAttempted) {
        console.log('[WorkflowDesignerContent] 使用已有workflowId加载工作流:', workflowId);
        setLoadAttempted(true);
        loadWorkflowDefinition(workflowId);
        return;
      }
      
      // 方式2: 尝试从localStorage获取path
      const lastPath = localStorage.getItem('lastPath');
      const lastWorkflowId = lastPath?.match(/\/workflows\/(\d+)/)?.[1];
      
      if (lastWorkflowId && lastPath?.includes(`/projects/${projectId}/`) && !loadAttempted) {
        console.log('[WorkflowDesignerContent] 从localStorage找到workflowId:', lastWorkflowId);
        
        // 更新URL
        const newPath = `/dashboard/projects/${projectId}/workflows/${lastWorkflowId}`;
        navigate(newPath, { replace: true });
        
        // 设置状态
        setWorkflowId(lastWorkflowId);
        setLoadAttempted(true);
        loadWorkflowDefinition(lastWorkflowId);
      }
    }
  }, [componentMounted, reactFlowInstance, workflowId, loadAttempted, nodes.length, projectId, navigate, loadWorkflowDefinition]);

  // 模态框状态
  const [clearDialogOpen, setClearDialogOpen] = useState(false);

  // 处理节点选择
  const handleNodeClick = (_: React.MouseEvent, node: any) => {
    setSelectedNode(node);
  };

  // 处理节点拖放结束
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // 修改fixNodeParametersField函数，确保文件路径被正确处理
  const fixNodeParametersField = (nodes: Node[]) => {
    return nodes.map((node) => {
      // 确保节点包含params和component
      if (node.data && node.data.component) {
        // 创建一个新节点副本
        const nodeClone = {...node};
        
        // 如果不存在params，初始化为空对象
        if (!nodeClone.data.params) {
          nodeClone.data.params = {};
        }
        
        // 确保包含parameters字段，用于后端
        // 重要：不能只是引用params，因为后面可能会将它们分别修改
        nodeClone.data.parameters = {...nodeClone.data.params};
        
        // 特殊处理CSV输入组件的文件路径参数
        if (node.data.component.id === 'csv-input') {
          const fileParam = nodeClone.data.params.file_path;
          const fileInfo = nodeClone.data.params._file_info;
          
          // 情况1：如果是File对象，不能传递到后端，设为null
          if (fileParam instanceof File) {
            nodeClone.data.parameters.file_path = null;
            console.log(`[FixNodeParameters] CSV节点 ${node.id} 包含File对象，在parameters中设置为null`);
          }
          // 情况2：如果有文件信息对象中包含服务器路径，使用它
          else if (fileInfo && typeof fileInfo === 'object' && fileInfo.serverPath) {
            nodeClone.data.parameters.file_path = fileInfo.serverPath;
            // 修复：同时更新params.file_path字段，确保前端状态一致
            nodeClone.data.params.file_path = fileInfo.serverPath;
            console.log(`[FixNodeParameters] CSV节点 ${node.id} 使用fileInfo中的服务器路径: ${fileInfo.serverPath}`);
          }
          // 情况3：如果是有效字符串路径，直接使用
          else if (typeof fileParam === 'string' && fileParam.length > 0) {
            nodeClone.data.parameters.file_path = fileParam;
            console.log(`[FixNodeParameters] CSV节点 ${node.id} 使用现有字符串路径: ${fileParam}`);
            
            // 修复：如果文件路径是字符串但没有fileInfo，创建一个基本的fileInfo
            if (!fileInfo || typeof fileInfo !== 'object') {
              // 从路径中提取文件名
              const fileName = fileParam.split('/').pop() || 'unknown.csv';
              nodeClone.data.params._file_info = {
                name: fileName,
                serverPath: fileParam
              };
              console.log(`[FixNodeParameters] CSV节点 ${node.id} 创建了缺失的fileInfo: ${JSON.stringify(nodeClone.data.params._file_info)}`);
            }
          }
          // 情况4：如果以上都不是，确保设置为null而不是空对象
          else if (fileParam === null || fileParam === undefined || 
                  (typeof fileParam === 'object' && Object.keys(fileParam).length === 0)) {
            nodeClone.data.parameters.file_path = null;
            nodeClone.data.params.file_path = null;
            console.log(`[FixNodeParameters] CSV节点 ${node.id} 参数无效，设置为null`);
          }
        }
        
        console.log(`[FixNodeParameters] 节点 ${node.id} 的parameters:`, nodeClone.data.parameters);
        
        return nodeClone;
      }
      return node;
    });
  };

  // 处理节点放置
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect();
      if (!reactFlowBounds || !event.dataTransfer.getData('application/reactflow')) {
        return;
      }

      const componentData = JSON.parse(event.dataTransfer.getData('application/reactflow')) as ComponentDefinition;
      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      useWorkflowStore.getState().addNode(componentData, position);
    },
    [reactFlowInstance]
  );
  
  // 自动保存工作流
  const autoSaveWorkflow = async (idToForceUpdate?: string) => {
    if (nodes.length === 0) {
      toast.error('工作流为空，无需保存');
      return null;
    }

    try {
      setSaving(true);
      
      // 优先使用强制更新的ID，其次是当前workflowId状态
      const idToUse = idToForceUpdate || workflowId;
      
      // 先记录是否有ID，用于最后确定是新建还是更新
      const isUpdatingExisting = !!idToUse;
      
      console.log(`[AutoSaveWorkflow] 开始${isUpdatingExisting ? '更新' : '创建'}工作流，ID: ${idToUse || 'NEW'}`);
      
      const store = useWorkflowStore.getState();
      const currentWorkflowFromStore = store.currentWorkflow;

      // 获取最新的节点和边缘数据，确保不使用可能为空的旧数据
      const currentNodesFromStore = store.nodes;
      const currentEdgesFromStore = store.edges;
      
      console.log(`[AutoSaveWorkflow] Current nodes in store (count: ${currentNodesFromStore.length}):`, 
                JSON.stringify(currentNodesFromStore.map(n => n.id), null, 2));
      
      // 修复节点参数映射，确保Parameters字段存在
      const fixedNodes = fixNodeParametersField(currentNodesFromStore);
      
      // 处理节点参数，特别是文件参数
      const processedNodes = fixedNodes.map(node => {
        if (node.data?.component?.id === 'csv-input') {
          const nodeClone = { ...node };
          
          // 处理文件参数
          if (nodeClone.data.params && nodeClone.data.params.file_path) {
            const fileParam = nodeClone.data.params.file_path;
            const fileInfo = nodeClone.data.params._file_info || {};
            
            console.log(`[AutoSaveWorkflow] Processing CSV node ${node.id} file_path:`, 
                      typeof fileParam, fileParam instanceof File ? 'File object' : fileParam);
            console.log(`[AutoSaveWorkflow] File info:`, fileInfo);
            
            // 情况1：如果是File对象，不能直接传输，需要设为null
            if (fileParam instanceof File) {
              // 保存文件信息，但不传递File对象
              nodeClone.data.params.file_path = null;
              nodeClone.data.parameters.file_path = null;
              
              // 确保文件信息被保存
              if (!nodeClone.data.params._file_info) {
                nodeClone.data.params._file_info = {
                  name: fileParam.name,
                  size: fileParam.size,
                  type: fileParam.type,
                  lastModified: fileParam.lastModified
                };
              }
              console.log(`[AutoSaveWorkflow] Removed File object from params, saved file info`);
            } 
            // 情况2：如果已经有服务器路径，保留
            else if (typeof fileParam === 'string' && fileParam) {
              // 确保parameters与params同步
              const normalizedPath = fileParam.replace(/\\/g, '/');
              nodeClone.data.params.file_path = normalizedPath;
              nodeClone.data.parameters.file_path = normalizedPath;
              console.log(`[AutoSaveWorkflow] Using existing server path: ${normalizedPath}`);
              
              // 更新文件信息中的服务器路径
              if (nodeClone.data.params._file_info) {
                nodeClone.data.params._file_info.serverPath = normalizedPath;
              }
            }
            // 情况3：如果有fileInfo中的服务器路径，使用它
            else if (fileInfo && fileInfo.serverPath) {
              const normalizedPath = fileInfo.serverPath.replace(/\\/g, '/');
              nodeClone.data.params.file_path = normalizedPath;
              nodeClone.data.parameters.file_path = normalizedPath;
              console.log(`[AutoSaveWorkflow] Using path from fileInfo: ${normalizedPath}`);
            }
            // 情况4：如果是空对象，确保设置为null
            else if (typeof fileParam === 'object' && Object.keys(fileParam).length === 0) {
              nodeClone.data.params.file_path = null;
              nodeClone.data.parameters.file_path = null;
              console.log(`[AutoSaveWorkflow] Setting empty object file_path to null`);
            }
          }
          
          return nodeClone;
        }
        return node;
      });

      // 准备工作流定义（使用处理后的节点）
      const latestDefinition = {
        nodes: processedNodes,
        edges: currentEdgesFromStore
      };
      
      // 准备请求数据的基础结构
      const workflowPayload: any = {
        definition: latestDefinition,
        version: currentWorkflowFromStore?.version || 1,
        project: Number(projectId), // projectId 总是需要的，确保转换为数字类型
      };
      
      // 获取工作流名称和描述
      if (isUpdatingExisting) {
        // 对于更新现有工作流，获取正确的名称和描述
        try {
          const checkResponse = await fetch(`/api/project/workflows/${idToUse}/`);
          if (checkResponse.ok) {
            const existingWorkflow = await checkResponse.json();
            workflowPayload.name = existingWorkflow.name;
            workflowPayload.description = existingWorkflow.description || '';
            console.log(`[AutoSaveWorkflow] 获取现有工作流信息成功: name=${existingWorkflow.name}`);
          } else {
            console.warn(`[AutoSaveWorkflow] 无法获取工作流 ${idToUse} 信息，使用备用名称`);
            // 回退到存储中的信息或构造一个名称
            if (currentWorkflowFromStore && String(currentWorkflowFromStore.id) === idToUse) {
              workflowPayload.name = currentWorkflowFromStore.name;
              workflowPayload.description = currentWorkflowFromStore.description || '';
            } else {
              // 这种情况应该很少发生，但保留作为备选
              workflowPayload.name = `工作流_${idToUse}`;
              workflowPayload.description = '自动保存的工作流';
            }
          }
        } catch (error) {
          console.error(`[AutoSaveWorkflow] 获取工作流信息出错: ${error}`);
          // 使用回退方案
          workflowPayload.name = currentWorkflowFromStore?.name || `工作流_${idToUse}`;
          workflowPayload.description = currentWorkflowFromStore?.description || '自动保存的工作流';
        }
      } else {
        // 创建新的工作流，生成一个唯一的名称
        const timestamp = new Date().getTime();
        const randomStr = Math.random().toString(36).substring(2, 8);
        workflowPayload.name = `工作流_${timestamp.toString().slice(-6)}_${randomStr}`;
        workflowPayload.description = '自动保存的工作流';
        console.log(`[AutoSaveWorkflow] 为新工作流生成名称: ${workflowPayload.name}`);
      }
      
      const csrftoken = getCookie('csrftoken');
      const headers: HeadersInit = {
        'Content-Type': 'application/json'
      };
      if (csrftoken) {
        headers['X-CSRFToken'] = csrftoken;
      }
      
      console.log(`[AutoSaveWorkflow] API调用方法: ${isUpdatingExisting ? 'PUT' : 'POST'}, ID: ${idToUse || 'NEW'}`);
      
      // 执行API请求，根据是否有ID决定使用PUT还是POST
      let response;
      let savedWorkflowData;
      
      if (isUpdatingExisting) {
        // 更新现有工作流 (PUT)
        response = await fetch(`/api/project/workflows/${idToUse}/`, {
          method: 'PUT',
          headers: headers,
          body: JSON.stringify(workflowPayload)
        });
      } else {
        // 创建新工作流 (POST)
        response = await fetch('/api/project/workflows/', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(workflowPayload)
        });
      }
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error(`[AutoSaveWorkflow] ${isUpdatingExisting ? '更新' : '创建'}工作流失败:`, 
                    response.status, errorData);
        throw new Error(`保存工作流失败: ${response.status} - ${JSON.stringify(errorData)}`);
      }
      
      // 解析响应并更新状态
      savedWorkflowData = await response.json();
      console.log('[AutoSaveWorkflow] 保存成功，后端返回的数据:', savedWorkflowData);
      
      // 使用toast显示具体的保存信息，包含工作流名称和ID
      toast.success(`${isUpdatingExisting ? '更新' : '创建'}工作流成功: ${savedWorkflowData.name} (ID: ${savedWorkflowData.id})`);
      
      // 更新store中的currentWorkflow为后端返回的最新数据
      store.setCurrentWorkflow(savedWorkflowData);

      // 更新URL和workflowId状态
      const newWorkflowId = String(savedWorkflowData.id);
      if (newWorkflowId !== workflowId) {
        console.log(`[AutoSaveWorkflow] 更新workflowId: ${workflowId} -> ${newWorkflowId}`);
        
        // 构建新的URL路径
        const newPath = `/dashboard/projects/${projectId}/workflows/${newWorkflowId}`;
        
        // 保存路径到localStorage，确保刷新后能恢复
        localStorage.setItem('lastPath', newPath);
        
        // 使用navigate而不是replaceState来更新URL，确保路由参数会被正确更新
        navigate(newPath, { replace: true });
        
        // 更新组件状态
        setWorkflowId(newWorkflowId);
      } else {
        // 即使ID没变，也要确保localStorage中有正确的路径
        const currentPath = `/dashboard/projects/${projectId}/workflows/${newWorkflowId}`;
        localStorage.setItem('lastPath', currentPath);
      }
      
      return savedWorkflowData;
    } catch (error) {
      console.error('[AutoSaveWorkflow] 错误:', error);
      toast.error(`保存工作流失败：${error instanceof Error ? error.message : '未知错误'}`);
      return null;
    } finally {
      setSaving(false);
    }
  };

  // 将autoSaveWorkflow函数暴露给window对象，以便PropertiesPanel调用
  useEffect(() => {
    // 将autoSaveWorkflow函数暴露给window对象，以便其他组件调用
    window.autoSaveWorkflow = async () => {
      console.log('[window.autoSaveWorkflow] 被调用');
      return await autoSaveWorkflow();
    };
    
    // 清理函数
    return () => {
      // @ts-ignore
      window.autoSaveWorkflow = undefined;
    };
  }, []);

  // 清空画布
  const clearCanvas = () => {
    useWorkflowStore.setState({ nodes: [], edges: [], selectedNode: null });
    toast.info('画布已清空');
    setClearDialogOpen(false);
    setWorkflowCompleted(false);
  };

  // 添加停止执行的函数
  const stopExecution = async () => {
    if (!executionId) {
      toast.error('没有正在执行的工作流');
      return;
    }

    console.log(`[StopExecution] 正在停止工作流执行，执行ID: ${executionId}`);
    
    // 立即设置轮询取消标志，中断轮询
    pollingCancelRef.current = true;
    
    try {
      const csrftoken = getCookie('csrftoken');
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (csrftoken) {
        headers['X-CSRFToken'] = csrftoken;
      }

      const response = await fetch(`/api/project/workflow-executions/${executionId}/cancel/`, {
        method: 'POST',
        headers: headers
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: '取消执行失败，无法解析错误响应' }));
        console.error('[StopExecution] Cancel API error response:', errorData);
        toast.error(`工作流执行取消失败: ${errorData.detail || response.statusText}`);
        return;
      }

      // 在取消请求成功后立即将节点状态更新为取消状态
      const updatedNodes = nodes.map(node => {
        if (node.data.status === 'running') {
          return {
            ...node,
            data: {
              ...node.data,
              status: 'cancelled',
            }
          };
        }
        return node;
      });
      useWorkflowStore.getState().setNodes(updatedNodes);

      toast.success('已成功停止工作流执行');
      // 立即重置执行状态
      setExecuting(false);
      setExecutionId(null);
      // 不在这里立即设置executing=false，应等待后端确认取消
    } catch (error) {
      console.error('[StopExecution] Error during cancellation:', error);
      toast.error(`停止工作流执行时发生错误: ${error instanceof Error ? error.message : '未知错误'}`);
      // 即使发生错误，也重置状态避免UI卡住
      setExecuting(false);
      setExecutionId(null);
    }
  };

  // 添加轮询执行状态的函数
  const pollExecutionStatus = async (executionId: number) => {
    console.log(`[PollExecutionStatus] 开始轮询执行状态，执行ID: ${executionId}`);
    
    const maxPolls = 120; // 最多轮询120次，每次间隔1秒，即最多等待2分钟
    let pollCount = 0;
    
    // 重置轮询取消标志
    pollingCancelRef.current = false;
    
    const csrftoken = getCookie('csrftoken');
    const headers: HeadersInit = {};
    if (csrftoken) {
      headers['X-CSRFToken'] = csrftoken;
    }
    
    while (pollCount < maxPolls) {
      // 检查是否应该取消轮询
      if (pollingCancelRef.current) {
        console.log(`[PollExecutionStatus] 检测到取消标志，立即终止轮询`);
        // 确保执行状态被重置
        setExecuting(false);
        setExecutionId(null);
        return;
      }
      
      try {
        pollCount++;
        
        // 获取执行状态
        const response = await fetch(`/api/project/workflow-executions/${executionId}/`);
        
        if (!response.ok) {
          console.error(`[PollExecutionStatus] 获取执行状态失败: ${response.status}`);
          
          // 如果返回404或403，说明工作流可能被删除或没有权限，停止轮询
          if (response.status === 404 || response.status === 403) {
            console.log(`[PollExecutionStatus] 工作流不存在或无权限，停止轮询`);
            setExecuting(false);
            setExecutionId(null);
            return;
          }
          
          // 如果请求失败，继续尝试
          await new Promise(resolve => setTimeout(resolve, 1000));
          continue;
        }
        
        const executionData = await response.json();
        console.log(`[PollExecutionStatus] 执行状态: ${executionData.status}`);
        
        // 如果工作流执行完成、失败或取消，立即结束轮询
        if (executionData.status === 'completed' || executionData.status === 'failed' || executionData.status === 'cancelled') {
          console.log(`[PollExecutionStatus] 工作流执行状态: ${executionData.status}，停止轮询`);
          
          // 标记工作流已完成执行
          setWorkflowCompleted(true);
          
          try {
            // 最后一次获取组件状态
            const componentsResponse = await fetch(`/api/project/workflow-executions/${executionId}/components/`);
            
            if (componentsResponse.ok) {
              const componentsData = await componentsResponse.json();
              
              // 更新节点状态
              const updatedNodes = nodes.map(node => {
                // 查找该节点对应的执行结果
                const componentResult = componentsData.find((comp: any) => comp.node_id === node.id);
                
                if (componentResult) {
                  // 将后端返回的状态转换为前端组件状态
                  let nodeStatus: 'idle' | 'running' | 'success' | 'error' | 'cancelled' = 'idle';
                  
                  switch (componentResult.status) {
                    case 'completed':
                      nodeStatus = 'success';
                      break;
                    case 'failed':
                      nodeStatus = 'error';
                      break;
                    case 'running':
                      // 如果工作流被取消，所有running状态改为cancelled
                      nodeStatus = executionData.status === 'cancelled' ? 'cancelled' : 'running';
                      break;
                    case 'cancelled':
                      nodeStatus = 'cancelled';
                      break;
                    default:
                      nodeStatus = 'idle';
                  }
                  
                  return {
                    ...node,
                    data: {
                      ...node.data,
                      status: nodeStatus,
                      outputs: componentResult.outputs || {},
                    }
                  };
                }
                
                return node;
              });
              
              // 使用store更新节点
              useWorkflowStore.getState().setNodes(updatedNodes);
            }
          } catch (error) {
            console.error('[PollExecutionStatus] 获取最终组件状态出错:', error);
          }
          
          // 显示相应的提示
          if (executionData.status === 'failed') {
            toast.error('工作流执行失败，请检查日志');
          } else if (executionData.status === 'cancelled') {
            toast.warning('工作流执行已取消');
          } else {
            toast.success('工作流执行完成，可查看结果');
          }
          
          // 重置执行状态
          setExecuting(false);
          setExecutionId(null);
          return;
        }
        
        // 获取组件执行状态，及时更新组件状态
        try {
          // 不管工作流是否完成，都尝试获取组件状态并更新UI
          const componentsResponse = await fetch(`/api/project/workflow-executions/${executionId}/components/`);
          
          if (componentsResponse.ok) {
            const componentsData = await componentsResponse.json();
            console.log('[PollExecutionStatus] 获取组件执行状态:', componentsData);
            
            // 更新节点状态
            const updatedNodes = nodes.map(node => {
              // 查找该节点对应的执行结果
              const componentResult = componentsData.find((comp: any) => comp.node_id === node.id);
              
              if (componentResult) {
                // 将后端返回的状态转换为前端组件状态
                let nodeStatus: 'idle' | 'running' | 'success' | 'error' | 'cancelled' = 'idle';
                
                switch (componentResult.status) {
                  case 'completed':
                    nodeStatus = 'success';
                    break;
                  case 'failed':
                    nodeStatus = 'error';
                    break;
                  case 'running':
                    nodeStatus = 'running';
                    break;
                  case 'pending':
                  case 'queued':
                    nodeStatus = 'idle';
                    break;
                  case 'cancelled': // 添加取消状态
                    nodeStatus = 'cancelled'; 
                    break;
                  default:
                    nodeStatus = 'idle';
                }
                
                return {
                  ...node,
                  data: {
                    ...node.data,
                    status: nodeStatus,
                    outputs: componentResult.outputs || {},
                  }
                };
              }
              
              return node;
            });
            
            // 使用store更新节点
            useWorkflowStore.getState().setNodes(updatedNodes);
          }
        } catch (compError) {
          console.error('[PollExecutionStatus] 获取组件状态出错:', compError);
        }
        
        // 等待1秒后再次轮询
        await new Promise(resolve => setTimeout(resolve, 1000));
        
      } catch (error) {
        console.error(`[PollExecutionStatus] 轮询过程中出错:`, error);
        // 如果出错，继续尝试
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
    
    // 如果达到最大轮询次数仍未完成
    console.warn('[PollExecutionStatus] 达到最大轮询次数，停止轮询');
    toast.warning('工作流执行时间过长，请稍后查看结果');
    setWorkflowCompleted(true);
    // 重置执行状态，避免按钮卡在"停止执行"状态
    setExecuting(false);
    setExecutionId(null);
  };

  // 修改executeWorkflow，确保在开始新的执行前取消之前的轮询
  const executeWorkflow = async () => {
    console.log('[ExecuteWorkflow] Clicked! Nodes count:', nodes.length, 'Project ID:', projectId);

    // 如果有进行中的执行，先取消
    if (executionId) {
      // 设置取消标志
      pollingCancelRef.current = true;
      // 等待一小段时间确保之前的轮询被取消
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    // 重置工作流完成状态
    setWorkflowCompleted(false);

    if (!projectId) {
      toast.error("无法确定当前项目ID，无法执行工作流。");
      return;
    }

    if (nodes.length === 0) {
      toast.error('工作流为空，请添加组件');
      return;
    }

    // 检查CSV输入组件是否有file_path参数
    let hasValidFileParams = true;
    nodes.forEach((node: Node) => {
      if (node.data && node.data.component && node.data.component.id === 'csv-input') {
        // 获取文件参数
        const fileParam = node.data.params?.file_path;
        const fileInfo = node.data.params?._file_info;
        
        console.log(`[ExecuteWorkflow] 检查CSV节点 ${node.id} 的file_path参数:`, fileParam);
        console.log(`[ExecuteWorkflow] 检查CSV节点 ${node.id} 的_file_info:`, fileInfo);
        
        // 判断文件参数是否有效
        const isServerPathValid = 
          // 如果fileParam是字符串且有内容，可能是服务器路径
          (typeof fileParam === 'string' && fileParam.length > 0) ||
          // 或者fileInfo中有serverPath
          (fileInfo && typeof fileInfo === 'object' && fileInfo.serverPath && typeof fileInfo.serverPath === 'string');
        
        const isFileParamValid = 
          // 场景1: File对象
          (fileParam instanceof File) ||
          // 场景2: 服务器路径有效
          isServerPathValid ||
          // 场景3: 有_file_info信息但file_path可能是对象(已应用但未上传)
          (fileInfo && typeof fileInfo === 'object' && fileInfo.name);
        
        if (!isFileParamValid) {
          toast.error(`CSV输入组件 "${node.data.label}" 没有选择文件，请在右侧面板上传CSV文件`);
          hasValidFileParams = false;
        } else if (!isServerPathValid && fileParam instanceof File) {
          // 如果是File对象但还没有serverPath，将在后续上传
          console.log(`[ExecuteWorkflow] CSV节点 ${node.id} 有File对象，需要上传`);
        } else if (isServerPathValid) {
          // 已有服务器路径，直接使用
          console.log(`[ExecuteWorkflow] CSV节点 ${node.id} 已有服务器路径，无需重新上传`);
        }
      }
    });
    
    if (!hasValidFileParams) return;

    // 设置执行状态
    setExecuting(true);
    
    // 重置所有节点的状态为idle
    const nodesWithInitialStatus = nodes.map(node => ({
      ...node,
      data: {
        ...node.data,
        status: 'idle',  // 初始状态设为idle
        outputs: {}      // 清空之前的执行结果
      }
    }));
    useWorkflowStore.getState().setNodes(nodesWithInitialStatus);
    
    console.log('[ExecuteWorkflow] State set to executing. All nodes reset to idle status.');
    
    let effectiveWorkflowId = workflowId; // 从组件状态初始化
    let currentExecutionId = null; // 添加变量存储执行ID

    try {
      // 步骤1: 确保工作流已保存并获取其ID
      if (!effectiveWorkflowId) {
        console.log('[ExecuteWorkflow] 工作流未在状态中找到ID，先进行初次自动保存...');
        const savedInitialWorkflow = await autoSaveWorkflow(); // 不传递ID，让其创建
        if (!savedInitialWorkflow || !savedInitialWorkflow.id) {
          toast.error('初次自动保存工作流失败，无法执行');
          setExecuting(false);
          return;
        }
        effectiveWorkflowId = String(savedInitialWorkflow.id); // 使用返回的ID
        console.log(`[ExecuteWorkflow] 初次保存完成，工作流 ID 为: ${effectiveWorkflowId}`);
      } else {
        // 如果已有ID，也自动保存以更新最新UI变更（在文件上传前）
        console.log(`[ExecuteWorkflow] 工作流已有ID: ${effectiveWorkflowId}，保存当前更改...`);
        const updatedWorkflow = await autoSaveWorkflow(effectiveWorkflowId); // 传递当前ID进行更新
        if (!updatedWorkflow) {
          toast.error('更新工作流失败（文件上传前），无法执行');
          setExecuting(false);
          return;
        }
        // effectiveWorkflowId 理论上不变，但可以从返回确认
        effectiveWorkflowId = String(updatedWorkflow.id);
      }
      
      // 重新获取store中的最新节点数据，以确保数据同步
      const currentNodesFromStore = useWorkflowStore.getState().nodes;
      const currentEdgesFromStore = useWorkflowStore.getState().edges;
      console.log('[ExecuteWorkflow] currentNodesFromStore for File check:', JSON.parse(JSON.stringify(currentNodesFromStore)));

      // 为执行准备的工作流定义副本，文件路径将在此更新
      const executionWorkflowDefinition = {
        nodes: JSON.parse(JSON.stringify(currentNodesFromStore)),
        edges: JSON.parse(JSON.stringify(currentEdgesFromStore)),
      };
      console.log('[ExecuteWorkflow] executionWorkflowDefinition created for parameter updates.');

      const fileUploadPromises: Promise<void>[] = [];
      console.log('[ExecuteWorkflow] Starting to iterate nodes for file uploads...');
      
      // 跟踪是否需要在文件上传后重新保存工作流
      let needsResave = false;
      
      for (let i = 0; i < currentNodesFromStore.length; i++) {
        const originalNode = currentNodesFromStore[i];
        const nodeForExecution = executionWorkflowDefinition.nodes[i];

        console.log(`[ExecuteWorkflow] Checking originalNode: ${originalNode.id}, component: ${originalNode.data.component.id}, params:`, JSON.parse(JSON.stringify(originalNode.data.params)));
        
        if (originalNode.data.component.id === 'csv-input') {
          const fileParamName = 'file_path'; 
          const fileObject = originalNode.data.params?.[fileParamName];
          const fileInfo = originalNode.data.params?._file_info;
          
          console.log(`[ExecuteWorkflow] CSV Input Node ${originalNode.id} - original file_path param:`, fileObject, 'Type:', typeof fileObject);
          console.log(`[ExecuteWorkflow] CSV Input Node ${originalNode.id} - _file_info:`, fileInfo);

          // 1. 文件对象 - 需要上传
          if (fileObject instanceof File) { 
            console.log(`[ExecuteWorkflow] Node ${originalNode.id} has a File object for ${fileParamName}. Preparing for upload.`);
            const formData = new FormData();
            formData.append('file', fileObject);
            
            console.log(`[ExecuteWorkflow] FormData created for ${fileObject.name}. ProjectId: ${projectId}`);

            const csrftoken = getCookie('csrftoken');
            const headers: HeadersInit = {};
            if (csrftoken) {
              headers['X-CSRFToken'] = csrftoken;
            }

            const uploadPromise = fetch(`/api/project/projects/${projectId}/upload-file/`, {
              method: 'POST',
              headers: headers,
              body: formData,
            })
            .then(response => {
              console.log(`[ExecuteWorkflow] Upload API response for ${fileObject.name}:`, response.status);
              if (!response.ok) {
                return response.json().then(err => { 
                  console.error(`[ExecuteWorkflow] Upload failed for ${fileObject.name}:`, err);
                  throw new Error(`文件上传失败: ${fileObject.name} - ${err.detail || response.statusText}`);
                });
              }
              return response.json();
            })
            .then(uploadData => {
              console.log(`[ExecuteWorkflow] Upload success for ${fileObject.name}. Server path: ${uploadData.file_path}`);
              const normalizedServerPath = uploadData.file_path.replace(/\\/g, '/'); 
              if (nodeForExecution && nodeForExecution.data && nodeForExecution.data.params) {
                // 同时更新params和parameters字段
                nodeForExecution.data.params[fileParamName] = normalizedServerPath;
                if (!nodeForExecution.data.parameters) {
                  nodeForExecution.data.parameters = {};
                }
                nodeForExecution.data.parameters[fileParamName] = normalizedServerPath;
                
                // 保存文件信息
                if (!nodeForExecution.data.params._file_info) {
                  nodeForExecution.data.params._file_info = {
                    name: fileObject.name,
                    size: fileObject.size,
                    type: fileObject.type,
                    lastModified: fileObject.lastModified,
                    serverPath: normalizedServerPath
                  };
                } else {
                  nodeForExecution.data.params._file_info.serverPath = normalizedServerPath;
                }
                
                console.log(`[ExecuteWorkflow] Updated file_path in executionWorkflowDefinition for node ${originalNode.id}:`, 
                  `params=${normalizedServerPath}, parameters=${nodeForExecution.data.parameters[fileParamName]}`);
                
                // 确保这些更改能够同步到后端，通过再次保存工作流
                needsResave = true;
              }
              // 更新Zustand store中的节点参数
              useWorkflowStore.getState().updateNodeParameters(originalNode.id, { 
                [fileParamName]: normalizedServerPath,
                _file_info: {
                  ...fileInfo,
                  serverPath: normalizedServerPath
                }
              });
              console.log(`[ExecuteWorkflow] Updated file_path in Zustand store for node ${originalNode.id}: ${normalizedServerPath}`);
              toast.success(`文件 ${fileObject.name} 上传成功`);
            })
            .catch(uploadError => {
              console.error(`[ExecuteWorkflow] Upload catch for ${fileObject.name}:`, uploadError);
              toast.error(uploadError.message);
              throw uploadError; 
            });
            fileUploadPromises.push(uploadPromise);
          } 
          // 2. 已有服务器路径的字符串
          else if (typeof fileObject === 'string' && fileObject) {
            const normalizedExistingPath = fileObject.replace(/\\/g, '/');
            console.log(`[ExecuteWorkflow] Node ${originalNode.id} - file_path is already a string: ${normalizedExistingPath}. No upload needed.`);
            if (nodeForExecution && nodeForExecution.data && nodeForExecution.data.params) {
                // 同时更新params和parameters字段
                nodeForExecution.data.params[fileParamName] = normalizedExistingPath;
                if (!nodeForExecution.data.parameters) {
                  nodeForExecution.data.parameters = {};
                }
                nodeForExecution.data.parameters[fileParamName] = normalizedExistingPath;
                console.log(`[ExecuteWorkflow] Confirmed file_path in executionWorkflowDefinition for node ${originalNode.id}:`, 
                  `params=${normalizedExistingPath}, parameters=${nodeForExecution.data.parameters[fileParamName]}`);
            }
            // 确保Zustand store中的参数也一致
            useWorkflowStore.getState().updateNodeParameters(originalNode.id, { [fileParamName]: normalizedExistingPath });
          } 
          // 3. 处理仅有文件信息但没有实际文件对象的情况
          else if (fileInfo && typeof fileInfo === 'object' && fileInfo.name) {
            console.log(`[ExecuteWorkflow] Node ${originalNode.id} - has file info but no actual file: `, fileInfo);
            // 如果有服务器路径，优先使用
            if (fileInfo.serverPath) {
              const normalizedServerPath = fileInfo.serverPath.replace(/\\/g, '/');
              
              if (nodeForExecution && nodeForExecution.data && nodeForExecution.data.params) {
                // 更新参数
                nodeForExecution.data.params[fileParamName] = normalizedServerPath;
                if (!nodeForExecution.data.parameters) {
                  nodeForExecution.data.parameters = {};
                }
                nodeForExecution.data.parameters[fileParamName] = normalizedServerPath;
                console.log(`[ExecuteWorkflow] Using serverPath from fileInfo: ${normalizedServerPath}`);
              }
              
              // 更新store
              useWorkflowStore.getState().updateNodeParameters(originalNode.id, { [fileParamName]: normalizedServerPath });
            } else {
              // 文件信息存在但没有服务器路径，告诉用户需要重新上传
              toast.warning(`节点 "${originalNode.data.label}" 的文件 "${fileInfo.name}" 需要重新上传`);
              throw new Error(`节点 ${originalNode.data.label} 的文件 ${fileInfo.name} 需要重新上传`);
            }
          }
          else if (originalNode.data.component.id === 'csv-input') { 
            console.warn(`[ExecuteWorkflow] CSV Input Node ${originalNode.id} - file_path is not a File object and not a string. Value:`, fileObject);
            // 如果 file_path 为空或无效，抛出错误
            toast.error(`节点 ${originalNode.data.label} 的文件路径无效，请重新选择文件。`);
            throw new Error(`节点 ${originalNode.data.label} 的文件路径无效，请重新选择文件`);
          }
        }
      }
      console.log('[ExecuteWorkflow] Node iteration for file uploads complete. Promises count:', fileUploadPromises.length);

      if (fileUploadPromises.length > 0) {
        console.log('[ExecuteWorkflow] Waiting for all file uploads to complete...');
        toast.info('正在上传数据文件...');
        await Promise.all(fileUploadPromises);
        console.log('[ExecuteWorkflow] All file uploads complete. Zustand store parameters are updated.');
        
        // 如果有文件上传，则总是重新保存工作流
        needsResave = true;
      } else {
        console.log('[ExecuteWorkflow] No new files to upload.');
      }
      
      // 步骤2: 在所有文件上传和参数更新后，如果需要则重新保存工作流以持久化这些更改到后端
      if (needsResave) {
        console.log(`[ExecuteWorkflow] Re-saving workflow (ID: ${effectiveWorkflowId}) after parameter updates to persist changes in DB.`);
        const savedWorkflowAfterUpload = await autoSaveWorkflow(effectiveWorkflowId); 
        if (!savedWorkflowAfterUpload || !savedWorkflowAfterUpload.id) {
          toast.error('自动保存工作流以更新文件路径失败，无法执行');
        setExecuting(false);
        return;
      }
        effectiveWorkflowId = String(savedWorkflowAfterUpload.id); // 确认ID
        console.log(`[ExecuteWorkflow] Workflow (ID: ${effectiveWorkflowId}) re-saved successfully with updated parameters.`);
      } else {
        console.log('[ExecuteWorkflow] No need to re-save workflow, continuing with execution.');
      }
      
      // 现在 effectiveWorkflowId 指向的是后端保存的、包含正确文件路径的工作流版本
      console.log(`[ExecuteWorkflow] Preparing to send to backend for execution. Final Workflow ID: ${effectiveWorkflowId}`);
      // executionWorkflowDefinition 此时也应包含服务器路径，但后端将从其数据库中加载由 effectiveWorkflowId 标识的定义

      const csrftoken = getCookie('csrftoken');
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (csrftoken) {
        headers['X-CSRFToken'] = csrftoken;
      }

      try {
        // 确认工作流存在 (可选，但良好的实践)
        const checkResponse = await fetch(`/api/project/workflows/${effectiveWorkflowId}/`, {
          method: 'GET',
          headers: headers
        });
        
        if (!checkResponse.ok) {
          console.error(`[ExecuteWorkflow] 工作流 (ID: ${effectiveWorkflowId}) 不存在或无法访问:`, checkResponse.status);
          toast.error('工作流不存在或无法访问，请重新保存');
          throw new Error('工作流不存在或无法访问');
        }
        console.log(`[ExecuteWorkflow] Workflow (ID: ${effectiveWorkflowId}) confirmed to exist.`);

        // 准备所有节点为running状态
        const currentNodes = useWorkflowStore.getState().nodes;
        // 更新连接中的节点为running状态 - 考虑工作流执行顺序，输入节点应该先执行
        const inputNodes = currentNodes.filter(node => 
          node.data?.component?.type === 'input' || 
          !currentNodes.some(otherNode => 
            useWorkflowStore.getState().edges.some(e => 
              e.source === otherNode.id && e.target === node.id
            )
          )
        );
        
        // 先将输入节点设置为running
        if (inputNodes.length > 0) {
          inputNodes.forEach(node => {
            useWorkflowStore.getState().updateNodeStatus(node.id, 'running');
          });
          
          // 稍微延迟，让用户可以看到状态变化
          await new Promise(resolve => setTimeout(resolve, 300));
        }

        // 执行API调用
        const response = await fetch(`/api/project/workflows/${effectiveWorkflowId}/execute/`, {
        method: 'POST',
        headers: headers,
          body: JSON.stringify({
            project_id: Number(projectId) // 确保项目ID是数字类型
          }) // 后端通过URL中的ID获取工作流定义
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: '执行失败，无法解析错误响应' }));
        console.error('[ExecuteWorkflow] Execution API error response:', errorData);
        toast.error(`工作流执行启动失败: ${errorData.detail || response.statusText}`);
        throw new Error(`工作流执行启动失败: ${errorData.detail || response.statusText}`);
      }

      const result = await response.json();
      currentExecutionId = result.id; // 保存执行ID，用于后续轮询
      setExecutionId(currentExecutionId); // 将执行ID保存到状态中
      console.log('[ExecuteWorkflow] Execution API success response:', result);
        toast.success(`工作流 "${result.workflow_name || effectiveWorkflowId}" 执行已启动 (执行ID: ${result.id})`);

        // 添加这里：轮询检查执行状态并获取结果
        await pollExecutionStatus(currentExecutionId);
        
      } catch (error) {
        console.error('[ExecuteWorkflow] API error:', error);
        toast.error(`工作流执行API错误: ${error instanceof Error ? error.message : '未知错误'}`);
      }

    } catch (error) {
      console.error('[ExecuteWorkflow] Error during execution:', error);
      if (error instanceof Error && 
         !error.message.startsWith('文件上传失败') && 
         !error.message.startsWith('工作流执行启动失败')) {
        toast.error(`执行工作流时发生错误: ${error.message}`);
      } else if (!(error instanceof Error)) {
        toast.error(`执行工作流时发生未知错误: ${String(error)}`);
      }
    } finally {
      console.log('[ExecuteWorkflow] Execution process finished, setting executing to false.');
      setExecuting(false);
      setExecutionId(null); // 重置执行ID
    }
  };

  // 渲染清空画布确认模态框
  const renderClearDialog = () => (
    <Modal
      title="确认清空画布"
      open={clearDialogOpen}
      onCancel={() => setClearDialogOpen(false)}
      destroyOnClose
      className="custom-dark-modal"
      footer={(
        <div className="flex justify-end space-x-3 pt-3">
          <Button
            key="cancel"
            variant="outline"
            size="sm"
            onClick={() => setClearDialogOpen(false)}
            className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white"
          >
            取消
          </Button>
          <Button
            key="confirm"
            variant="destructive"
            size="sm"
            onClick={clearCanvas}
            className="bg-red-600 hover:bg-red-700 text-white"
          >
            确认清空
          </Button>
        </div>
      )}
    >
      <p className="text-slate-300">您确定要清空当前工作流画布吗？所有未保存的更改都将丢失。</p>
    </Modal>
  );
  
  // 渲染结果展示模态框
  const renderResultsDialog = () => (
    <Modal
      title="工作流执行结果"
      open={showResultsDialog}
      onCancel={() => setShowResultsDialog(false)}
      destroyOnClose
      className="custom-dark-modal results-modal"
      width="90%"
      style={{ 
        maxWidth: '1400px', 
        top: '40px',
        margin: '0 auto 40px'
      }}
      bodyStyle={{ padding: '16px', maxHeight: '85vh' }}
      footer={(
        <div className="flex justify-end space-x-3 pt-3">
          <Button
            key="close"
            variant="outline"
            size="sm"
            onClick={() => setShowResultsDialog(false)}
            className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white"
          >
            关闭
          </Button>
        </div>
      )}
    >
      <div className="max-h-[65vh] overflow-y-auto pr-2 custom-scrollbar">
        {nodes
          .filter(node => node.data?.status === 'success' && node.data?.outputs)
          .map((node, index) => {
            const outputs = node.data.outputs || {};
            const nodeLabel = node.data.label;
            return (
              <div key={node.id} className="mb-6 border border-slate-700 rounded-md overflow-hidden">
                <div className="px-4 py-2 bg-slate-700/50 flex justify-between items-center">
                  <h3 className="text-white font-medium text-lg">{nodeLabel}</h3>
                  <span className="text-green-400 text-xs px-2 py-1 bg-green-900/50 rounded">执行成功</span>
                </div>
                <div className="p-4 overflow-x-auto">
                  <ResultViewPanel outputs={outputs} nodeLabel={nodeLabel} />
                </div>
              </div>
            );
          })}
          
        {nodes.filter(node => node.data?.status === 'success' && node.data?.outputs).length === 0 && (
          <div className="p-6 text-center text-slate-400">
            暂无可视化结果或组件未执行成功
          </div>
        )}
      </div>
    </Modal>
  );

  // 初始加载状态
  const [initialLoading, setInitialLoading] = useState(true);
  
  // 当节点首次加载完成后，取消初始加载状态
  useEffect(() => {
    if (initialLoading && nodes.length > 0) {
      console.log('[WorkflowDesignerContent] 初始节点加载完成，节点数量:', nodes.length);
      setInitialLoading(false);
    }
  }, [nodes.length, initialLoading]);
  
  // 仅在初始加载工作流时调整视图，而不是每次节点变化都调整
  useEffect(() => {
    // 当有节点且reactFlowInstance可用时，执行一次视图适配
    if (nodes.length > 0 && reactFlowInstance && initialLoading) {
      console.log('[WorkflowDesignerContent] 初始加载工作流，自动调整视图一次');
      
      try {
        // 延迟调整视图，确保DOM已渲染
        setTimeout(() => {
          if (reactFlowInstance) {
            reactFlowInstance.fitView({ 
              padding: 0.2, 
              includeHiddenNodes: false,
              minZoom: 0.5,
              maxZoom: 1.5
            });
            console.log('[WorkflowDesignerContent] 初始加载后自动调整视图完成');
          }
        }, 300);
      } catch (error) {
        console.error('[WorkflowDesignerContent] 调整视图失败:', error);
      }
    }
  }, [nodes.length, reactFlowInstance, initialLoading]);

  return (
    <div ref={reactFlowWrapper} className="h-full relative">
      <ReactFlow
        key={`flow-${workflowId || 'empty'}-${windowSize.width}-${windowSize.height}-${nodes.length}`}
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        onDragOver={onDragOver}
        onDrop={onDrop}
        proOptions={{ hideAttribution: true }}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        className="bg-slate-900"
        // 移除fitView属性，允许用户自由定位组件
      >
        <Background color="#475569" gap={16} size={1} />
        <Controls className="bg-slate-800/70 border border-slate-600/50 rounded-md" />
        
        <Panel position="top-center" className="mt-2">
          <div className="p-2 rounded-md bg-slate-800/80 backdrop-blur-sm border border-slate-700/50 shadow-lg">
            <div className="flex items-center space-x-2">
              {/* 切换为执行/停止按钮 */}
              {executing ? (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={stopExecution}
                  className="bg-red-600/80 hover:bg-red-700/80 text-white"
                >
                  <Square className="w-4 h-4 mr-2" />
                  停止执行
                </Button>
              ) : (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={executeWorkflow}
                  disabled={nodes.length === 0}
                className={cn(
                    "text-white",
                    "bg-green-600/80 hover:bg-green-700/80"
                )}
              >
                    <Play className="w-4 h-4 mr-2" />
                    执行工作流
              </Button>
              )}
              
              {/* 添加查看结果按钮 */}
              {workflowCompleted && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setShowResultsDialog(true)}
                  className="text-purple-400 hover:text-purple-300 border-slate-600/50 hover:bg-purple-950/30"
                >
                  <Eye className="w-4 h-4 mr-2" />
                  查看结果
                </Button>
              )}
              
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => autoSaveWorkflow()}
                disabled={executing || nodes.length === 0 || saving}
                className="text-blue-400 hover:text-blue-300 border-slate-600/50 hover:bg-blue-950/30"
              >
                {saving ? (
                  <>
                    <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                    保存中...
                  </>
                ) : (
                  <>
                <Save className="w-4 h-4 mr-2" />
                保存
                  </>
                )}
              </Button>
              
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setClearDialogOpen(true)}
                disabled={executing || nodes.length === 0}
                className="text-red-400 hover:text-red-300 border-slate-600/50 hover:bg-red-950/30"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                清空画布
              </Button>
              
              {/* 添加一个按钮，允许用户手动适配视图 */}
              {nodes.length > 0 && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => {
                    if (reactFlowInstance) {
                      reactFlowInstance.fitView({ 
                        padding: 0.2, 
                        includeHiddenNodes: false,
                        minZoom: 0.5,
                        maxZoom: 1.5
                      });
                      toast.success('已适配视图以显示所有节点');
                    }
                  }}
                  className="text-amber-400 hover:text-amber-300 border-slate-600/50 hover:bg-amber-950/30"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 mr-2">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <path d="M9 3v18" />
                    <path d="M3 9h18" />
                  </svg>
                  适配视图
                </Button>
              )}
            </div>
          </div>
        </Panel>
      </ReactFlow>
      
      {/* Render Modals */}
      {renderClearDialog()}
      {renderResultsDialog()}
      
      {/* 自定义暗色模态框样式 */}
      <style>{`
        .custom-dark-modal .ant-modal-content {
          background-color: rgba(15, 23, 42, 0.75);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(51, 65, 85, 0.5);
          border-radius: 0.75rem;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }
        .custom-dark-modal .ant-modal-header {
          background-color: transparent;
          border-bottom: 1px solid rgba(51, 65, 85, 0.5);
        }
        .custom-dark-modal .ant-modal-title {
          color: white;
        }
        .custom-dark-modal .ant-modal-close {
          color: rgba(148, 163, 184, 0.8);
        }
        .custom-dark-modal .ant-modal-close:hover {
          color: white;
        }
        .custom-dark-modal .ant-form-item-label > label {
          color: rgb(209, 213, 219) !important;
        }
        .custom-dark-modal .ant-input,
        .custom-dark-modal .ant-input-affix-wrapper,
        .custom-dark-modal .ant-input-number,
        .custom-dark-modal .ant-input-number-input,
        .custom-dark-modal .ant-select-selector,
        .custom-dark-modal .ant-select-selection-item,
        .custom-dark-modal .ant-input-textarea {
          background-color: rgba(30, 41, 59, 0.5) !important;
          border-color: rgba(51, 65, 85, 0.5) !important;
          color: white !important;
        }
        .custom-dark-modal .ant-input::placeholder,
        .custom-dark-modal .ant-input-number-input::placeholder,
        .custom-dark-modal .ant-input-textarea::placeholder {
          color: rgba(148, 163, 184, 0.5) !important;
        }
        
        /* 结果弹窗特殊样式 */
        .results-modal .ant-modal-content {
          max-height: 90vh;
          display: flex;
          flex-direction: column;
        }
        .results-modal .ant-modal-body {
          flex: 1;
          overflow: visible;
          padding: 16px;
        }
        .results-modal .ant-modal-footer {
          border-top: 1px solid rgba(51, 65, 85, 0.5);
          margin-top: 8px;
        }
        
        /* 自定义滚动条样式 */
        .custom-scrollbar::-webkit-scrollbar {
          width: 10px;
          height: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(15, 23, 42, 0.5);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(71, 85, 105, 0.8);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(100, 116, 139, 0.8);
        }
        
        /* 优化表格溢出处理 */
        .overflow-x-auto {
          overflow-x: auto;
          max-width: 100%;
          scrollbar-width: thin;
          scrollbar-color: rgba(71, 85, 105, 0.8) rgba(15, 23, 42, 0.5);
        }
        .overflow-x-auto::-webkit-scrollbar {
          height: 10px;
        }
        .overflow-x-auto::-webkit-scrollbar-track {
          background: rgba(15, 23, 42, 0.5);
        }
        .overflow-x-auto::-webkit-scrollbar-thumb {
          background: rgba(71, 85, 105, 0.8);
          border-radius: 4px;
        }
        
        /* JSON数据显示优化 */
        pre {
          white-space: pre-wrap !important;
          word-break: break-word !important;
          overflow-wrap: break-word !important;
          max-width: 100% !important;
        }
        
        /* 表格样式优化 */
        table {
          border-spacing: 0;
          border-collapse: separate;
          table-layout: auto;
          width: 100%;
        }
        th, td {
          word-break: break-word;
          max-width: 250px;
          overflow-wrap: break-word;
        }
        
        /* 详情显示优化 */
        details summary {
          user-select: none;
        }

        /* 状态变化动画效果 */
        @keyframes statusFadeIn {
          0% { opacity: 0; transform: translateY(-5px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes statusPulse {
          0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }
          70% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
          100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
        }
        
        @keyframes successPulse {
          0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4); }
          70% { box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); }
          100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
        }
        
        @keyframes errorShake {
          0%, 100% { transform: translateX(0); }
          20%, 60% { transform: translateX(-2px); }
          40%, 80% { transform: translateX(2px); }
        }
        
        @keyframes cancelledFade {
          0% { opacity: 1; }
          50% { opacity: 0.6; }
          100% { opacity: 0.8; }
        }
        
        /* 状态指示器样式应用 */
        .status-indicator {
          animation: statusFadeIn 0.3s ease-out;
        }
        
        .status-running {
          animation: statusPulse 1.5s infinite;
        }
        
        .status-success {
          animation: successPulse 1.5s ease-out;
        }
        
        .status-error {
          animation: errorShake 0.5s;
        }
        
        .status-cancelled {
          animation: cancelledFade 0.8s ease-out;
        }
      `}</style>
    </div>
  );
};

// 主页面组件，包括左侧组件面板和右侧属性面板
const WorkflowDesignerPage: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [fetchCompleted, setFetchCompleted] = useState<boolean>(false); // 添加状态跟踪是否已完成加载
  const { isComponentPanelOpen, isPropertiesPanelOpen, toggleComponentPanel, togglePropertiesPanel } = useWorkflowStore();

  // 加载项目数据
  useEffect(() => {
    // 如果已经完成加载，不再重复执行
    if (fetchCompleted) {
      console.log('[WorkflowDesignerPage] fetchProject已执行过，跳过');
      return;
    }
    
    // 防止工作流重复加载的标记
    let hasNavigatedToWorkflow = false;
    
    const fetchProject = async () => {
      if (!id) return;
      
      try {
        setLoading(true);
        const response = await getProject(Number(id));
        
        if (response && response.status === 'success' && response.data) {
          setProject(response.data);
          
          // 如果项目类型不是canvas，返回到项目详情页
          if (response.data.project_type !== 'canvas') {
            toast.error('该项目不是可视化工作流类型');
            navigate(`/dashboard/projects/${id}`);
            return;
          }
          
          // 获取URL信息
          const pathParts = window.location.pathname.split('/');
          const hasWorkflowIdInURL = pathParts.length > 4 && pathParts[4] === 'workflows' && pathParts[5];
          
          // 获取存储在localStorage中的上次路径
          const lastPath = localStorage.getItem('lastPath');
          const lastPathWorkflowId = lastPath?.match(/\/workflows\/(\d+)/)?.[1];
          
          console.log('[WorkflowDesignerPage] URL中的workflowId:', hasWorkflowIdInURL ? pathParts[5] : 'none');
          console.log('[WorkflowDesignerPage] localStorage中的路径:', lastPath);
          console.log('[WorkflowDesignerPage] localStorage中的workflowId:', lastPathWorkflowId);
          
          // 优先级1：URL中有workflowId，直接使用
          if (hasWorkflowIdInURL) {
            console.log('[WorkflowDesignerPage] 使用URL中的workflowId:', pathParts[5]);
            // 保存这个路径，防止页面刷新后丢失
            localStorage.setItem('lastPath', window.location.pathname);
            // 不需要额外操作，WorkflowDesignerContent组件会基于URL参数自动加载
            
            // URL中已有工作流ID，标记已导航
            hasNavigatedToWorkflow = true;
            return;
          }
          
          // 优先级2：localStorage中有上次访问的工作流ID，且属于当前项目
          if (!hasNavigatedToWorkflow && lastPathWorkflowId && lastPath?.includes(`/projects/${id}/`)) {
            console.log('[WorkflowDesignerPage] 从localStorage恢复workflowId:', lastPathWorkflowId);
            
            // 确认这个工作流存在并属于当前项目
            try {
              const checkResponse = await fetch(`/api/project/workflows/${lastPathWorkflowId}/`);
              if (checkResponse.ok) {
                const workflowData = await checkResponse.json();
                if (workflowData && Number(workflowData.project) === Number(id)) {
                  console.log('[WorkflowDesignerPage] 确认工作流存在且属于当前项目:', workflowData.name);
                  
                  // 更新URL
                  const newPath = `/dashboard/projects/${id}/workflows/${lastPathWorkflowId}`;
                  window.history.replaceState(null, '', newPath);
                  
                  // 显示恢复提示
                  toast.success(`已恢复上次编辑的工作流: ${workflowData.name}`);
                  
                  // 重要：强制触发路由更新，确保WorkflowDesignerContent能感知workflowId的变化
                  navigate(newPath, { replace: true });
                  
                  // 标记已导航到工作流
                  hasNavigatedToWorkflow = true;
                  return;
                }
              }
            } catch (error) {
              console.error('[WorkflowDesignerPage] 检查localStorage中的workflowId出错:', error);
              // 继续尝试加载最新工作流
            }
          }
          
          // 优先级3：尝试加载该项目的最新工作流
          if (!hasNavigatedToWorkflow) {
            try {
              console.log('[WorkflowDesignerPage] 尝试加载项目最新工作流');
              const workflowsResponse = await fetch(`/api/project/workflows/project/${id}/`);
              if (workflowsResponse.ok) {
                const workflows = await workflowsResponse.json();
                if (workflows && workflows.length > 0) {
                  // 获取最新的工作流（按更新时间排序，第一个即为最新）
                  const latestWorkflow = workflows[0];
                  console.log('[WorkflowDesignerPage] 找到最新工作流:', latestWorkflow);
                  
                  // 更新URL
                  const newPath = `/dashboard/projects/${id}/workflows/${latestWorkflow.id}`;
                  
                  // 保存这个路径，防止页面刷新后丢失
                  localStorage.setItem('lastPath', newPath);
                
                  // 显示加载成功的提示 - 不在这里显示，防止重复
                  // 在navigate触发后，由WorkflowDesignerContent组件的成功加载时显示一次即可
                  // toast.success(`已加载最新工作流: ${latestWorkflow.name}`);
                  
                  // 为子组件传递工作流名称信息，用于显示toast
                  sessionStorage.setItem('last_loaded_workflow_name', latestWorkflow.name);
                  
                  // 重要：使用navigate而非replaceState，确保路由参数更新，触发子组件加载
                  navigate(newPath, { replace: true });
                  
                  // 标记已导航到工作流
                  hasNavigatedToWorkflow = true;
                } else {
                  console.log('[WorkflowDesignerPage] 项目没有现有工作流');
                }
              } else {
                console.warn('[WorkflowDesignerPage] 获取项目工作流失败:', workflowsResponse.status);
              }
            } catch (error) {
              console.error('[WorkflowDesignerPage] 获取项目工作流出错:', error);
            }
          }
        } else {
          toast.error('加载项目失败');
          navigate('/dashboard/projects');
        }
      } catch (error) {
        console.error('获取项目详情失败:', error);
        toast.error('加载项目失败，请重试');
        navigate('/dashboard/projects');
      } finally {
        setLoading(false);
        setFetchCompleted(true); // 标记已完成加载
      }
    };

    fetchProject();
  }, [id, navigate, fetchCompleted]); // 添加fetchCompleted到依赖数组

  // 初始化工作流组件
  React.useEffect(() => {
    useWorkflowStore.setState({ components: allComponents });
  }, []);

  return (
    <ReactFlowProvider>
      <div className="h-full w-full flex flex-col overflow-hidden">
        {/* 顶部导航 */}
        <div className="p-4 bg-slate-800 border-b border-slate-700 flex justify-between items-center shrink-0">
          <div className="flex items-center">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate("/dashboard/projects")}
              className="mr-4 text-slate-300 hover:text-white border-slate-600 hover:bg-slate-700/50"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回项目列表
            </Button>
            <h1 className="text-2xl font-bold text-white">
              {loading ? '加载中...' : `${project?.name || '未命名项目'} - 工作流设计器`}
            </h1>
          </div>
        </div>

        {/* 主内容区域 */}
        {loading ? (
          <div className="flex-1 flex items-center justify-center bg-slate-900">
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 border-4 border-t-blue-500 border-blue-500/30 rounded-full animate-spin mb-4"></div>
              <p className="text-slate-300">加载项目数据中...</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-1 overflow-hidden">
            {/* 左侧组件面板 - 可收起 */}
            <div className={`bg-slate-900 border-r border-slate-700 overflow-hidden flex transition-all duration-300 ease-in-out ${
              isComponentPanelOpen ? 'w-72' : 'w-0'
            }`}>
              <ComponentPanel />
            </div>
            
            {/* 左侧收起/展开按钮 */}
            <div className="relative">
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleComponentPanel}
                className="absolute left-0 top-4 z-10 w-6 h-20 p-0 flex items-center justify-center bg-slate-700/70 hover:bg-slate-600 text-white border-0 rounded-r-md"
              >
                {isComponentPanelOpen 
                  ? <ChevronLeft className="h-4 w-4" /> 
                  : <ChevronRight className="h-4 w-4" />}
              </Button>
            </div>

            {/* 中间工作流画布 */}
            <div className="flex-1 overflow-y-auto relative bg-slate-800/30 hide-scrollbar">
              <WorkflowDesignerContent />
            </div>

            {/* 右侧收起/展开按钮 */}
            <div className="relative">
              <Button
                variant="ghost"
                size="sm"
                onClick={togglePropertiesPanel}
                className="absolute right-0 top-4 z-10 w-6 h-20 p-0 flex items-center justify-center bg-slate-700/70 hover:bg-slate-600 text-white border-0 rounded-l-md"
              >
                {isPropertiesPanelOpen 
                  ? <ChevronRight className="h-4 w-4" /> 
                  : <><ChevronLeft className="h-4 w-4" /><Sliders className="h-4 w-4 absolute opacity-50" /></>}
              </Button>
            </div>

            {/* 右侧属性面板 - 可收起 */}
            <div className={`bg-slate-900 border-l border-slate-700 overflow-hidden flex transition-all duration-300 ease-in-out ${
              isPropertiesPanelOpen ? 'w-80' : 'w-0'
            }`}>
              <PropertiesPanel />
            </div>
          </div>
        )}
      </div>
    </ReactFlowProvider>
  );
};

export default WorkflowDesignerPage;
