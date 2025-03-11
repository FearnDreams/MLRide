import React, { useState, useEffect } from 'react';
import { Search, Plus, Upload, Rocket, Code, FileText, BarChart3, Clock, Image, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

const RecentPage: React.FC = () => {
  // 最近项目数据
  const recentProjects = [
    {
      id: 1,
      title: "test_canvas",
      description: "2024/12/23 21:59",
      type: "canvas"
    },
    {
      id: 2,
      title: "未命名_2024_12_23",
      description: "2024/12/23 21:42",
      type: "ide"
    },
    {
      id: 3,
      title: "test",
      description: "2024/12/23 21:24",
      type: "canvas"
    }
  ];

  // 最近使用的镜像数据
  const recentImages = [
    {
      id: 1,
      name: "Python 3.9 数据科学环境",
      description: "包含 NumPy, Pandas, Scikit-learn",
      lastUsed: "2 小时前"
    },
    {
      id: 2,
      name: "TensorFlow 2.8 GPU",
      description: "深度学习环境，CUDA 11.2",
      lastUsed: "1 天前"
    }
  ];

  // 系统资源使用数据
  const systemResources = {
    cpu: {
      title: "2核8G CPU资源",
      used: 0,
      total: 19.6,
      unit: "小时"
    },
    gpu: {
      title: "按需购买资源 (腾讯云)",
      used: 0,
      total: "不限",
      unit: "小时"
    }
  };

  // 使用统计数据
  const usageStats = {
    totalHours: 3,
    dailyUsage: [
      { date: "2025-03-04", hours: 0 },
      { date: "2025-03-05", hours: 0 },
      { date: "2025-03-06", hours: 0 },
      { date: "2025-03-07", hours: 0 },
      { date: "2025-03-08", hours: 0 },
      { date: "2025-03-09", hours: 0 },
      { date: "2025-03-10", hours: 0 },
      { date: "2025-03-11", hours: 0 }
    ]
  };

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex-1 overflow-y-auto">
        {/* 快速创建 */}
        <div className="mb-8">
          <h2 className="text-xl font-bold mb-4 text-white">快速创建</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Link to="/dashboard/projects/create-ide" className="block">
              <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center">
                  <Code className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-white">新建 IDE</h3>
                </div>
              </div>
            </Link>
            <Link to="/dashboard/projects/create-notebook" className="block">
              <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-green-500/30 transition-all duration-300 hover:shadow-md hover:shadow-green-500/5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-white">新建 Notebook</h3>
                </div>
              </div>
            </Link>
            <Link to="/dashboard/projects/create-canvas" className="block">
              <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-purple-500/30 transition-all duration-300 hover:shadow-md hover:shadow-purple-500/5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-purple-500/10 flex items-center justify-center">
                  <BarChart3 className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-white">新建 Canvas</h3>
                </div>
              </div>
            </Link>
          </div>
        </div>

        {/* 最近项目 */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-white">最近项目</h2>
            <Link to="/dashboard/projects" className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-sm">
              查看全部 <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {recentProjects.map((project) => (
              <div key={project.id} className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center">
                    {project.type === 'canvas' ? (
                      <BarChart3 className="w-5 h-5 text-blue-400" />
                    ) : (
                      <Code className="w-5 h-5 text-green-400" />
                    )}
                  </div>
                  <div>
                    <h3 className="font-medium text-white">{project.title}</h3>
                    <p className="text-gray-400 text-sm">{project.description}</p>
                  </div>
                </div>
                <div className="mt-4 flex justify-end">
                  <Button size="sm" className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 text-white">
                    运行
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 最近使用的镜像 */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-white">最近使用的镜像</h2>
            <Link to="/dashboard/images" className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-sm">
              查看全部 <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {recentImages.map((image) => (
              <div key={image.id} className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center">
                    <Image className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <h3 className="font-medium text-white">{image.name}</h3>
                    <p className="text-gray-400 text-sm">{image.description}</p>
                    <p className="text-gray-500 text-xs mt-1">最后使用: {image.lastUsed}</p>
                  </div>
                </div>
              </div>
            ))}
            <Link to="/dashboard/images/create" className="block">
              <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-green-500/30 transition-all duration-300 hover:shadow-md hover:shadow-green-500/5 flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center mx-auto mb-3">
                    <Plus className="w-6 h-6 text-green-400" />
                  </div>
                  <h3 className="text-lg font-medium text-white">创建新镜像</h3>
                </div>
              </div>
            </Link>
          </div>
        </div>

        {/* 仪表盘 */}
        <div>
          <h2 className="text-xl font-bold mb-4 text-white">仪表盘</h2>
          
          {/* 资源使用情况 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50">
              <h3 className="text-lg font-medium mb-3 text-gray-300">{systemResources.cpu.title}</h3>
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-400">已用量 (小时)</span>
                <span className="text-gray-400">余量 (小时)</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-2xl font-bold text-blue-400">{systemResources.cpu.used}</span>
                <span className="text-2xl font-bold text-blue-400">{systemResources.cpu.total}</span>
              </div>
              <div className="w-full bg-slate-700/50 h-2 rounded-full mt-4 overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full" 
                  style={{ width: `${(systemResources.cpu.used / systemResources.cpu.total) * 100}%` }}
                ></div>
              </div>
            </div>
            
            <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50">
              <h3 className="text-lg font-medium mb-3 text-gray-300">{systemResources.gpu.title}</h3>
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-400">已用量 (小时)</span>
                <span className="text-gray-400">余量 (小时)</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-2xl font-bold text-green-400">{systemResources.gpu.used}</span>
                <span className="text-2xl font-bold text-green-400">{systemResources.gpu.total}</span>
              </div>
              <div className="w-full bg-slate-700/50 h-2 rounded-full mt-4 overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-green-500 to-emerald-500 h-full rounded-full" 
                  style={{ width: '0%' }}
                ></div>
              </div>
            </div>
          </div>
          
          {/* 使用统计 */}
          <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50">
            <h3 className="text-lg font-medium mb-4 text-gray-300">用量统计</h3>
            <div className="text-sm text-gray-400 mb-2">时长 (小时)</div>
            <div className="text-3xl font-bold text-white mb-6">{usageStats.totalHours}</div>
            
            <div className="h-40 flex items-end justify-between">
              {usageStats.dailyUsage.map((day, index) => (
                <div key={index} className="flex flex-col items-center">
                  <div className="w-8 bg-blue-500/20 rounded-t-sm" style={{ height: `${day.hours * 10}px` }}></div>
                  <div className="text-xs text-gray-500 mt-2">{day.date.split('-')[2]}</div>
                </div>
              ))}
            </div>
            <div className="text-right text-xs text-gray-500 mt-2">2025-03-11</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RecentPage; 