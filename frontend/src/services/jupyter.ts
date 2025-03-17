import api from './api';
import { ApiResponse } from '../types/auth';

// Jupyter会话接口定义
export interface JupyterSession {
  id: number;
  project: number;
  token: string | null;
  url: string | null;
  status: 'creating' | 'running' | 'stopped' | 'error';
  created_at: string;
  updated_at: string;
}

/**
 * 获取指定项目的Jupyter会话
 * @param projectId 项目ID
 * @returns API响应
 */
export const getJupyterSession = async (projectId: number) => {
  try {
    const response = await api.get<ApiResponse>(`jupyter/sessions/by_project/?project_id=${projectId}`);
    return response.data;
  } catch (error: any) {
    console.error('获取Jupyter会话失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '获取Jupyter会话失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '获取Jupyter会话失败'
    };
  }
};

/**
 * 启动Jupyter会话
 * @param sessionId 会话ID
 * @returns API响应
 */
export const startJupyterSession = async (sessionId: number) => {
  try {
    const response = await api.post<ApiResponse>(`jupyter/sessions/${sessionId}/start/`);
    return response.data;
  } catch (error: any) {
    console.error('启动Jupyter会话失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '启动Jupyter会话失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '启动Jupyter会话失败'
    };
  }
};

/**
 * 停止Jupyter会话
 * @param sessionId 会话ID
 * @returns API响应
 */
export const stopJupyterSession = async (sessionId: number) => {
  try {
    const response = await api.post<ApiResponse>(`jupyter/sessions/${sessionId}/stop/`);
    return response.data;
  } catch (error: any) {
    console.error('停止Jupyter会话失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '停止Jupyter会话失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '停止Jupyter会话失败'
    };
  }
};
