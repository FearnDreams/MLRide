import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { Button } from '@/components/ui/button';

const ProjectsPage: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState("我的项目");

  const projects = [
    {
      title: "图像分类模型",
      description: "最后更新于 2 小时前",
      status: "进行中",
      type: "机器学习"
    },
    {
      title: "自然语言处理",
      description: "最后更新于 1 天前",
      status: "已完成",
      type: "深度学习"
    },
    {
      title: "数据预处理流程",
      description: "最后更新于 3 天前",
      status: "进行中",
      type: "数据处理"
    }
  ];

  return (
    <div className="flex-1 flex flex-col">
      {/* Header */}
      <header className="bg-white h-14 flex items-center justify-between px-4 border-b">
        <h1 className="text-xl">项目概览</h1>
      </header>

      {/* Content */}
      <div className="flex-1 p-6 overflow-y-auto">
        {/* Search and Create */}
        <div className="flex justify-between mb-6">
          <div className="relative flex-1 max-w-2xl">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="搜索项目名称或描述"
              className="w-full pl-10 pr-4 py-2 border rounded-md"
            />
          </div>
          <Button className="bg-blue-600 text-white px-4 py-2 rounded-md flex items-center gap-2">
            <span>+</span> 新建项目
          </Button>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow-sm">
            <h3 className="text-lg font-medium mb-2">创建新项目</h3>
            <p className="text-gray-500 mb-4">开始一个新的机器学习项目</p>
            <Button>创建项目</Button>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm">
            <h3 className="text-lg font-medium mb-2">导入数据集</h3>
            <p className="text-gray-500 mb-4">上传或连接您的数据源</p>
            <Button variant="outline">导入数据</Button>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm">
            <h3 className="text-lg font-medium mb-2">部署模型</h3>
            <p className="text-gray-500 mb-4">将模型部署到生产环境</p>
            <Button variant="outline">开始部署</Button>
          </div>
        </div>

        {/* Projects List */}
        <div className="mb-8">
          <div className="border-b mb-6">
            <div className="flex gap-6">
              <button 
                className={`pb-2 ${selectedTab === "我的项目" ? "border-b-2 border-blue-600 text-blue-600" : ""}`}
                onClick={() => setSelectedTab("我的项目")}
              >
                我的项目 (3)
              </button>
              <button 
                className={`pb-2 ${selectedTab === "团队项目" ? "border-b-2 border-blue-600 text-blue-600" : ""}`}
                onClick={() => setSelectedTab("团队项目")}
              >
                团队项目 (8)
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project, index) => (
              <div key={index} className="bg-white p-6 rounded-lg shadow-sm">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-medium mb-2">{project.title}</h3>
                    <p className="text-gray-500 text-sm mb-2">{project.description}</p>
                    <div className="flex items-center gap-2">
                      <span className="text-sm px-2 py-1 bg-blue-100 text-blue-600 rounded">
                        {project.status}
                      </span>
                      <span className="text-sm px-2 py-1 bg-gray-100 text-gray-600 rounded">
                        {project.type}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="mt-4 flex gap-2">
                  <Button size="sm" variant="outline">查看</Button>
                  <Button size="sm" variant="outline">编辑</Button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* System Status */}
        <div>
          <h2 className="text-xl font-bold mb-4">系统状态</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-lg shadow-sm">
              <h3 className="text-lg font-medium mb-2">CPU 使用率</h3>
              <p className="text-2xl font-bold text-blue-500">45%</p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-sm">
              <h3 className="text-lg font-medium mb-2">内存使用率</h3>
              <p className="text-2xl font-bold text-green-500">60%</p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-sm">
              <h3 className="text-lg font-medium mb-2">GPU 使用率</h3>
              <p className="text-2xl font-bold text-purple-500">30%</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectsPage;
