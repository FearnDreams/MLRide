import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, Square, RefreshCw, Settings, Cpu, HardDrive, Zap, BookOpen, Trash2, Loader2, Image } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getProject, startProject, stopProject, getProjectStats, deleteProject } from '@/services/projects';
import { ProjectResponse } from '@/services/projects';
import { getJupyterSession, startJupyterSession, stopJupyterSession, JupyterSession } from '@/services/jupyter';
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
      const response = await getJupyterSession(parseInt(id));
      if (response && response.data) {
        setJupyterSession(response.data as unknown as JupyterSession);
      }
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
      await stopProject(parseInt(id));
      const response = await getProject(parseInt(id));
      if (response && response.data) {
        setProject(response.data as unknown as ProjectResponse);
        setJupyterSession(null);
      }
    } catch (error) {
      console.error('停止项目失败:', error);
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

  const getIdeUrl = () => {
    if (!project || project.status !== 'running' || !project.container_details) {
      return null;
    }

    const { project_type } = project;
    
    const hostname = window.location.hostname;
    
    if (project_type === 'ide') {
      return `http://${hostname}:3000`;
    }
    
    return null;
  };

  const getJupyterUrl = () => {
    if (!project || project.status !== 'running' || !jupyterSession || jupyterSession.status !== 'running') {
      return null;
    }
    
    return `/api/jupyter/proxy/${jupyterSession.id}/`;
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mb-4" />
          <p className="text-slate-400">加载项目信息...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="bg-red-500/10 border border-red-500/30 p-6 rounded-lg max-w-md text-center">
          <h2 className="text-xl font-semibold mb-2 text-red-400">加载失败</h2>
          <p className="text-slate-300 mb-4">项目不存在或已被删除</p>
          <Button 
            onClick={() => navigate('/dashboard/projects')}
            variant="outline"
          >
            返回项目列表
          </Button>
        </div>
      </div>
    );
  }

  const ideUrl = getIdeUrl();
  const jupyterUrl = getJupyterUrl();

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
            <h1 className="text-2xl font-bold text-white">{project.name}</h1>
            <p className="text-gray-300">{project.description || '无项目描述'}</p>
            {project.image_details && (
              <div className="flex items-center gap-1.5 mt-1.5">
                <Image className="w-4 h-4 text-blue-400" />
                <span className="text-sm text-gray-400">
                  使用镜像: {project.image_details.name}
                  {project.image_details.pythonVersion && ` (Python ${project.image_details.pythonVersion})`}
                </span>
              </div>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {project.status === 'running' ? (
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
          
          {/* Jupyter控制按钮 */}
          {project.status === 'running' && jupyterSession && (
            jupyterSession.status === 'running' ? (
              <Button 
                variant="outline" 
                className="bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-300 border-yellow-500/50"
                onClick={handleStopJupyter}
                disabled={jupyterLoading}
              >
                {jupyterLoading ? (
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Square className="w-4 h-4 mr-2" />
                )}
                停止Jupyter
              </Button>
            ) : (
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
            )
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
                  project.status === 'running' ? 'bg-green-500' :
                  project.status === 'stopped' ? 'bg-yellow-500' :
                  project.status === 'error' ? 'bg-red-500' :
                  'bg-blue-500'
                }`}></span>
                <p className="text-lg font-semibold text-white">
                  {project.status === 'running' ? '运行中' :
                  project.status === 'stopped' ? '已停止' :
                  project.status === 'error' ? '错误' :
                  project.status === 'creating' ? '创建中' : project.status}
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
                {project.project_type === 'ide' ? 'IDE开发环境' :
                project.project_type === 'notebook' ? 'Jupyter Notebook' :
                project.project_type === 'canvas' ? '可视化拖拽编程' : project.project_type}
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
      
      {/* Jupyter 状态 */}
      {project.status === 'running' && jupyterSession && (
        <div className="mb-6 bg-slate-800 rounded-xl border border-slate-600 p-4">
          <div className="flex items-center">
            <div className="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center mr-3">
              <BookOpen className="w-5 h-5 text-indigo-300" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-medium text-gray-300">Jupyter 会话状态</h3>
              <div className="flex items-center">
                <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                  jupyterSession.status === 'running' ? 'bg-green-500' :
                  jupyterSession.status === 'stopped' ? 'bg-yellow-500' :
                  jupyterSession.status === 'error' ? 'bg-red-500' :
                  'bg-blue-500'
                }`}></span>
                <p className="text-lg font-semibold text-white">
                  {jupyterSession.status === 'running' ? '运行中' :
                  jupyterSession.status === 'stopped' ? '已停止' :
                  jupyterSession.status === 'error' ? '错误' :
                  jupyterSession.status === 'creating' ? '创建中' : jupyterSession.status}
                </p>
              </div>
            </div>
            {jupyterLoading && (
              <RefreshCw className="w-4 h-4 text-blue-300 animate-spin ml-2" />
            )}
          </div>
        </div>
      )}
      
      {/* IDE/Jupyter 界面 */}
      <div className="flex-1 bg-slate-800 rounded-xl border border-slate-600 overflow-hidden">
        {project.status === 'running' ? (
          jupyterUrl ? (
            <iframe 
              src={jupyterUrl}
              className="w-full h-full"
              title={`${project.name} Jupyter`}
            />
          ) : ideUrl ? (
            <iframe 
              src={ideUrl}
              className="w-full h-full"
              title={`${project.name} 开发环境`}
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-md p-6">
                <h2 className="text-xl font-semibold mb-2 text-white">环境已启动</h2>
                <p className="text-gray-300 mb-4">
                  项目环境已成功启动，但未启动开发工具。请选择启动Jupyter笔记本或其他工具。
                </p>
                {jupyterSession && jupyterSession.status !== 'running' && (
                  <Button 
                    className="bg-purple-600 hover:bg-purple-500 text-white"
                    onClick={handleStartJupyter}
                    disabled={jupyterLoading}
                  >
                    {jupyterLoading ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <BookOpen className="w-4 h-4 mr-2" />
                    )}
                    启动Jupyter笔记本
                  </Button>
                )}
              </div>
            </div>
          )
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md p-6">
              <h2 className="text-xl font-semibold mb-2 text-white">项目环境未启动</h2>
              <p className="text-gray-300 mb-4">
                {project.status === 'creating' 
                  ? '项目环境正在创建中，请稍候...' 
                  : '请点击"启动项目"按钮以启动项目环境'}
              </p>
              {project.status !== 'creating' && (
                <Button 
                  className="bg-blue-600 hover:bg-blue-500 text-white"
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
            </div>
          </div>
        )}
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