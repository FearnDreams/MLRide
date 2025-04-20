// 导入必要的依赖
import React from 'react';
import { Form, Input, Button, message } from 'antd';
import { useDispatch } from 'react-redux';
import { login } from '../../store/authSlice';
import { AppDispatch } from '../../store';
import { LoginRequest } from '../../types/auth';
import { useNavigate } from 'react-router-dom';

// 登录表单组件
const LoginForm: React.FC = () => {
    // useDispatch 是 react-redux 提供的 hook，用于获取 store 的 dispatch 方法
    const dispatch = useDispatch<AppDispatch>();
    // isLoading 状态用于控制登录按钮的加载状态，默认为 false
    const [isLoading, setIsLoading] = React.useState(false);
    // 移除 formError 状态
    const navigate = useNavigate();

    // 格式化错误信息函数
    const formatErrorMessage = (error: any): string => {
        // 如果错误信息是字符串类型，则直接返回
        if (typeof error === 'string') return error;
        // 如果错误对象有 message 属性，则返回 message 属性
        if (error.message) {
            return error.message;
        }
        // 默认错误信息
        return '登录失败，请重试';
    };

    // 表单提交处理函数
    const onFinish = async (values: LoginRequest) => {
        // 开始登录时设置加载状态为 true，禁用按钮
        setIsLoading(true);
        try {
            // 打印开始登录请求的日志，密码部分隐藏
            console.log('开始登录请求:', {
                ...values,
                password: '[HIDDEN]'
            });
            
            // 调用 dispatch(login(values)) 发起登录请求，并使用 unwrap() 处理 Promise 返回结果
            const result = await dispatch(login(values)).unwrap();
            // 打印登录响应的日志
            console.log('登录响应:', result);
            
            // 如果登录状态为 'success'
            if (result.status === 'success') {
                // 弹出登录成功的消息提示
                message.success({
                    content: '登录成功！正在跳转到主页...',
                    duration: 2,
                    key: 'login_success',
                    style: {
                        marginTop: '20vh',
                    },
                });
                // 延迟1秒后跳转到主页
                setTimeout(() => {
                    navigate('/dashboard');
                }, 1000);
            } else {
                // 如果登录状态不是 'success'，抛出错误
                throw new Error(result.message || '登录失败');
            }
        } catch (err: any) {
            // 捕获错误，打印错误日志
            console.error('登录错误:', err);
            // 格式化错误信息
            const errorMessage = formatErrorMessage(err);
            // 移除设置表单错误信息状态的代码
            // 弹出登录失败的消息提示
            message.error({
                content: errorMessage,
                duration: 3,
                key: 'login_error'
            });
        } finally {
            // 无论登录成功或失败，最终都设置加载状态为 false，启用按钮
            setIsLoading(false);
        }
    };

    // 表单验证失败处理函数
    const onFinishFailed = (errorInfo: any) => {
        // 打印表单验证失败的错误信息
        console.log('表单验证失败:', errorInfo);
        // 弹出表单验证失败的消息提示
        message.error({
            content: '请检查输入信息是否正确',
            duration: 3,
            key: 'form_validation_error'
        });
    };

    return (
        // Form 组件，用于创建表单
        <Form
            name="login" // 表单名称，用于标识表单
            onFinish={onFinish} // 表单提交成功的回调函数
            onFinishFailed={onFinishFailed} // 表单验证失败的回调函数
            layout="vertical" // 表单布局方式为垂直布局
            className="auth-form mt-6" // 表单的 CSS 类名
        >
            {/* 移除错误提示 Alert */}

            {/* 用户名输入框 */}
            <Form.Item
                label={<span className="text-gray-300">用户名</span>}
                name="username"
                rules={[
                    { required: true, message: '请输入用户名' },
                    { min: 3, message: '用户名至少3个字符' },
                    { max: 20, message: '用户名最多20个字符' }
                ]}
                tooltip="用户名长度3-20个字符"
            >
                <Input 
                    placeholder="请输入用户名" 
                    className="bg-slate-800/50 border-slate-700 text-white h-10 rounded-lg focus:border-blue-500 hover:border-slate-600 transition-colors duration-200"
                    prefix={
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                    }
                />
            </Form.Item>

            {/* 密码输入框 */}
            <Form.Item
                label={<span className="text-gray-300">密码</span>}
                name="password"
                rules={[
                    { required: true, message: '请输入密码' },
                    { min: 6, message: '密码至少6个字符' }
                ]}
                tooltip="密码长度至少6个字符"
            >
                <Input.Password 
                    placeholder="请输入密码" 
                    className="bg-slate-800/50 border-slate-700 text-white h-10 rounded-lg focus:border-blue-500 hover:border-slate-600 transition-colors duration-200"
                    prefix={
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                    }
                />
            </Form.Item>

            {/* 提交按钮 Form.Item */}
            <Form.Item className="mt-8">
                {/* Button 组件，按钮 */}
                <Button 
                    type="primary" 
                    htmlType="submit" 
                    loading={isLoading} 
                    block 
                    className="h-10 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 rounded-lg font-medium text-white shadow-lg shadow-blue-900/20"
                >
                    登录
                </Button>
            </Form.Item>
        </Form>
    );
};

export default LoginForm; 