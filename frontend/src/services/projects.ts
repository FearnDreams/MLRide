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

// 创建项目快照
export const createProjectSnapshot = async (id: number, data: { version: string; description?: string }) => {
  try {
    const response = await api.post<ApiResponse>(`project/projects/${id}/create_snapshot/`, data);
    return response.data;
  } catch (error: any) {
    console.error('创建项目快照失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.detail || '创建项目快照失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '创建项目快照失败'
    };
  }
};

// 获取项目快照列表
export const getProjectSnapshots = async (id: number) => {
  try {
    const response = await api.get<ApiResponse>(`project/projects/${id}/list_snapshots/`);
    return response.data;
  } catch (error: any) {
    console.error('获取项目快照列表失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.detail || '获取项目快照列表失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '获取项目快照列表失败'
    };
  }
};

// 获取快照详情
export const getProjectSnapshot = async (id: number, snapshotId: string) => {
  try {
    const response = await api.get<ApiResponse>(`project/projects/${id}/get_snapshot/?snapshot_id=${snapshotId}`);
    return response.data;
  } catch (error: any) {
    console.error('获取项目快照详情失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.detail || '获取项目快照详情失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '获取项目快照详情失败'
    };
  }
};

// 获取快照中文件的内容
export const getSnapshotFileContent = async (id: number, snapshotId: string, filePath: string) => {
  try {
    // 移除文件路径末尾可能的斜杠
    const cleanFilePath = filePath.replace(/[/\\]+$/, '');
    console.log(`开始获取文件内容: 项目=${id}, 快照=${snapshotId}, 文件=${cleanFilePath}`);
    const response = await api.get<ApiResponse>(
      `project/projects/${id}/get_snapshot_file/?snapshot_id=${snapshotId}&file_path=${encodeURIComponent(cleanFilePath)}`
    );
    console.log(`获取文件内容成功: ${cleanFilePath}`);
    return response.data;
  } catch (error: any) {
    console.error('获取快照文件内容失败:', error);
    console.error('请求参数:', { id, snapshotId, filePath: filePath.replace(/[/\\]+$/, '') });
    
    let errorDetail = '获取快照文件内容失败';
    
    if (error.response?.data) {
      if (error.response.data.detail) {
        errorDetail = error.response.data.detail;
        console.error('错误详情:', errorDetail);
      }
      throw {
        status: 'error',
        message: errorDetail
      };
    }
    
    if (error.message) {
      errorDetail = error.message;
      console.error('错误信息:', errorDetail);
    }
    
    throw {
      status: 'error',
      message: errorDetail
    };
  }
};

// 恢复到指定快照
export const restoreProjectSnapshot = async (id: number, snapshotId: string) => {
  try {
    const response = await api.post<ApiResponse>(`project/projects/${id}/restore_snapshot/`, { snapshot_id: snapshotId });
    return response.data;
  } catch (error: any) {
    console.error('恢复项目快照失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.detail || '恢复项目快照失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '恢复项目快照失败'
    };
  }
};

// 删除项目快照
export const deleteProjectSnapshot = async (id: number, snapshotId: string) => {
  try {
    console.log(`删除项目快照 [项目ID: ${id}, 快照ID: ${snapshotId}]`);
    const response = await api.post<ApiResponse>(`project/projects/${id}/delete_snapshot/`, { snapshot_id: snapshotId });
    return response.data;
  } catch (error: any) {
    console.error('删除项目快照失败:', error);
    
    if (error.response?.data) {
      throw {
        status: 'error',
        message: error.response.data.detail || '删除项目快照失败'
      };
    }
    throw {
      status: 'error',
      message: error.message || '删除项目快照失败'
    };
  }
};

/**
 * 获取当前项目工作区的文件列表
 * @param projectId 项目ID
 */
export const getCurrentProjectFiles = async (projectId: number) => {
  console.log(`获取当前项目工作区文件列表 [项目ID: ${projectId}]`);
  try {
    const response = await api.get<ApiResponse>(`/project/projects/${projectId}/current_files/`);
    return response.data;
  } catch (error) {
    console.error('获取当前项目工作区文件列表失败:', error);
    throw error;
  }
};

/**
 * 获取当前项目工作区中特定文件的内容
 * @param projectId 项目ID
 * @param filePath 文件路径
 */
export const getCurrentFileContent = async (projectId: number, filePath: string) => {
  console.log(`获取当前项目工作区文件内容 [项目ID: ${projectId}, 文件路径: ${filePath}]`);
  try {
    const response = await api.get<ApiResponse>(`/project/projects/${projectId}/current_file_content/?file_path=${encodeURIComponent(filePath)}`);
    return response.data;
  } catch (error) {
    console.error(`获取当前项目工作区文件内容失败 [文件路径: ${filePath}]:`, error);
    throw error;
  }
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
  createProjectSnapshot,
  getProjectSnapshots,
  getProjectSnapshot,
  getSnapshotFileContent,
  restoreProjectSnapshot,
  deleteProjectSnapshot,
  getCurrentProjectFiles,
  getCurrentFileContent,
}; 