// 导入必要的依赖
import React from 'react';
import { Card, Typography } from 'antd';
import { Link } from 'react-router-dom';
import RegisterForm from '../../components/auth/RegisterForm';
import '../../styles/auth.css';

const { Title } = Typography;

// 注册页面组件
const RegisterPage: React.FC = () => {
    return (
        <div className="auth-container">
            <Card className="auth-card">
                <Title level={2} className="auth-title">
                    注册
                </Title>
                <p className="auth-description">
                    创建您的账户，开始使用服务
                </p>
                <RegisterForm />
                <div className="auth-footer">
                    已有账号？ <Link to="/login" className="auth-link">立即登录</Link>
                </div>
            </Card>
        </div>
    );
};

export default RegisterPage; 