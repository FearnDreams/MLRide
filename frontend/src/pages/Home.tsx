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

  // 获取用户信息
  useEffect(() => {
    const fetchUserProfile = async () => {
      if (isAuthenticated && user) {
        console.log('Fetching user profile, isAuthenticated:', isAuthenticated);
        try {
          const response = await authService.getUserProfile();
          console.log('User profile response:', response);
          if (response.status === 'success' && response.data) {
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
          }
        } catch (error) {
          console.error('获取用户资料失败:', error);
        }
      }
    };

    fetchUserProfile();
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
    <AntMenu className="bg-slate-800/90 backdrop-blur-md border border-slate-700/50 rounded-lg shadow-lg text-white">
      <AntMenu.Item key="profile" className="hover:bg-slate-700/50">
        <Link to="/dashboard/profile" className="text-gray-300 hover:text-white">个人信息</Link>
      </AntMenu.Item>
      <AntMenu.Divider className="border-slate-700/50" />
      <AntMenu.Item key="logout" onClick={handleLogout} className="hover:bg-slate-700/50">
        <span className="text-gray-300 hover:text-white">退出登录</span>
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
    <div className="flex min-h-screen bg-gradient-to-br from-slate-950 via-gray-900 to-slate-900 text-white overflow-hidden relative">
      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl"></div>
        <div className="absolute top-1/3 -left-20 w-60 h-60 bg-purple-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-1/4 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl"></div>
      </div>

      {/* Sidebar */}
      <div className="w-56 bg-slate-800/30 backdrop-blur-md border-r border-slate-700/50 z-10">
        <div className="p-6 flex items-center gap-2">
          <span className="font-bold text-xl bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">MLRide</span>
        </div>
        
        <nav className="mt-6 px-3">
          {sidebarItems.map((item, index) => (
            <Link 
              key={index} 
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 my-1 rounded-lg transition-all duration-200 ${
                location.pathname.includes(item.path) 
                  ? "bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm shadow-blue-500/10" 
                  : "text-gray-300 hover:bg-slate-700/30 hover:text-white"
              }`}
            >
              <item.icon className={`w-5 h-5 ${location.pathname.includes(item.path) ? "text-blue-400" : ""}`} />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="mt-auto p-4 mx-3 mb-6">
          <button className="w-full py-2 px-4 text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-lg shadow-md shadow-blue-900/20 transition-all duration-200">
            工作台管理
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col z-10">
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-6 bg-slate-800/30 backdrop-blur-md border-b border-slate-700/50">
          <h1 className="text-xl font-semibold text-white">
            {location.pathname === '/dashboard/profile' 
              ? "个人信息设置"
              : sidebarItems.find(item => location.pathname.includes(item.path))?.label || "项目概览"}
          </h1>
          <div className="flex items-center gap-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="搜索..."
                className="pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-sm text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
              />
            </div>
            <Dropdown overlay={userMenu} trigger={['click']}>
              <div className="flex items-center cursor-pointer bg-slate-800/50 hover:bg-slate-700/50 px-3 py-2 rounded-lg border border-slate-700/50 transition-all duration-200">
                <img 
                  src={getAvatarUrl()} 
                  alt="User avatar" 
                  className="w-6 h-6 rounded-full object-cover"
                />
                <span className="ml-2 text-gray-300">{getDisplayName()}</span>
                <ChevronDown className="w-4 h-4 ml-1 text-gray-400" />
              </div>
            </Dropdown>
            <div className="flex items-center gap-1 text-gray-300 hover:text-white cursor-pointer">
              <Bell className="w-5 h-5" />
            </div>
            <div className="flex items-center gap-1 text-gray-300 hover:text-white cursor-pointer">
              <HelpCircle className="w-5 h-5" />
              <span>帮助</span>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl border border-slate-700/50 shadow-md p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default Home;
