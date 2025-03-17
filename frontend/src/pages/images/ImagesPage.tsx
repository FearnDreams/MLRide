import React, { useState, useEffect } from 'react';
import { Search, Info, AlertCircle, Trash2, Plus } from 'lucide-react';
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
        console.log('镜像页面原始数据:', imagesData);
        if(imagesData.length > 0) {
          console.log('第一个镜像详情:', JSON.stringify(imagesData[0], null, 2));
          console.log('Python版本字段:', imagesData[0].python_version, imagesData[0].pythonVersion);
        }
        
        // 处理数据，确保能够正确显示Python版本
        const processedImages = imagesData.map(image => {
          // 如果后端返回的是pythonVersion而不是python_version，做字段兼容
          if (image.pythonVersion && !image.python_version) {
            return {
              ...image,
              python_version: image.pythonVersion
            };
          }
          // 如果后端返回的是python_version而不是pythonVersion，做字段兼容
          if (image.python_version && !image.pythonVersion) {
            return {
              ...image,
              pythonVersion: image.python_version
            };
          }
          return image;
        });
        
        setUserImages(processedImages);
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
      title: <span className="text-white">确认删除</span>,
      content: <span className="text-gray-300">确定要删除这个镜像吗？此操作不可恢复。</span>,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      className: 'custom-dark-modal',
      okButtonProps: {
        className: 'bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-500 hover:to-pink-500 border-0',
      },
      cancelButtonProps: {
        className: 'bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600',
      },
      onOk: async () => {
        setDeleteLoading(true);
        try {
          console.log('开始删除镜像:', id);
          const response = await imagesService.deleteImage(id);
          console.log('删除镜像响应:', response);
          
          if (response.status === 'success') {
            message.success('镜像删除成功');
            // 重新获取镜像列表
            fetchUserImages();
          } else {
            message.error(response.message || '删除镜像失败');
            // 即使API返回错误，也刷新列表，因为数据库记录可能已被删除
            fetchUserImages();
          }
        } catch (error: any) {
          console.error('删除镜像失败:', error);
          message.error(error.message || '删除镜像失败，请重试');
          // 即使发生错误，也刷新列表，因为数据库记录可能已被删除
          fetchUserImages();
        } finally {
          setDeleteLoading(false);
        }
      }
    });
  };
  
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

  // 获取状态对应的样式
  const getStatusStyle = (status: string) => {
    const styleMap: Record<string, { bg: string, text: string, border: string }> = {
      'pending': { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30' },
      'building': { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
      'ready': { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
      'failed': { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' }
    };
    return styleMap[status] || { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/30' };
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
              <div className="flex items-center text-gray-300 mb-2">
                <AlertCircle className="w-5 h-5 mr-2" />
                <span>暂未创建任何镜像</span>
              </div>
              <p className="text-gray-400 text-sm">您可以点击"新建镜像"按钮创建自己的镜像</p>
            </div>
          }
        >
          <Button 
            className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-4 py-2 rounded-lg shadow-md shadow-blue-900/20 border-0 transition-all duration-200 mt-4"
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
          <div key={image.id} className="bg-slate-800/30 backdrop-blur-sm p-5 rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-medium text-white">{image.name}</h3>
                  <Tooltip title="查看详情">
                    <Info 
                      className="w-4 h-4 text-gray-400 hover:text-blue-400 cursor-pointer transition-colors"
                      aria-label="查看镜像详情"
                    />
                  </Tooltip>
                </div>
                <p className="text-gray-400 text-sm mb-3">{image.description || '暂无描述'}</p>
                
                {/* 添加详细信息区域 */}
                <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/50 mb-3">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <span className="text-xs text-blue-400">Py</span>
                      </div>
                      <span className="text-sm text-gray-300 bg-blue-500/10 px-2 py-0.5 rounded-full border border-blue-500/30">
                        Python {image.pythonVersion || '未指定'}
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center">
                        <span className="text-xs text-green-400">创</span>
                      </div>
                      <span className="text-sm text-gray-300">创建于 {new Date(image.created).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                {/* 显示包信息（如果有的话） */}
                {image.packages && (
                  <div className="mt-2">
                    <h4 className="text-sm text-gray-300 mb-1">包含的工具包:</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {image.packages.split(',').map((pkg, index) => (
                        <span key={index} className="text-xs px-2 py-0.5 bg-indigo-500/10 text-indigo-300 rounded border border-indigo-500/20">
                          {pkg.trim()}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-4">
                <span className={`text-sm px-2 py-1 rounded-full ${getStatusStyle(image.status).bg} ${getStatusStyle(image.status).text} border ${getStatusStyle(image.status).border}`}>
                  {getStatusText(image.status)}
                </span>
                <span className="text-sm px-2 py-1 bg-indigo-500/20 text-indigo-400 rounded-full border border-indigo-500/30">
                  个人
                </span>
                <Tooltip title="删除镜像">
                  <button 
                    className="text-red-400 hover:text-red-300 p-1.5 rounded-full hover:bg-red-500/10 transition-all duration-200"
                    onClick={() => handleDeleteImage(image.id)}
                    disabled={deleteLoading}
                    aria-label="删除镜像"
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
          <div key={index} className="bg-slate-800/30 backdrop-blur-sm p-5 rounded-xl border border-slate-700/50 hover:border-purple-500/30 transition-all duration-300 hover:shadow-md hover:shadow-purple-500/5">
            <div className="flex justify-between items-start">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-medium text-white">{image.title}</h3>
                  <Tooltip title="查看详情">
                    <Info 
                      className="w-4 h-4 text-gray-400 hover:text-purple-400 cursor-pointer transition-colors"
                      aria-label="查看官方镜像详情"
                    />
                  </Tooltip>
                </div>
                <p className="text-gray-400 text-sm mb-3">{image.description}</p>
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded-full bg-purple-500/20 flex items-center justify-center">
                    <span className="text-xs text-purple-400">Py</span>
                  </div>
                  <span className="text-sm text-gray-300">{image.version}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {image.type.map((type, i) => (
                  <span key={i} className={`text-sm px-2 py-1 rounded-full ${
                    type === "官方" 
                      ? "bg-purple-500/20 text-purple-400 border border-purple-500/30" 
                      : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                  }`}>
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
      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Search and Create */}
        <div className="flex justify-between mb-6">
          <div className="relative flex-1 max-w-2xl">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="搜索镜像名或标签，搜索多个标名用英文逗号分隔"
              className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
            />
          </div>
          <Button 
            className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-4 py-2 rounded-lg shadow-md shadow-blue-900/20 border-0 transition-all duration-200 flex items-center gap-2"
            onClick={() => navigate('/dashboard/images/create')}
          >
            <Plus className="w-5 h-5" /> 新建镜像
          </Button>
        </div>

        {/* Filters */}
        <div className="mb-6">
          <div className="border-b border-slate-700/50 mb-6">
            <div className="flex gap-6">
              <button 
                className={`pb-2 text-gray-300 hover:text-white transition-colors duration-200 ${selectedTab === "我的镜像" ? "border-b-2 border-blue-500 text-blue-400" : ""}`}
                onClick={() => setSelectedTab("我的镜像")}
              >
                我的镜像
              </button>
              <button 
                className={`pb-2 text-gray-300 hover:text-white transition-colors duration-200 ${selectedTab === "官方镜像" ? "border-b-2 border-purple-500 text-purple-400" : ""}`}
                onClick={() => setSelectedTab("官方镜像")}
              >
                官方镜像
              </button>
            </div>
          </div>
        </div>

        {/* Images List */}
        {selectedTab === "我的镜像" ? renderUserImages() : renderOfficialImages()}
      </div>
      
      {/* Add global styles for dark modal */}
      <style>{`
        .custom-dark-modal .ant-modal-content {
          background-color: rgba(30, 41, 59, 0.95);
          backdrop-filter: blur(8px);
          border: 1px solid rgba(51, 65, 85, 0.5);
          border-radius: 0.75rem;
        }
        .custom-dark-modal .ant-modal-header {
          background-color: transparent;
          border-bottom: 1px solid rgba(51, 65, 85, 0.5);
        }
        .custom-dark-modal .ant-modal-title {
          color: white;
        }
        .custom-dark-modal .ant-modal-close {
          color: rgba(148, 163, 184, 0.8);
        }
        .custom-dark-modal .ant-modal-close:hover {
          color: white;
        }
        .custom-dark-modal .ant-btn-primary {
          color: white !important;
        }
        .custom-dark-modal .ant-btn-default {
          color: rgb(209, 213, 219) !important;
          border-color: rgba(71, 85, 105, 0.5) !important;
          background-color: rgba(51, 65, 85, 0.5) !important;
        }
        .custom-dark-modal .ant-btn-default:hover {
          color: white !important;
          border-color: rgba(59, 130, 246, 0.5) !important;
          background-color: rgba(71, 85, 105, 0.5) !important;
        }
        /* 确保所有输入框文字颜色 */
        .custom-dark-modal input, 
        .custom-dark-modal textarea, 
        .custom-dark-modal select {
          color: rgb(209, 213, 219) !important;
          background-color: rgba(51, 65, 85, 0.5) !important;
        }
        .custom-dark-modal input::placeholder, 
        .custom-dark-modal textarea::placeholder {
          color: rgba(148, 163, 184, 0.6) !important;
        }
        .custom-dark-modal input:focus, 
        .custom-dark-modal input:hover, 
        .custom-dark-modal input:active,
        .custom-dark-modal textarea:focus,
        .custom-dark-modal textarea:hover,
        .custom-dark-modal textarea:active,
        .custom-dark-modal select:focus,
        .custom-dark-modal select:hover,
        .custom-dark-modal select:active {
          background-color: rgba(51, 65, 85, 0.5) !important;
          border-color: rgba(59, 130, 246, 0.5) !important;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1) !important;
        }
      `}</style>
    </div>
  );
};

export default ImagesPage;
