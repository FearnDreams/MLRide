import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, Square, RefreshCw, Settings, Cpu, HardDrive, Zap, BookOpen, Trash2, Loader2, Image } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getProject, startProject, stopProject, getProjectStats, deleteProject } from '@/services/projects';
import { ProjectResponse } from '@/services/projects';
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

  const { toast } = useToast();

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
      
      toast({
        title: "成功",
        description: "项目已成功停止",
      });
    } catch (error) {
      console.error('停止项目失败:', error);
      toast({
        title: "错误",
        description: "停止项目失败，请稍后重试",
        variant: "destructive",
      });
    } finally {
      setStatusLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!project) return;
    
    setIsDeleting(true);
    try {
      await deleteProject(project.id);
      toast({
        title: "项目已删除",
        description: `项目 "${project.name}" 已成功删除`,
        variant: "default",
      });
      navigate('/dashboard/projects');
    } catch (error) {
      console.error('删除项目失败:', error);
      toast({
        title: "删除失败",
        description: "删除项目时出现错误",
        variant: "destructive",
      });
    } finally {
      setIsDeleting(false);
      setDeleteDialogOpen(false);
    }
  };

  // 处理Jupyter会话错误
  const handleJupyterSessionError = () => {
    toast({
      title: "Jupyter错误",
      description: "Jupyter会话发生错误，请尝试刷新页面或重启Jupyter",
      variant: "destructive",
    });
    fetchJupyterSession(); // 重新获取会话状态
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
        <div className="text-center py-10">
          <p className="text-gray-300 mb-4">项目当前未运行</p>
          <Button 
            className="bg-green-600 hover:bg-green-700"
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
      );
    }

    // 根据项目类型渲染不同的内容
    if (project_type === 'notebook') {
      // 检查是否有Jupyter会话
      if (!jupyterSession && !jupyterLoading && !forceShowJupyter) {
        return (
          <div className="text-center py-10">
            <p className="text-gray-300 mb-4">Jupyter服务未启动</p>
            <Button 
              className="bg-green-600 hover:bg-green-700 mr-2"
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
              onClick={() => setForceShowJupyter(true)}
            >
              强制显示Notebook
            </Button>
          </div>
        );
      }

      // 显示Jupyter界面
      return (
        <div className="h-full">
          <JupyterNotebook 
            projectId={parseInt(project.id.toString())}
            sessionId={jupyterSession?.id} 
            onSessionError={handleJupyterSessionError}
          />
        </div>
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
          <div>
            <h1 className="text-2xl font-bold text-white">{project?.name}</h1>
            <p className="text-gray-300">{project?.description || '无项目描述'}</p>
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
              <Zap className="w-5 h-5 text-purple-300" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-300">资源使用</h3>
              <p className="text-lg font-semibold text-white">
                {statusLoading ? (
                  <span className="text-sm text-gray-400">加载中...</span>
                ) : stats ? (
                  <span>{stats.cpu_usage?.toFixed(1)}% CPU | {stats.memory_usage?.toFixed(1)}MB 内存</span>
                ) : (
                  <span className="text-sm text-gray-400">项目未运行</span>
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
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除项目</AlertDialogTitle>
            <AlertDialogDescription>
              此操作将永久删除项目 "{project?.name}" 及其相关数据和容器。此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>取消</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-red-500 hover:bg-red-600 text-white"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  删除中...
                </>
              ) : (
                '确认删除'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default ProjectDetailPage;