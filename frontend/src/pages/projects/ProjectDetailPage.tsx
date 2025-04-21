import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, Square, RefreshCw, Settings, Cpu, HardDrive, Zap, BookOpen, Trash2, Loader2, Image, Edit2, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getProject, startProject, stopProject, getProjectStats, deleteProject, updateProject } from '@/services/projects';
import { ProjectResponse, CreateProjectRequest } from '@/services/projects';
import { getJupyterSession, startJupyterSession, stopJupyterSession } from '@/services/jupyter';
import type { JupyterSession } from '@/types/jupyter';
import JupyterNotebook from '@/components/jupyter/JupyterNotebook';
import { useToast } from '@/components/ui/use-toast';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Modal, Form, Input, message } from 'antd';

const ProjectDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [jupyterSession, setJupyterSession] = useState<JupyterSession | null>(null);
  const [jupyterLoading, setJupyterLoading] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [forceShowJupyter, setForceShowJupyter] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    const fetchProject = async () => {
      if (!id) return;
      
      setLoading(true);
      try {
        const response = await getProject(parseInt(id));
        if (response && response.data) {
          setProject(response.data as unknown as ProjectResponse);
          fetchStats();
          fetchJupyterSession();
        }
      } catch (error) {
        console.error('获取项目失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProject();
  }, [id]);

  const fetchJupyterSession = async () => {
    if (!id) return;
    
    setJupyterLoading(true);
    try {
      // 确保id是纯数字
      const cleanId = id.replace(/[^\d]/g, '');
      console.log('项目ID清理前:', id, '清理后:', cleanId);
      const response = await getJupyterSession(cleanId);
      setJupyterSession(response);
    } catch (error) {
      console.error('获取Jupyter会话失败:', error);
    } finally {
      setJupyterLoading(false);
    }
  };

  const handleStartJupyter = async () => {
    if (!jupyterSession) return;
    
    setJupyterLoading(true);
    try {
      await startJupyterSession(jupyterSession.id);
      fetchJupyterSession();
    } catch (error) {
      console.error('启动Jupyter失败:', error);
    } finally {
      setJupyterLoading(false);
    }
  };

  const handleStopJupyter = async () => {
    if (!jupyterSession) return;
    
    setJupyterLoading(true);
    try {
      await stopJupyterSession(jupyterSession.id);
      fetchJupyterSession();
    } catch (error) {
      console.error('停止Jupyter失败:', error);
    } finally {
      setJupyterLoading(false);
    }
  };

  const fetchStats = async () => {
    if (!id) return;
    
    setStatusLoading(true);
    try {
      const response = await getProjectStats(parseInt(id));
      if (response && response.data) {
        setStats(response.data);
      }
    } catch (error) {
      console.error('获取资源统计信息失败:', error);
    } finally {
      setStatusLoading(false);
    }
  };

  const handleStartProject = async () => {
    if (!id || !project) return;
    
    setStatusLoading(true);
    try {
      await startProject(parseInt(id));
      const response = await getProject(parseInt(id));
      if (response && response.data) {
        setProject(response.data as unknown as ProjectResponse);
        fetchStats();
        fetchJupyterSession();
      }
    } catch (error) {
      console.error('启动项目失败:', error);
    } finally {
      setStatusLoading(false);
    }
  };

  const handleStopProject = async () => {
    if (!id || !project) return;
    
    setStatusLoading(true);
    try {
      // 尝试停止项目，如果失败可能需要重试
      const stopProjectWithRetry = async (retries = 3) => {
        try {
          // 尝试停止项目
          await stopProject(parseInt(id));
          
          // 停止成功后获取更新的项目状态
          const response = await getProject(parseInt(id));
          if (response && response.data) {
            setProject(response.data as unknown as ProjectResponse);
            // 清除Jupyter会话状态
            setJupyterSession(null);
            return true;
          }
          return false;
        } catch (error) {
          console.error(`停止项目尝试失败 (剩余重试次数: ${retries-1}):`, error);
          if (retries > 1) {
            // 等待一秒后重试
            await new Promise(resolve => setTimeout(resolve, 1000));
            return stopProjectWithRetry(retries - 1);
          }
          throw error;
        }
      };
      
      await stopProjectWithRetry();
      
      message.success('项目已成功停止');
    } catch (error) {
      console.error('停止项目失败:', error);
      message.error('停止项目失败，请稍后重试');
    } finally {
      setStatusLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!project) return;
    
    setIsDeleting(true);
    try {
      await deleteProject(project.id);
      message.success(`项目 "${project.name}" 已成功删除`);
      navigate('/dashboard/projects');
    } catch (error: any) {
      console.error('删除项目失败:', error);
      message.error(error.message || '删除项目时出现错误');
    } finally {
      setIsDeleting(false);
      setDeleteDialogOpen(false);
    }
  };

  // 处理Jupyter会话错误
  const handleJupyterSessionError = () => {
    message.error('Jupyter会话发生错误，请尝试刷新页面或重启Jupyter');
    fetchJupyterSession(); // 重新获取会话状态
  };

  // 打开编辑项目模态框
  const handleOpenEditModal = () => {
    if (!project) return;
    
    form.setFieldsValue({
      name: project.name,
      description: project.description || '',
    });
    setEditModalVisible(true);
  };
  
  // 提交编辑项目
  const handleEditSubmit = async () => {
    if (!project || !id) return;
    
    try {
      setEditLoading(true);
      const values = await form.validateFields();
      
      console.log('提交编辑项目数据:', {
        id: project.id,
        values: values
      });
      
      const response = await updateProject(parseInt(id), {
        name: values.name,
        description: values.description
      });
      
      console.log('更新项目响应:', response);
      
      message.success('项目信息已成功更新');
      
      setEditModalVisible(false);
      
      // 刷新项目数据
      const updatedProject = await getProject(parseInt(id));
      if (updatedProject && updatedProject.data) {
        setProject(updatedProject.data as unknown as ProjectResponse);
      }
    } catch (error: any) {
      console.error('更新项目失败:', error);
      message.error(error.message || '更新项目信息失败');
    } finally {
      setEditLoading(false);
    }
  };

  // 渲染基于项目类型的界面
  const renderProjectContent = () => {
    if (loading) {
      return (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="w-10 h-10 text-blue-400 animate-spin" />
        </div>
      );
    }

    if (!project) {
      return (
        <div className="text-center py-10">
          <p className="text-gray-400">项目不存在或已被删除</p>
        </div>
      );
    }

    const project_type = project.project_type?.toLowerCase() || '';

    // 检查项目容器状态，如果不是运行中，显示启动按钮
    if (project.status !== 'running' && project.container_details) {
      return (
        <div className="flex-grow flex items-center justify-center">
          <div className="text-center max-w-xl w-full">
            <div className="flex justify-center mb-8 mt-8">
              <img 
                src="/jupyter-logo.svg" 
                alt="Jupyter" 
                className="w-20 h-20" 
                onError={(e) => {
                  (e.target as HTMLImageElement).src = "https://jupyter.org/favicon.ico";
                }} 
              />
            </div>
            
            <h2 className="text-2xl font-bold text-white mb-6">项目当前未运行</h2>
            <p className="text-slate-400 mb-10 px-4">您的项目环境已准备就绪但尚未启动，点击下方按钮启动项目</p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10 px-6">
              <div className="bg-slate-700/50 rounded-lg p-5 text-left">
                <h3 className="text-sm font-medium text-slate-300 mb-3">项目信息</h3>
                <p className="text-xs text-slate-400 mb-2">状态: <span className="text-yellow-400">已停止</span></p>
                <p className="text-xs text-slate-400">类型: <span className="text-blue-400">
                  {project.project_type === 'notebook' ? 'Jupyter Notebook' :
                   project.project_type === 'canvas' ? '可视化拖拽编程' : 
                   project.project_type}
                </span></p>
              </div>
              
              <div className="bg-slate-700/50 rounded-lg p-5 text-left">
                <h3 className="text-sm font-medium text-slate-300 mb-3">环境信息</h3>
                {project.image_details ? (
                  <>
                    <p className="text-xs text-slate-400 mb-2">Docker镜像: <span className="text-blue-400">{project.image_details.name}</span></p>
                    {project.image_details.pythonVersion && (
                      <p className="text-xs text-slate-400">Python版本: <span className="text-blue-400">{project.image_details.pythonVersion}</span></p>
                    )}
                  </>
                ) : (
                  <p className="text-xs text-slate-400">环境: <span className="text-blue-400">未指定镜像</span></p>
                )}
              </div>
            </div>
            
            <div className="max-w-md mx-auto mb-8">
              <Button 
                className="w-full py-3 bg-green-600 hover:bg-green-700"
                onClick={handleStartProject}
                disabled={statusLoading}
              >
                {statusLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    正在启动...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    启动项目
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      );
    }

    // 根据项目类型渲染不同的内容
    if (project_type === 'notebook') {
      // 检查是否有Jupyter会话
      if (!jupyterSession && !jupyterLoading && !forceShowJupyter) {
        return (
          <div className="flex-grow flex items-center justify-center">
            <div className="text-center max-w-xl w-full">
              <div className="flex justify-center mb-8 mt-8">
                <img 
                  src="/jupyter-logo.svg" 
                  alt="Jupyter" 
                  className="w-20 h-20" 
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = "https://jupyter.org/favicon.ico";
                  }} 
                />
              </div>
              
              <h2 className="text-2xl font-bold text-white mb-6">Jupyter服务未启动</h2>
              <p className="text-slate-400 mb-10 px-4">项目已运行，但Jupyter服务尚未启动，点击下方按钮启动Jupyter服务</p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10 px-6">
                <div className="bg-slate-700/50 rounded-lg p-5 text-left">
                  <h3 className="text-sm font-medium text-slate-300 mb-3">项目信息</h3>
                  <p className="text-xs text-slate-400 mb-2">状态: <span className="text-green-400">运行中</span></p>
                  <p className="text-xs text-slate-400">类型: <span className="text-blue-400">Jupyter Notebook</span></p>
                </div>
                
                <div className="bg-slate-700/50 rounded-lg p-5 text-left">
                  <h3 className="text-sm font-medium text-slate-300 mb-3">环境信息</h3>
                  {project.image_details ? (
                    <>
                      <p className="text-xs text-slate-400 mb-2">Docker镜像: <span className="text-blue-400">{project.image_details.name}</span></p>
                      {project.image_details.pythonVersion && (
                        <p className="text-xs text-slate-400">Python版本: <span className="text-blue-400">{project.image_details.pythonVersion}</span></p>
                      )}
                    </>
                  ) : (
                    <p className="text-xs text-slate-400">环境: <span className="text-blue-400">未指定镜像</span></p>
                  )}
                </div>
              </div>
              
              <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4 max-w-md mx-auto mb-8">
                <Button 
                  className="flex-1 py-3 bg-green-600 hover:bg-green-700"
                  onClick={handleStartJupyter}
                  disabled={jupyterLoading}
                >
                  {jupyterLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      正在启动...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      启动Jupyter
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  className="flex-1 py-3 border-slate-600 hover:bg-slate-700"
                  onClick={() => setForceShowJupyter(true)}
                >
                  强制显示Notebook
                </Button>
              </div>
            </div>
          </div>
        );
      }

      // 显示Jupyter界面
      return (
        <JupyterNotebook 
          projectId={parseInt(project.id.toString())}
          sessionId={jupyterSession?.id} 
          onSessionError={handleJupyterSessionError}
        />
      );
    } else if (project_type === 'canvas') {
      return (
        <div className="text-center py-10">
          <p className="text-gray-300">可视化拖拽编程界面正在开发中...</p>
        </div>
      );
    } else {
      return (
        <div className="text-center py-10">
          <p className="text-gray-300">未知项目类型或不支持的界面</p>
        </div>
      );
    }
  };

  // 项目详细信息部分
  const renderProjectDetails = () => {
    if (!project) return null;
    
    return (
      <div>
        <h2 className="text-lg font-bold mb-4 text-white">项目详情</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">项目类型:</span>
            <span className="text-white font-medium">
              {project.project_type === 'notebook' ? 'Jupyter Notebook' :
               project.project_type === 'canvas' ? '可视化拖拽编程' : 
               project.project_type}
            </span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-400">项目状态:</span>
            <span className="text-white font-medium">
              {project.status === 'running' ? '运行中' :
               project.status === 'stopped' ? '已停止' :
               project.status === 'error' ? '错误' :
               project.status === 'creating' ? '创建中' : project.status}
            </span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-400">资源使用:</span>
            <span className="text-white font-medium">
              {statusLoading ? (
                <span className="text-sm text-gray-400">加载中...</span>
              ) : stats ? (
                <span>{stats.cpu_usage?.toFixed(1)}% CPU | {stats.memory_usage?.toFixed(1)}MB 内存</span>
              ) : (
                <span className="text-sm text-gray-400">项目未运行</span>
              )}
            </span>
          </div>

          {project.image_details && (
            <div className="flex justify-between">
              <span className="text-gray-400">使用镜像:</span>
              <span className="text-white font-medium">
                {project.image_details.name}
                {project.image_details.pythonVersion && ` (Python ${project.image_details.pythonVersion})`}
              </span>
            </div>
          )}
        </div>
      </div>
    );
  };

  // 编辑项目模态框
  const renderEditModal = () => {
    return (
      <Modal
        title={<span className="text-white font-medium">编辑项目</span>}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={[
          <Button
            key="cancel"
            onClick={() => setEditModalVisible(false)}
            className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600 mr-4"
          >
            取消
          </Button>,
          <Button
            key="submit"
            onClick={handleEditSubmit}
            className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white border-0"
            disabled={editLoading}
          >
            {editLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                保存
              </>
            )}
          </Button>
        ]}
        className="custom-dark-modal"
      >
        <Form
          form={form}
          layout="vertical"
          className="mt-4"
        >
          <Form.Item
            name="name"
            label={<span className="text-gray-300">项目名称</span>}
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input 
              placeholder="请输入项目名称" 
              className="bg-slate-800/50 border-slate-700 text-white" 
            />
          </Form.Item>
          <Form.Item
            name="description"
            label={<span className="text-gray-300">项目描述</span>}
          >
            <Input.TextArea 
              placeholder="请输入项目描述（可选）" 
              className="bg-slate-800/50 border-slate-700 text-white"
              rows={4}
            />
          </Form.Item>
        </Form>
      </Modal>
    );
  };

  return (
    <div className="flex-1 flex flex-col">
      {/* 顶部导航栏 */}
      <div className="flex justify-between items-center mb-6 pb-4 border-b border-slate-600">
        <div className="flex items-center">
          <Button
            variant="ghost"
            className="mr-4 text-white hover:bg-slate-700"
            onClick={() => navigate('/dashboard/projects')}
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            返回项目列表
          </Button>
          <div className="flex items-center">
            <div>
              <h1 className="text-2xl font-bold text-white">{project?.name}</h1>
              <p className="text-gray-300">{project?.description || '无项目描述'}</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="ml-2 text-gray-400 hover:text-white hover:bg-slate-700"
              onClick={handleOpenEditModal}
            >
              <Edit2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {project?.status === 'running' ? (
            <Button 
              variant="outline" 
              className="bg-red-500/10 hover:bg-red-500/20 text-red-300 border-red-500/50"
              onClick={handleStopProject}
              disabled={statusLoading}
            >
              {statusLoading ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Square className="w-4 h-4 mr-2" />
              )}
              停止项目
            </Button>
          ) : (
            <Button 
              variant="outline" 
              className="bg-green-500/10 hover:bg-green-500/20 text-green-300 border-green-500/50"
              onClick={handleStartProject}
              disabled={statusLoading}
            >
              {statusLoading ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              启动项目
            </Button>
          )}
          
          {/* Jupyter控制按钮 - 只有当Jupyter未启动时才显示启动按钮 */}
          {project?.status === 'running' && jupyterSession && 
           jupyterSession.status !== 'running' && (
            <Button 
              variant="outline" 
              className="bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border-purple-500/50"
              onClick={handleStartJupyter}
              disabled={jupyterLoading}
            >
              {jupyterLoading ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <BookOpen className="w-4 h-4 mr-2" />
              )}
              启动Jupyter
            </Button>
          )}
          
          <Button 
            variant="outline"
            className="text-white border-slate-500 hover:bg-slate-700"
            onClick={handleOpenEditModal}
          >
            <Settings className="w-4 h-4 mr-2" />
            项目设置
          </Button>
          <Button 
            variant="outline"
            className="text-red-500 border-red-500 hover:bg-red-500/10"
            onClick={() => setDeleteDialogOpen(true)}
          >
            <Trash2 className="w-4 h-4 mr-2" />
            删除项目
          </Button>
        </div>
      </div>
      
      {/* 状态信息 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-slate-800 rounded-xl border border-slate-600 p-4">
          <div className="flex items-center">
            <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center mr-3">
              <Cpu className="w-5 h-5 text-blue-300" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-300">项目状态</h3>
              <div className="flex items-center">
                <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                  project?.status === 'running' ? 'bg-green-500' :
                  project?.status === 'stopped' ? 'bg-yellow-500' :
                  project?.status === 'error' ? 'bg-red-500' :
                  'bg-blue-500'
                }`}></span>
                <p className="text-lg font-semibold text-white">
                  {project?.status === 'running' ? '运行中' :
                  project?.status === 'stopped' ? '已停止' :
                  project?.status === 'error' ? '错误' :
                  project?.status === 'creating' ? '创建中' : project?.status}
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-slate-800 rounded-xl border border-slate-600 p-4">
          <div className="flex items-center">
            <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center mr-3">
              <HardDrive className="w-5 h-5 text-green-300" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-300">项目类型</h3>
              <p className="text-lg font-semibold text-white">
                {project?.project_type === 'notebook' ? 'Jupyter Notebook' :
                project?.project_type === 'canvas' ? '可视化拖拽编程' : project?.project_type}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-slate-800 rounded-xl border border-slate-600 p-4">
          <div className="flex items-center">
            <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center mr-3">
              <Image className="w-5 h-5 text-purple-300" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-300">Docker镜像</h3>
              <p className="text-lg font-semibold text-white">
                {project?.image_details ? (
                  <span>
                    {project.image_details.name}
                    {project.image_details.pythonVersion && ` (Python ${project.image_details.pythonVersion})`}
                  </span>
                ) : (
                  <span className="text-sm text-gray-400">未指定镜像</span>
                )}
              </p>
            </div>
          </div>
        </div>
      </div>
      
      {/* IDE/Jupyter 界面 */}
      <div className="flex-1 bg-slate-800 rounded-xl border border-slate-600 overflow-hidden">
        {renderProjectContent()}
      </div>
      
      {/* 删除确认对话框 */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="bg-slate-800/75 backdrop-blur-sm border border-slate-700/50 shadow-lg">
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除项目</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-400">
              此操作将永久删除项目 "{project?.name}" 及其相关数据和容器。此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting} className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600" autoFocus={false}>取消</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white border-0"
              autoFocus={true}
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  删除中...
                </>
              ) : (
                <>
                  <Trash2 className="mr-2 h-4 w-4" />
                  确认删除
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      
      {/* 编辑项目模态框 */}
      {renderEditModal()}
      
      {/* 添加Dark Modal样式 */}
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
        .custom-dark-modal .ant-btn-primary {
          color: white !important;
        }
        .custom-dark-modal .ant-btn-default {
          color: rgb(209, 213, 219) !important;
          border-color: rgba(71, 85, 105, 0.5) !important;
          background-color: rgba(51, 65, 85, 0.5) !important;
        }
        .custom-dark-modal .ant-btn-default:hover {
          color: white !important;
          border-color: rgba(59, 130, 246, 0.5) !important;
          background-color: rgba(71, 85, 105, 0.5) !important;
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
          border-color: rgba(51, 65, 85, 0.8) !important;
          color: rgb(237, 242, 247) !important;
        }
        .custom-dark-modal .ant-input::placeholder,
        .custom-dark-modal .ant-input-number-input::placeholder,
        .custom-dark-modal .ant-input-textarea textarea::placeholder {
          color: rgba(148, 163, 184, 0.5) !important;
        }
        .custom-dark-modal .ant-input:hover,
        .custom-dark-modal .ant-input-affix-wrapper:hover,
        .custom-dark-modal .ant-input-number:hover,
        .custom-dark-modal .ant-select-selector:hover,
        .custom-dark-modal .ant-input-textarea:hover {
          border-color: rgba(59, 130, 246, 0.5) !important;
        }
        .custom-dark-modal .ant-input:focus,
        .custom-dark-modal .ant-input-affix-wrapper:focus,
        .custom-dark-modal .ant-input-number:focus,
        .custom-dark-modal .ant-select-selector:focus,
        .custom-dark-modal .ant-input-textarea:focus {
          border-color: rgba(59, 130, 246, 0.8) !important;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
        }
        .custom-dark-modal .ant-form-item-explain-error {
          color: #f56565 !important;
        }

        /* AlertDialog 样式 */
        [role="dialog"][data-state="open"] {
          animation: fadeIn 150ms ease-out;
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        [data-state="open"] > [data-state="open"] {
          animation: zoomIn 150ms ease-out;
        }
        @keyframes zoomIn {
          from { 
            opacity: 0; 
            transform: scale(0.95);
          }
          to { 
            opacity: 1; 
            transform: scale(1);
          }
        }
        
        div[role="alertdialog"] {
          background-color: rgba(15, 23, 42, 0.75) !important;
          backdrop-filter: blur(12px) !important;
          border: 1px solid rgba(51, 65, 85, 0.5) !important;
          border-radius: 0.75rem !important;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3) !important;
          padding: 1.5rem !important;
        }
        
        div[role="alertdialog"] h2 {
          color: white !important;
          font-size: 1.25rem !important;
          margin-bottom: 0.5rem !important;
        }
        
        div[role="alertdialog"] button:first-of-type {
          background-color: rgba(51, 65, 85, 0.5) !important;
          border-color: rgba(71, 85, 105, 0.5) !important;
          color: rgb(209, 213, 219) !important;
          outline: none !important;
        }
        
        div[role="alertdialog"] button:first-of-type:hover {
          background-color: rgba(71, 85, 105, 0.5) !important;
          border-color: rgba(59, 130, 246, 0.5) !important;
          color: white !important;
        }
        
        div[role="alertdialog"] button:first-of-type:focus,
        div[role="alertdialog"] button:first-of-type:focus-visible {
          background-color: rgba(51, 65, 85, 0.5) !important;
          border-color: rgba(71, 85, 105, 0.5) !important;
          outline: none !important;
          box-shadow: none !important;
          color: rgb(209, 213, 219) !important;
        }

        div[role="alertdialog"] button:focus,
        div[role="alertdialog"] button:focus-visible {
          outline: none !important;
          box-shadow: none !important;
        }
        
        div[role="alertdialog"] button:last-of-type {
          background: linear-gradient(to right, #dc2626, #b91c1c) !important;
        }
        
        div[role="alertdialog"] button:last-of-type:hover {
          background: linear-gradient(to right, #ef4444, #dc2626) !important;
        }
      `}</style>
    </div>
  );
};

export default ProjectDetailPage;