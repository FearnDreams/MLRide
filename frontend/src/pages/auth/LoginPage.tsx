// 导入必要的依赖
import React from 'react';
import { Card, Typography } from 'antd';
import { Link } from 'react-router-dom';
import LoginForm from '../../components/auth/LoginForm';
import '../../styles/auth.css';

const { Title } = Typography;

// 登录页面组件
const LoginPage: React.FC = () => {
    return (
        <div className="auth-container">
            <Card className="auth-card">
                <Title level={2} className="auth-title">
                    登录
                </Title>
                <p className="auth-description">
                    欢迎回来！请输入您的账户信息
                </p>
                <LoginForm />
                <div className="auth-footer">
                    还没有账号？ <Link to="/register" className="auth-link">立即注册</Link>
                </div>
            </Card>
        </div>
    );
};

export default LoginPage; 