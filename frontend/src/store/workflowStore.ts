import { create } from 'zustand';
import { Edge, Node, Connection, addEdge, OnNodesChange, OnEdgesChange, OnConnect, applyNodeChanges, applyEdgeChanges } from 'reactflow';

// 工作流序列化接口
export interface WorkflowData {
  id: string;
  name: string;
  description?: string;
  nodes: Node[];
  edges: Edge[];
  createdAt?: string;
  updatedAt?: string;
  version?: number;
}

// 定义数据类型枚举
export enum DataType {
  ANY = 'any',
  NUMBER = 'number',
  STRING = 'string',
  BOOLEAN = 'boolean',
  ARRAY = 'array',
  OBJECT = 'object',
  DATAFRAME = 'dataframe',
  MODEL = 'model',
  IMAGE = 'image',
  FILE = 'file'
}

// 定义组件端口类型
export interface PortDefinition {
  id: string;
  type: DataType;
  label: string;
  description?: string;
  required?: boolean;
  multiple?: boolean; // 是否允许多个连接
  defaultValue?: any;
}

// 定义参数类型
export interface ParamDefinition {
  name: string;
  label: string;
  type: 'string' | 'number' | 'boolean' | 'select' | 'multiselect' | 'text' | 'file' | 'color';
  description?: string;
  defaultValue?: any;
  required?: boolean;
  options?: Array<{ value: string, label: string }>; // 用于select类型
  min?: number; // 用于number类型
  max?: number; // 用于number类型
  step?: number; // 用于number类型
  placeholder?: string; // 用于string/text类型
  accept?: string; // 用于file类型，指定接受的文件类型，如'.csv'
  showWhen?: { field: string, value: any }; // 条件显示
}

// 定义组件类型枚举
export enum ComponentType {
  INPUT = 'input',
  PROCESS = 'process',
  MODEL = 'model',
  EVALUATION = 'evaluation',
  VISUALIZATION = 'visualization',
  EXPORT = 'export',
  CUSTOM = 'custom'
}

// 定义组件类别枚举
export enum ComponentCategory {
  ALL = 'all',
  DATA_INPUT = 'data',
  DATA_PREPROCESSING = 'preprocessing',
  MODEL_TRAINING = 'model',
  EVALUATION = 'evaluation',
  VISUALIZATION = 'visualization'
}

// 定义组件类型
export interface ComponentDefinition {
  id: string;
  type: ComponentType;
  category: ComponentCategory;
  name: string;
  description: string;
  icon?: string; // 图标名称或SVG路径
  color?: string; // 组件颜色
  inputs: PortDefinition[];
  outputs: PortDefinition[];
  params: ParamDefinition[]; // 参数定义
  defaultParams: Record<string, any>; // 参数默认值
  paramTypes?: Record<string, string>; // 兼容现有代码
  paramLabels?: Record<string, string>; // 兼容现有代码
  execute?: (inputs: Record<string, any>, params: Record<string, any>) => Promise<Record<string, any>>; // 执行函数
}

// 定义工作流状态类型
export interface WorkflowState {
  nodes: Node[];
  edges: Edge[];
  components: ComponentDefinition[];
  selectedNode: Node | null;
  isComponentPanelOpen: boolean;
  isPropertiesPanelOpen: boolean;
  currentWorkflow: WorkflowData | null;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  updateNodeParameters: (nodeId: string, params: Record<string, any>) => void;
  setSelectedNode: (node: Node | null) => void;
  addNode: (component: ComponentDefinition, position: { x: number, y: number }) => void;
  removeNode: (nodeId: string) => void;
  toggleComponentPanel: () => void;
  togglePropertiesPanel: () => void;
  saveWorkflow: (name: string, description?: string) => WorkflowData;
  loadWorkflow: (workflow: WorkflowData) => void;
  setCurrentWorkflow: (workflow: WorkflowData) => void;
  exportWorkflow: () => string;
  importWorkflow: (jsonData: string) => WorkflowData | null;
}

