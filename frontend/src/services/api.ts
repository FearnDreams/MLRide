import axios, { AxiosResponse } from 'axios';

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

// 初始化CSRF Token
const initCSRFToken = async () => {
    try {
        await api.get('auth/csrf-token/');
    } catch (error) {
        console.error('获取CSRF Token失败:', error);
    }
};

// 请求拦截器
api.interceptors.request.use(
    async (config) => {
        // 如果是非GET请求且没有CSRF token，先获取token
        if (config.method !== 'get' && !getCSRFToken()) {
            await initCSRFToken();
        }

        // 从localStorage获取token
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Token ${token}`;
        }
        
        // 添加CSRF Token（对于非GET请求）
        if (config.method !== 'get') {
            const csrfToken = getCSRFToken();
            if (csrfToken) {
                config.headers['X-CSRFToken'] = csrfToken;
            }
        }
        
        // 确保URL格式正确
        if (config.url && !config.url.endsWith('/')) {
            config.url += '/';
        }
        
        // 添加时间戳防止缓存（对于GET请求）
        if (config.method === 'get' && config.url) {
            config.url += `${config.url.includes('?') ? '&' : '?'}_t=${new Date().getTime()}`;
        }
        
        console.log('API请求配置:', {
            url: config.url,
            method: config.method,
            headers: config.headers,
            data: config.data
        });
        
        return config;
    },
    (error) => {
        console.error('API请求错误:', error);
        return Promise.reject(error);
    }
);

// 响应拦截器
api.interceptors.response.use(
    (response: AxiosResponse) => {
        console.log('API响应成功:', {
            status: response.status,
            data: response.data
        });

        // 修改响应数据结构以匹配ApiResponse接口
        if (response.data) {
            response.data = {
                status: response.data.status || 'success',
                message: response.data.message || '操作成功',
                data: response.data.data || response.data
            };
        }
        
        return response;
    },
    (error) => {
        console.error('API响应错误:', {
            message: error.message,
            response: error.response ? {
                status: error.response.status,
                data: error.response.data
            } : 'No response'
        });

        // 处理401未授权错误
        if (error.response?.status === 401) {
            localStorage.removeItem('token');
        }
        
        // 处理错误响应
        if (error.response?.data) {
            const errorData = error.response.data;
            
            // 检查字段验证错误（如项目名称重名）
            if (errorData.name && Array.isArray(errorData.name) && errorData.name.length > 0) {
                error.response.data = {
                    status: 'error',
                    message: errorData.name[0],
                    data: errorData
                };
            } 
            // 检查非字段错误
            else if (errorData.non_field_errors && Array.isArray(errorData.non_field_errors) && errorData.non_field_errors.length > 0) {
                error.response.data = {
                    status: 'error',
                    message: errorData.non_field_errors[0],
                    data: errorData
                };
            }
            // 其他常规错误
            else {
                error.response.data = {
                    status: 'error',
                    message: errorData.message || errorData.detail || '请求失败',
                    data: errorData
                };
            }
            return Promise.reject(error);
        }
        
        // 处理网络错误
        error.response = {
            data: {
                status: 'error',
                message: '网络错误，请检查网络连接',
                data: null
            }
        };
        return Promise.reject(error);
    }
);

// 初始化时获取CSRF Token
initCSRFToken();

export default api;