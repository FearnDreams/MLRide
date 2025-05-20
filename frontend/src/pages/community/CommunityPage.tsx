import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, PlusCircle, User, Info, AlertCircle, ExternalLink, Loader2, Code, BookOpen, Layers, Rocket } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getProjects, ProjectResponse } from '@/services/projects'; // Assuming ProjectResponse is exported
// import { cloneProject } from '@/services/projects'; // This function will be needed later
import { message, Spin, Empty, Tooltip, Card, Modal } from 'antd';
import _ from 'lodash';

const CommunityPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [allProjects, setAllProjects] = useState<ProjectResponse[]>([]);
  const [communityProjects, setCommunityProjects] = useState<ProjectResponse[]>([]);
  const [filteredCommunityProjects, setFilteredCommunityProjects] = useState<ProjectResponse[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [addingProjectId, setAddingProjectId] = useState<number | null>(null);

  const fetchCommunityProjects = async () => {
    setLoading(true);
    try {
      const response = await getProjects(); // Get all projects
      if (response && response.status === 'success' && Array.isArray(response.data)) {
        const allProjs = response.data as ProjectResponse[];
        setAllProjects(allProjs);
        const publicProjects = allProjs.filter(p => p.is_public);
        setCommunityProjects(publicProjects);
        setFilteredCommunityProjects(publicProjects); // Initialize filter with all public projects
      } else {
        message.error(response.message || '获取社区项目失败');
        setCommunityProjects([]);
        setFilteredCommunityProjects([]);
      }
    } catch (error: any) {
      console.error('获取社区项目失败:', error);
      message.error(error.message || '获取社区项目失败，请重试');
      setCommunityProjects([]);
      setFilteredCommunityProjects([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCommunityProjects();
  }, []);

  // Debounced search
  const debouncedSearch = React.useCallback(
    _.debounce((term: string, projectsToFilter: ProjectResponse[]) => {
      if (!term) {
        setFilteredCommunityProjects(projectsToFilter);
        return;
      }
      const lowerCaseTerm = term.toLowerCase();
      const filtered = projectsToFilter.filter(project => 
        project.name.toLowerCase().includes(lowerCaseTerm) ||
        (project.description && project.description.toLowerCase().includes(lowerCaseTerm)) ||
        (project.username && project.username.toLowerCase().includes(lowerCaseTerm)) // Search by creator username
      );
      setFilteredCommunityProjects(filtered);
    }, 300),
    [] 
  );

  useEffect(() => {
    debouncedSearch(searchTerm, communityProjects);
  }, [searchTerm, communityProjects, debouncedSearch]);

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  };

  const handleAddProject = async (project: ProjectResponse) => {
    setAddingProjectId(project.id);
    message.loading({ content: `正在添加 "${project.name}" 到我的项目...`, key: 'addProject' });
    try {
      // Simulate API call for cloning project
      // const response = await cloneProject(project.id); // Replace with actual API call
      // For now, simulate success after a delay
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Simulate a successful response
      const response = { status: 'success', message: '项目已成功添加到您的列表！' };

      if (response.status === 'success') {
        message.success({ content: response.message || `项目 "${project.name}" 已成功添加！`, key: 'addProject', duration: 3 });
        // Optionally, you could update the UI to show it's added, or navigate to projects page
        // For now, just a message.
      } else {
        message.error({ content: response.message || '添加到项目失败', key: 'addProject', duration: 3 });
      }
    } catch (error: any) {
      console.error('添加到项目失败:', error);
      message.error({ content: error.message || '添加到项目失败，请重试', key: 'addProject', duration: 3 });
    } finally {
      setAddingProjectId(null);
    }
  };

  // 根据项目类型返回对应的图标 (copied from ProjectsPage for consistency)
  const getProjectIcon = (projectType: string | undefined) => {
    if (!projectType) return <Rocket className="w-6 h-6 text-indigo-400" />;
    switch (projectType.toLowerCase()) {
      case 'ide':
        return <Code className="w-6 h-6 text-blue-400" />;
      case 'notebook':
      case 'jupyter':
      case 'jupyter notebook':
        return <BookOpen className="w-6 h-6 text-green-400" />;
      case 'canvas':
      case 'visual':
      case 'drag':
        return <Layers className="w-6 h-6 text-purple-400" />;
      default:
        return <Rocket className="w-6 h-6 text-indigo-400" />;
    }
  };
  
  // 获取项目类型的显示名称 (copied from ProjectsPage for consistency)
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
        return '可视化画布';
      default:
        return projectType;
    }
  };


  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Spin size="large" tip="加载社区资源中..." />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">社区资源</h1>
        <div className="relative flex-1 max-w-md ml-4">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="搜索项目名、描述或创建者"
            className="w-full pl-10 pr-4 py-2.5 bg-slate-800/70 border border-slate-700 rounded-lg text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
            value={searchTerm}
            onChange={handleSearchChange}
          />
        </div>
      </div>

      {filteredCommunityProjects.length === 0 && !loading ? (
        <Empty
          image={<AlertCircle className="w-16 h-16 text-slate-500 mx-auto" />}
          description={
            <div className="text-center">
              <p className="text-gray-400 text-lg mb-2">
                {searchTerm ? '未找到匹配的社区项目' : '暂无共享项目'}
              </p>
              <p className="text-gray-500 text-sm">
                {searchTerm ? '尝试调整您的搜索关键词。' : '当前还没有用户共享项目，敬请期待！'}
              </p>
            </div>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCommunityProjects.map((project) => (
            <Card 
              key={project.id} 
              className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/60 rounded-xl shadow-lg hover:shadow-blue-500/10 hover:border-blue-500/50 transition-all duration-300 flex flex-col justify-between"
            >
              <div className="p-5">
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-slate-700/50 flex items-center justify-center shrink-0">
                      {getProjectIcon(project.project_type)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg text-white truncate" title={project.name}>
                        {project.name}
                      </h3>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-gray-300">
                        {getProjectTypeName(project.project_type)}
                      </span>
                    </div>
                  </div>
                  {/* Future: Add more actions like view details if needed */}
                </div>
                <p className="text-gray-400 text-sm mb-3 line-clamp-2 h-10" title={project.description}>
                  {project.description || '暂无描述'}
                </p>
                <div className="text-xs text-gray-500 mb-1">
                  <Tooltip title={`创建者: ${project.username}`}>
                    <span className="flex items-center">
                      <User className="w-3.5 h-3.5 mr-1.5 text-sky-400" />
                      贡献者: {project.username}
                    </span>
                  </Tooltip>
                </div>
                <div className="text-xs text-gray-500">
                  共享于: {new Date(project.created_at).toLocaleDateString()}
                </div>
              </div>
              <div className="border-t border-slate-700/50 mt-auto p-4">
                <Button
                  className="w-full bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 text-white flex items-center justify-center gap-2 transition-all"
                  onClick={() => handleAddProject(project)}
                  disabled={addingProjectId === project.id}
                >
                  {addingProjectId === project.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <PlusCircle className="w-4 h-4" />
                  )}
                  {addingProjectId === project.id ? '添加中...' : '添加到我的项目'}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
      <style>{`
        .ant-tooltip-inner {
          background-color: #1e293b !important; /* slate-800 */
          color: #cbd5e1 !important; /* slate-300 */
        }
        .ant-tooltip-arrow-content {
          background-color: #1e293b !important;
        }
      `}</style>
    </div>
  );
};

export default CommunityPage; 