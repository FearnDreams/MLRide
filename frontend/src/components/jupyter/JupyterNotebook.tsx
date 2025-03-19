import React, { useState, useEffect } from 'react';
import { Button, Spin } from 'antd';
import { getJupyterSession } from '../../services/jupyter';
import type { JupyterResponse, JupyterSession } from '../../types/jupyter';
import './JupyterNotebook.css';

interface JupyterNotebookProps {
  projectId: number;
}

const JupyterNotebook: React.FC<JupyterNotebookProps> = ({ projectId }) => {
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState<JupyterSession | null>(null);
  const [iframeUrl, setIframeUrl] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [retriesCount, setRetriesCount] = useState(0);

  const initJupyterSession = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // 确保projectId是纯数字
      const cleanId = projectId.toString().replace(/\D/g, '');
      console.log('JupyterNotebook组件 - 清理后的项目ID:', cleanId);
      
      console.log('正在获取Jupyter会话信息...');
      const response: JupyterResponse = await getJupyterSession(cleanId);
      console.log('获取到会话信息:', response);
      
      if (response.status === 'success' && response.data) {
        setSession(response.data as unknown as JupyterSession);
        const sessionData = response.data as unknown as JupyterSession;
        
        // 使用Django代理访问Jupyter服务
        const proxyUrl = `/api/jupyter/proxy/${sessionData.id}/?project_id=${cleanId}`;
        console.log('使用代理URL访问Jupyter:', proxyUrl);
        setIframeUrl(proxyUrl);
        
        // 存储token供自动登录使用
        if (sessionData.token) {
          localStorage.setItem('jupyter_token', sessionData.token);
        }
        
        setLoading(false);
      } else {
        setError(response.message || '获取会话信息失败');
        setLoading(false);
      }
    } catch (error: any) {
      console.error('初始化Jupyter会话失败:', error);
      setError(`初始化Jupyter会话失败: ${error.message || '未知错误'}`);
      setLoading(false);
    }
  };

  // 初始加载和重试机制
  useEffect(() => {
    initJupyterSession();
    // 定时重试最多3次
    const interval = setInterval(() => {
      if (!session && retriesCount < 3) {
        setRetriesCount(prev => prev + 1);
        console.log(`第${retriesCount+1}次尝试加载Jupyter会话...`);
        initJupyterSession();
      } else {
        clearInterval(interval);
      }
    }, 3000);
    
    return () => clearInterval(interval);
  }, [projectId, retriesCount]);

  // 添加iframe自动登录功能
  const autoLoginToJupyter = () => {
    if (!iframeUrl) return;
    
    const iframe = document.querySelector('iframe#jupyter-iframe') as HTMLIFrameElement;
    if (!iframe) return;

    try {
      console.log('尝试自动登录Jupyter...');
      
      // 监听iframe加载完成
      iframe.onload = () => {
        try {
          // 检查iframe是否加载完成且可访问
          if (!iframe.contentWindow || !iframe.contentDocument) {
            console.log('无法访问iframe内容，可能是跨域限制');
            return;
          }
          
          console.log('iframe加载完成，检查是否需要登录');
          
          // 检查当前URL是否包含login
          const currentUrl = iframe.contentWindow.location.href;
          console.log('当前iframe URL:', currentUrl);
          
          if (currentUrl && currentUrl.includes('/login')) {
            console.log('检测到登录页面，尝试直接导航到tree页面');
            
            // 构造正确的tree URL（使用相对路径避免端口问题）
            const cleanProjectId = projectId.toString();
            const queryParam = `project_id=${cleanProjectId}`;
            const baseUrl = currentUrl.split('/login')[0];
            const treeUrl = `${baseUrl}/tree?${queryParam}`;
            
            console.log('尝试导航到:', treeUrl);
            
            // 1. 尝试直接设置iframe的src
            iframe.src = `${iframeUrl}&_ts=${new Date().getTime()}`;
            
            // 2. 备用方案：尝试在iframe内导航
            try {
              iframe.contentWindow.location.href = treeUrl;
            } catch (e) {
              console.log('iframe内部导航失败，可能是跨域限制:', e);
            }
            
            // 3. 第三方案：如果发现是登录页面，直接刷新整个iframe
            setTimeout(() => {
              // 检查是否仍在登录页面
              try {
                if (iframe.contentWindow?.location.href.includes('/login')) {
                  console.log('仍在登录页面，尝试刷新iframe');
                  refreshIframe();
                }
              } catch (e) {
                console.log('检查iframe URL失败:', e);
              }
            }, 2000);
          } else {
            console.log('当前不是登录页面，无需处理');
          }
        } catch (e) {
          console.log('iframe加载处理出错:', e);
        }
      };
    } catch (e) {
      console.error('设置自动登录失败:', e);
    }
  };

  // 刷新iframe
  const refreshIframe = () => {
    setLoading(true);
    if (iframeUrl) {
      // 强制重新加载iframe
      const iframe = document.querySelector('iframe#jupyter-iframe') as HTMLIFrameElement;
      if (iframe) {
        iframe.src = `${iframeUrl}&_t=${new Date().getTime()}`;
      }
    }
    setTimeout(() => setLoading(false), 1000);
  };

  // 当iframe URL更改时尝试自动登录
  useEffect(() => {
    if (iframeUrl) {
      console.log('iframe URL已更新，准备自动登录');
      autoLoginToJupyter();
    }
  }, [iframeUrl]);

  // 替换原有的handleRefresh函数
  const handleRefresh = () => {
    // 使用新的refreshIframe函数刷新iframe
    refreshIframe();
  };

  const openInNewWindow = () => {
    if (iframeUrl) {
      window.open(iframeUrl, '_blank');
    }
  };

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-700 p-6">
        <div className="text-center max-w-md">
          <div className="text-red-500 mb-4">
            <span className="text-3xl">⚠️</span>
          </div>
          <h3 className="text-xl font-medium text-gray-200 mb-2">Jupyter环境加载失败</h3>
          <p className="text-gray-400 mb-4">{error}</p>
          <div className="space-x-3">
            <Button onClick={handleRefresh}>
              重试加载
            </Button>
            <Button 
              onClick={() => window.location.reload()} 
              danger
            >
              刷新页面
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col">
      {loading ? (
        <div className="w-full h-full flex items-center justify-center bg-slate-700">
          <Spin tip="正在加载Jupyter环境..." size="large" />
        </div>
      ) : (
        <>
          <div className="flex justify-between items-center bg-slate-700 px-4 py-2">
            <h3 className="text-sm font-medium text-gray-200">Jupyter Notebook</h3>
            <div className="space-x-2">
              <Button onClick={handleRefresh}>
                刷新
              </Button>
              <Button onClick={openInNewWindow} type="primary">
                在新窗口打开
              </Button>
            </div>
          </div>
          
          {iframeUrl ? (
            <iframe
              id="jupyter-iframe"
              src={iframeUrl}
              className="flex-1 w-full border-0"
              title="Jupyter Notebook"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-slate-700">
              <div className="text-center max-w-md">
                <span className="text-3xl text-yellow-500 mb-4 block">⚠️</span>
                <h3 className="text-xl font-medium text-gray-200 mb-2">无法加载Jupyter环境</h3>
                <p className="text-gray-400 mb-4">
                  无法获取Jupyter会话URL，请重试或刷新页面。
                </p>
                <div className="space-x-3">
                  <Button onClick={handleRefresh} type="primary">
                    重试加载
                  </Button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default JupyterNotebook;
