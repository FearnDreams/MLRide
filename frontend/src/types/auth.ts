// 用户信息接口
export interface User {
    id: number;
    username: string;
    email: string;
}

// 登录请求数据接口
export interface LoginRequest {
    username: string;
    password: string;
}

// 注册请求数据接口
export interface RegisterRequest {
    username: string;
    email: string;
    password: string;
    password2: string;
}

// API响应数据接口
export interface ApiResponseData {
    user?: User;
    token?: string;
}

// API响应接口
export interface ApiResponse {
    status: 'success' | 'error';
    message: string;
    data?: ApiResponseData;
}

// 认证状态接口
export interface AuthState {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
} 