// 创建工作流状态管理
const useWorkflowStore = create<WorkflowState>((set, get) => ({
  nodes: [],
  edges: [],
  components: [],
  selectedNode: null,
  isComponentPanelOpen: true,
  isPropertiesPanelOpen: true,
  currentWorkflow: null,

  // 处理节点变化
  onNodesChange: (changes) => {
    set({
      nodes: applyNodeChanges(changes, get().nodes),
    });
  },

  // 处理边变化
  onEdgesChange: (changes) => {
    set({
      edges: applyEdgeChanges(changes, get().edges),
    });
  },

  // 处理连接
  onConnect: (connection: Connection) => {
    set({
      edges: addEdge({
        ...connection,
        animated: true,
        style: { stroke: '#4287f5', strokeWidth: 2 },
      }, get().edges),
    });
  },

  // 更新节点参数
  updateNodeParameters: (nodeId: string, params: Record<string, any>) => {
    console.log('[WorkflowStore] updateNodeParameters - Node ID:', nodeId);
    console.log('[WorkflowStore] updateNodeParameters - Incoming params:', params);
    set({
      nodes: get().nodes.map(node => {
        if (node.id === nodeId) {
          console.log('[WorkflowStore] updateNodeParameters - Found node:', node.id, 'Current data.params:', node.data.params);
          const updatedNodeDataParams = {
            ...node.data.params,
            ...params
          };
          console.log('[WorkflowStore] updateNodeParameters - Updated data.params for node:', node.id, updatedNodeDataParams);
          return {
            ...node,
            data: {
              ...node.data,
              params: updatedNodeDataParams
            }
          };
        }
        return node;
      })
    });
  },

  // 设置选中节点
  setSelectedNode: (node: Node | null) => {
    set({ selectedNode: node });
  },

  // 添加节点
  addNode: (component: ComponentDefinition, position: { x: number, y: number }) => {
    const newNode: Node = {
      id: `node_${Date.now()}`,
      type: 'component', // 固定类型为'component'，与ReactFlow注册的节点类型匹配
      position,
      data: {
        label: component.name,
        component: component,
        params: { ...component.defaultParams }
      }
    };

    set({
      nodes: [...get().nodes, newNode]
    });
  },

  // 移除节点
  removeNode: (nodeId: string) => {
    // 移除相关连接
    const newEdges = get().edges.filter(
      edge => edge.source !== nodeId && edge.target !== nodeId
    );
    
    // 移除节点
    const newNodes = get().nodes.filter(node => node.id !== nodeId);
    
    set({
      nodes: newNodes,
      edges: newEdges,
      selectedNode: get().selectedNode?.id === nodeId ? null : get().selectedNode
    });
  },

  // 切换组件面板
  toggleComponentPanel: () => {
    set({ isComponentPanelOpen: !get().isComponentPanelOpen });
  },

  // 切换属性面板
  togglePropertiesPanel: () => {
    set({ isPropertiesPanelOpen: !get().isPropertiesPanelOpen });
  },

  // 保存工作流
  saveWorkflow: (name: string, description?: string) => {
    const { nodes, edges, currentWorkflow } = get();
    // 如果提供了新的name，则使用新的name，否则如果currentWorkflow存在，则使用它的name
    const workflowName = name || (currentWorkflow?.name || '未命名工作流');
    // 类似地处理description
    const workflowDescription = description || (currentWorkflow?.description || '');
    
    return {
      id: currentWorkflow?.id || `wf_${Date.now()}`, // 如果是新保存，生成ID
      name: workflowName,
      description: workflowDescription,
      nodes: nodes,
      edges: edges,
      version: currentWorkflow?.version || 1,
      createdAt: currentWorkflow?.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  },

  // 加载工作流
  loadWorkflow: (workflow: WorkflowData) => {
    console.log('[WorkflowStore] Loading workflow:', workflow);
    set({ 
      nodes: workflow.nodes || [], 
      edges: workflow.edges || [],
      currentWorkflow: workflow, // 保存整个 workflow 对象
      selectedNode: null // 清除选中节点
    });
  },

  // 仅更新currentWorkflow元数据，不修改节点和边缘
  setCurrentWorkflow: (workflow: WorkflowData) => {
    console.log('[WorkflowStore] Setting currentWorkflow metadata only:', workflow);
    set({
      currentWorkflow: {
        ...workflow,
        // 保留当前UI状态中的节点和边缘
        nodes: get().nodes,
        edges: get().edges
      }
    });
  },

  // 导出工作流
  exportWorkflow: () => {
    const workflow = get().currentWorkflow;
    if (!workflow) return '';
    return JSON.stringify(workflow, null, 2);
  },

  // 导入工作流
  importWorkflow: (jsonData: string) => {
    try {
      const workflow = JSON.parse(jsonData) as WorkflowData;
      set({
        nodes: workflow.nodes,
        edges: workflow.edges,
        currentWorkflow: workflow,
      });
      return workflow;
    } catch (error) {
      console.error('导入工作流失败:', error);
      return null;
    }
  },
}));

export default useWorkflowStore;
