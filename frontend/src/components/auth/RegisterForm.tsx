// 导入必要的依赖
import React from 'react';
import { Form, Input, Button, message, Alert, Tooltip } from 'antd';
import { useDispatch } from 'react-redux';
import { register } from '../../store/authSlice';
import { AppDispatch } from '../../store';
import { RegisterRequest } from '../../types/auth';
import { useNavigate, useLocation } from 'react-router-dom';

// 注册表单组件
const RegisterForm: React.FC = () => {
    // 获取dispatch方法，用于触发redux action
    const dispatch = useDispatch<AppDispatch>();
    // 获取navigate方法，用于页面跳转
    const navigate = useNavigate();
    const location = useLocation();
    // 定义loading状态，控制注册按钮的loading效果
    const [isLoading, setIsLoading] = React.useState(false);
    // 使用Form.useForm hook创建表单实例，用于表单操作
    const [form] = Form.useForm();
    // 定义表单错误状态，用于显示错误信息
    const [formError, setFormError] = React.useState<string | null>(null);

    // 格式化错误信息函数
    const formatErrorMessage = (error: any): string => {
        // 如果错误是字符串类型，直接返回
        if (typeof error === 'string') return error;
        // 如果错误对象有message属性，返回message
        if (error.message) {
            return error.message;
        }
        // 默认错误信息
        return '注册失败，请重试';
    };

    // 表单提交处理函数
    const onFinish = async (values: RegisterRequest) => {
        // 设置loading为true，显示加载状态
        setIsLoading(true);
        try {
            console.log('开始注册流程');
            // 打印提交的注册数据，密码和确认密码脱敏处理
            console.log('提交的注册数据:', {
                ...values,
                password: '[HIDDEN]',
                password2: '[HIDDEN]'
            });

            // 派发注册action，并等待结果
            const result = await dispatch(register(values)).unwrap();
            console.log('注册响应:', result);

            // 如果注册成功
            if (result.status === 'success') {
                // 弹出注册成功提示信息
                message.success({
                    content: '注册成功！正在跳转到登录页面...',
                    duration: 2,
                    key: 'register_success',
                    style: {
                        marginTop: '20vh',
                    },
                });
                // 重置表单
                form.resetFields();
                // 清空错误信息
                setFormError(null);
                // 延迟1秒后跳转到登录页
                setTimeout(() => {
                    navigate('/login');
                }, 1000);
            } else {
                // 注册失败，抛出错误
                throw new Error(result.message || '注册失败');
            }
        } catch (err: any) {
            console.error('注册错误:', err);
            // 格式化错误信息
            const errorMessage = formatErrorMessage(err);
            // 设置表单错误信息
            setFormError(errorMessage);
            // 弹出错误提示信息
            message.error({
                content: errorMessage,
                duration: 3,
                key: 'register_error'
            });
        } finally {
            // 注册流程结束，设置loading为false，隐藏加载状态
            setIsLoading(false);
        }
    };

    // 表单验证失败处理函数
    const onFinishFailed = (errorInfo: any) => {
        console.log('表单验证失败:', errorInfo);
        // 弹出表单验证失败提示信息
        message.error({
            content: '请检查输入信息是否正确',
            duration: 3,
            key: 'form_validation_error'
        });
    };

    // 密码验证规则函数
    const validatePassword = (_: any, value: string) => {
        // 密码为空
        if (!value) {
            return Promise.reject('请输入密码');
        }
        // 密码长度小于8位
        if (value.length < 8) {
            return Promise.reject('密码长度至少为8个字符');
        }
        // 密码只包含数字
        if (/^\d+$/.test(value)) {
            return Promise.reject('密码不能只包含数字');
        }
        // 验证通过
        return Promise.resolve();
    };

    return (
        <Form
            // 绑定表单实例
            form={form}
            // 表单名称
            name="register"
            // 表单提交成功回调
            onFinish={onFinish}
            // 表单验证失败回调
            onFinishFailed={onFinishFailed}
            // 表单布局
            layout="vertical"
            // 表单样式类名
            className="auth-form mt-6"
        >
            {/* 表单错误提示 */}
            {formError && (
                <Form.Item>
                    <Alert
                        message="注册错误" // 错误提示标题
                        description={formError} // 错误详细描述
                        type="error" // 提示类型为错误
                        showIcon // 显示图标
                        closable // 可关闭
                        className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg" // 样式类名
                        onClose={() => setFormError(null)} // 关闭回调，清空错误信息
                    />
                </Form.Item>
            )}

            {/* 用户名表单项 */}
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
                    className="bg-slate-800/50 border-slate-700 text-white h-10 rounded-lg focus:border-indigo-500 hover:border-slate-600 transition-colors duration-200"
                    prefix={
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                    }
                />
            </Form.Item>

            {/* 邮箱表单项 */}
            <Form.Item
                label={<span className="text-gray-300">邮箱</span>}
                name="email"
                rules={[
                    { required: true, message: '请输入邮箱' },
                    { type: 'email', message: '请输入有效的邮箱地址' }
                ]}
                tooltip="请输入有效的邮箱地址"
            >
                <Input 
                    placeholder="请输入邮箱地址" 
                    className="bg-slate-800/50 border-slate-700 text-white h-10 rounded-lg focus:border-indigo-500 hover:border-slate-600 transition-colors duration-200"
                    prefix={
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                    }
                />
            </Form.Item>

            {/* 密码表单项 */}
            <Form.Item
                label={<span className="text-gray-300">密码</span>}
                name="password"
                rules={[
                    { required: true, message: '请输入密码' },
                    { validator: validatePassword }
                ]}
                tooltip="密码长度至少8个字符，不能只包含数字"
            >
                <Input.Password 
                    placeholder="请输入密码" 
                    className="bg-slate-800/50 border-slate-700 text-white h-10 rounded-lg focus:border-indigo-500 hover:border-slate-600 transition-colors duration-200"
                    prefix={
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                    }
                />
            </Form.Item>

            {/* 确认密码表单项 */}
            <Form.Item
                label={<span className="text-gray-300">确认密码</span>}
                name="password2"
                dependencies={['password']}
                rules={[
                    { required: true, message: '请确认密码' },
                    ({ getFieldValue }) => ({
                        validator(_, value) {
                            if (!value || getFieldValue('password') === value) {
                                return Promise.resolve();
                            }
                            return Promise.reject(new Error('两次输入的密码不一致'));
                        },
                    }),
                ]}
                tooltip="请再次输入密码进行确认"
            >
                <Input.Password 
                    placeholder="请再次输入密码" 
                    className="bg-slate-800/50 border-slate-700 text-white h-10 rounded-lg focus:border-indigo-500 hover:border-slate-600 transition-colors duration-200"
                    prefix={
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                    }
                />
            </Form.Item>

            {/* 提交按钮表单项 */}
            <Form.Item className="mt-8">
                <Button 
                    type="primary" 
                    htmlType="submit" 
                    loading={isLoading} 
                    block 
                    className="h-10 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 border-0 rounded-lg font-medium text-white shadow-lg shadow-indigo-900/20"
                >
                    注册
                </Button>
            </Form.Item>
        </Form>
    );
};

export default RegisterForm; 