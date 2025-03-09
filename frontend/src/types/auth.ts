// 用户信息接口
export interface User {
    id: number;
    username: string;
    email: string;
}

// 用户个人信息接口
export interface UserProfile extends User {
    nickname: string | null;
    avatar: string | null;
    avatar_url: string | null;
    created_at: string;
    updated_at: string;
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

// 用户信息更新请求数据接口
export interface UserUpdateRequest {
    nickname?: string;
    avatar?: File | null;
    current_password?: string;
    new_password?: string;
}

// API响应数据接口
export interface ApiResponseData {
    user?: User;
    token?: string;
    [key: string]: any; // 允许其他属性
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