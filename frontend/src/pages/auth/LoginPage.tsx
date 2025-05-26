// 导入必要的依赖
import React from 'react';
import { Typography } from 'antd';
import LoginForm from '../../components/auth/LoginForm';
import '../../styles/auth.css';
import { Link } from 'react-router-dom';

const { Title } = Typography;

// 登录页面组件
const LoginPage: React.FC = () => {
  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-950 via-gray-900 to-slate-900 overflow-y-auto relative">
      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl"></div>
        <div className="absolute top-1/3 -left-20 w-60 h-60 bg-purple-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-1/4 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl"></div>
      </div>
      
      <div className="container mx-auto px-4 py-16 flex flex-col items-center justify-center min-h-screen relative z-10">
        <Link to="/" className="absolute top-8 left-8 text-white hover:text-blue-400 transition-colors duration-200 flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
          </svg>
          返回首页
        </Link>
        
        <div className="w-full max-w-md space-y-8 bg-slate-800/30 backdrop-blur-sm p-8 rounded-xl border border-slate-700/50 shadow-xl">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-500/10 mb-4">
              <img src="/mlride-icon.svg" alt="MLRide Logo" className="h-9 w-9" />
            </div>
            <h2 className="text-3xl font-bold text-white">登录到 MLRide</h2>
            <p className="mt-2 text-gray-400">欢迎回来！请登录您的账户</p>
          </div>
          
          <LoginForm />
          
          <div className="mt-6 text-center">
            <p className="text-gray-400">
              还没有账户？{' '}
              <Link to="/register" className="text-blue-400 hover:text-blue-300 transition-colors duration-200 font-medium">
                立即注册
              </Link>
            </p>
          </div>
          
          <div className="pt-6 mt-6 border-t border-slate-700/50 text-center">
            <a href="#" className="text-sm text-gray-500 hover:text-gray-400 transition-colors duration-200">
              忘记密码？
            </a>
          </div>
        </div>
        
        <div className="mt-8 text-center text-sm text-gray-500">
          © 2025 MLRide. 保留所有权利。
        </div>
      </div>
    </div>
  );
};

export default LoginPage;