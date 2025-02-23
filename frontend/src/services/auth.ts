import api from './api';
import { LoginRequest, RegisterRequest, ApiResponse } from '../types/auth';

export const authService = {
    // 用户登录
    login: async (data: LoginRequest): Promise<ApiResponse> => {
        try {
            // 先清除旧的token
            localStorage.removeItem('token');
            
            const response = await api.post<ApiResponse>('auth/login/', data);
            if (response.data.status === 'success' && response.data.data?.token) {
                // 保存新token
                localStorage.setItem('token', response.data.data.token);
            }
            return response.data;
        } catch (error: any) {
            console.error('登录错误:', error);
            // 确保清除token
            localStorage.removeItem('token');
            
            // 处理后端返回的错误
            if (error.response?.data) {
                throw {
                    status: 'error',
                    message: error.response.data.message || '登录失败，请重试'
                };
            }
            throw {
                status: 'error',
                message: error.message || '登录失败，请重试'
            };
        }
    },

    // 用户注册
    register: async (data: RegisterRequest): Promise<ApiResponse> => {
        try {
            // 验证密码匹配
            if (data.password !== data.password2) {
                throw {
                    status: 'error',
                    message: '两次输入的密码不匹配'
                } as ApiResponse;
            }
            
            // 验证密码长度
            if (data.password.length < 8) {
                throw {
                    status: 'error',
                    message: '密码长度至少为8个字符'
                } as ApiResponse;
            }
            
            // 验证用户名长度
            if (data.username.length < 3) {
                throw {
                    status: 'error',
                    message: '用户名长度至少为3个字符'
                } as ApiResponse;
            }

            // 先清除旧的token
            localStorage.removeItem('token');

            // 发送注册请求
            const response = await api.post<ApiResponse>('auth/register/', data);
            
            // 如果注册成功，保存token
            if (response.data.status === 'success' && response.data.data?.token) {
                localStorage.setItem('token', response.data.data.token);
            }
            
            return response.data;
        } catch (error: any) {
            console.error('注册错误:', error);
            // 确保清除token
            localStorage.removeItem('token');
            
            // 处理后端返回的错误信息
            if (error.response?.data) {
                const errorData = error.response.data;
                let errorMessage = '';
                
                // 处理字段错误
                if (typeof errorData === 'object') {
                    const messages = [];
                    for (const key in errorData) {
                        if (Array.isArray(errorData[key])) {
                            messages.push(errorData[key][0]);
                        } else if (typeof errorData[key] === 'string') {
                            messages.push(errorData[key]);
                        }
                    }
                    errorMessage = messages.join('; ');
                } else {
                    errorMessage = String(errorData);
                }

                throw {
                    status: 'error',
                    message: errorMessage || '注册失败，请重试'
                };
            }

            throw {
                status: 'error',
                message: error.message || '注册失败，请重试'
            };
        }
    },

    // 用户登出
    logout: async (): Promise<ApiResponse> => {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                throw {
                    status: 'error',
                    message: '用户未登录'
                };
            }

            const response = await api.post<ApiResponse>('auth/logout/');
            // 确保清除token
            localStorage.removeItem('token');
            return response.data;
        } catch (error: any) {
            console.error('登出错误:', error);
            // 无论如何都要清除token
            localStorage.removeItem('token');
            
            if (error.response?.data) {
                throw {
                    status: 'error',
                    message: error.response.data.message || '登出失败，请重试'
                };
            }
            throw {
                status: 'error',
                message: error.message || '登出失败，请重试'
            };
        }
    },

    // 获取当前用户信息
    getCurrentUser: async (): Promise<ApiResponse> => {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                throw {
                    status: 'error',
                    message: '用户未登录'
                };
            }

            const response = await api.get<ApiResponse>('auth/user/');
            return response.data;
        } catch (error: any) {
            console.error('获取用户信息错误:', error);
            
            if (error.response?.status === 401) {
                // 如果是未授权错误，清除token
                localStorage.removeItem('token');
            }
            
            if (error.response?.data) {
                throw {
                    status: 'error',
                    message: error.response.data.message || '获取用户信息失败'
                };
            }
            throw {
                status: 'error',
                message: error.message || '获取用户信息失败'
            };
        }
    },
};