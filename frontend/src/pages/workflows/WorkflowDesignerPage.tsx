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
import { ArrowLeft, FileCode, Download, ChevronLeft, ChevronRight, Sliders, Play, Save, Trash2 } from 'lucide-react';
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
  const [saving, setSaving] = useState(false);
  
  const routeParams = useParams<{ id: string; workflowId?: string }>(); 
  const projectId = routeParams.id;
  const [workflowId, setWorkflowId] = useState<string | undefined>(routeParams.workflowId);

  // 在useEffect中打印一次projectId确保其正确获取
  useEffect(() => {
    console.log('[WorkflowDesignerContent] Initial projectId from routeParams:', projectId);
    console.log('[WorkflowDesignerContent] Initial workflowId from routeParams:', workflowId);
  }, [projectId, workflowId]);

  // 检测URL变化，更新workflowId
  useEffect(() => {
    const newWorkflowId = routeParams.workflowId;
    if (newWorkflowId !== workflowId) {
      console.log('[WorkflowDesignerContent] Updating workflowId from URL:', newWorkflowId);
      setWorkflowId(newWorkflowId);
      
      // 如果URL中有workflowId，则尝试加载工作流定义
      if (newWorkflowId) {
        const loadWorkflowDefinition = async () => {
          try {
            const response = await fetch(`/api/project/workflows/${newWorkflowId}/`);
            if (response.ok) {
              const workflowData = await response.json();
              console.log('[WorkflowDesignerContent] 加载工作流定义成功:', workflowData);
              
              // 将工作流定义加载到store中
              if (workflowData.definition && workflowData.definition.nodes && workflowData.definition.edges) {
                console.log('[WorkflowDesignerContent] 正在加载工作流节点到store, 节点数量:', workflowData.definition.nodes.length);
                
                // 预处理节点数据，确保文件路径信息正确
                if (workflowData.definition.nodes.length > 0) {
                  workflowData.definition.nodes = workflowData.definition.nodes.map((node: Node) => {
                    if (node.data && node.data.component && node.data.component.id === 'csv-input') {
                      console.log(`[WorkflowDesignerContent] 检查CSV节点参数:`, node.data.params);
                      
                      // 修复文件路径和文件信息
                      if (node.data.params) {
                        const filePathParam = node.data.params.file_path;
                        const fileInfoParam = node.data.params._file_info;
                        
                        // 如果有有效的file_path但没有_file_info
                        if (typeof filePathParam === 'string' && filePathParam && (!fileInfoParam || typeof fileInfoParam !== 'object')) {
                          // 从路径提取文件名
                          const fileName = filePathParam.split('/').pop() || 'data.csv';
                          // 创建基本的file_info对象
                          node.data.params._file_info = {
                            name: fileName,
                            serverPath: filePathParam
                          };
                          console.log(`[WorkflowDesignerContent] 为CSV节点添加缺失的文件信息:`, node.data.params._file_info);
                        }
                        
                        // 如果有_file_info但file_path是空的或无效的，使用serverPath
                        if (fileInfoParam && typeof fileInfoParam === 'object' && fileInfoParam.serverPath &&
                            (!filePathParam || typeof filePathParam === 'object' || filePathParam === '')) {
                          node.data.params.file_path = fileInfoParam.serverPath;
                          console.log(`[WorkflowDesignerContent] 从_file_info恢复file_path:`, fileInfoParam.serverPath);
                        }
                        
                        // 修复空对象参数问题
                        if (node.data.params && typeof node.data.params.file_path === 'object' && 
                            Object.keys(node.data.params.file_path).length === 0) {
                          console.log(`[WorkflowDesignerContent] 发现空file_path对象，检查是否有serverPath可用`);
                          
                          // 尝试从_file_info恢复
                          if (node.data.params._file_info && node.data.params._file_info.serverPath) {
                            node.data.params.file_path = node.data.params._file_info.serverPath;
                            console.log(`[WorkflowDesignerContent] 从_file_info恢复file_path:`, node.data.params.file_path);
                          } else {
                            node.data.params.file_path = null;
                            console.log(`[WorkflowDesignerContent] 无法恢复file_path，设置为null防止后端解析错误`);
                          }
                        }
                      }
                    }
                    return node;
                  });
                }
                
                // 保留完整的工作流对象作为currentWorkflow，同时也更新nodes和edges
                useWorkflowStore.getState().loadWorkflow(workflowData);
              } else {
                console.warn('[WorkflowDesignerContent] 工作流定义不完整');
              }
            } else {
              console.error('[WorkflowDesignerContent] 加载工作流定义失败:', response.status);
            }
          } catch (error) {
            console.error('[WorkflowDesignerContent] 加载工作流定义出错:', error);
          }
        };
        
        loadWorkflowDefinition();
      }
    }
  }, [routeParams.workflowId, workflowId, projectId]);

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
      toast.success(`工作流${isUpdatingExisting ? '更新' : '创建'}成功`);
      
      // 更新store中的currentWorkflow为后端返回的最新数据
      store.setCurrentWorkflow(savedWorkflowData);

      // 更新URL和workflowId状态
      const newWorkflowId = String(savedWorkflowData.id);
      if (newWorkflowId !== workflowId) {
        console.log(`[AutoSaveWorkflow] 更新workflowId: ${workflowId} -> ${newWorkflowId}`);
        
        // 更新URL，但不刷新页面
        const newPath = `/dashboard/projects/${projectId}/workflows/${newWorkflowId}`;
        // 使用replaceState替代，防止页面导航
        window.history.replaceState(null, '', newPath);
        
        // 更新组件状态
        setWorkflowId(newWorkflowId);
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
  };

  // 执行工作流
  const executeWorkflow = async () => {
    console.log('[ExecuteWorkflow] Clicked! Nodes count:', nodes.length, 'Project ID:', projectId);

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

    setExecuting(true);
    console.log('[ExecuteWorkflow] State set to executing.');
    
    let effectiveWorkflowId = workflowId; // 从组件状态初始化

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
      console.log('[ExecuteWorkflow] Execution API success response:', result);
        toast.success(`工作流 "${result.workflow_name || effectiveWorkflowId}" 执行已启动 (执行ID: ${result.id})`);
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
      console.log('[ExecuteWorkflow] Execution finished, setting executing to false.');
      setExecuting(false);
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

  return (
    <div ref={reactFlowWrapper} className="h-full relative">
      <ReactFlow
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
      >
        <Background color="#475569" gap={16} size={1} />
        <Controls className="bg-slate-800/70 border border-slate-600/50 rounded-md" />
        
        <Panel position="top-center" className="mt-2">
          <div className="p-2 rounded-md bg-slate-800/80 backdrop-blur-sm border border-slate-700/50 shadow-lg">
            <div className="flex items-center space-x-2">
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={executeWorkflow}
                disabled={executing || nodes.length === 0}
                className={cn(
                  "text-white bg-green-600/80 hover:bg-green-700/80",
                  executing && "opacity-50 cursor-wait"
                )}
              >
                {executing ? (
                  <>
                    <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                    执行中...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    执行工作流
                  </>
                )}
              </Button>
              
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
            </div>
          </div>
        </Panel>
      </ReactFlow>
      
      {/* Render Modals */}
      {renderClearDialog()}
      
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
  const { isComponentPanelOpen, isPropertiesPanelOpen, toggleComponentPanel, togglePropertiesPanel } = useWorkflowStore();

  // 加载项目数据
  useEffect(() => {
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
      }
    };

    fetchProject();
  }, [id, navigate]);

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
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="text-slate-300 hover:text-white border-slate-600 hover:bg-slate-700/50"
            >
              <FileCode className="w-4 h-4 mr-2" />
              生成代码
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-slate-300 hover:text-white border-slate-600 hover:bg-slate-700/50"
            >
              <Download className="w-4 h-4 mr-2" />
              导出工作流
            </Button>
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
