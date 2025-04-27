import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Search, Plus, Rocket, Loader2, Trash2, MoreVertical, Code, Image, BookOpen, Layers, Edit2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getProjects, deleteProject, updateProject } from '@/services/projects';
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
import { Modal, Form, Input, message } from 'antd';

const ProjectsPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState("我的项目");
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<ProjectResponse | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [projectToEdit, setProjectToEdit] = useState<ProjectResponse | null>(null);
  const [form] = Form.useForm();
  
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
      
      message.success(`项目 "${projectToDelete.name}" 已删除`);
    } catch (error: any) {
      console.error('删除项目失败:', error);
      message.error(error.message || "删除项目失败");
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

  // 打开编辑项目模态框
  const openEditModal = (project: ProjectResponse, e: React.MouseEvent) => {
    e.stopPropagation(); // 阻止事件冒泡，防止点击编辑按钮时跳转到项目详情
    setProjectToEdit(project);
    form.setFieldsValue({
      name: project.name,
      description: project.description || '',
    });
    setEditModalVisible(true);
  };

  // 提交编辑项目
  const handleEditSubmit = async () => {
    if (!projectToEdit) return;
    
    try {
      setEditLoading(true);
      const values = await form.validateFields();
      
      console.log('提交编辑项目数据:', {
        id: projectToEdit.id,
        values: values
      });
      
      const response = await updateProject(projectToEdit.id, {
        name: values.name,
        description: values.description
      });
      
      console.log('更新项目响应:', response);
      
      // 更新本地项目列表
      setProjects(prev => 
        prev.map(p => 
          p.id === projectToEdit.id 
            ? { ...p, name: values.name, description: values.description } 
            : p
        )
      );
      
      message.success("项目信息已成功更新");
      
      setEditModalVisible(false);
      setProjectToEdit(null);
    } catch (error: any) {
      console.error('更新项目失败:', error);
      message.error(error.message || "更新项目信息失败");
    } finally {
      setEditLoading(false);
    }
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

  // 编辑项目模态框
  const renderEditModal = () => {
    return (
      <Modal
        title={<span className="text-white font-medium">编辑项目</span>}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={[
          <Button
            key="cancel"
            onClick={() => setEditModalVisible(false)}
            className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600 mr-4"
          >
            取消
          </Button>,
          <Button
            key="submit"
            onClick={handleEditSubmit}
            className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white border-0"
            disabled={editLoading}
          >
            {editLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                保存中...
              </>
            ) : (
              '保存'
            )}
          </Button>
        ]}
        className="custom-dark-modal"
      >
        <Form
          form={form}
          layout="vertical"
          className="mt-4"
        >
          <Form.Item
            name="name"
            label={<span className="text-gray-300">项目名称</span>}
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input 
              placeholder="请输入项目名称" 
              className="bg-slate-800/50 border-slate-700 text-white" 
            />
          </Form.Item>
          <Form.Item
            name="description"
            label={<span className="text-gray-300">项目描述</span>}
          >
            <Input.TextArea 
              placeholder="请输入项目描述（可选）" 
              className="bg-slate-800/50 border-slate-700 text-white"
              rows={4}
            />
          </Form.Item>
        </Form>
      </Modal>
    );
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

        {/* Quick Create Section (Replaced) */}
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
        {/* End of Quick Create Section */}

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
                    <div className="p-5" onClick={() => {
                      // 对于Canvas类型的项目，跳转到工作流设计页面
                      if (project.project_type === 'canvas') {
                        navigate(`/dashboard/projects/${project.id}/workflow`);
                      } else {
                        // 其他类型项目跳转到常规项目详情页
                        navigate(`/dashboard/projects/${project.id}`);
                      }
                    }}>
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center">
                            {getProjectIcon(project.project_type)}
                          </div>
                          <div>
                            <h3 className="font-semibold text-lg text-white">
                              <span className="mr-2">{project.name}</span>
                              <button 
                                className="text-gray-400 hover:text-amber-400 transition-colors inline-flex items-center opacity-0 group-hover:opacity-100 focus:opacity-100"
                                onClick={(e) => openEditModal(project, e)}
                                title="编辑项目"
                                aria-label="编辑项目"
                              >
                                <Edit2 className="w-3.5 h-3.5" />
                              </button>
                            </h3>
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
                            <DropdownMenuItem onClick={(e) => openEditModal(project, e)}>
                              <Edit2 className="mr-2 h-4 w-4" />
                              编辑项目
                            </DropdownMenuItem>
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
        <AlertDialogContent className="bg-slate-800/75 backdrop-blur-sm border border-slate-700/50 shadow-lg">
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除项目</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-400">
              此操作将永久删除项目 "{projectToDelete?.name}" 及其相关数据和容器。此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting} className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600" autoFocus={false}>取消</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteProject}
              disabled={isDeleting}
              className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white border-0"
              autoFocus={true}
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  删除中...
                </>
              ) : (
                <>
                  <Trash2 className="mr-2 h-4 w-4" />
                  确认删除
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* 编辑项目模态框 */}
      {renderEditModal()}
      
      {/* 添加Dark Modal样式 */}
      <style>{`
        .custom-dark-modal .ant-modal-content {
          background-color: rgba(15, 23, 42, 0.75);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(51, 65, 85, 0.5);
          border-radius: 0.75rem;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
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
        .custom-dark-modal .ant-form-item-label > label {
          color: rgb(209, 213, 219) !important;
        }
        .custom-dark-modal .ant-input,
        .custom-dark-modal .ant-input-affix-wrapper,
        .custom-dark-modal .ant-input-number,
        .custom-dark-modal .ant-input-number-input,
        .custom-dark-modal .ant-select-selector,
        .custom-dark-modal .ant-select-selection-item,
        .custom-dark-modal .ant-input-textarea {
          background-color: rgba(30, 41, 59, 0.5) !important;
          border-color: rgba(51, 65, 85, 0.8) !important;
          color: rgb(237, 242, 247) !important;
        }
        .custom-dark-modal .ant-input::placeholder,
        .custom-dark-modal .ant-input-number-input::placeholder,
        .custom-dark-modal .ant-input-textarea textarea::placeholder {
          color: rgba(148, 163, 184, 0.5) !important;
        }
        .custom-dark-modal .ant-input:hover,
        .custom-dark-modal .ant-input-affix-wrapper:hover,
        .custom-dark-modal .ant-input-number:hover,
        .custom-dark-modal .ant-select-selector:hover,
        .custom-dark-modal .ant-input-textarea:hover {
          border-color: rgba(59, 130, 246, 0.5) !important;
        }
        .custom-dark-modal .ant-input:focus,
        .custom-dark-modal .ant-input-affix-wrapper:focus,
        .custom-dark-modal .ant-input-number:focus,
        .custom-dark-modal .ant-select-selector:focus,
        .custom-dark-modal .ant-input-textarea:focus {
          border-color: rgba(59, 130, 246, 0.8) !important;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
        }
        .custom-dark-modal .ant-form-item-explain-error {
          color: #f56565 !important;
        }

        /* AlertDialog 样式 */
        [role="dialog"][data-state="open"] {
          animation: fadeIn 150ms ease-out;
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        [data-state="open"] > [data-state="open"] {
          animation: zoomIn 150ms ease-out;
        }
        @keyframes zoomIn {
          from { 
            opacity: 0; 
            transform: scale(0.95);
          }
          to { 
            opacity: 1; 
            transform: scale(1);
          }
        }
        
        div[role="alertdialog"] {
          background-color: rgba(15, 23, 42, 0.75) !important;
          backdrop-filter: blur(12px) !important;
          border: 1px solid rgba(51, 65, 85, 0.5) !important;
          border-radius: 0.75rem !important;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3) !important;
          padding: 1.5rem !important;
        }
        
        div[role="alertdialog"] h2 {
          color: white !important;
          font-size: 1.25rem !important;
          margin-bottom: 0.5rem !important;
        }
        
        div[role="alertdialog"] button:first-of-type {
          background-color: rgba(51, 65, 85, 0.5) !important;
          border-color: rgba(71, 85, 105, 0.5) !important;
          color: rgb(209, 213, 219) !important;
          outline: none !important;
        }
        
        div[role="alertdialog"] button:first-of-type:hover {
          background-color: rgba(71, 85, 105, 0.5) !important;
          border-color: rgba(59, 130, 246, 0.5) !important;
          color: white !important;
        }
        
        div[role="alertdialog"] button:first-of-type:focus,
        div[role="alertdialog"] button:first-of-type:focus-visible {
          background-color: rgba(51, 65, 85, 0.5) !important;
          border-color: rgba(71, 85, 105, 0.5) !important;
          outline: none !important;
          box-shadow: none !important;
          color: rgb(209, 213, 219) !important;
        }

        div[role="alertdialog"] button:focus,
        div[role="alertdialog"] button:focus-visible {
          outline: none !important;
          box-shadow: none !important;
        }
        
        div[role="alertdialog"] button:last-of-type {
          background: linear-gradient(to right, #dc2626, #b91c1c) !important;
        }
        
        div[role="alertdialog"] button:last-of-type:hover {
          background: linear-gradient(to right, #ef4444, #dc2626) !important;
        }
      `}</style>
    </div>
  );
};

export default ProjectsPage;
