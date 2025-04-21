import request from '../utils/request';
import type { JupyterResponse, JupyterSession } from '../types/jupyter';

/**
 * 获取指定项目的Jupyter会话
 * @param projectId 项目ID
 * @param options 可选的请求选项
 * @returns API响应
 */
export async function getJupyterSession(
  projectId: string | number, 
  options?: Record<string, any>
): Promise<JupyterSession> {
  // 设置最小必要的请求头和超时设置
  const requestOptions = {
    timeout: 30000, // 30秒超时
    headers: {
      // 只保留必要的头部
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      // 移除其他可能导致头部过大的字段
    },
    ...options
  };
  
  return request(`/jupyter/sessions/by_project/?project_id=${projectId}`, requestOptions);
}

/**
 * 检查Jupyter服务健康状态并在必要时重启服务
 * @param projectId 项目ID
 * @param forceRestart 是否强制重启
 * @returns API响应
 */
export async function checkJupyterHealth(
  projectId: string | number, 
  forceRestart: boolean = false
): Promise<JupyterResponse> {
  return request(`/jupyter/health-check/?project_id=${projectId}&force_restart=${forceRestart ? 'true' : 'false'}`);
}

/**
 * 启动Jupyter会话
 * @param projectId 项目ID
 * @returns API响应
 */
export async function startJupyterSession(projectId: string | number): Promise<JupyterResponse> {
  // 获取CSRF令牌 - 如果服务器要求
  const getCookie = (name: string): string | null => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
    return null;
  };
  
  const csrfToken = getCookie('csrftoken');
  
  return request('/jupyter/sessions/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {})
    },
    data: { project_id: projectId },
  });
}

/**
 * 停止Jupyter会话
 * @param sessionId 会话ID
 * @returns API响应
 */
export async function stopJupyterSession(sessionId: string | number): Promise<JupyterResponse> {
  // 获取CSRF令牌
  const getCookie = (name: string): string | null => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
    return null;
  };
  
  const csrfToken = getCookie('csrftoken');
  
  return request(`/jupyter/sessions/${sessionId}/stop/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {})
    },
  });
}
