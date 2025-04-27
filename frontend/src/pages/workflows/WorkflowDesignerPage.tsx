import React, { useRef, useCallback, useState, useEffect } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Background,
  Controls,
  useReactFlow,
  NodeTypes,
  Panel
} from 'reactflow';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, FileCode, Download, ChevronLeft, ChevronRight, Sliders, Play, Save, Trash2, Loader2 } from 'lucide-react';
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
import { Modal, Form, Input } from 'antd';

// 定义节点类型
const nodeTypes: NodeTypes = {
  component: ComponentNode,
};

// 工作流设计器核心组件
const WorkflowDesigner: React.FC = () => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect, setSelectedNode } = useWorkflowStore();
  const reactFlowInstance = useReactFlow();
  const [executing, setExecuting] = useState(false);
  
  // 模态框状态
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [workflowForm] = Form.useForm();

  // 处理节点选择
  const handleNodeClick = (_: React.MouseEvent, node: any) => {
    setSelectedNode(node);
  };

  // 处理节点拖放结束
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

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

  // 执行工作流
  const executeWorkflow = async () => {
    if (nodes.length === 0) {
      toast.error('工作流为空，请添加组件');
      return;
    }

    setExecuting(true);
    try {
      // 这里模拟执行工作流
      // 实际实现中，这里会调用后端API执行工作流
      await new Promise(resolve => setTimeout(resolve, 2000));
      toast.success('工作流执行成功');
    } catch (error) {
      console.error('执行工作流失败:', error);
      toast.error('执行工作流失败，请重试');
    } finally {
      setExecuting(false);
    }
  };

  // 清空画布
  const clearCanvas = () => {
    // 直接清空画布
    useWorkflowStore.setState({ nodes: [], edges: [], selectedNode: null });
    toast.info('画布已清空');
    setClearDialogOpen(false);
  };

  // 保存工作流
  const saveWorkflow = (name: string, description: string) => {
    if (nodes.length === 0) {
      toast.error('工作流为空，无需保存');
      return;
    }

    // 弹出保存对话框
    try {
      // 调用store的saveWorkflow方法
      const workflow = useWorkflowStore.getState().saveWorkflow(name, description);
      
      // 这里可以调用后端API保存工作流
      // 目前先模拟API调用
      console.log('保存的工作流数据:', workflow);
      
      toast.success('工作流保存成功');
      
      // 导出工作流到文件（临时功能，后续会替换为实际API调用）
      const dataStr = JSON.stringify(workflow, null, 2);
      const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
      
      const exportFileDefaultName = `${name.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.json`;
      
      const linkElement = document.createElement('a');
      linkElement.setAttribute('href', dataUri);
      linkElement.setAttribute('download', exportFileDefaultName);
      linkElement.click();
    } catch (error) {
      console.error('保存工作流失败:', error);
      toast.error('保存工作流失败，请重试');
    }
  };

  const handleSaveWorkflow = (name: string, description: string) => {
    setIsSaving(true);
    try {
      saveWorkflow(name, description);
    } finally {
      setIsSaving(false);
    }
  };

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
                onClick={() => setSaveDialogOpen(true)}
                disabled={executing || nodes.length === 0}
                className="text-blue-400 hover:text-blue-300 border-slate-600/50 hover:bg-blue-950/30"
              >
                <Save className="w-4 h-4 mr-2" />
                保存
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
      <Modal
        title={<span className="text-white font-medium">保存工作流</span>}
        open={saveDialogOpen}
        onCancel={() => setSaveDialogOpen(false)}
        footer={[
          <Button
            key="cancel"
            onClick={() => setSaveDialogOpen(false)}
            className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600 mr-4"
          >
            取消
          </Button>,
          <Button
            key="submit"
            onClick={() => {
              workflowForm.validateFields().then(values => {
                handleSaveWorkflow(values.name, values.description);
              });
            }}
            className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white border-0"
            disabled={isSaving}
          >
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                确认保存
              </>
            )}
          </Button>
        ]}
        className="custom-dark-modal"
      >
        <Form
          form={workflowForm}
          layout="vertical"
          className="mt-4"
          initialValues={{
            name: '',
            description: ''
          }}
        >
          <Form.Item
            name="name"
            label={<span className="text-gray-300">工作流名称</span>}
            rules={[{ required: true, message: '请输入工作流名称' }]}
          >
            <Input 
              placeholder="请输入工作流名称"
              className="bg-slate-800/50 border-slate-700 text-white" 
            />
          </Form.Item>
          <Form.Item
            name="description"
            label={<span className="text-gray-300">工作流描述</span>}
          >
            <Input.TextArea 
              placeholder="请输入工作流描述（可选）"
              className="bg-slate-800/50 border-slate-700 text-white"
              rows={4}
            />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title={<span className="text-white font-medium">清空画布</span>}
        open={clearDialogOpen}
        onCancel={() => setClearDialogOpen(false)}
        footer={[
          <Button
            key="cancel"
            onClick={() => setClearDialogOpen(false)}
            className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600 mr-4"
          >
            取消
          </Button>,
          <Button
            key="submit"
            onClick={clearCanvas}
            className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white border-0"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            确认清空
          </Button>
        ]}
        className="custom-dark-modal"
      >
        <p className="text-gray-300 mt-2">确定要清空画布吗？此操作不可撤销。</p>
      </Modal>
      
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
              <WorkflowDesigner />
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
