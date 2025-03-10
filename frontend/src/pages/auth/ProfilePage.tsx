import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Form, Input, Upload, message, Modal } from 'antd';
import { UserOutlined, UploadOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { RootState } from '@/store';
import { authService } from '@/services/auth';
import { UserProfile, UserUpdateRequest } from '@/types/auth';
import { setUser } from '@/store/authSlice';

const { confirm } = Modal;

const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [fileList, setFileList] = useState<any[]>([]);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [isPasswordModalVisible, setIsPasswordModalVisible] = useState(false);
  const [passwordForm] = Form.useForm();
  
  const user = useSelector((state: RootState) => state.auth.user);
  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);

  // 如果用户未登录，重定向到登录页面
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  // 获取用户个人信息
  useEffect(() => {
    const fetchUserProfile = async () => {
      try {
        const response = await authService.getUserProfile();
        if (response.status === 'success' && response.data) {
          // 确保数据符合UserProfile类型
          const profileData: UserProfile = {
            id: response.data.id,
            username: response.data.username,
            email: response.data.email,
            nickname: response.data.nickname,
            avatar: response.data.avatar,
            avatar_url: response.data.avatar_url,
            created_at: response.data.created_at,
            updated_at: response.data.updated_at
          };
          
          setUserProfile(profileData);
          
          // 设置表单初始值
          form.setFieldsValue({
            username: response.data.username,
            email: response.data.email,
            nickname: response.data.nickname || '',
          });
          
          // 如果有头像，设置文件列表
          if (response.data.avatar_url) {
            setFileList([
              {
                uid: '-1',
                name: 'avatar',
                status: 'done',
                url: response.data.avatar_url,
              },
            ]);
            setPreviewImage(response.data.avatar_url);
          }
        }
      } catch (error) {
        console.error('获取用户信息失败:', error);
        message.error('获取用户信息失败，请重试');
      }
    };

    if (isAuthenticated) {
      fetchUserProfile();
    }
  }, [isAuthenticated, form]);

  // 处理表单提交
  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      const updateData: UserUpdateRequest = {
        nickname: values.nickname,
      };
      
      // 如果有新上传的头像
      if (fileList.length > 0 && fileList[0].originFileObj) {
        updateData.avatar = fileList[0].originFileObj;
      }
      
      const response = await authService.updateUserProfile(updateData);
      if (response.status === 'success') {
        message.success('个人信息更新成功');
        
        // 更新Redux中的用户信息
        if (response.data && response.data.user) {
          dispatch(setUser(response.data.user));
        }
        
        // 重新获取用户信息
        const profileResponse = await authService.getUserProfile();
        if (profileResponse.status === 'success' && profileResponse.data) {
          // 确保数据符合UserProfile类型
          const profileData: UserProfile = {
            id: profileResponse.data.id,
            username: profileResponse.data.username,
            email: profileResponse.data.email,
            nickname: profileResponse.data.nickname,
            avatar: profileResponse.data.avatar,
            avatar_url: profileResponse.data.avatar_url,
            created_at: profileResponse.data.created_at,
            updated_at: profileResponse.data.updated_at
          };
          
          setUserProfile(profileData);
          
          // 触发自定义事件，通知其他组件用户信息已更新
          window.dispatchEvent(new Event('profile-updated'));
        }
      } else {
        message.error(response.message || '更新失败，请重试');
      }
    } catch (error: any) {
      console.error('更新用户信息失败:', error);
      message.error(error.message || '更新失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 处理密码更新
  const handlePasswordUpdate = async (values: any) => {
    setLoading(true);
    try {
      const updateData: UserUpdateRequest = {
        current_password: values.currentPassword,
        new_password: values.newPassword,
      };
      
      const response = await authService.updateUserProfile(updateData);
      if (response.status === 'success') {
        message.success('密码更新成功');
        passwordForm.resetFields();
        setIsPasswordModalVisible(false);
        
        // 触发自定义事件，通知其他组件用户信息已更新
        window.dispatchEvent(new Event('profile-updated'));
      } else {
        message.error(response.message || '密码更新失败，请重试');
      }
    } catch (error: any) {
      console.error('更新密码失败:', error);
      message.error(error.message || '更新失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 处理账户删除
  const showDeleteConfirm = () => {
    confirm({
      title: '确定要注销账户吗？',
      icon: <ExclamationCircleOutlined />,
      content: '注销后，您的所有数据将被永久删除，且无法恢复。',
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk() {
        handleDeleteAccount();
      },
    });
  };

  const handleDeleteAccount = async () => {
    try {
      const password = await new Promise<string>((resolve, reject) => {
        Modal.confirm({
          title: '请输入您的密码以确认删除账户',
          content: (
            <Input.Password 
              placeholder="请输入密码" 
              onChange={(e) => resolve(e.target.value)}
            />
          ),
          onOk: () => {},
          onCancel: () => reject(new Error('已取消')),
        });
      });
      
      const response = await authService.deleteAccount(password);
      if (response.status === 'success') {
        message.success('账户已成功注销');
        // 清除本地存储的token
        localStorage.removeItem('token');
        // 重定向到登录页面
        navigate('/login');
      } else {
        message.error(response.message || '账户注销失败，请重试');
      }
    } catch (error: any) {
      if (error.message !== '已取消') {
        console.error('删除账户失败:', error);
        message.error(error.message || '账户注销失败，请重试');
      }
    }
  };

  // 头像上传配置
  const uploadProps = {
    beforeUpload: (file: File) => {
      const isImage = file.type.startsWith('image/');
      if (!isImage) {
        message.error('只能上传图片文件!');
        return false;
      }
      const isLt2M = file.size / 1024 / 1024 < 2;
      if (!isLt2M) {
        message.error('图片必须小于2MB!');
        return false;
      }
      return false;
    },
    onChange: (info: any) => {
      let fileList = [...info.fileList];
      // 限制只能上传一张图片
      fileList = fileList.slice(-1);
      
      // 读取上传的图片并预览
      if (fileList.length > 0 && fileList[0].originFileObj) {
        const reader = new FileReader();
        reader.onload = (e) => {
          setPreviewImage(e.target?.result as string);
        };
        reader.readAsDataURL(fileList[0].originFileObj);
      } else if (fileList.length === 0) {
        setPreviewImage(null);
      }
      
      setFileList(fileList);
    },
    fileList,
  };

  return (
    <div className="container mx-auto py-8">
      <Card className="max-w-2xl mx-auto bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 shadow-md rounded-xl">
        <CardHeader>
          <CardTitle className="text-white">个人信息</CardTitle>
          <CardDescription className="text-gray-400">查看和更新您的个人信息</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-6 flex justify-center">
            <div className="text-center">
              <div className="mb-2">
                {previewImage ? (
                  <img 
                    src={previewImage} 
                    alt="头像" 
                    className="w-24 h-24 rounded-full object-cover mx-auto border-2 border-blue-500/30"
                  />
                ) : (
                  <div className="w-24 h-24 rounded-full bg-slate-700/50 flex items-center justify-center mx-auto border border-slate-600/50">
                    <UserOutlined style={{ fontSize: 36, color: '#94a3b8' }} />
                  </div>
                )}
              </div>
              <Upload {...uploadProps} showUploadList={false}>
                <Button className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 shadow-md shadow-blue-900/20 text-white transition-all duration-200">
                  <UploadOutlined className="mr-2" />
                  更换头像
                </Button>
              </Upload>
            </div>
          </div>

          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
          >
            <Form.Item
              label={<span className="text-gray-300">用户名</span>}
              name="username"
            >
              <Input disabled className="bg-slate-700/50 border-slate-600/50 text-gray-300 cursor-not-allowed" />
            </Form.Item>
            
            <Form.Item
              label={<span className="text-gray-300">邮箱</span>}
              name="email"
            >
              <Input disabled className="bg-slate-700/50 border-slate-600/50 text-gray-300 cursor-not-allowed" />
            </Form.Item>
            
            <Form.Item
              label={<span className="text-gray-300">昵称</span>}
              name="nickname"
              rules={[{ max: 30, message: '昵称最多30个字符' }]}
            >
              <Input 
                placeholder="请输入昵称" 
                className="bg-slate-700/50 border-slate-600/50 text-gray-300 focus:border-blue-500/50 hover:border-blue-500/30 transition-colors"
              />
            </Form.Item>
            
            <Form.Item>
              <Button 
                type="submit" 
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 shadow-md shadow-blue-900/20 text-white transition-all duration-200" 
                disabled={loading}
              >
                {loading ? '保存中...' : '保存修改'}
              </Button>
            </Form.Item>
          </Form>
          
          <div className="mt-6 flex justify-between">
            <Button 
              onClick={() => setIsPasswordModalVisible(true)}
              className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 border-0 shadow-md shadow-indigo-900/20 text-white transition-all duration-200"
            >
              修改密码
            </Button>
            <Button 
              onClick={showDeleteConfirm}
              className="bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-500 hover:to-pink-500 border-0 shadow-md shadow-red-900/20 text-white transition-all duration-200"
            >
              注销账户
            </Button>
          </div>
        </CardContent>
      </Card>
      
      {/* 修改密码弹窗 */}
      <Modal
        title={<span className="text-white">修改密码</span>}
        open={isPasswordModalVisible}
        onCancel={() => setIsPasswordModalVisible(false)}
        footer={null}
        className="custom-dark-modal"
      >
        <Form
          form={passwordForm}
          layout="vertical"
          onFinish={handlePasswordUpdate}
        >
          <Form.Item
            label={<span className="text-gray-300">当前密码</span>}
            name="currentPassword"
            rules={[
              { required: true, message: '请输入当前密码' },
            ]}
          >
            <Input.Password 
              placeholder="请输入当前密码" 
              className="bg-slate-700/50 border-slate-600/50 text-gray-300 focus:border-blue-500/50 hover:border-blue-500/30 transition-colors"
            />
          </Form.Item>
          
          <Form.Item
            label={<span className="text-gray-300">新密码</span>}
            name="newPassword"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 8, message: '密码至少8个字符' },
              { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$/, message: '密码必须包含大小写字母和数字' }
            ]}
          >
            <Input.Password 
              placeholder="请输入新密码" 
              className="bg-slate-700/50 border-slate-600/50 text-gray-300 focus:border-blue-500/50 hover:border-blue-500/30 transition-colors"
            />
          </Form.Item>
          
          <Form.Item
            label={<span className="text-gray-300">确认新密码</span>}
            name="confirmPassword"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password 
              placeholder="请确认新密码" 
              className="bg-slate-700/50 border-slate-600/50 text-gray-300 focus:border-blue-500/50 hover:border-blue-500/30 transition-colors"
            />
          </Form.Item>
          
          <Form.Item>
            <div className="flex justify-end gap-2">
              <Button 
                onClick={() => setIsPasswordModalVisible(false)}
                className="bg-slate-700 hover:bg-slate-600 text-gray-300 border-slate-600/50 transition-all duration-200"
              >
                取消
              </Button>
              <Button 
                type="submit" 
                className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 shadow-md shadow-blue-900/20 text-white transition-all duration-200"
                disabled={loading}
              >
                {loading ? '提交中...' : '确认修改'}
              </Button>
            </div>
          </Form.Item>
        </Form>
      </Modal>

      {/* 添加全局样式 */}
      <style>{`
        .custom-dark-modal .ant-modal-content {
          background-color: rgba(30, 41, 59, 0.95);
          backdrop-filter: blur(8px);
          border: 1px solid rgba(51, 65, 85, 0.5);
          border-radius: 0.75rem;
        }
        .custom-dark-modal .ant-modal-header {
          background-color: transparent;
          border-bottom: 1px solid rgba(51, 65, 85, 0.5);
        }
        .custom-dark-modal .ant-modal-title {
          color: white;
        }
        .custom-dark-modal .ant-modal-close {
          color: rgba(148, 163, 184, 0.8);
        }
        .custom-dark-modal .ant-modal-close:hover {
          color: white;
        }
        .custom-dark-modal .ant-input-affix-wrapper {
          background-color: rgba(51, 65, 85, 0.5) !important;
          border-color: rgba(71, 85, 105, 0.5) !important;
        }
        .custom-dark-modal .ant-input-affix-wrapper:hover {
          border-color: rgba(59, 130, 246, 0.5) !important;
        }
        .custom-dark-modal .ant-input-affix-wrapper-focused {
          border-color: rgba(59, 130, 246, 0.5) !important;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1) !important;
        }
        .custom-dark-modal .ant-input {
          background-color: transparent !important;
          color: rgb(209, 213, 219) !important;
        }
        .custom-dark-modal .ant-input-password-icon {
          color: rgba(148, 163, 184, 0.8) !important;
        }
        .custom-dark-modal .ant-input-password-icon:hover {
          color: white !important;
        }
        
        /* 全局输入框样式 */
        .ant-input {
          color: rgb(209, 213, 219) !important;
          background-color: rgba(51, 65, 85, 0.5) !important;
        }
        .ant-input-disabled {
          color: rgb(148, 163, 184) !important;
          background-color: rgba(51, 65, 85, 0.5) !important;
        }
        .ant-input::placeholder {
          color: rgba(148, 163, 184, 0.6) !important;
        }
        /* 确保输入时文字颜色和背景色 */
        .ant-input:focus, 
        .ant-input:hover, 
        .ant-input:active, 
        .ant-input-focused {
          color: rgb(209, 213, 219) !important;
          background-color: rgba(51, 65, 85, 0.5) !important;
          border-color: rgba(59, 130, 246, 0.5) !important;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1) !important;
        }
        /* 确保输入框内的所有文字都是浅色 */
        input, textarea {
          color: rgb(209, 213, 219) !important;
          background-color: rgba(51, 65, 85, 0.5) !important;
        }
        /* 确保输入框在所有状态下都保持深色背景 */
        input:focus, 
        input:hover, 
        input:active,
        textarea:focus,
        textarea:hover,
        textarea:active {
          background-color: rgba(51, 65, 85, 0.5) !important;
          border-color: rgba(59, 130, 246, 0.5) !important;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1) !important;
        }
      `}</style>
    </div>
  );
};

export default ProfilePage; 