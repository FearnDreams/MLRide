import React, { useState, useEffect, useRef } from 'react';
import { getJupyterSession } from '@/services/jupyter';
import type { JupyterSession } from '@/types/jupyter';
import { RefreshCw, ExternalLink, Info, Server, AlertTriangle, Upload, Loader, X, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogTrigger,
  AlertDialogCancel
} from '@/components/ui/alert-dialog';
import { Badge } from '../../components/ui/badge';
import axios from 'axios';
import { Modal } from 'antd';

// 本地存储键名
const SESSION_STORAGE_KEY = 'jupyter_session_cache';

// 从本地存储恢复会话信息的函数
const getStoredSessionInfo = (projectId: number): Partial<JupyterSession> | null => {
  try {
    const storedData = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!storedData) {
      console.log('本地存储中没有会话信息');
      return null;
    }
    
    const parsedData = JSON.parse(storedData);
    // 只恢复与当前项目匹配的会话信息
    if (parsedData && parsedData.project === projectId) {
      console.log('从本地存储恢复会话信息:', parsedData);
      
      // 确保各字段的有效性
      const validatedData = {
        ...parsedData,
        running_in_docker: parsedData.running_in_docker === true,
        docker_image: parsedData.docker_image || '',
        kernel_info: parsedData.kernel_info || {}
      };
      
      console.log('恢复的docker_image:', validatedData.docker_image);
      console.log('恢复的running_in_docker:', validatedData.running_in_docker);
      console.log('恢复的kernel_info:', validatedData.kernel_info);
      
      return validatedData;
    }
    console.log('本地存储中的会话信息与当前项目不匹配');
    return null;
  } catch (error) {
    console.error('从本地存储恢复会话信息时出错:', error);
    return null;
  }
};

// 保存会话信息到本地存储
const saveSessionToStorage = (session: JupyterSession) => {
  try {
    if (!session) {
      console.log('未提供会话信息，无法保存');
      return;
    }
    
    // 在sessionToStore变量定义中添加更多字段，以确保所有重要字段都被持久化
    const sessionToStore = {
      id: session.id,
      project: session.project,
      status: session.status,
      running_in_docker: session.running_in_docker === true ? true : false, // 显式转换为布尔值
      docker_image: session.docker_image || '',
      kernel_info: session.kernel_info ? { ...session.kernel_info } : {}, // 确保内核信息被复制保存
      updated_at: session.updated_at,
      created_at: session.created_at,
      url: session.url,
      direct_access_url: session.direct_access_url
    };
    
    console.log('保存会话信息到本地存储:', sessionToStore);
    console.log('保存的docker_image:', sessionToStore.docker_image);
    console.log('保存的running_in_docker:', sessionToStore.running_in_docker);
    console.log('保存的kernel_info:', sessionToStore.kernel_info);
    
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessionToStore));
    console.log('会话信息已成功保存到本地存储');
  } catch (error) {
    console.error('保存会话信息到本地存储时出错:', error);
  }
};

// 合并API返回的会话信息和本地存储的会话信息
const mergeSessionInfo = (apiSession: JupyterSession, storedSession: Partial<JupyterSession> | null): JupyterSession => {
  if (!storedSession) {
    console.log('没有本地存储的会话信息，使用API返回的会话信息');
    return apiSession;
  }
  
  console.log('合并会话信息开始');
  console.log('API返回的会话信息:', apiSession);
  console.log('本地存储的会话信息:', storedSession);
  
  // 如果API返回的信息缺少docker_image或kernel_info，则从本地存储中恢复
  const mergedSession = { ...apiSession };
  
  // 强化running_in_docker合并逻辑，更明确的检查条件
  if ((mergedSession.running_in_docker === undefined || mergedSession.running_in_docker === false) && 
      storedSession.running_in_docker === true) {
    console.log('从本地存储恢复running_in_docker:', storedSession.running_in_docker);
    mergedSession.running_in_docker = storedSession.running_in_docker;
  }
  
  // 改进docker_image合并逻辑
  if ((!mergedSession.docker_image || mergedSession.docker_image === '' || mergedSession.docker_image === undefined) && 
      storedSession.docker_image && storedSession.docker_image !== '') {
    console.log('从本地存储恢复docker_image:', storedSession.docker_image);
    mergedSession.docker_image = storedSession.docker_image;
  }
  
  // 加强kernel_info合并逻辑，确保内核信息不丢失
  if ((!mergedSession.kernel_info || 
       !mergedSession.kernel_info.name || 
       Object.keys(mergedSession.kernel_info || {}).length === 0) && 
      storedSession.kernel_info && 
      Object.keys(storedSession.kernel_info).length > 0) {
    console.log('从本地存储恢复kernel_info:', storedSession.kernel_info);
    mergedSession.kernel_info = { ...storedSession.kernel_info };
  }
  
  console.log('合并后的会话信息:', mergedSession);
  return mergedSession;
};

