import React, { useState } from 'react';
import { Search, Plus, Upload, Rocket } from 'lucide-react';
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
      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Search and Create */}
        <div className="flex justify-between mb-6">
          <div className="relative flex-1 max-w-2xl">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="搜索项目名称或描述"
              className="w-full pl-10 pr-4 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-colors"
            />
          </div>
          <Button className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-gray-100 px-4 py-2 rounded-lg shadow-md shadow-blue-900/20 border-0 transition-all duration-200 flex items-center">
            <Plus className="w-5 h-5 mr-1" /> 新建项目
          </Button>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5">
            <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center mb-4">
              <Plus className="w-5 h-5 text-blue-400" />
            </div>
            <h3 className="text-lg font-medium mb-2 text-white">创建新项目</h3>
            <p className="text-gray-400 mb-4">开始一个新的机器学习项目</p>
            <Button className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 shadow-md shadow-blue-900/20 text-gray-100 transition-all duration-200">
              创建项目
            </Button>
          </div>
          <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-green-500/30 transition-all duration-300 hover:shadow-md hover:shadow-green-500/5">
            <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center mb-4">
              <Upload className="w-5 h-5 text-green-400" />
            </div>
            <h3 className="text-lg font-medium mb-2 text-white">导入数据集</h3>
            <p className="text-gray-400 mb-4">上传或导入已有的数据集</p>
            <Button className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 border-0 shadow-md shadow-green-900/20 text-gray-100 transition-all duration-200">
              导入数据
            </Button>
          </div>
          <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-purple-500/30 transition-all duration-300 hover:shadow-md hover:shadow-purple-500/5">
            <div className="w-10 h-10 rounded-full bg-purple-500/10 flex items-center justify-center mb-4">
              <Rocket className="w-5 h-5 text-purple-400" />
            </div>
            <h3 className="text-lg font-medium mb-2 text-white">部署模型</h3>
            <p className="text-gray-400 mb-4">将训练好的模型部署到生产环境</p>
            <Button className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 border-0 shadow-md shadow-purple-900/20 text-gray-100 transition-all duration-200">
              开始部署
            </Button>
          </div>
        </div>

        {/* Projects List */}
        <div className="mb-8">
          <div className="border-b border-slate-700/50 mb-6">
            <div className="flex gap-6">
              <button 
                className={`pb-2 text-gray-300 hover:text-white transition-colors duration-200 ${selectedTab === "我的项目" ? "border-b-2 border-blue-500 text-blue-400" : ""}`}
                onClick={() => setSelectedTab("我的项目")}
              >
                我的项目 (3)
              </button>
              <button 
                className={`pb-2 text-gray-300 hover:text-white transition-colors duration-200 ${selectedTab === "团队项目" ? "border-b-2 border-blue-500 text-blue-400" : ""}`}
                onClick={() => setSelectedTab("团队项目")}
              >
                团队项目 (8)
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project, index) => (
              <div key={index} className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-medium mb-2 text-white">{project.title}</h3>
                    <p className="text-gray-400 text-sm mb-2">{project.description}</p>
                    <div className="flex items-center gap-2">
                      <span className={`text-sm px-2 py-1 rounded-full ${
                        project.status === "进行中" 
                          ? "bg-blue-500/20 text-blue-400 border border-blue-500/30" 
                          : "bg-green-500/20 text-green-400 border border-green-500/30"
                      }`}>
                        {project.status}
                      </span>
                      <span className="text-sm px-2 py-1 bg-slate-700/50 text-gray-300 rounded-full border border-slate-600/50">
                        {project.type}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="mt-4 flex gap-2">
                  <Button size="sm" className="border-slate-700 bg-slate-800/50 hover:bg-slate-700/50 text-gray-300 hover:text-white transition-all duration-200 flex items-center gap-2">
                    查看
                  </Button>
                  <Button size="sm" className="border-slate-700 bg-slate-800/50 hover:bg-slate-700/50 text-gray-300 hover:text-white transition-all duration-200 flex items-center gap-2">
                    编辑
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* System Status */}
        <div>
          <h2 className="text-xl font-bold mb-4 text-white">系统状态</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5">
              <h3 className="text-lg font-medium mb-2 text-gray-300">CPU 使用率</h3>
              <p className="text-2xl font-bold text-blue-400">45%</p>
            </div>
            <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-green-500/30 transition-all duration-300 hover:shadow-md hover:shadow-green-500/5">
              <h3 className="text-lg font-medium mb-2 text-gray-300">内存使用率</h3>
              <p className="text-2xl font-bold text-green-400">60%</p>
            </div>
            <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-purple-500/30 transition-all duration-300 hover:shadow-md hover:shadow-purple-500/5">
              <h3 className="text-lg font-medium mb-2 text-gray-300">GPU 使用率</h3>
              <p className="text-2xl font-bold text-purple-400">30%</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectsPage;
