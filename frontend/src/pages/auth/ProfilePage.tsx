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
      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle>个人信息</CardTitle>
          <CardDescription>查看和更新您的个人信息</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-6 flex justify-center">
            <div className="text-center">
              <div className="mb-2">
                {previewImage ? (
                  <img 
                    src={previewImage} 
                    alt="头像" 
                    className="w-24 h-24 rounded-full object-cover mx-auto"
                  />
                ) : (
                  <div className="w-24 h-24 rounded-full bg-gray-200 flex items-center justify-center mx-auto">
                    <UserOutlined style={{ fontSize: 36 }} />
                  </div>
                )}
              </div>
              <Upload {...uploadProps} showUploadList={false}>
                <Button className="bg-blue-500 hover:bg-blue-600 text-white">
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
              label="用户名"
              name="username"
            >
              <Input disabled />
            </Form.Item>
            
            <Form.Item
              label="邮箱"
              name="email"
            >
              <Input disabled />
            </Form.Item>
            
            <Form.Item
              label="昵称"
              name="nickname"
              rules={[{ max: 30, message: '昵称最多30个字符' }]}
            >
              <Input placeholder="请输入昵称" />
            </Form.Item>
            
            <Form.Item>
              <Button 
                type="submit" 
                className="w-full bg-blue-500 hover:bg-blue-600 text-white" 
                disabled={loading}
              >
                {loading ? '保存中...' : '保存修改'}
              </Button>
            </Form.Item>
          </Form>
          
          <div className="mt-6 flex justify-between">
            <Button 
              onClick={() => setIsPasswordModalVisible(true)}
              className="bg-blue-400 hover:bg-blue-500 text-white"
            >
              修改密码
            </Button>
            <Button 
              onClick={showDeleteConfirm}
              className="bg-red-500 hover:bg-red-600 text-white"
            >
              注销账户
            </Button>
          </div>
        </CardContent>
      </Card>
      
      {/* 修改密码弹窗 */}
      <Modal
        title="修改密码"
        open={isPasswordModalVisible}
        onCancel={() => setIsPasswordModalVisible(false)}
        footer={null}
      >
        <Form
          form={passwordForm}
          layout="vertical"
          onFinish={handlePasswordUpdate}
        >
          <Form.Item
            label="当前密码"
            name="currentPassword"
            rules={[
              { required: true, message: '请输入当前密码' },
            ]}
          >
            <Input.Password placeholder="请输入当前密码" />
          </Form.Item>
          
          <Form.Item
            label="新密码"
            name="newPassword"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 8, message: '密码至少8个字符' },
              { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$/, message: '密码必须包含大小写字母和数字' }
            ]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
          
          <Form.Item
            label="确认新密码"
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
            <Input.Password placeholder="请确认新密码" />
          </Form.Item>
          
          <Form.Item>
            <div className="flex justify-end gap-2">
              <Button 
                onClick={() => setIsPasswordModalVisible(false)}
                className="bg-gray-200 hover:bg-gray-300"
              >
                取消
              </Button>
              <Button 
                type="submit" 
                className="bg-blue-500 hover:bg-blue-600 text-white"
                disabled={loading}
              >
                {loading ? '提交中...' : '确认修改'}
              </Button>
            </div>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ProfilePage; 