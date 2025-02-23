import React, { useState } from 'react';
import { Search, Info, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';

const ImagesPage: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState("我的镜像");
  
  const languageVersions = [
    { name: "Python", versions: ["版本"] },
    { name: "R", versions: ["版本"] },
    { name: "Julia", versions: ["版本"] },
    { name: "其它", versions: ["请选择"] }
  ];

  const cudaVersions = [
    "1.11.1", "1.13.1", "10", "10.2", "11.0", "11.1.1", "11.3",
    "11.3.1", "11.6", "11.7", "12.1", "12.1.1", "12.3", "9"
  ];

  const images = [
    {
      title: "气象分析镜像 Python 3.7",
      description: "气象专用，使用conda安装可能存在较多冲突, Python 3.7.8",
      version: "Python 3.7.8",
      type: ["官方", "CPU"]
    },
    {
      title: "TF2.4 Torch1.7 推断",
      description: "tf2.4.2-torch1.7.1-py3.7.10",
      version: "Python 3.7.10",
      type: ["官方", "CPU"]
    },
    {
      title: "Python 3.7 数据科学镜像",
      description: "兼容 ModelWhale IDE，Python 3.7.12",
      version: "Python 3.7.12",
      type: ["官方", "CPU"]
    }
  ];

  return (
    <div className="flex-1 flex flex-col">
      {/* Header */}
      <header className="bg-white h-14 flex items-center justify-between px-4 border-b">
        <h1 className="text-xl">镜像</h1>
      </header>

      {/* Content */}
      <div className="flex-1 p-6 overflow-y-auto">
        {/* Search and Create */}
        <div className="flex justify-between mb-6">
          <div className="relative flex-1 max-w-2xl">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="搜索镜像名或标签，搜索多个标名用英文逗号分隔"
              className="w-full pl-10 pr-4 py-2 border rounded-md"
            />
          </div>
          <Button className="bg-blue-600 text-white px-4 py-2 rounded-md flex items-center gap-2">
            <span>+</span> 新建镜像
          </Button>
        </div>

        {/* Filters */}
        <div className="bg-white p-6 rounded-md mb-6">
          <div className="mb-6">
            <h3 className="mb-4">语言版本</h3>
            <div className="grid grid-cols-4 gap-4">
              {languageVersions.map((lang, index) => (
                <div key={index} className="relative">
                  <select 
                    className="w-full p-2 border rounded appearance-none bg-white"
                    aria-label={`选择${lang.name}版本`}
                  >
                    <option>{lang.name}</option>
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4" />
                </div>
              ))}
            </div>
          </div>

          <div className="mb-6">
            <h3 className="mb-4">CUDA 版本</h3>
            <div className="flex flex-wrap gap-2">
              {cudaVersions.map((version, index) => (
                <span 
                  key={index} 
                  className="px-3 py-1 bg-gray-100 rounded-full text-sm cursor-pointer hover:bg-gray-200"
                >
                  {version}
                </span>
              ))}
            </div>
          </div>

          <div>
            <h3 className="mb-4">应用类型</h3>
            <div className="flex gap-4">
              <span className="px-4 py-1 bg-gray-100 rounded-full cursor-pointer hover:bg-gray-200">
                Notebook
              </span>
              <span className="px-4 py-1 bg-gray-100 rounded-full cursor-pointer hover:bg-gray-200">
                Canvas
              </span>
              <span className="px-4 py-1 bg-gray-100 rounded-full cursor-pointer hover:bg-gray-200">
                IDE
              </span>
            </div>
          </div>
        </div>

        {/* Tabs and Images List */}
        <div>
          <div className="border-b mb-6">
            <div className="flex gap-6">
              <button 
                className={`pb-2 ${selectedTab === "我的镜像" ? "border-b-2 border-blue-600 text-blue-600" : ""}`}
                onClick={() => setSelectedTab("我的镜像")}
              >
                我的镜像 11
              </button>
              <button 
                className={`pb-2 ${selectedTab === "更多镜像" ? "border-b-2 border-blue-600 text-blue-600" : ""}`}
                onClick={() => setSelectedTab("更多镜像")}
              >
                更多镜像 179
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {images.map((image, index) => (
              <div key={index} className="bg-white p-4 rounded-md">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-medium">{image.title}</h3>
                      <Info className="w-4 h-4 text-gray-400" />
                    </div>
                    <p className="text-gray-500 text-sm mb-2">{image.description}</p>
                    <div className="flex items-center gap-2">
                      <img src="https://picsum.photos/16/16" alt="Python logo" className="w-4 h-4" />
                      <span className="text-sm">{image.version}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {image.type.map((type, i) => (
                      <span key={i} className={`text-sm ${type === "CPU" ? "text-blue-600" : "text-gray-600"}`}>
                        {type}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImagesPage;
