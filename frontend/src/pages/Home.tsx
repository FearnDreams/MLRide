import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { Button } from '@/components/ui/button';
import { 
  Menu, 
  Search, 
  Bell, 
  HelpCircle, 
  ChevronDown,
  Clock,
  User,
  Image,
  Monitor,
  Database,
  Network,
  Box,
  Server,
  Users,
  FolderOpen
} from 'lucide-react';
import { RootState } from '@/store';
import { authService } from '@/services/auth';
import { UserProfile } from '@/types/auth';
import { Dropdown, Menu as AntMenu, message } from 'antd';

interface HomeProps {
  children?: React.ReactNode;
}

const Home: React.FC<HomeProps> = ({ children }) => {
  const [selectedTab, setSelectedTab] = useState("我的项目");
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  
  const user = useSelector((state: RootState) => state.auth.user);
  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);

  // 如果在仪表板根路径，重定向到项目页面
  useEffect(() => {
    if (location.pathname === '/dashboard') {
      navigate('/dashboard/projects');
    }
  }, [location.pathname, navigate]);

  // 根据当前路径更新选中的标签
  useEffect(() => {
    const currentPath = location.pathname.split('/')[2]; // 修改为获取 dashboard 后的路径部分
    const currentItem = sidebarItems.find(item => item.path.includes(currentPath));
    if (currentItem) {
      setSelectedTab(currentItem.label);
    }
  }, [location.pathname]);

  // 获取用户个人信息
  useEffect(() => {
    const fetchUserProfile = async () => {
      try {
        console.log('Fetching user profile, isAuthenticated:', isAuthenticated);
        const response = await authService.getUserProfile();
        console.log('User profile response:', response);
        if (response.status === 'success' && response.data) {
          // 确保数据符合UserProfile类型
          const profileData = {
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
        }
      } catch (error) {
        console.error('获取用户信息失败:', error);
      }
    };

    if (isAuthenticated && user) {
      console.log('User is authenticated, fetching profile');
      fetchUserProfile();
    } else {
      console.log('User is not authenticated or user is null');
    }
    
    // 添加一个事件监听器，当用户信息更新时刷新数据
    const handleProfileUpdate = () => {
      if (isAuthenticated) {
        fetchUserProfile();
      }
    };
    
    // 监听自定义事件 'profile-updated'
    window.addEventListener('profile-updated', handleProfileUpdate);
    
    // 组件卸载时移除事件监听器
    return () => {
      window.removeEventListener('profile-updated', handleProfileUpdate);
    };
  }, [isAuthenticated, user]);

  const sidebarItems = [
    { icon: Clock, label: "最近", path: "/dashboard/recent" },
    { icon: FolderOpen, label: "我的项目", path: "/dashboard/projects" },
    { icon: User, label: "我的空间", path: "/dashboard/my-space" },
    { icon: Image, label: "镜像", path: "/dashboard/images" },
    { icon: Monitor, label: "计算资源", path: "/dashboard/compute" },
    { icon: Database, label: "案例库", path: "/dashboard/cases" },
    { icon: Network, label: "离线任务", path: "/dashboard/tasks" },
    { icon: Box, label: "模型库", path: "/dashboard/models" },
    { icon: Server, label: "模型服务", path: "/dashboard/services" },
    { icon: Users, label: "社区资源", path: "/dashboard/community" }
  ];

  // 处理登出
  const handleLogout = async () => {
    try {
      const response = await authService.logout();
      if (response.status === 'success') {
        message.success('已成功登出');
        navigate('/login');
      } else {
        message.error(response.message || '登出失败，请重试');
      }
    } catch (error: any) {
      console.error('登出错误:', error);
      message.error(error.message || '登出失败，请重试');
    }
  };

  // 用户下拉菜单
  const userMenu = (
    <AntMenu>
      <AntMenu.Item key="profile">
        <Link to="/dashboard/profile">个人信息</Link>
      </AntMenu.Item>
      <AntMenu.Divider />
      <AntMenu.Item key="logout" onClick={handleLogout}>
        退出登录
      </AntMenu.Item>
    </AntMenu>
  );

  // 获取显示名称
  const getDisplayName = () => {
    if (userProfile?.nickname) {
      return userProfile.nickname;
    } else if (user?.username) {
      return user.username;
    } else {
      return '用户';
    }
  };

  // 获取头像URL
  const getAvatarUrl = () => {
    if (userProfile?.avatar_url) {
      return userProfile.avatar_url;
    } else {
      return 'https://picsum.photos/24/24'; // 默认头像
    }
  };

  return (
    <div className="flex min-h-screen bg-[#f8f9fa]">
      {/* Sidebar */}
      <div className="w-48 bg-[#2A1B4A] text-white">
        <div className="p-4 flex items-center gap-2">
          <Menu className="w-6 h-6" />
          <span className="font-bold text-xl">MLRide</span>
        </div>
        
        <nav className="mt-4">
          {sidebarItems.map((item, index) => (
            <Link 
              key={index} 
              to={item.path}
              className={`flex items-center gap-3 px-4 py-2 hover:bg-[#3d2b5f] cursor-pointer ${
                location.pathname === item.path ? "bg-[#3d2b5f]" : ""
              }`}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="mt-auto p-4">
          <button className="w-full py-2 text-white bg-[#3d2b5f] hover:bg-[#4d3b6f] rounded">工作台管理</button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white h-14 flex items-center justify-between px-4 border-b">
          <h1 className="text-xl">
            {location.pathname === '/dashboard/profile' 
              ? "个人信息设置"
              : sidebarItems.find(item => item.path === location.pathname)?.label || "项目概览"}
          </h1>
          <div className="flex items-center gap-4">
            <Dropdown overlay={userMenu} trigger={['click']}>
              <div className="flex items-center cursor-pointer">
                <img 
                  src={getAvatarUrl()} 
                  alt="User avatar" 
                  className="w-6 h-6 rounded-full object-cover"
                />
                <span className="ml-2">{getDisplayName()}</span>
                <ChevronDown className="w-4 h-4 ml-1" />
              </div>
            </Dropdown>
            <Bell className="w-5 h-5 cursor-pointer" />
            <HelpCircle className="w-5 h-5 cursor-pointer" />
            <span>帮助</span>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto bg-gray-100 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Home;