interface JupyterNotebookProps {
  projectId: number;
  sessionId?: number; // 可选的会话ID，用于恢复特定会话
  onSessionError?: () => void;
  onUploadDataClick?: () => void; // 新增 prop，用于处理上传数据按钮点击
}

const JupyterNotebook: React.FC<JupyterNotebookProps> = ({ 
  projectId, 
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  sessionId, 
  onSessionError, 
  onUploadDataClick // 接收 prop
}) => {
  const [loading, setLoading] = useState(true);
  const [initializing, setInitializing] = useState(true); // 初始化状态，包括检查后端是否真正准备好
  const [session, setSession] = useState<JupyterSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshCount, setRefreshCount] = useState(0);
  const [retryCount, setRetryCount] = useState(0);
  const [statusCheckCount, setStatusCheckCount] = useState(0);
  const [checkingStatus, setCheckingStatus] = useState(false); // 添加状态检查标志，避免重复检查
  
  const timeoutRef = useRef<number | null>(null);
  const statusCheckRef = useRef<number | null>(null);
  
  // 清理函数 - 用于清理所有定时器
  const cleanupTimers = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    
    if (statusCheckRef.current) {
      clearTimeout(statusCheckRef.current);
      statusCheckRef.current = null;
    }
  };
  
  // 在组件卸载时清理所有定时器
  useEffect(() => {
    return () => {
      cleanupTimers();
    };
  }, []);
  
  // 检查Jupyter状态是否真正准备好
  const checkJupyterReady = async (jupyterSession: JupyterSession): Promise<boolean> => {
    try {
      console.log('开始检查Jupyter服务是否准备就绪...');
      
      // 如果状态不是running，则认为未准备好
      if (jupyterSession.status !== 'running') {
        console.log('Jupyter会话状态不是running:', jupyterSession.status);
        return false;
      }
      
      // 验证URL是否存在
      if (!jupyterSession.url) {
        console.log('Jupyter会话URL不存在');
        return false;
      }
      
      // 仅检查一次后直接认为已准备就绪
      console.log('Jupyter会话状态是running且URL存在，认为服务已就绪');
      return true;
    } catch (error) {
      console.log('检查Jupyter状态时出错:', error);
      return false;
    }
  };
  
  // 主要的Jupyter会话初始化逻辑
  useEffect(() => {
    const initJupyterSession = async () => {
      // 如果已经在检查状态，则直接返回，避免重复检查
      if (checkingStatus) {
        console.log('已有状态检查在进行中，跳过本次检查');
        return;
      }
      
      try {
        setCheckingStatus(true);
        setLoading(true);
        setError(null);
        
        // 只有在未初始化状态或需要重试时才进行
        if (initializing || retryCount > 0) {
          cleanupTimers(); // 清除之前的所有定时器
          
          // 减少请求头大小，只保留绝对必要的头部
          const fetchOptions = {
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            },
            timeout: 60000, // 60秒超时
            withCredentials: false
          };
          
          const cleanId = projectId.toString();
          console.log(`尝试获取Jupyter会话 (尝试 ${retryCount + 1}): 项目ID=${cleanId}`);
          
          // 先从本地存储获取会话信息
          const storedSession = getStoredSessionInfo(projectId);
          console.log('从本地存储获取的会话信息:', storedSession);
          
          const response = await getJupyterSession(cleanId, fetchOptions);
          console.log('API Jupyter响应:', response);
          console.log('响应详情:', {
            status: response?.status,
            running_in_docker: response?.running_in_docker,
            docker_image: response?.docker_image,
            kernel_info: response?.kernel_info
          });
          
          if (response && response.url) {
            // 重置重试计数器
            setRetryCount(0);
            
            // 合并API返回的会话信息和本地存储的会话信息
            const mergedSession = mergeSessionInfo(response, storedSession);
            console.log('最终合并的会话信息:', mergedSession);
            
            // 确保保存核心会话信息，防止信息丢失
            if (!mergedSession.running_in_docker && storedSession?.running_in_docker) {
              mergedSession.running_in_docker = storedSession.running_in_docker;
            }
            
            if ((!mergedSession.docker_image || mergedSession.docker_image === '') && storedSession?.docker_image) {
              mergedSession.docker_image = storedSession.docker_image;
            }
            
            if ((!mergedSession.kernel_info || Object.keys(mergedSession.kernel_info || {}).length === 0) && storedSession?.kernel_info) {
              mergedSession.kernel_info = storedSession.kernel_info;
            }
            
            // 保存合并后的会话信息到状态和本地存储
            setSession(mergedSession);
            saveSessionToStorage(mergedSession);
            
            // 检查Jupyter是否真正准备好
            const isReady = await checkJupyterReady(mergedSession);
            
            if (isReady) {
              console.log('Jupyter服务已准备就绪，显示信息面板');
              setInitializing(false);
              setStatusCheckCount(0); // 重置检查计数
            } else if (statusCheckCount < 5) { // 减少检查次数，最多检查5次
              console.log(`Jupyter服务尚未完全准备就绪，这是第 ${statusCheckCount + 1} 次检查`);
              
              // 增加检查计数并设置下一次检查
              setStatusCheckCount(prev => prev + 1);
              statusCheckRef.current = window.setTimeout(() => {
                setCheckingStatus(false); // 重置检查状态标志
                setRefreshCount(prev => prev + 1);
              }, 2000);
            } else {
              // 检查次数达到上限，假设服务已就绪
              console.log('检查次数达到上限，假设Jupyter服务已准备就绪');
              setInitializing(false);
              setStatusCheckCount(0);
            }
          } else {
            setError('无法获取Jupyter会话');
            console.log('Jupyter会话状态:', response?.status);
            
            // 重试逻辑 - 最多重试5次，且使用指数退避策略
            if (retryCount < 5) {
              const delay = Math.min(2000 * Math.pow(1.5, retryCount), 15000);
              console.log(`将在${delay/1000}秒后重试 (${retryCount + 1}/5)...`);
              
              timeoutRef.current = window.setTimeout(() => {
                setCheckingStatus(false); // 重置检查状态标志
                setRetryCount(prev => prev + 1);
                setRefreshCount(prev => prev + 1); // 触发useEffect重新执行
              }, delay);
            } else if (onSessionError) {
              onSessionError();
            }
          }
        }
      } catch (error: any) {
        setError('加载Jupyter失败');
        console.error('Jupyter加载错误:', error);
        
        // 使用指数退避策略进行重试
        if (retryCount < 5) {
          const delay = Math.min(2000 * Math.pow(1.5, retryCount), 15000);
          console.log(`请求错误，将在${delay/1000}秒后重试 (${retryCount + 1}/5)...`);
          
          timeoutRef.current = window.setTimeout(() => {
            setCheckingStatus(false); // 重置检查状态标志
            setRetryCount(prev => prev + 1);
            setRefreshCount(prev => prev + 1); // 触发useEffect重新执行
          }, delay);
        } else if (onSessionError) {
          onSessionError();
        }
      } finally {
        setLoading(false);
        setCheckingStatus(false);
      }
    };

    initJupyterSession();
  }, [projectId, refreshCount, retryCount, onSessionError, initializing, checkingStatus, statusCheckCount]);

  const handleRefresh = () => {
    cleanupTimers();
    setStatusCheckCount(0);
    setInitializing(true); // 重置初始化状态
    setCheckingStatus(false); // 重置检查状态
    // 不要清除session变量，以便在重新加载时保持页面显示
    console.log("开始刷新，准备重新获取会话信息...");
    console.log("当前session信息:", session);
    setRefreshCount(prev => prev + 1);
  };

  const handleOpenNewWindow = () => {
    if (!session?.url) return;
    
    const url = session.direct_access_url || session.url;
    window.open(url, '_blank');
  };
  
  const handleUploadData = () => {
    // 调用传入的 prop 函数
    if (onUploadDataClick) {
      onUploadDataClick();
    } else {
      // 如果没有传入 prop，可以保留原来的日志或提示
      console.log('上传数据功能未连接到父组件');
    }
  };
  
  // 显示加载状态UI
  if (loading && (retryCount > 0 || statusCheckCount === 0)) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center max-w-md w-full p-8">
          <div className="relative mb-8">
            <div className="w-16 h-16 rounded-full border-4 border-blue-500/30 border-t-blue-500 animate-spin"></div>
            <RefreshCw className="w-6 h-6 text-blue-400 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
          </div>
          
          <h3 className="text-xl font-medium text-white mb-4">加载Jupyter中...</h3>
          <p className="text-slate-400 text-center mb-6">我们正在为您准备Jupyter环境，这可能需要一些时间</p>
          
          {/* 加载动画 - 替代进度条 */}
          <div className="flex justify-center space-x-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '300ms' }}></div>
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '450ms' }}></div>
          </div>
          
          {/* 尝试次数显示 */}
          {retryCount > 0 && (
            <div className="flex items-center justify-center space-x-2 mt-4 p-2 bg-slate-800/60 rounded-lg">
              <RefreshCw className="w-4 h-4 text-amber-400 animate-spin" />
              <p className="text-sm text-amber-400">
                重试中 ({retryCount}/5)
              </p>
            </div>
          )}
        </div>
      </div>
    );
  }
  
  // 显示初始化状态UI
  if (initializing) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center max-w-md w-full p-8">
          <div className="relative mb-8">
            <svg className="w-20 h-20 animate-spin" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <circle cx="50" cy="50" r="45" fill="none" stroke="#1e293b" strokeWidth="8" />
              <path 
                d="M50 5 A 45 45 0 0 1 95 50" 
                fill="none" 
                stroke="#3b82f6" 
                strokeWidth="8" 
                strokeLinecap="round" 
              />
            </svg>
            <Loader className="w-6 h-6 text-blue-400 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
          </div>
          
          <h3 className="text-xl font-medium text-white mb-4">初始化Jupyter环境</h3>
          <p className="text-slate-400 text-center mb-6">
            {statusCheckCount > 0 
              ? '正在检查Jupyter服务，请稍候...' 
              : '正在初始化Docker容器和Jupyter服务...'
            }
          </p>
          
          {/* 状态信息卡片 */}
          <div className="w-full bg-slate-800/60 rounded-lg p-4 mb-6">
            <div className="flex items-center mb-4">
              <Server className="w-5 h-5 text-blue-400 mr-2" />
              <span className="text-sm text-slate-300 font-medium">服务状态</span>
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-400">Docker容器</span>
                <span className="text-xs text-green-400 flex items-center">
                  <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></span>
                  运行中
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-400">Jupyter服务</span>
                <span className="text-xs text-amber-400 flex items-center">
                  <span className="w-2 h-2 bg-amber-500 rounded-full mr-1 animate-pulse"></span>
                  正在初始化
                </span>
              </div>
              
              {statusCheckCount > 0 && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-400">检查尝试</span>
                  <span className="text-xs text-blue-400">{statusCheckCount} / 5</span>
                </div>
              )}
            </div>
          </div>
          
          {/* 脉冲动画 - 替代进度条 */}
          <div className="flex justify-center mb-1">
            <div className="flex space-x-1">
              {[...Array(5)].map((_, i) => (
                <div 
                  key={i}
                  className="w-2 h-8 bg-blue-500 rounded-full animate-pulse" 
                  style={{ 
                    animationDelay: `${i * 200}ms`,
                    opacity: i < statusCheckCount ? 1 : 0.3
                  }}
                ></div>
              ))}
            </div>
          </div>
          <div className="text-xs text-slate-500 text-center">
            {statusCheckCount === 0 ? '初始化中...' : `检查中 (${statusCheckCount}/5)`}
          </div>
        </div>
      </div>
    );
  }

  if (error || !session?.url) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center max-w-md w-full p-8">
          <div className="w-20 h-20 flex items-center justify-center bg-red-500/10 rounded-full mb-6">
            <AlertTriangle className="w-10 h-10 text-red-500" />
          </div>
          
          <h3 className="text-xl font-medium text-white mb-4">加载Jupyter失败</h3>
          <p className="text-red-400 text-center mb-2">{error || 'Jupyter服务未启动'}</p>
          <p className="text-slate-400 text-center mb-6">请尝试重新启动Jupyter服务或刷新页面</p>
          
          {session && (
            <div className="w-full bg-slate-800/60 rounded-lg p-4 mb-6">
              <h4 className="text-sm font-medium text-slate-300 mb-2">会话状态</h4>
              <p className="text-xs text-slate-400">
                当前状态: <span className="text-amber-400">{session.status}</span>
              </p>
            </div>
          )}
          
          <Button onClick={handleRefresh} className="w-full bg-blue-600 hover:bg-blue-700 py-3">
            <RefreshCw className="w-4 h-4 mr-2" />
            刷新Jupyter状态
          </Button>
        </div>
      </div>
    );
  }

  const directUrl = session.direct_access_url || session.url;

  // 新的信息展示界面，不再使用iframe
  return (
    <div className="flex flex-col h-full">
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
          {session.running_in_docker === true && (
            <Badge variant="outline" className="ml-2 bg-blue-900/30 text-blue-300 border-blue-500/50">
              <Server className="w-3 h-3 mr-1" />
              Docker
            </Badge>
          )}
          {session.docker_image && session.docker_image !== '' && (
            <Badge variant="outline" className="ml-2 bg-slate-900/30 text-slate-300 border-slate-500/50 text-xs">
              {session.docker_image.includes(':') 
                ? session.docker_image.split(':')[1] || 'custom'
                : session.docker_image}
            </Badge>
          )}
          {session.kernel_info && Object.keys(session.kernel_info).length > 0 && (
            <Badge variant="outline" className="ml-2 bg-green-900/30 text-green-300 border-green-500/50 text-xs">
              {session.kernel_info.display_name || session.kernel_info.name || 'Unknown Kernel'}
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
          
          {/* 替换原来的AlertDialog为按钮+Modal组合 */}
          <Button
            variant="outline"
            size="sm"
            title="调试信息"
            className="bg-slate-700 hover:bg-slate-600 text-white border-slate-600"
            onClick={() => {
              Modal.info({
                title: <span className="text-white font-medium">Jupyter 会话信息</span>,
                icon: null,
                content: (
                  <div className="space-y-2 text-sm mt-4">
                    <p><span className="text-slate-400">Session ID:</span> <span className="text-white">{session.id}</span></p>
                    <p><span className="text-slate-400">Project ID:</span> <span className="text-white">{session.project}</span></p>
                    <p><span className="text-slate-400">Status:</span> <span className="text-white">{session.status}</span></p>
                    <p><span className="text-slate-400">URL:</span> <span className="text-white">{session.url}</span></p>
                    <p><span className="text-slate-400">Direct URL:</span> <span className="text-white">{directUrl}</span></p>
                    <p><span className="text-slate-400">Created:</span> <span className="text-white">{session.created_at}</span></p>
                    <p><span className="text-slate-400">Updated:</span> <span className="text-white">{session.updated_at}</span></p>
                    {session.running_in_docker && (
                      <p><span className="text-slate-400">环境:</span> <span className="text-green-400">Docker容器</span></p>
                    )}
                    {session.docker_image && (
                      <p><span className="text-slate-400">镜像:</span> <span className="text-white">{session.docker_image}</span></p>
                    )}
                    {session.kernel_info && (
                      <p><span className="text-slate-400">内核:</span> <span className="text-green-400">{session.kernel_info.display_name}</span></p>
                    )}
                  </div>
                ),
                centered: true,
                okText: "关闭",
                className: "custom-dark-modal",
                footer: (_, { OkBtn }) => (
                  <div className="flex justify-end space-x-4 mt-4">
                    <Button
                      variant="outline"
                      onClick={() => directUrl && window.open(directUrl, '_blank')}
                      className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600"
                    >
                      <ExternalLink className="mr-2 h-4 w-4" />
                      在新窗口打开
                    </Button>
                    <Button
                      className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white border-0"
                      onClick={() => Modal.destroyAll()}
                    >
                      关闭
                    </Button>
                  </div>
                ),
              });
            }}
          >
            <Info className="w-4 h-4" />
          </Button>
        </div>
      </div>
      
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
          
          <h2 className="text-2xl font-bold text-white mb-6">Jupyter Notebook 已准备就绪</h2>
          <p className="text-slate-400 mb-10 px-4">您的Jupyter环境已成功启动，您可以在新窗口中打开它或上传数据</p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10 px-6">
            <div className="bg-slate-700/50 rounded-lg p-5 text-left">
              <h3 className="text-sm font-medium text-slate-300 mb-3">会话信息</h3>
              <p className="text-xs text-slate-400 mb-2">状态: <span className="text-green-400">运行中</span></p>
              <p className="text-xs text-slate-400">创建时间: {new Date(session.created_at).toLocaleString()}</p>
            </div>
            
            <div className="bg-slate-700/50 rounded-lg p-5 text-left">
              <h3 className="text-sm font-medium text-slate-300 mb-3">环境信息</h3>
              {session.docker_image ? (
                <>
                  <p className="text-xs text-slate-400 mb-2">Docker镜像: <span className="text-blue-400">{session.docker_image}</span></p>
                  
                  {/* 尝试解析镜像名称中的版本信息，添加错误处理 */}
                  {session.docker_image.includes('py') && (
                    <p className="text-xs text-slate-400 mb-2">Python版本: <span className="text-blue-400">
                      {session.docker_image.match(/py(\d+\.\d+)/)?.[1] || '未知'}
                    </span></p>
                  )}
                  {session.docker_image.includes('pt') && (
                    <p className="text-xs text-slate-400 mb-2">PyTorch版本: <span className="text-blue-400">
                      {session.docker_image.match(/pt(\d+\.\d+\.\d+)/)?.[1] || '未知'}
                    </span></p>
                  )}
                  {session.docker_image.includes('cuda') && (
                    <p className="text-xs text-slate-400">CUDA版本: <span className="text-blue-400">
                      {session.docker_image.match(/cuda(\d+\.\d+)/)?.[1] || '未知'}
                    </span></p>
                  )}
                </>
              ) : session.running_in_docker ? (
                // 如果running_in_docker为true但没有docker_image，显示一个基本信息
                <p className="text-xs text-slate-400">环境: <span className="text-blue-400">Docker容器 (详细信息不可用)</span></p>
              ) : (
                <p className="text-xs text-slate-400">环境: <span className="text-blue-400">本地环境</span></p>
              )}
              
              {session.kernel_info && Object.keys(session.kernel_info).length > 0 && session.kernel_info.display_name ? (
                <p className="text-xs text-slate-400 mt-2">内核: <span className="text-green-400">{session.kernel_info.display_name}</span></p>
              ) : session.kernel_info && session.kernel_info.name ? (
                <p className="text-xs text-slate-400 mt-2">内核: <span className="text-green-400">{session.kernel_info.name}</span></p>
              ) : (
                <p className="text-xs text-slate-400 mt-2">内核: <span className="text-yellow-400">信息不可用</span></p>
              )}
            </div>
          </div>
          
          <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-6 max-w-md mx-auto mb-8">
            <Button 
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-3"
              onClick={handleUploadData}
            >
              <Upload className="w-4 h-4 mr-2" />
              上传数据
            </Button>
            <Button 
              className="flex-1 bg-green-600 hover:bg-green-700 text-white py-3"
              onClick={handleOpenNewWindow}
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              在新窗口打开
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JupyterNotebook;
