import axios from 'axios';
import api from './api';
import { ApiResponse } from '../types/auth';

// 定义API基础URL
const BASE_URL = '/api/project';

// 创建axios实例
const apiInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 添加请求拦截器
apiInstance.interceptors.request.use((config) => {
  // 从localStorage获取token
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

// 定义创建项目的请求参数接口
export interface CreateProjectRequest {
  name: string;
  description?: string;
  project_type: 'notebook' | 'canvas';
  image: number;
  is_public?: boolean;
}

// 定义项目响应接口
export interface ProjectResponse {
  id: number;
  name: string;
  description: string;
  project_type: string;
  created_at: string;
  updated_at: string;
  user: number;
  image: number;
  container: number | null;
  is_public: boolean;
  status: string;
  image_details: {
    id: number;
    name: string;
    description: string;
    pythonVersion: string;
    created: string;
    status: string;
    creator_username: string;
  };
  container_details: {
    id: number;
    user: number;
    image: number;
    container_id: string;
    name: string;
    status: string;
    created_at: string;
    started_at: string | null;
    cpu_limit: number;
    memory_limit: number;
    gpu_limit: number;
  } | null;
  files: ProjectFileResponse[];
  username: string;
}

// 定义项目文件响应接口
export interface ProjectFileResponse {
  id: number;
  project: number;
  name: string;
  path: string;
  content_type: string;
  size: number;
  created_at: string;
  updated_at: string;
}

// 获取项目列表
export const getProjects = async () => {
  try {
    const response = await api.get<ApiResponse>('project/projects/');
    return response.data;
  } catch (error: any) {
    console.error('获取项目列表失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '获取项目列表失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '获取项目列表失败'
    };
  }
};

// 获取项目详情
export const getProject = async (id: number) => {
  try {
    const response = await api.get<ApiResponse>(`project/projects/${id}/`);
    return response.data;
  } catch (error: any) {
    console.error('获取项目详情失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '获取项目详情失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '获取项目详情失败'
    };
  }
};

// 创建项目
export const createProject = async (data: CreateProjectRequest) => {
  try {
    const response = await api.post<ApiResponse>('project/projects/', data);
    return response.data;
  } catch (error: any) {
    console.error('创建项目失败:', error);
    
    if (error.response?.data) {
      // 处理DRF返回的字段验证错误
      if (error.response.data.name) {
        // 如果是项目名称的错误（如重名）
        throw {
          status: 'error',
          message: error.response.data.name[0] || '项目名称无效'
        };
      } else if (error.response.data.detail) {
        // 如果有detail字段
        throw {
          status: 'error',
          message: error.response.data.detail
        };
      } else if (error.response.data.non_field_errors) {
        // 如果有非字段错误
        throw {
          status: 'error',
          message: error.response.data.non_field_errors[0]
        };
      } else {
        // 其他情况
        throw {
          status: 'error',
          message: error.response.data.message || '创建项目失败，请稍后重试'
        };
      }
    }
    throw {
      status: 'error',
      message: error.message || '创建项目失败，请稍后重试'
    };
  }
};

// 更新项目
export const updateProject = async (id: number, data: Partial<CreateProjectRequest>) => {
  try {
    const response = await api.patch<ApiResponse>(`project/projects/${id}/`, data);
    return response.data;
  } catch (error: any) {
    console.error('更新项目失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '更新项目失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '更新项目失败'
    };
  }
};

// 删除项目
export const deleteProject = async (id: number) => {
  try {
    const response = await api.delete<ApiResponse>(`project/projects/${id}/`);
    return response.data;
  } catch (error: any) {
    console.error('删除项目失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '删除项目失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '删除项目失败'
    };
  }
};

// 启动项目
export const startProject = async (id: number) => {
  try {
    const response = await api.post<ApiResponse>(`project/projects/${id}/start/`);
    return response.data;
  } catch (error: any) {
    console.error('启动项目失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '启动项目失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '启动项目失败'
    };
  }
};

// 停止项目
export const stopProject = async (id: number) => {
  try {
    const response = await api.post<ApiResponse>(`project/projects/${id}/stop/`);
    return response.data;
  } catch (error: any) {
    console.error('停止项目失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '停止项目失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '停止项目失败'
    };
  }
};

// 获取项目资源使用状态
export const getProjectStats = async (id: number) => {
  try {
    const response = await api.get<ApiResponse>(`project/projects/${id}/stats/`);
    return response.data;
  } catch (error: any) {
    console.error('获取项目资源使用状态失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.message || '获取项目资源使用状态失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '获取项目资源使用状态失败'
    };
  }
};

// 获取项目文件列表
export const getProjectFiles = (projectId: number) => {
  return apiInstance.get<ProjectFileResponse[]>(`/files/?project_id=${projectId}`);
};

// 创建项目文件
export const createProjectFile = (data: {
  project: number;
  name: string;
  path: string;
  content_type: string;
  size: number;
}) => {
  return apiInstance.post<ProjectFileResponse>('/files/', data);
};

// 删除项目文件
export const deleteProjectFile = (id: number) => {
  return apiInstance.delete(`/files/${id}/`);
};

export default {
  getProjects,
  getProject,
  createProject,
  updateProject,
  deleteProject,
  startProject,
  stopProject,
  getProjectStats,
  getProjectFiles,
  createProjectFile,
  deleteProjectFile,
}; 