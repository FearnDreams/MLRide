import api from './api';
import { ApiResponse } from '../types/auth';

// 定义数据集接口
export interface Dataset {
  id: number;
  name: string;
  description: string;
  file_size: number; // 文件大小，单位为字节
  file_type: string; // 文件类型 (例如 csv, json, zip等)
  created: string;
  updated: string;
  status: string; // 'pending' | 'processing' | 'ready' | 'failed'
  creator: number;
  creator_name?: string;
  downloads?: number; // 下载次数
  visibility: string; // 'private' | 'public'
  tags?: string[]; // 标签数组
  license?: string; // 许可证类型
  preview_available?: boolean; // 是否可预览
  preview_url?: string; // 预览地址
  error_message?: string; // 处理失败时的错误信息
}

// 定义创建数据集请求接口
export interface CreateDatasetRequest {
  name: string;
  description?: string;
  visibility: string; // 'private' | 'public'
  file: File; // 数据集文件
  tags?: string[]; // 标签
  license?: string; // 许可证
}

export const datasetsService = {
  // 获取用户的数据集列表
  getUserDatasets: async (): Promise<ApiResponse> => {
    try {
      const response = await api.get<ApiResponse>('data/datasets/');
      return response.data;
    } catch (error: any) {
      console.error('获取用户数据集失败:', error);
      
      if (error.response?.data) {
        throw {
          status: 'error',
          message: error.response.data.message || '获取用户数据集失败'
        };
      }
      throw {
        status: 'error',
        message: error.message || '获取用户数据集失败'
      };
    }
  },
  
  // 获取官方/公共数据集列表
  getPublicDatasets: async (): Promise<ApiResponse> => {
    try {
      const response = await api.get<ApiResponse>('data/datasets/public/');
      return response.data;
    } catch (error: any) {
      console.error('获取公共数据集失败:', error);
      
      if (error.response?.data) {
        throw {
          status: 'error',
          message: error.response.data.message || '获取公共数据集失败'
        };
      }
      throw {
        status: 'error',
        message: error.message || '获取公共数据集失败'
      };
    }
  },
  
  // 创建/上传新数据集
  createDataset: async (data: FormData): Promise<ApiResponse> => {
    try {
      const response = await api.post<ApiResponse>('data/datasets/', data, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error: any) {
      console.error('创建数据集失败:', error);
      
      if (error.response?.data) {
        throw {
          status: 'error',
          message: error.response.data.message || '创建数据集失败'
        };
      }
      throw {
        status: 'error',
        message: error.message || '创建数据集失败'
      };
    }
  },
  
  // 获取数据集详情
  getDatasetDetails: async (id: number): Promise<ApiResponse> => {
    try {
      const response = await api.get<ApiResponse>(`data/datasets/${id}/`);
      return response.data;
    } catch (error: any) {
      console.error('获取数据集详情失败:', error);
      
      if (error.response?.data) {
        throw {
          status: 'error',
          message: error.response.data.message || '获取数据集详情失败'
        };
      }
      throw {
        status: 'error',
        message: error.message || '获取数据集详情失败'
      };
    }
  },
  
  // 删除数据集
  deleteDataset: async (id: number): Promise<ApiResponse> => {
    try {
      const response = await api.delete<ApiResponse>(`data/datasets/${id}/`);
      return response.data;
    } catch (error: any) {
      console.error('删除数据集失败:', error);
      
      if (error.response?.data) {
        throw {
          status: 'error',
          message: error.response.data.message || '删除数据集失败'
        };
      }
      throw {
        status: 'error',
        message: error.message || '删除数据集失败'
      };
    }
  },
  
  // 更新数据集
  updateDataset: async (id: number, data: { name?: string; description?: string; visibility?: string; tags?: string[] }): Promise<ApiResponse> => {
    try {
      const response = await api.patch<ApiResponse>(`data/datasets/${id}/`, data);
      return response.data;
    } catch (error: any) {
      console.error('更新数据集失败:', error);
      
      if (error.response?.data) {
        throw {
          status: 'error',
          message: error.response.data.message || '更新数据集失败'
        };
      }
      throw {
        status: 'error',
        message: error.message || '更新数据集失败'
      };
    }
  },
  
  // 下载数据集
  downloadDataset: async (id: number): Promise<ApiResponse> => {
    try {
      const response = await api.get<Blob>(`data/datasets/${id}/download/`, {
        responseType: 'blob'
      });
      
      // 从响应头中获取文件名
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'dataset.zip';
      
      if (contentDisposition) {
        const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
        const matches = filenameRegex.exec(contentDisposition);
        if (matches != null && matches[1]) {
          filename = matches[1].replace(/['"]/g, '');
        }
      }
      
      // 创建下载链接并触发下载
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      return {
        status: 'success',
        message: '下载成功',
        data: undefined
      };
    } catch (error: any) {
      console.error('下载数据集失败:', error);
      
      if (error.response?.data) {
        throw {
          status: 'error',
          message: error.response.data.message || '下载数据集失败'
        };
      }
      throw {
        status: 'error',
        message: error.message || '下载数据集失败'
      };
    }
  },
  
  // 预览数据集
  previewDataset: async (id: number): Promise<ApiResponse> => {
    try {
      const response = await api.get<ApiResponse>(`data/datasets/${id}/preview/`);
      return response.data;
    } catch (error: any) {
      console.error('预览数据集失败:', error);
      
      if (error.response?.data) {
        throw {
          status: 'error',
          message: error.response.data.message || '预览数据集失败'
        };
      }
      throw {
        status: 'error',
        message: error.message || '预览数据集失败'
      };
    }
  }
}; 