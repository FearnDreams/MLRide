// 导入必要的依赖
import React from 'react';
import { Form, Input, Button, message, Alert } from 'antd';
import { useDispatch } from 'react-redux';
import { login } from '../../store/authSlice';
import { AppDispatch } from '../../store';
import { LoginRequest } from '../../types/auth';

// 登录表单组件
const LoginForm: React.FC = () => {
    // useDispatch 是 react-redux 提供的 hook，用于获取 store 的 dispatch 方法
    const dispatch = useDispatch<AppDispatch>();
    // isLoading 状态用于控制登录按钮的加载状态，默认为 false
    const [isLoading, setIsLoading] = React.useState(false);
    // formError 状态用于存储表单错误信息，初始值为 null，表示没有错误
    const [formError, setFormError] = React.useState<string | null>(null);

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
                    content: '登录成功！',
                    duration: 3,
                    key: 'login_success'
                });
                // 清空错误信息
                setFormError(null);
            } else {
                // 如果登录状态不是 'success'，抛出错误
                throw new Error(result.message || '登录失败');
            }
        } catch (err: any) {
            // 捕获错误，打印错误日志
            console.error('登录错误:', err);
            // 格式化错误信息
            const errorMessage = formatErrorMessage(err);
            // 设置表单错误信息状态
            setFormError(errorMessage);
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
            className="auth-form" // 表单的 CSS 类名
        >
            {/* 如果 formError 状态有值，则显示错误提示 */}
            {formError && (
                <Form.Item>
                    {/* Alert 组件，用于显示错误提示信息 */}
                    <Alert
                        message="登录错误" // 提示框标题
                        description={formError} // 错误详细描述，从 formError 状态获取
                        type="error" // 提示类型为错误
                        showIcon // 显示图标
                        closable // 显示关闭按钮
                        className="auth-error" // 提示框的 CSS 类名
                        onClose={() => setFormError(null)} // 关闭按钮的回调函数，清空 formError 状态
                    />
                </Form.Item>
            )}

            {/* 用户名 Form.Item */}
            <Form.Item
                label="用户名"
                name="username"
                rules={[
                    { required: true, message: '请输入用户名！' },
                    { min: 3, message: '用户名至少3个字符！' }
                ]}
                help="用户名长度至少为3个字符"
            >
                <Input placeholder="请输入用户名" />
            </Form.Item>

            {/* 密码 Form.Item */}
            <Form.Item
                label="密码"
                name="password"
                rules={[
                    { required: true, message: '请输入密码！' },
                    { min: 8, message: '密码至少8个字符！' }
                ]}
                help="密码长度至少8个字符"
            >
                <Input.Password placeholder="请输入密码" />
            </Form.Item>

            {/* 提交按钮 Form.Item */}
            <Form.Item>
                {/* Button 组件，按钮 */}
                <Button type="primary" htmlType="submit" loading={isLoading} block className="auth-button">
                    登录
                </Button>
            </Form.Item>
        </Form>
    );
};

export default LoginForm; 