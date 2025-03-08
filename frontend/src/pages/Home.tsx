import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
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

interface HomeProps {
  children?: React.ReactNode;
}

const Home: React.FC<HomeProps> = ({ children }) => {
  const [selectedTab, setSelectedTab] = useState("我的项目");
  const location = useLocation();
  const navigate = useNavigate();

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
            {sidebarItems.find(item => item.path === location.pathname)?.label || "项目概览"}
          </h1>
          <div className="flex items-center gap-4">
            <div className="flex items-center">
              <img src="https://picsum.photos/24/24" alt="User avatar" className="w-6 h-6 rounded-full" />
              <span className="ml-2">用户名</span>
              <ChevronDown className="w-4 h-4 ml-1" />
            </div>
            <Bell className="w-5 h-5" />
            <HelpCircle className="w-5 h-5" />
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
