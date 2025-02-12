import api from './api';
import { LoginRequest, RegisterRequest, ApiResponse } from '../types/auth';

export const authService = {
    // 用户登录
    login: async (data: LoginRequest): Promise<ApiResponse> => {
        console.log('开始登录请求:', {
            ...data,
            password: '[HIDDEN]'
        });
        try {
            const response = await api.post<ApiResponse>('auth/login/', data);
            if (response.data.status === 'success' && response.data.data?.token) {
                localStorage.setItem('token', response.data.data.token);
            }
            return response.data;
        } catch (error: any) {
            console.error('登录错误:', error);
            throw error.response?.data || {
                status: 'error',
                message: error.message || '登录失败，请重试'
            };
        }
    },

    // 用户注册
    register: async (data: RegisterRequest): Promise<ApiResponse> => {
        console.log('开始注册请求:', {
            ...data,
            password: '[HIDDEN]',
            password2: '[HIDDEN]'
        });
        
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
                    message: '用户名至少为3个字符'
                } as ApiResponse;
            }
            
            // 验证邮箱格式
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(data.email)) {
                throw {
                    status: 'error',
                    message: '请输入有效的邮箱地址'
                } as ApiResponse;
            }
            
            const response = await api.post<ApiResponse>('auth/register/', data);
            return response.data;
        } catch (error: any) {
            console.error('注册错误:', error);
            throw error.response?.data || {
                status: 'error',
                message: error.message || '注册失败，请重试'
            };
        }
    },

    // 用户登出
    logout: async (): Promise<ApiResponse> => {
        console.log('开始登出请求');
        try {
            const response = await api.post<ApiResponse>('auth/logout/', {});
            if (response.data.status === 'success') {
                localStorage.removeItem('token');
            }
            return response.data;
        } catch (error: any) {
            console.error('登出错误:', error);
            throw error.response?.data || {
                status: 'error',
                message: error.message || '登出失败，请重试'
            };
        }
    },

    // 获取当前用户信息
    getCurrentUser: async (): Promise<ApiResponse> => {
        console.log('开始获取当前用户信息');
        try {
            const response = await api.get<ApiResponse>('auth/user/');
            return response.data;
        } catch (error: any) {
            console.error('获取用户信息错误:', error);
            throw error.response?.data || {
                status: 'error',
                message: error.message || '获取用户信息失败，请重试'
            };
        }
    },
}; 