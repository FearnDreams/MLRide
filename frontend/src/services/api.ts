import axios, { AxiosResponse } from 'axios';
// import { ApiResponse } from '../types/auth';

// 创建axios实例
const api = axios.create({
    baseURL: 'http://localhost:8000/api/',  // 确保末尾有斜杠
    timeout: 5000,  // 请求超时时间
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
    withCredentials: true,  // 允许跨域请求携带cookie
});

// 获取CSRF Token的函数
const getCSRFToken = (): string | null => {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
};

// 请求拦截器
api.interceptors.request.use(
    (config) => {
        // 从localStorage获取token
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        
        // 添加CSRF Token
        const csrfToken = getCSRFToken();
        if (csrfToken) {
            config.headers['X-CSRFToken'] = csrfToken;
        }
        
        // 确保URL格式正确
        if (config.url && !config.url.endsWith('/')) {
            config.url += '/';
        }
        
        console.log('API请求配置:', {
            url: config.url,
            method: config.method,
            headers: config.headers,
            data: config.data,
            baseURL: config.baseURL,
            withCredentials: config.withCredentials
        });
        return config;
    },
    (error) => {
        console.error('API请求错误:', {
            message: error.message,
            config: error.config
        });
        return Promise.reject(error);
    }
);

// 响应拦截器
api.interceptors.response.use(
    (response: AxiosResponse<any>) => {
        console.log('API响应成功:', {
            status: response.status,
            statusText: response.statusText,
            data: response.data
        });

        // 修改响应数据结构以匹配ApiResponse接口
        response.data = {
            status: response.data.status || 'success',
            message: response.data.message || '操作成功',
            data: response.data.data
        };
        
        return response;
    },
    (error) => {
        console.error('API响应错误:', {
            message: error.message,
            response: error.response ? {
                status: error.response.status,
                statusText: error.response.statusText,
                data: error.response.data
            } : 'No response',
            request: error.request ? 'Request was made but no response received' : 'Request setup failed'
        });
        
        if (error.response?.data) {
            error.response.data = {
                status: 'error',
                message: error.response.data.message || '请求失败',
                data: error.response.data.data
            };
            return Promise.reject(error);
        }
        
        error.response = {
            data: {
                status: 'error',
                message: error.message || '请求失败，请重试'
            }
        };
        return Promise.reject(error);
    }
);

export default api; 