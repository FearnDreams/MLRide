import React, { useState, useEffect } from 'react';
import { getJupyterSession } from '@/services/jupyter';
import type { JupyterSession } from '@/types/jupyter';
import { RefreshCw, Maximize, ExternalLink, Info, Server } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogTrigger
} from '@/components/ui/alert-dialog';
import { Badge } from '../../components/ui/badge';

interface JupyterNotebookProps {
  projectId: number;
  sessionId?: number; // 可选的会话ID，用于恢复特定会话
  onSessionError?: () => void;
}

const JupyterNotebook: React.FC<JupyterNotebookProps> = ({ 
  projectId, 
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  sessionId, 
  onSessionError 
}) => {
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState<JupyterSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshCount, setRefreshCount] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const initJupyterSession = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const cleanId = projectId.toString();
        const response = await getJupyterSession(cleanId);
        console.log('Jupyter响应:', response);
        
        if (response && response.url) {
          setSession(response);
        } else {
          setError('无法获取Jupyter会话');
          console.log('Jupyter会话状态:', response?.status);
        }
      } catch (error: any) {
        setError('加载Jupyter失败');
        console.error('Jupyter加载错误:', error);
        if (onSessionError) {
          onSessionError();
        }
      } finally {
        setLoading(false);
      }
    };

    initJupyterSession();
  }, [projectId, refreshCount]);

  const handleRefresh = () => {
    setRefreshCount(prev => prev + 1);
  };

  const handleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const handleOpenNewWindow = () => {
    if (!session?.url) return;
    
    const url = session.direct_access_url || session.url;
    window.open(url, '_blank');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mb-4" />
          <p className="text-slate-400">加载Jupyter...</p>
        </div>
      </div>
    );
  }

  if (error || !session?.url) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-red-400 mb-2">{error || 'Jupyter未启动'}</p>
          <p className="text-slate-400">请尝试重新启动Jupyter服务</p>
          {session && (
            <p className="text-xs text-gray-500 mt-4">
              当前状态: {session.status}
            </p>
          )}
          <div className="mt-4">
            <Button onClick={handleRefresh} className="w-full">
              <RefreshCw className="w-4 h-4 mr-2" />
              刷新Jupyter状态
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const directUrl = session.direct_access_url || session.url;

  const jupyterFrame = (
    <iframe
      key={`jupyter-frame-${refreshCount}`}
      src={directUrl || ''}
      className={`w-full border-0 ${isFullscreen ? 'fixed inset-0 z-50 h-screen' : 'h-full min-h-[700px]'}`}
      title="Jupyter Notebook"
      onError={(e) => console.error('iframe加载错误:', e)}
    />
  );

  // 全屏模式直接返回
  if (isFullscreen) {
    return (
      <>
        {jupyterFrame}
        <div className="fixed top-2 right-2 z-50">
          <Button
            variant="outline"
            size="sm"
            onClick={handleFullscreen}
            className="bg-slate-800/80 hover:bg-slate-700/90 text-white"
          >
            退出全屏
          </Button>
        </div>
      </>
    );
  }

  return (
    <div className="relative w-full h-full flex flex-col" style={{ minHeight: "calc(100vh - 250px)" }}>
      <div className="bg-slate-800 p-2 flex items-center justify-between">
        <h3 className="text-white font-medium flex items-center">
          <img 
            src="/jupyter-logo.svg" 
            alt="Jupyter" 
            className="w-5 h-5 mr-2" 
            onError={(e) => {
              (e.target as HTMLImageElement).src = "https://jupyter.org/favicon.ico";
            }} 
          />
          Jupyter
          {session.running_in_docker && (
            <Badge variant="outline" className="ml-2 bg-blue-900/30 text-blue-300 border-blue-500/50">
              <Server className="w-3 h-3 mr-1" />
              Docker
            </Badge>
          )}
          {session.docker_image && (
            <Badge variant="outline" className="ml-2 bg-slate-900/30 text-slate-300 border-slate-500/50 text-xs">
              {session.docker_image.split(':')[1] || 'custom'}
            </Badge>
          )}
          {session.kernel_info && (
            <Badge variant="outline" className="ml-2 bg-green-900/30 text-green-300 border-green-500/50 text-xs">
              {session.kernel_info.display_name}
            </Badge>
          )}
        </h3>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            title="刷新"
            className="bg-slate-700 hover:bg-slate-600 text-white border-slate-600"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleFullscreen}
            title="全屏模式"
            className="bg-slate-700 hover:bg-slate-600 text-white border-slate-600"
          >
            <Maximize className="w-4 h-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleOpenNewWindow}
            title="在新窗口打开"
            className="bg-slate-700 hover:bg-slate-600 text-white border-slate-600"
          >
            <ExternalLink className="w-4 h-4" />
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                title="调试信息"
                className="bg-slate-700 hover:bg-slate-600 text-white border-slate-600"
              >
                <Info className="w-4 h-4" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent className="sm:max-w-[525px] bg-slate-900">
              <div className="bg-slate-800 text-white p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-3">Jupyter 会话信息</h3>
                <div className="space-y-2 text-sm">
                  <p><span className="text-slate-400">Session ID:</span> {session.id}</p>
                  <p><span className="text-slate-400">Project ID:</span> {session.project}</p>
                  <p><span className="text-slate-400">Status:</span> {session.status}</p>
                  <p><span className="text-slate-400">URL:</span> {session.url}</p>
                  <p><span className="text-slate-400">Direct URL:</span> {directUrl}</p>
                  <p><span className="text-slate-400">Created:</span> {session.created_at}</p>
                  <p><span className="text-slate-400">Updated:</span> {session.updated_at}</p>
                  {session.running_in_docker && (
                    <p><span className="text-slate-400">环境:</span> <span className="text-green-400">Docker容器</span></p>
                  )}
                  {session.docker_image && (
                    <p><span className="text-slate-400">镜像:</span> {session.docker_image}</p>
                  )}
                  {session.kernel_info && (
                    <p><span className="text-slate-400">内核:</span> <span className="text-green-400">{session.kernel_info.display_name}</span></p>
                  )}
                </div>
                <div className="mt-4 space-y-2">
                  <Button
                    variant="outline"
                    onClick={() => directUrl && window.open(directUrl, '_blank')}
                    className="w-full"
                  >
                    在新窗口打开
                  </Button>
                </div>
              </div>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
      
      <div className="flex-grow overflow-hidden" style={{ height: "calc(100vh - 250px)" }}>
        {jupyterFrame}
      </div>
    </div>
  );
};

export default JupyterNotebook;
