// 导入必要的依赖
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { authService } from '../services/auth';
import { AuthState, LoginRequest, RegisterRequest, ApiResponse } from '../types/auth';

// 初始状态
const initialState: AuthState = {
    user: null,
    token: localStorage.getItem('token'),
    isAuthenticated: false,
    isLoading: false,
    error: null,
};

// 异步action: 登录
export const login = createAsyncThunk<
    ApiResponse,
    LoginRequest,
    { rejectValue: string }
>(
    'auth/login',
    async (credentials, { rejectWithValue }) => {
        try {
            const response = await authService.login(credentials);
            return response;
        } catch (error: any) {
            return rejectWithValue(error.message || '登录失败，请重试');
        }
    }
);

// 异步action: 注册
export const register = createAsyncThunk<
    ApiResponse,
    RegisterRequest,
    { rejectValue: string }
>(
    'auth/register',
    async (data, { rejectWithValue }) => {
        try {
            const response = await authService.register(data);
            return response;
        } catch (error: any) {
            return rejectWithValue(error.message || '注册失败，请重试');
        }
    }
);

// 异步action: 登出
export const logout = createAsyncThunk<
    ApiResponse,
    void,
    { rejectValue: string }
>(
    'auth/logout',
    async (_, { rejectWithValue }) => {
        try {
            const response = await authService.logout();
            return response;
        } catch (error: any) {
            return rejectWithValue(error.message || '登出失败，请重试');
        }
    }
);

// 创建slice
const authSlice = createSlice({
    name: 'auth',
    initialState,
    reducers: {
        // 清除错误信息
        clearError: (state) => {
            state.error = null;
        },
        // 设置加载状态
        setLoading: (state, action: PayloadAction<boolean>) => {
            state.isLoading = action.payload;
        },
    },
    extraReducers: (builder) => {
        builder
            // 登录
            .addCase(login.pending, (state) => {
                state.isLoading = true;
                state.error = null;
            })
            .addCase(login.fulfilled, (state, action) => {
                state.isLoading = false;
                if (action.payload.status === 'success' && action.payload.data) {
                    state.isAuthenticated = true;
                    state.user = action.payload.data.user || null;
                    state.token = action.payload.data.token || null;
                    // 将 token 保存到 localStorage
                    if (action.payload.data.token) {
                        localStorage.setItem('token', action.payload.data.token);
                    }
                    state.error = null;
                } else {
                    state.error = action.payload.message;
                }
            })
            .addCase(login.rejected, (state, action) => {
                state.isLoading = false;
                state.error = action.payload || '登录失败，请重试';
            })
            // 注册
            .addCase(register.pending, (state) => {
                state.isLoading = true;
                state.error = null;
            })
            .addCase(register.fulfilled, (state, action) => {
                state.isLoading = false;
                if (action.payload.status === 'success' && action.payload.data) {
                    state.user = action.payload.data.user || null;
                    state.error = null;
                } else {
                    state.error = action.payload.message;
                }
            })
            .addCase(register.rejected, (state, action) => {
                state.isLoading = false;
                state.error = action.payload || '注册失败，请重试';
            })
            // 登出
            .addCase(logout.fulfilled, (state) => {
                state.user = null;
                state.token = null;
                state.isAuthenticated = false;
                state.error = null;
                // 清除 localStorage 中的 token
                localStorage.removeItem('token');
            });
    },
});

// 导出actions和reducer
export const { clearError, setLoading } = authSlice.actions;
export default authSlice.reducer; 