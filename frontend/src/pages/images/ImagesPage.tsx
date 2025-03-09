import React, { useState, useEffect } from 'react';
import { Search, Info, ChevronDown, AlertCircle, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { imagesService, DockerImage } from '@/services/images';
import { message, Spin, Empty, Modal, Tooltip } from 'antd';

const ImagesPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState("我的镜像");
  const [userImages, setUserImages] = useState<DockerImage[]>([]);
  const [loading, setLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  
  // 获取用户镜像
  const fetchUserImages = async () => {
    setLoading(true);
    try {
      const response = await imagesService.getUserImages();
      if (response.status === 'success' && response.data) {
        // 确保数据是数组类型
        const imagesData = Array.isArray(response.data) ? response.data : [];
        setUserImages(imagesData);
      } else {
        message.error(response.message || '获取镜像失败');
      }
    } catch (error: any) {
      console.error('获取用户镜像失败:', error);
      message.error(error.message || '获取镜像失败，请重试');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchUserImages();
  }, []);
  
  // 删除镜像
  const handleDeleteImage = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个镜像吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        setDeleteLoading(true);
        try {
          const response = await imagesService.deleteImage(id);
          if (response.status === 'success') {
            message.success('镜像删除成功');
            // 重新获取镜像列表
            fetchUserImages();
          } else {
            message.error(response.message || '删除镜像失败');
          }
        } catch (error: any) {
          console.error('删除镜像失败:', error);
          message.error(error.message || '删除镜像失败，请重试');
        } finally {
          setDeleteLoading(false);
        }
      }
    });
  };
  
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

  const officialImages = [
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

  // 获取镜像状态对应的中文
  const getStatusText = (status: string) => {
    const statusMap: Record<string, string> = {
      'pending': '等待中',
      'building': '构建中',
      'ready': '就绪',
      'failed': '失败'
    };
    return statusMap[status] || status;
  };

  // 渲染用户镜像列表
  const renderUserImages = () => {
    if (loading) {
      return (
        <div className="flex justify-center items-center py-12">
          <Spin size="large" tip="加载中..." />
        </div>
      );
    }

    if (userImages.length === 0) {
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <div className="flex flex-col items-center">
              <div className="flex items-center text-gray-500 mb-2">
                <AlertCircle className="w-5 h-5 mr-2" />
                <span>暂未创建任何镜像</span>
              </div>
              <p className="text-gray-400 text-sm">您可以点击"新建镜像"按钮创建自己的镜像</p>
            </div>
          }
        >
          <Button 
            className="bg-blue-600 text-white px-4 py-2 rounded-md mt-4"
            onClick={() => navigate('/dashboard/images/create')}
          >
            新建镜像
          </Button>
        </Empty>
      );
    }

    return (
      <div className="space-y-4">
        {userImages.map((image) => (
          <div key={image.id} className="bg-white p-4 rounded-md">
            <div className="flex justify-between items-start">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-medium">{image.name}</h3>
                  <Info className="w-4 h-4 text-gray-400" />
                </div>
                <p className="text-gray-500 text-sm mb-2">{image.description}</p>
                <div className="flex items-center gap-2">
                  <img src="https://picsum.photos/16/16" alt="Python logo" className="w-4 h-4" />
                  <span className="text-sm">Python {image.python_version}</span>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-600">
                  {getStatusText(image.status)}
                </span>
                <span className="text-sm text-blue-600">
                  个人
                </span>
                <Tooltip title="删除镜像">
                  <button 
                    className="text-red-500 hover:text-red-700 p-1 rounded-full hover:bg-gray-100"
                    onClick={() => handleDeleteImage(image.id)}
                    disabled={deleteLoading}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </Tooltip>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  // 渲染官方镜像列表
  const renderOfficialImages = () => {
    return (
      <div className="space-y-4">
        {officialImages.map((image, index) => (
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
    );
  };

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
          <Button 
            className="bg-blue-600 text-white px-4 py-2 rounded-md flex items-center gap-2"
            onClick={() => navigate('/dashboard/images/create')}
          >
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
                我的镜像 {userImages.length}
              </button>
              <button 
                className={`pb-2 ${selectedTab === "更多镜像" ? "border-b-2 border-blue-600 text-blue-600" : ""}`}
                onClick={() => setSelectedTab("更多镜像")}
              >
                更多镜像 {officialImages.length}
              </button>
            </div>
          </div>

          {selectedTab === "我的镜像" ? renderUserImages() : renderOfficialImages()}
        </div>
      </div>
    </div>
  );
};

export default ImagesPage;
