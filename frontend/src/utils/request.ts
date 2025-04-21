import axios, { AxiosRequestConfig } from 'axios';
import { message } from 'antd';

// 创建axios实例
const instance = axios.create({
  baseURL: '/api',
  timeout: 60000, // 增加超时时间到60秒
  headers: {
    'Content-Type': 'application/json',
  },
  // 减少重定向，提高稳定性
  maxRedirects: 3,
  // 减少最大内容长度
  maxContentLength: 10 * 1024 * 1024, // 10MB
});

// 请求拦截器
instance.interceptors.request.use(
  (config) => {
    // 获取token并添加到请求头
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // 移除不必要的请求头，减少请求头大小
    if (config.headers) {
      // 删除大多数可能会导致头过大的字段，只保留少数必要的
      const headers = { ...config.headers };
      
      // 保留这些头，删除其他所有头
      const keysToKeep = ['content-type', 'accept', 'authorization'];
      
      // 删除不在保留列表中的头
      Object.keys(headers).forEach(key => {
        if (!keysToKeep.includes(key.toLowerCase())) {
          delete config.headers[key];
        }
      });
    }
    
    // 确保请求有超时设置
    config.timeout = 60000;
    
    return config;
  },
  (error) => {
    console.error('请求拦截器错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
instance.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    console.error('请求错误:', error);
    
    // 处理错误信息
    let errorMessage = '请求失败，请检查网络连接';
    let errorDetails = null;
    
    if (error.response) {
      // 服务器返回了错误状态码
      const { status, data } = error.response;
      
      // 处理特定状态码
      switch (status) {
        case 401:
          errorMessage = '未授权，请重新登录';
          // 清除token并重定向到登录页
          localStorage.removeItem('token');
          // window.location.href = '/login';
          break;
        case 403:
          errorMessage = '没有权限访问该资源';
          break;
        case 404:
          errorMessage = '请求的资源不存在';
          break;
        case 500:
          errorMessage = '服务器内部错误';
          break;
        default:
          errorMessage = data?.message || `请求失败 (${status})`;
      }
      
      // 获取详细错误信息
      if (data?.error_details) {
        errorDetails = data.error_details;
      }
    } else if (error.request) {
      // 请求已发出，但没有收到响应
      errorMessage = '服务器未响应，请稍后重试';
    } else {
      // 请求配置错误
      errorMessage = error.message || '请求配置错误';
    }
    
    // 非401错误显示错误消息
    if (error.response?.status !== 401) {
      message.error(errorMessage);
    }
    
    // 构建错误对象
    const errorObj = {
      status: 'error',
      message: errorMessage,
    };
    
    // 添加详细错误信息
    if (errorDetails) {
      Object.assign(errorObj, { error_details: errorDetails });
    }
    
    return Promise.reject(errorObj);
  }
);

/**
 * 通用请求函数
 * @param url 请求URL
 * @param options 请求选项
 * @returns Promise
 */
const request = async <T>(url: string, options?: AxiosRequestConfig): Promise<T> => {
  try {
    return await instance(url, options) as T;
  } catch (error) {
    return Promise.reject(error);
  }
};

export default request; 