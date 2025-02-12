// 导入必要的依赖
import React from 'react';
import { Form, Input, Button, message, Alert } from 'antd';
import { useDispatch } from 'react-redux';
import { register } from '../../store/authSlice';
import { AppDispatch } from '../../store';
import { RegisterRequest } from '../../types/auth';
import { useNavigate } from 'react-router-dom';

// 注册表单组件
const RegisterForm: React.FC = () => {
    // 获取dispatch方法，用于触发redux action
    const dispatch = useDispatch<AppDispatch>();
    // 获取navigate方法，用于页面跳转
    const navigate = useNavigate();
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
                    duration: 3,
                    key: 'register_success'
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
            className="auth-form"
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
                        className="auth-error" // 样式类名
                        onClose={() => setFormError(null)} // 关闭回调，清空错误信息
                    />
                </Form.Item>
            )}

            {/* 用户名表单项 */}
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

            {/* 邮箱表单项 */}
            <Form.Item
                label="邮箱"
                name="email"
                rules={[
                    { required: true, message: '请输入邮箱！' },
                    { type: 'email', message: '请输入有效的邮箱地址！' }
                ]}
            >
                <Input placeholder="请输入邮箱地址" />
            </Form.Item>

            {/* 密码表单项 */}
            <Form.Item
                label="密码"
                name="password"
                rules={[
                    { required: true, message: '请输入密码！' },
                    { validator: validatePassword }
                ]}
                help="密码长度至少8个字符，不能只包含数字"
            >
                <Input.Password placeholder="请输入密码" />
            </Form.Item>

            {/* 确认密码表单项 */}
            <Form.Item
                label="确认密码"
                name="password2"
                dependencies={['password']}
                rules={[
                    { required: true, message: '请确认密码！' },
                    ({ getFieldValue }) => ({
                        validator(_, value) {
                            if (!value || getFieldValue('password') === value) {
                                return Promise.resolve();
                            }
                            return Promise.reject(new Error('两次输入的密码不一致！'));
                        },
                    }),
                ]}
            >
                <Input.Password placeholder="请再次输入密码" />
            </Form.Item>

            {/* 提交按钮表单项 */}
            <Form.Item>
                <Button type="primary" htmlType="submit" loading={isLoading} block className="auth-button">
                    注册
                </Button>
            </Form.Item>
        </Form>
    );
};

export default RegisterForm; 