import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { useNavigate, Link } from 'react-router-dom';
import projectsService from '@/services/projects';
import { Rocket, Loader2, ExternalLink, Plus, Image, BookOpen, Layers } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

const RecentPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<any[]>([]);
  const [images, setImages] = useState<any[]>([]);
  
  // 根据项目类型返回对应的图标
  const getProjectIcon = (projectType: string | undefined) => {
    if (!projectType) return <Rocket className="w-5 h-5 text-indigo-400" />;
    
    switch (projectType.toLowerCase()) {
      case 'notebook':
      case 'jupyter':
      case 'jupyter notebook':
        return <BookOpen className="w-5 h-5 text-green-400" />;
      case 'canvas':
      case 'visual':
      case 'drag':
        return <Layers className="w-5 h-5 text-purple-400" />;
      default:
        return <Rocket className="w-5 h-5 text-indigo-400" />;
    }
  };
  
  // 获取项目类型的显示名称
  const getProjectTypeName = (projectType: string | undefined) => {
    if (!projectType) return '未知类型';
    
    switch (projectType.toLowerCase()) {
      case 'notebook':
      case 'jupyter':
      case 'jupyter notebook':
        return 'Jupyter Notebook';
      case 'canvas':
      case 'visual':
      case 'drag':
        return '可视化拖拽编程';
      default:
        return projectType;
    }
  };

  // 格式化相对时间（如：2小时前）
  const formatRelativeTime = (dateString: string): string => {
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true, locale: zhCN });
    } catch (e) {
      return '未知时间';
    }
  };

  // 获取最近项目和镜像数据
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // 获取项目列表
        const projectsResponse = await projectsService.getProjects();
        
        if (projectsResponse && projectsResponse.data) {
          // 确保results字段存在，如果不存在，使用data本身
          const projectsData = Array.isArray(projectsResponse.data.results) 
              ? projectsResponse.data.results 
              : projectsResponse.data.results === undefined 
              ? (Array.isArray(projectsResponse.data) ? projectsResponse.data : [])
              : [];
              
          // 按更新时间排序并只取最近的3个
          const sortedProjects = [...projectsData]
            .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
            .slice(0, 3);
          setProjects(sortedProjects);
        } else {
          console.warn('项目响应数据格式不符合预期:', projectsResponse);
          setProjects([]);
        }
        
        // 使用imagesService直接获取镜像
        try {
          const { imagesService } = await import('@/services/images');
          const imagesResponse = await imagesService.getUserImages();
          
          if (imagesResponse.status === 'success' && imagesResponse.data) {
            // 确保数据是数组格式
            const imagesData = Array.isArray(imagesResponse.data) ? imagesResponse.data : [imagesResponse.data];
            
            // 排序并限制数量
            const sortedImages = [...imagesData]
              .sort((a, b) => {
                try {
                  const dateA = new Date(a.created || 0);
                  const dateB = new Date(b.created || 0);
                  return dateB.getTime() - dateA.getTime();
                } catch (error: any) {
                  return 0;
                }
              })
              .slice(0, 2);
              
            setImages(sortedImages);
          } else {
            console.warn('镜像响应数据格式不符合预期:', imagesResponse);
            setImages([]);
          }
        } catch (error: any) {
          console.error('获取镜像列表失败:', error);
          setImages([]);
        }
      } catch (error: any) {
        console.error('获取项目数据失败:', error);
        setProjects([]);
        setImages([]);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex-1 overflow-y-auto">
        {/* 快速创建 */}
        <div className="mb-8">
          <h2 className="text-xl font-bold mb-4 text-white">快速创建</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Link to="/dashboard/projects/create-notebook" className="block">
              <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-green-500/30 transition-all duration-300 hover:shadow-md hover:shadow-green-500/5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-white">新建 Notebook</h3>
                </div>
              </div>
            </Link>
            <Link to="/dashboard/projects/create-canvas" className="block">
              <div className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-purple-500/30 transition-all duration-300 hover:shadow-md hover:shadow-purple-500/5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-purple-500/10 flex items-center justify-center">
                  <Layers className="w-5 h-5 text-purple-400" />
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
            <h2 className="text-xl font-bold text-white">最近的项目</h2>
            <Link to="/dashboard/projects" className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-sm">
              查看全部 <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {loading ? (
              <div className="col-span-3 flex justify-center py-8">
                <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
              </div>
            ) : projects.length === 0 ? (
              <div className="col-span-3 bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 text-center py-8">
                <p className="text-gray-400">暂无项目，开始创建您的第一个项目吧！</p>
                <Button 
                  className="mt-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 text-white"
                  onClick={() => navigate('/dashboard/projects/create')}
                >
                  创建项目
                </Button>
              </div>
            ) : (
              projects.map((project) => (
                <div 
                  key={project.id} 
                  className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5 cursor-pointer"
                  onClick={() => navigate(`/dashboard/projects/${project.id}`)}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center">
                      {getProjectIcon(project.project_type)}
                    </div>
                    <div>
                      <h3 className="font-medium text-white">{project.name}</h3>
                      <p className="text-gray-400 text-sm line-clamp-2 mt-1">{project.description || '无描述'}</p>
                      <div className="flex items-center gap-2 mt-2">
                        <span className="px-2 py-0.5 text-xs rounded-full bg-slate-700/70 text-gray-300">
                          {getProjectTypeName(project.project_type)}
                        </span>
                        <span className="text-gray-400 text-xs">
                          更新于: {formatRelativeTime(project.updated_at)}
                        </span>
                      </div>
                      {project.image_details && (
                        <div className="flex items-center gap-1.5 mt-1.5">
                          <Image className="w-3.5 h-3.5 text-blue-400" />
                          <span className="text-xs text-gray-400">
                            镜像: {project.image_details.name}
                            {project.image_details.pythonVersion && ` (Python ${project.image_details.pythonVersion})`}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="mt-4 flex justify-end">
                    <Button 
                      size="sm" 
                      className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 text-white"
                      onClick={(e) => {
                        e.stopPropagation(); // 阻止事件冒泡
                        // 跳转到项目详情页面
                        navigate(`/dashboard/projects/${project.id}`);
                      }}
                    >
                      运行
                    </Button>
                  </div>
                </div>
              ))
            )}
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
            {loading ? (
              <div className="col-span-2 flex justify-center py-8">
                <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
              </div>
            ) : images.length === 0 ? (
              <div className="col-span-2 bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 text-center py-8">
                <p className="text-gray-400">暂无镜像，开始创建您的第一个镜像吧！</p>
                <Button 
                  className="mt-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 text-white"
                  onClick={() => navigate('/dashboard/images/create')}
                >
                  创建镜像
                </Button>
              </div>
            ) : (
              <>
                {images.map((image) => (
                  <div key={image.id} className="bg-slate-800/30 backdrop-blur-sm p-5 rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="font-medium text-white mb-2">{image.name}</h3>
                        <p className="text-gray-400 text-sm mb-3">{image.description || '无描述'}</p>
                        
                        {/* 详细信息区域 */}
                        <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/50 mb-3">
                          <div className="grid grid-cols-2 gap-2">
                            <div className="flex items-center gap-2">
                              <div className="w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center">
                                <span className="text-xs text-blue-400">Py</span>
                              </div>
                              <span className="text-sm text-gray-300 bg-blue-500/10 px-2 py-0.5 rounded-full border border-blue-500/30">
                                Python {image.pythonVersion || image.python_version || '未指定'}
                              </span>
                            </div>
                            
                            {/* PyTorch版本信息 */}
                            {image.pytorch_version && (
                              <div className="flex items-center gap-2">
                                <div className="w-5 h-5 rounded-full bg-orange-500/20 flex items-center justify-center">
                                  <span className="text-xs text-orange-400">Pt</span>
                                </div>
                                <span className="text-sm text-gray-300 bg-orange-500/10 px-2 py-0.5 rounded-full border border-orange-500/30">
                                  PyTorch {image.pytorch_version}
                                </span>
                              </div>
                            )}
                            
                            {/* CUDA版本信息 */}
                            {image.cuda_version && (
                              <div className="flex items-center gap-2">
                                <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center">
                                  <span className="text-xs text-green-400">Cu</span>
                                </div>
                                <span className="text-sm text-gray-300 bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/30">
                                  CUDA {image.cuda_version}
                                </span>
                              </div>
                            )}
                            
                            <div className="flex items-center gap-2">
                              <div className="w-5 h-5 rounded-full bg-purple-500/20 flex items-center justify-center">
                                <span className="text-xs text-purple-400">创</span>
                              </div>
                              <span className="text-sm text-gray-300">
                                创建于 {formatRelativeTime(image.created)}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* 显示包信息（如果有的话） */}
                        {image.packages && (
                          <div className="mt-2">
                            <h4 className="text-sm text-gray-300 mb-1">包含的工具包:</h4>
                            <div className="flex flex-wrap gap-1.5">
                              {image.packages.split(',').map((pkg: string, index: number) => (
                                <span key={index} className="text-xs px-2 py-0.5 bg-indigo-500/10 text-indigo-300 rounded border border-indigo-500/20">
                                  {pkg.trim()}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                      
                      {/* 状态指示器 */}
                      {image.status && (
                        <div>
                          <span className={`text-sm px-2 py-1 rounded-full 
                            ${image.status === 'ready' ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 
                              image.status === 'building' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' :
                              image.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                              image.status === 'failed' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                              'bg-gray-500/20 text-gray-400 border border-gray-500/30'}`}>
                            {image.status === 'ready' ? '就绪' : 
                             image.status === 'building' ? '构建中' : 
                             image.status === 'pending' ? '等待中' : 
                             image.status === 'failed' ? '失败' : image.status}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                
                {/* 只保留一个创建新镜像按钮 */}
                {images.length === 1 && (
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
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RecentPage;