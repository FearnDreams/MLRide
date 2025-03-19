import api from './api';
import type { JupyterResponse } from '../types/jupyter';

/**
 * 获取指定项目的Jupyter会话
 * @param projectId 项目ID
 * @returns API响应
 */
export const getJupyterSession = async (projectId: number | string): Promise<JupyterResponse> => {
  try {
    // 确保projectId是纯数字，去除可能的斜杠和其他非数字字符
    const cleanId = String(projectId).replace(/[^\d]/g, '');
    console.log('清理后的项目ID:', cleanId);
    
    // 确保URL构建正确，不要在参数值后添加额外字符
    const url = `jupyter/sessions/by_project/?project_id=${cleanId}`;
    console.log('请求URL:', url);
    
    const response = await api.get<JupyterResponse>(url);
    return response.data;
  } catch (error: any) {
    console.error('获取Jupyter会话失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '获取Jupyter会话失败'
      } as JupyterResponse;
    }
    throw {
      status: 'error',
      message: error.message || '获取Jupyter会话失败'
    } as JupyterResponse;
  }
};

/**
 * 启动Jupyter会话
 * @param sessionId 会话ID
 * @returns API响应
 */
export const startJupyterSession = async (sessionId: number): Promise<JupyterResponse> => {
  try {
    const response = await api.post<JupyterResponse>(`jupyter/sessions/${sessionId}/start/`);
    return response.data;
  } catch (error: any) {
    console.error('启动Jupyter会话失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '启动Jupyter会话失败'
      } as JupyterResponse;
    }
    throw {
      status: 'error',
      message: error.message || '启动Jupyter会话失败'
    } as JupyterResponse;
  }
};

/**
 * 停止Jupyter会话
 * @param sessionId 会话ID
 * @returns API响应
 */
export const stopJupyterSession = async (sessionId: number): Promise<JupyterResponse> => {
  try {
    const response = await api.post<JupyterResponse>(`jupyter/sessions/${sessionId}/stop/`);
    return response.data;
  } catch (error: any) {
    console.error('停止Jupyter会话失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '停止Jupyter会话失败'
      } as JupyterResponse;
    }
    throw {
      status: 'error',
      message: error.message || '停止Jupyter会话失败'
    } as JupyterResponse;
  }
};
