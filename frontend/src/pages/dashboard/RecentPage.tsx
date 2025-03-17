import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { useNavigate, Link } from 'react-router-dom';
import projectsService from '@/services/projects';
import { Code, Rocket, Loader2, ExternalLink, Plus, Image, BookOpen, Layers } from 'lucide-react';
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
      case 'ide':
        return <Code className="w-5 h-5 text-blue-400" />;
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
      case 'ide':
        return 'IDE开发环境';
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
                        if (project.status === 'running') {
                          window.open(`/api/jupyter/proxy/${project.id}/lab`);
                        } else {
                          projectsService.startProject(project.id)
                            .then(() => {
                              setTimeout(() => {
                                window.open(`/api/jupyter/proxy/${project.id}/lab`);
                              }, 3000);
                            })
                            .catch(error => {
                              console.error('启动项目失败:', error);
                            });
                        }
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
                  <div key={image.id} className="bg-slate-800/30 backdrop-blur-sm p-6 rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center">
                        <Image className="w-5 h-5 text-blue-400" />
                      </div>
                      <div>
                        <h3 className="font-medium text-white">{image.name}</h3>
                        <p className="text-gray-400 text-sm line-clamp-2">{image.description || '无描述'}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="px-2 py-0.5 text-xs rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
                            Python {(image as any).pythonVersion || image.python_version || '未指定'}
                          </span>
                          <p className="text-gray-500 text-xs">
                            创建于: {formatRelativeTime(image.created)}
                          </p>
                        </div>
                      </div>
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