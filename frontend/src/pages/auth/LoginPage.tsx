// 导入必要的依赖
import React from 'react';
import { Typography } from 'antd';
import LoginForm from '../../components/auth/LoginForm';
import '../../styles/auth.css';

const { Title } = Typography;

// 登录页面组件
const LoginPage: React.FC = () => {
  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-gray-900 to-gray-800 overflow-y-auto">
      <div className="container mx-auto px-4 py-16 flex flex-col items-center justify-center min-h-screen">
        <div className="w-full max-w-md space-y-8 bg-gray-800/50 p-8 rounded-lg shadow-xl">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-white">登录到 MLRide</h2>
            <p className="mt-2 text-gray-400">欢迎回来！请登录您的账户</p>
          </div>
          
          <LoginForm />
          
          <div className="mt-4 text-center">
            <p className="text-gray-400">
              还没有账户？{' '}
              <a href="/register" className="text-blue-500 hover:text-blue-400">
                立即注册
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;