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

// Helper function to convert Base64 to Blob
const base64ToBlob = (base64: string, contentType: string = 'application/octet-stream'): Blob => {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], { type: contentType });
};

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
  
  // 下载数据集 (修改后)
  downloadDataset: async (id: number): Promise<ApiResponse> => {
    try {
      // 请求API，期望接收JSON响应
      const response = await api.get<ApiResponse>(`data/datasets/${id}/download/`);
      
      // 检查响应状态和数据结构
      if (response.data.status !== 'success' || !response.data.data) {
         console.error('下载API响应无效:', response.data);
         throw new Error(response.data.message || '获取下载数据失败');
      }
      
      // 从响应数据中提取文件名、Base64内容和MIME类型
      const { file_name, file_content, content_type } = response.data.data;
      
      if (!file_name || !file_content) {
        console.error('下载API响应缺少必要数据:', response.data.data);
        throw new Error('下载数据不完整');
      }
      
      // 将Base64内容解码为Blob
      const blobData = base64ToBlob(file_content, content_type);
      
      // 创建下载链接并触发下载
      const url = window.URL.createObjectURL(blobData);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', file_name); // 使用从API获取的文件名
      document.body.appendChild(link);
      link.click();
      
      // 清理
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      // 返回成功状态（因为下载已触发）
      return {
        status: 'success',
        message: '下载已开始', // 消息可以调整
        data: undefined
      };
      
    } catch (error: any) {
      console.error('下载数据集失败:', error);
      let message = '下载数据集失败';
      // 保留之前的错误处理逻辑，以防API直接返回错误
      if (error.response?.data?.message) {
          message = error.response.data.message;
      } else if (error.message) {
           message = error.message;
      }
      // 抛出包含错误消息的对象，以便上层捕获
      throw { 
        status: 'error',
        message: message 
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