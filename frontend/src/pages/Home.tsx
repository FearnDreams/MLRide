import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { 
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
  FolderOpen,
  LogOut,
  Settings,
  BarChart,
  ChevronsLeft,
  ChevronsRight
} from 'lucide-react';
import { RootState } from '@/store';
import { authService } from '@/services/auth';
import { UserProfile } from '@/types/auth';
import { message, Modal } from 'antd';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip } from 'antd';

const Home: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState("我的项目");
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isHelpModalVisible, setIsHelpModalVisible] = useState(false);
  
  const user = useSelector((state: RootState) => state.auth.user);
  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);

  // 如果在仪表板根路径，重定向到项目页面
  useEffect(() => {
    if (location.pathname === '/dashboard') {
      navigate('/dashboard/recent');
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
    { icon: Image, label: "镜像", path: "/dashboard/images" },
    { icon: Database, label: "数据集", path: "/dashboard/datasets" },
    { icon: BarChart, label: "统计面板", path: "/dashboard/tasks" },
    { icon: Users, label: "社区资源", path: "/dashboard/community" },
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

  // Function to render the help modal
  const renderHelpModal = (): JSX.Element => (
    <Modal
      title={
        <div className="flex items-center text-white">
          <HelpCircle className="w-5 h-5 mr-2 text-blue-400" />
          欢迎使用 MLRide 平台
        </div>
      }
      open={isHelpModalVisible}
      onCancel={() => setIsHelpModalVisible(false)}
      footer={[
        <Button
          key="close"
          onClick={() => setIsHelpModalVisible(false)}
          className="bg-blue-600 hover:bg-blue-500 text-white border-0"
          size="sm"
        >
          我知道了
        </Button>
      ]}
      width={600}
      className="custom-dark-modal"
      centered // Center the modal
    >
      <div className="text-gray-300 space-y-4 mt-4 text-sm">
        <p>
          MLRide 是一个面向机器学习开发者的集成化生产力平台，旨在简化从环境配置、代码编写、版本控制到模型部署的全流程。
        </p>
        <h3 className="text-base font-medium text-white pt-2 text-center">🔥🔥🔥核心功能🔥🔥🔥</h3>
        <ul className="list-disc list-inside space-y-2 pl-2">
          <li>
            <strong className="text-blue-400">📂项目管理:</strong> 创建和管理您的机器学习项目，支持不同类型的项目（如 Jupyter Notebook）。
          </li>
          <li>
            <strong className="text-blue-400">🐋镜像管理:</strong> 选择或自定义 Docker 镜像，为项目提供一致的运行环境。
          </li>
          <li>
            <strong className="text-blue-400">💻在线开发环境:</strong> 使用镜像直接在浏览器中运行和调试 Jupyter Notebook。
          </li>
          <li>
            <strong className="text-blue-400">🔧版本控制:</strong> 实现项目（代码）版本的追踪与比较。
          </li>
          <li>
            <strong className="text-blue-400">💾数据集管理:</strong> 上传并管理您的项目数据集。
          </li>
          <li>
            <strong className="text-blue-400">🖌️可视化拖拽编程:</strong> 在画布上设计并执行工作流。
          </li>
        </ul>
        <p className="pt-2">
          平台致力于提供一个高效、易用、可扩展的机器学习工作流解决方案。祝您使用愉快！
        </p>
      </div>
    </Modal>
  );

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-slate-950 via-gray-900 to-slate-900 text-white overflow-hidden relative">
      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl"></div>
        <div className="absolute top-1/3 -left-20 w-60 h-60 bg-purple-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-1/4 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl"></div>
      </div>

      {/* Sidebar */}
      <div className={`flex flex-col justify-between bg-slate-800/30 backdrop-blur-md border-r border-slate-700/50 z-10 transition-all duration-300 ${isCollapsed ? 'w-20' : 'w-56'}`}>
        <div>
          <div className={`flex items-center justify-between p-6 ${isCollapsed ? 'px-4' : ''}`}>
            {!isCollapsed && (
              <Link to="/dashboard/recent" className="flex items-center gap-2">
                <img src="/mlride-icon.svg" alt="MLRide Logo" className="w-8 h-8 flex-shrink-0" />
                <span className="font-bold text-xl bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent whitespace-nowrap">MLRide</span>
              </Link>
            )}
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={() => setIsCollapsed(!isCollapsed)} 
              className="text-gray-400 hover:text-white hover:bg-slate-700/50"
            >
              {isCollapsed ? <ChevronsRight className="w-5 h-5" /> : <ChevronsLeft className="w-5 h-5" />}
            </Button>
          </div>
          
          <nav className={`mt-6 ${isCollapsed ? 'px-2' : 'px-3'}`}>
            {sidebarItems.map((item, index) => (
              <Tooltip key={index} title={isCollapsed ? item.label : ''} placement="right">
                <Link 
                  to={item.path}
                  className={`flex items-center gap-3 my-1 rounded-lg transition-all duration-200 ${isCollapsed ? 'justify-center px-2 py-3' : 'px-4 py-3'} ${
                    location.pathname.includes(item.path) 
                      ? "bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm shadow-blue-500/10" 
                      : "text-gray-300 hover:bg-slate-700/30 hover:text-white"
                  }`}
                >
                  <item.icon className={`w-5 h-5 flex-shrink-0 ${location.pathname.includes(item.path) ? "text-blue-400" : ""}`} />
                  {!isCollapsed && <span>{item.label}</span>}
                </Link>
              </Tooltip>
            ))}
          </nav>
        </div>

        <div className={`p-4 ${isCollapsed ? 'px-2' : 'px-3'} mb-6`}>
           <Tooltip title={isCollapsed ? '退出登录' : ''} placement="right">
            <Button 
              onClick={handleLogout}
              className={`w-full py-2 flex items-center gap-3 transition-all duration-200 bg-red-500/10 hover:bg-red-500/20 text-red-300 border border-red-500/50 ${isCollapsed ? 'justify-center px-0' : 'px-4'}`}
            >
              <LogOut className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span>退出登录</span>}
            </Button>
          </Tooltip>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col z-10 transition-all duration-300">
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-6 bg-slate-800/30 backdrop-blur-md border-b border-slate-700/50 flex-shrink-0">
          <h1 className="text-xl font-semibold text-white">
            {location.pathname === '/dashboard/profile' 
              ? "个人信息设置"
              : sidebarItems.find(item => location.pathname.includes(item.path))?.label || "项目概览"}
          </h1>
          <div className="flex items-center gap-4">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <div className="flex items-center cursor-pointer bg-slate-800/50 hover:bg-slate-700/50 px-3 py-2 rounded-lg border border-slate-700/50 transition-all duration-200">
                  <img 
                    src={getAvatarUrl()} 
                    alt="User avatar" 
                    className="w-6 h-6 rounded-full object-cover"
                  />
                  <span className="ml-2 text-gray-300">{getDisplayName()}</span>
                  <ChevronDown className="w-4 h-4 ml-1 text-gray-400" />
                </div>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => navigate('/dashboard/profile')}>
                  <Settings className="mr-2 h-4 w-4" />
                  个人信息
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleLogout} className="text-red-500 focus:text-red-500">
                  <LogOut className="mr-2 h-4 w-4" />
                  退出登录
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Tooltip title="帮助文档" placement="bottom">
              <div 
                className="flex items-center gap-1 text-gray-300 hover:text-white cursor-pointer p-2 hover:bg-slate-700/50 rounded-md"
                onClick={() => setIsHelpModalVisible(true)}
              >
                <HelpCircle className="w-5 h-5" />
                {!isCollapsed && <span>帮助</span>}
              </div>
            </Tooltip>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="h-full">
            <Outlet />
          </div>
        </main>
      </div>
      {renderHelpModal()}
    </div>
  );
};

export default Home;
