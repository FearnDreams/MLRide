// 导入必要的依赖
import { configureStore } from '@reduxjs/toolkit';
import authReducer from './authSlice';

// 配置store
export const store = configureStore({
    reducer: {
        auth: authReducer,
    },
});

// 导出类型
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;