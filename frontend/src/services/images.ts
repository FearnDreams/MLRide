import axios from 'axios';

// 定义API基础URL
const BASE_URL = '/api/container';

// 创建axios实例
const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 添加请求拦截器
api.interceptors.request.use((config) => {
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

// 镜像服务类
export class ImageService {
  // 创建新镜像
  static async createImage(data: CreateImageRequest): Promise<ImageResponse> {
    try {
      const response = await api.post('/images/', data);
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
      const response = await api.get('/images/');
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
      const response = await api.get(`/images/${id}/`);
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
