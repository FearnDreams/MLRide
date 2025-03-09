import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { RootState } from '@/store';
import { Spin } from 'antd';

interface ProtectedRouteProps {
  children?: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading, token } = useSelector((state: RootState) => state.auth);
  
  // 如果正在加载，显示加载状态
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Spin size="large" tip="正在加载..." />
      </div>
    );
  }
  
  // 如果未认证且不在加载状态，重定向到登录页面
  if (!isAuthenticated && !isLoading && !token) {
    console.log('未认证，重定向到登录页面');
    return <Navigate to="/login" replace />;
  }
  
  // 如果已认证或有token，渲染子组件
  return <>{children || <Outlet />}</>;
};

export default ProtectedRoute; 