import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Plus, Upload, Rocket, Loader2, Trash2, MoreVertical, Code, Image, BookOpen, Layers } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getProjects, deleteProject } from '@/services/projects';
import { ProjectResponse } from '@/services/projects';
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from '@/components/ui/use-toast';

const ProjectsPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState("我的项目");
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<ProjectResponse | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    const fetchProjects = async () => {
      setLoading(true);
      try {
        const response = await getProjects();
        if (response && response.status === 'success' && response.data) {
          // 类型转换
          setProjects(response.data as unknown as ProjectResponse[]);
        } else {
          // 如果没有数据，设置为空数组
          setProjects([]);
        }
      } catch (error) {
        console.error('获取项目失败:', error);
        setProjects([]);
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);

  const handleCreateProject = () => {
    navigate('/dashboard/projects/create');
  };

  const handleDeleteProject = async () => {
    if (!projectToDelete) return;
    
    setIsDeleting(true);
    try {
      await deleteProject(projectToDelete.id);
      
      // 从列表中移除已删除的项目
      setProjects(prev => prev.filter(p => p.id !== projectToDelete.id));
      
      toast({
        title: "成功",
        description: `项目 "${projectToDelete.name}" 已删除`,
      });
    } catch (error: any) {
      console.error('删除项目失败:', error);
      toast({
        title: "错误",
        description: error.message || "删除项目失败",
        variant: "destructive",
      });
    } finally {
      setIsDeleting(false);
      setDeleteDialogOpen(false);
      setProjectToDelete(null);
    }
  };

  const openDeleteDialog = (project: ProjectResponse, e: React.MouseEvent) => {
    e.stopPropagation(); // 阻止事件冒泡，防止点击删除按钮时跳转到项目详情
    setProjectToDelete(project);
    setDeleteDialogOpen(true);
  };

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

  const filteredProjects = projects.filter(project => 
    (selectedTab === "我的项目" || (selectedTab === "共享项目" && project.is_public)) &&
    (searchTerm === '' || 
     project.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
     project.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

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
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <Button 
            className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-gray-100 px-4 py-2 rounded-lg shadow-md shadow-blue-900/20 border-0 transition-all duration-200 flex items-center"
            onClick={handleCreateProject}
          >
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
            <Button 
              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 shadow-md shadow-blue-900/20 text-gray-100 transition-all duration-200"
              onClick={handleCreateProject}
            >
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
        <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl border border-slate-700/50 overflow-hidden">
          <div className="border-b border-slate-700/50 px-6 py-4 flex justify-between items-center">
            <h2 className="text-xl font-semibold">我的项目</h2>
            <div className="flex space-x-2">
              <button
                className={`px-3 py-1 rounded-md transition-colors ${
                  selectedTab === "我的项目" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
                }`}
                onClick={() => setSelectedTab("我的项目")}
              >
                我的项目
              </button>
              <button
                className={`px-3 py-1 rounded-md transition-colors ${
                  selectedTab === "共享项目" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
                }`}
                onClick={() => setSelectedTab("共享项目")}
              >
                共享项目
              </button>
            </div>
          </div>
          
          <div className="p-6">
            {loading ? (
              <div className="text-center py-8 flex items-center justify-center">
                <Loader2 className="w-6 h-6 text-blue-500 animate-spin mr-2" />
                <p className="text-gray-400">加载中...</p>
              </div>
            ) : filteredProjects.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredProjects.map((project) => (
                  <div
                    key={project.id}
                    className="bg-slate-900/40 rounded-lg border border-slate-700/50 hover:border-blue-500/30 overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-blue-900/10 cursor-pointer group"
                  >
                    <div className="p-5" onClick={() => navigate(`/dashboard/projects/${project.id}`)}>
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center">
                            {getProjectIcon(project.project_type)}
                          </div>
                          <div>
                            <h3 className="font-semibold text-lg text-white">{project.name}</h3>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="px-2 py-0.5 text-xs rounded-full bg-slate-700/70 text-gray-300">
                                {getProjectTypeName(project.project_type)}
                              </span>
                              <span className={`px-2 py-0.5 text-xs rounded-full ${
                                project.status === 'running' 
                                  ? 'bg-green-500/20 text-green-400' 
                                  : 'bg-gray-500/20 text-gray-400'
                              }`}>
                                {project.status === 'running' ? '运行中' : '已停止'}
                              </span>
                            </div>
                            {project.image_details && (
                              <div className="flex items-center gap-1 mt-1.5">
                                <Image className="w-3.5 h-3.5 text-blue-400" />
                                <span className="text-xs text-gray-400">
                                  镜像: {project.image_details.name}
                                  {project.image_details.pythonVersion && ` (Python ${project.image_details.pythonVersion})`}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={(e) => openDeleteDialog(project, e)} className="text-red-500 focus:text-red-500">
                              <Trash2 className="mr-2 h-4 w-4" />
                              删除项目
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                      <p className="text-gray-400 text-sm mb-3 line-clamp-2">{project.description || '无描述'}</p>
                      <div className="text-xs text-gray-500">
                        创建于: {new Date(project.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                {searchTerm ? (
                  <p className="text-gray-400 mb-4">没有找到匹配的项目</p>
                ) : (
                  <>
                    <p className="text-gray-400 mb-4">您还没有创建任何项目</p>
                    <Button 
                      onClick={handleCreateProject}
                      className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500"
                    >
                      创建第一个项目
                    </Button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* 删除确认对话框 */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除项目</AlertDialogTitle>
            <AlertDialogDescription>
              此操作将永久删除项目 "{projectToDelete?.name}" 及其相关数据和容器。此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>取消</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteProject}
              disabled={isDeleting}
              className="bg-red-500 hover:bg-red-600 text-white"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  删除中...
                </>
              ) : (
                '确认删除'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default ProjectsPage;
