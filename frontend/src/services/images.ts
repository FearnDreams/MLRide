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
  pythonVersion?: string; // 添加可选的pythonVersion字段
  created: string;
  status: string; 
  creator: number;
  packages?: string; // 可选字段，存储镜像包含的工具包信息，以逗号分隔
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
      // 转换数据字段名 - 将前端的pythonVersion转为后端的python_version
      const apiData = {
        ...data,
        python_version: data.pythonVersion,
        use_slim: false,  // 确保始终使用常规版本而非slim版本
      };
      
      // 移除原始字段以避免冗余
      if ('pythonVersion' in apiData) {
        delete apiData.pythonVersion;
      }
      
      const response = await api.post<ApiResponse>('container/images/', apiData);
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
      console.log('删除镜像响应:', response);
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
      // 转换数据字段名 - 将前端的pythonVersion转为后端的python_version
      const apiData = {
        name: data.name,
        description: data.description,
        python_version: data.pythonVersion,
      };
      
      const response = await api.post<ApiResponse>('container/images/', apiData);
      if (!response.data.data) {
        throw new Error('创建镜像失败: 服务器未返回有效数据');
      }
      return response.data.data as ImageResponse;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        // 处理API错误，尝试获取更详细的错误信息
        console.error('创建镜像失败，详情:', {
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data,
        });
        
        // 优先获取详细的错误消息
        const errorMessage = 
          error.response?.data?.error_message || 
          error.response?.data?.detail || 
          error.response?.data?.message || 
          error.response?.data?.error ||
          '创建镜像失败，请检查网络连接或Docker服务状态';
        
        throw new Error(errorMessage);
      }
      // 对于非Axios错误，直接抛出
      console.error('创建镜像时发生未知错误:', error);
      throw error;
    }
  }

  // 获取镜像列表
  static async getImages(): Promise<ImageResponse[]> {
    try {
      const response = await api.get<ApiResponse>('container/images/');
      if (!response.data.data) {
        return [];
      }
      return Array.isArray(response.data.data) 
        ? response.data.data as ImageResponse[]
        : [response.data.data as ImageResponse];
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
      const response = await api.get<ApiResponse>(`container/images/${id}/`);
      if (!response.data.data) {
        throw new Error('获取镜像详情失败: 服务器未返回有效数据');
      }
      return response.data.data as ImageResponse;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const message = error.response?.data?.message || '获取镜像详情失败';
        throw new Error(message);
      }
      throw error;
    }
  }
}

// 为了与CreateProjectPage.tsx兼容，添加getDockerImages函数
export const getDockerImages = async () => {
  try {
    // 直接使用imagesService确保API路径一致
    const response = await imagesService.getUserImages();
    console.log('原始镜像API响应:', response);
    
    // 确保返回格式一致
    if (response.status === 'success' && response.data) {
      const imagesData = Array.isArray(response.data) ? response.data : [response.data];
      
      console.log('处理后的镜像数据:', imagesData);
      return { data: imagesData };
    }
    
    // 如果API未正确响应，返回空数组
    console.warn('API返回了不符合预期的响应:', response);
    return { data: [] };
  } catch (error) {
    console.error('获取镜像列表失败:', error);
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.message || '获取镜像列表失败';
      throw new Error(message);
    }
    throw error;
  }
};
