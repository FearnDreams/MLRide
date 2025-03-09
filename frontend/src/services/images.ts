import axios from 'axios';
import api from './api';
import { ApiResponse } from '../types/auth';

// 定义API基础URL
const BASE_URL = '/api/container';

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

// 定义创建镜像的请求参数接口
export interface CreateImageRequest {
  name: string;
  description?: string;
  pythonVersion: string;
}

// 定义镜像响应接口
export interface ImageResponse {
  id: string;
  name: string;
  description: string;
  pythonVersion: string;
  created: string;
  status: string;
  creator_username: string;
}

export interface DockerImage {
  id: number;
  name: string;
  description: string;
  python_version: string;
  created: string;
  status: 'pending' | 'building' | 'ready' | 'failed';
  creator: number;
}

export const imagesService = {
  // 获取用户的镜像列表
  getUserImages: async (): Promise<ApiResponse> => {
    try {
      const response = await api.get<ApiResponse>('container/images/');
      return response.data;
    } catch (error: any) {
      console.error('获取用户镜像失败:', error);
      
      if (error.response?.data) {
        throw {
          status: 'error',
          message: error.response.data.message || '获取用户镜像失败'
        };
      }
      throw {
        status: 'error',
        message: error.message || '获取用户镜像失败'
      };
    }
  },
  
  // 创建新镜像
  createImage: async (data: any): Promise<ApiResponse> => {
    try {
      const response = await api.post<ApiResponse>('container/images/', data);
      return response.data;
    } catch (error: any) {
      console.error('创建镜像失败:', error);
      
      if (error.response?.data) {
        throw {
          status: 'error',
          message: error.response.data.message || '创建镜像失败'
        };
      }
      throw {
        status: 'error',
        message: error.message || '创建镜像失败'
      };
    }
  },
  
  // 获取镜像详情
  getImageDetails: async (id: number): Promise<ApiResponse> => {
    try {
      const response = await api.get<ApiResponse>(`container/images/${id}/`);
      return response.data;
    } catch (error: any) {
      console.error('获取镜像详情失败:', error);
      
      if (error.response?.data) {
        throw {
          status: 'error',
          message: error.response.data.message || '获取镜像详情失败'
        };
      }
      throw {
        status: 'error',
        message: error.message || '获取镜像详情失败'
      };
    }
  },
  
  // 删除镜像
  deleteImage: async (id: number): Promise<ApiResponse> => {
    try {
      const response = await api.delete<ApiResponse>(`container/images/${id}/`);
      return response.data;
    } catch (error: any) {
      console.error('删除镜像失败:', error);
      
      if (error.response?.data) {
        throw {
          status: 'error',
          message: error.response.data.message || '删除镜像失败'
        };
      }
      throw {
        status: 'error',
        message: error.message || '删除镜像失败'
      };
    }
  }
};

// 镜像服务类
export class ImageService {
  // 创建新镜像
  static async createImage(data: CreateImageRequest): Promise<ImageResponse> {
    try {
      const response = await apiInstance.post('/images/', data);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        // 处理API错误
        const message = error.response?.data?.message || '创建镜像失败';
        throw new Error(message);
      }
      throw error;
    }
  }

  // 获取镜像列表
  static async getImages(): Promise<ImageResponse[]> {
    try {
      const response = await apiInstance.get('/images/');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const message = error.response?.data?.message || '获取镜像列表失败';
        throw new Error(message);
      }
      throw error;
    }
  }

  // 获取单个镜像详情
  static async getImage(id: string): Promise<ImageResponse> {
    try {
      const response = await apiInstance.get(`/images/${id}/`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const message = error.response?.data?.message || '获取镜像详情失败';
        throw new Error(message);
      }
      throw error;
    }
  }
}
