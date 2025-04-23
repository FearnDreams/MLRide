import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, Square, RefreshCw, Settings, Cpu, HardDrive, Zap, BookOpen, Trash2, Loader2, Image, Edit2, Save, GitBranch, RotateCcw, ExternalLink, Clock, FileText, GitCompare, ChevronDown, ChevronUp, ChevronRight, Eye, EyeOff, AlertCircle, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getProject, startProject, stopProject, getProjectStats, deleteProject, updateProject, createProjectSnapshot, getProjectSnapshots, restoreProjectSnapshot, getProjectSnapshot, getSnapshotFileContent, deleteProjectSnapshot } from '@/services/projects';
import services from '@/services/projects';
import { ProjectResponse, CreateProjectRequest } from '@/services/projects';
import { getJupyterSession, startJupyterSession, stopJupyterSession } from '@/services/jupyter';
import type { JupyterSession } from '@/types/jupyter';
import JupyterNotebook from '@/components/jupyter/JupyterNotebook';
import { useToast } from '@/components/ui/use-toast';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Modal, Form, Input, message, Table, Tooltip, Badge, Popconfirm, Select, Tabs, Spin, Empty } from 'antd';
import { formatDistance } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { Diff, Hunk, parseDiff } from 'react-diff-view';
import 'react-diff-view/style/index.css';

// 版本信息接口
interface SnapshotInfo {
  id: string;
  version: string;
  description: string;
  created_at: string;
  created_by: string;
  file_count?: number;
}

// 快照详细信息接口
interface SnapshotDetail {
  id: string;
  version: string;
  description: string;
  files: string[];
  created_at: string;
  created_by: string;
}

// 简单的文件差异比较结果
interface FileDiff {
  oldPath: string;
  newPath: string;
  hunks: any[];
  type: string;
}

// 文件内容接口
interface FileContent {
  file_path: string;
  content: string;
  file_type: string;
}

// 替换原有的formatJsonContent函数为更强大的版本
const formatJsonContent = (content: string, filePath: string, indent: number = 2): string => {
  try {
    // 判断是否为空内容
    if (!content || content.trim() === '') {
      return '';
    }
    
    const parsedJson = JSON.parse(content);
    
    // 特殊处理ipynb文件
    if (filePath.toLowerCase().endsWith('.ipynb')) {
      return formatJupyterNotebook(parsedJson);
    }
    
    // 标准JSON格式化，增加更多空间使结构更清晰
    return JSON.stringify(parsedJson, null, indent);
  } catch (e) {
    console.error(`格式化JSON失败: ${e}`);
    // 如果解析失败，返回原始内容
    return content;
  }
};

// 专门处理Jupyter Notebook文件的函数
const formatJupyterNotebook = (notebook: any): string => {
  try {
    // 创建一个简化版本的notebook对象
    const simplifiedNotebook: any = {};
    
    // 保留基本元数据
    if (notebook.metadata) {
      simplifiedNotebook.metadata = notebook.metadata;
    }
    
    // 处理kernelspec信息
    if (notebook.metadata?.kernelspec) {
      simplifiedNotebook.kernelspec = notebook.metadata.kernelspec;
    }
    
    // 处理cells
    if (notebook.cells && Array.isArray(notebook.cells)) {
      simplifiedNotebook.cells = notebook.cells.map((cell: any, index: number) => {
        const simplifiedCell: any = {
          cell_number: index + 1,
          cell_type: cell.cell_type
        };
        
        // 处理源代码
        if (cell.source) {
          if (Array.isArray(cell.source)) {
            simplifiedCell.source = cell.source.join('');
          } else {
            simplifiedCell.source = cell.source;
          }
        }
        
        // 处理输出内容
        if (cell.outputs && Array.isArray(cell.outputs) && cell.outputs.length > 0) {
          simplifiedCell.outputs = cell.outputs.map((output: any) => {
            const simplifiedOutput: any = {
              output_type: output.output_type
            };
            
            // 处理文本输出
            if (output.text) {
              if (Array.isArray(output.text)) {
                simplifiedOutput.text = output.text.join('');
              } else {
                simplifiedOutput.text = output.text;
              }
            }
            
            // 处理执行结果
            if (output.data) {
              simplifiedOutput.data_types = Object.keys(output.data);
              
              // 处理文本/html结果
              if (output.data['text/plain']) {
                simplifiedOutput.text_plain = Array.isArray(output.data['text/plain']) 
                  ? output.data['text/plain'].join('') 
                  : output.data['text/plain'];
              }
            }
            
            return simplifiedOutput;
          });
        }
        
        // 处理元数据
        if (cell.metadata && Object.keys(cell.metadata).length > 0) {
          simplifiedCell.has_metadata = true;
        }
        
        // 处理执行计数
        if (cell.execution_count !== null && cell.execution_count !== undefined) {
          simplifiedCell.execution_count = cell.execution_count;
        }
        
        return simplifiedCell;
      });
    }
    
    // 保持阅读格式良好
    return JSON.stringify(simplifiedNotebook, null, 2);
  } catch (e) {
    console.error(`格式化Jupyter笔记本失败: ${e}`);
    // 如果处理失败，回退到标准JSON格式化
    return JSON.stringify(notebook, null, 2);
  }
};

// 修改原有的isJsonFile函数，增强检测能力
const isJsonFile = (filePath: string, content: string): boolean => {
  // 通过扩展名判断
  const jsonExtensions = ['.json', '.ipynb', '.config'];
  
  // 先检查扩展名
  const ext = filePath.substring(filePath.lastIndexOf('.')).toLowerCase();
  if (jsonExtensions.includes(ext)) {
    return true;
  }
  
  // 若没有匹配的扩展名，尝试解析内容
  try {
    const trimmed = content.trim();
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || 
        (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      // 尝试解析
      JSON.parse(trimmed);
      return true;
    }
  } catch (e) {
    // 解析失败，不是JSON
  }
  
  return false;
};

// 检查是否为需要忽略比较的文件或文件夹
const isIgnoredFile = (filePath: string): boolean => {
  // 转换为标准格式的路径以便更准确地匹配
  const normalizedPath = filePath.replace(/\\/g, '/');
  
  // 忽略.log文件
  if (normalizedPath.toLowerCase().endsWith('.log')) {
    return true;
  }
  
  // 忽略.ipynb_checkpoints文件夹中的内容 - 更精确的匹配
  if (normalizedPath.includes('/.ipynb_checkpoints/') || 
      normalizedPath.endsWith('/.ipynb_checkpoints') ||
      normalizedPath.includes('.ipynb_checkpoints')) {
    return true;
  }
  
  // 忽略.jupyter文件夹中的内容 - 更全面的匹配
  if (normalizedPath.includes('/.jupyter/') || 
      normalizedPath.endsWith('/.jupyter') ||
      normalizedPath.startsWith('.jupyter/') ||
      normalizedPath === '.jupyter' ||
      (/[\/\\]\.jupyter([\/\\]|$)/).test(normalizedPath)) {
    console.log(`忽略.jupyter文件夹内容: ${normalizedPath}`);
    return true;
  }
  
  // 忽略所有snapshots文件夹的内容
  if (normalizedPath.includes('/snapshots/') || 
      normalizedPath.endsWith('/snapshots') ||
      normalizedPath.startsWith('snapshots/') ||
      normalizedPath === 'snapshots' ||
      (/[\/\\]snapshots([\/\\]|$)/).test(normalizedPath)) {
    console.log(`忽略snapshots文件夹内容: ${normalizedPath}`);
    return true;
  }
  
  // 忽略.Trash相关文件夹中的内容（包括.Trash-0等变体）
  if (normalizedPath.includes('/.Trash') || 
      normalizedPath.match(/\.Trash-\d+/) ||
      normalizedPath.startsWith('.Trash')) {
    return true;
  }
  
  return false;
};

const ProjectDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [jupyterSession, setJupyterSession] = useState<JupyterSession | null>(null);
  const [jupyterLoading, setJupyterLoading] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [forceShowJupyter, setForceShowJupyter] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [form] = Form.useForm();
  
  // 版本控制相关状态
  const [snapshots, setSnapshots] = useState<SnapshotInfo[]>([]);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [createSnapshotModalVisible, setCreateSnapshotModalVisible] = useState(false);
  const [createSnapshotLoading, setCreateSnapshotLoading] = useState(false);
  const [createSnapshotForm] = Form.useForm();
  const [restoreLoading, setRestoreLoading] = useState<string | null>(null);
  
  // 版本比较相关状态
  const [compareModalVisible, setCompareModalVisible] = useState(false);
  const [compareForm] = Form.useForm();
  const [compareSourceId, setCompareSourceId] = useState<string | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareResult, setCompareResult] = useState<FileDiff[]>([]);
  const [compareResultModalVisible, setCompareResultModalVisible] = useState(false);
  const [selectedSourceSnapshot, setSelectedSourceSnapshot] = useState<SnapshotDetail | null>(null);
  const [selectedTargetSnapshot, setSelectedTargetSnapshot] = useState<SnapshotDetail | null>(null);
  // 添加当前版本比较状态
  const [compareWithCurrent, setCompareWithCurrent] = useState(false);
  // 添加收起/展开状态管理
  const [collapsedDiffs, setCollapsedDiffs] = useState<Record<string, boolean>>({});
  // 在状态定义中添加新的状态变量
  const [compareWithCurrentAsSource, setCompareWithCurrentAsSource] = useState(false);

  // 修复useEffect依赖问题
  // 添加一个监听源版本和模态框变化的效果
  const [sourceVersionForEffect, setSourceVersionForEffect] = useState<string | null>(null);

  // 在ProjectDetailPage组件中添加删除快照的状态和处理函数
  const [deleteSnapshotLoading, setDeleteSnapshotLoading] = useState<string | null>(null);

  useEffect(() => {
    const fetchProject = async () => {
      if (!id) return;
      
      setLoading(true);
      try {
        const response = await getProject(parseInt(id));
        if (response && response.data) {
          const projectData = response.data as unknown as ProjectResponse;
          setProject(projectData);
          fetchStats();
          // 不要在这里调用fetchJupyterSession，改为在project状态更新后通过下面的useEffect调用
          fetchSnapshots(); // 加载项目版本列表
        }
      } catch (error) {
        console.error('获取项目失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProject();
  }, [id]);

  // 添加新的useEffect，监听project状态变化，确保在project状态更新后调用fetchJupyterSession
  useEffect(() => {
    if (project) {
      fetchJupyterSession();
    }
  }, [project?.status]); // 只在project.status变化时重新获取会话状态

  const fetchJupyterSession = async () => {
    if (!id) return;
    
    // 添加条件检查：只有当项目状态为'running'时才获取Jupyter会话
    if (project?.status !== 'running') {
      // 项目未运行时，直接清空会话状态而不是请求API
      setJupyterSession(null);
      return;
    }
    
    setJupyterLoading(true);
    try {
      // 确保id是纯数字
      const cleanId = id.replace(/[^\d]/g, '');
      console.log('项目ID清理前:', id, '清理后:', cleanId);
      const response = await getJupyterSession(cleanId);
      setJupyterSession(response);
    } catch (error) {
      console.error('获取Jupyter会话失败:', error);
      // 出错时也清空会话状态，确保不会显示旧的会话信息
      setJupyterSession(null);
    } finally {
      setJupyterLoading(false);
    }
  };

  const handleStartJupyter = async () => {
    if (!jupyterSession) return;
    
    setJupyterLoading(true);
    try {
      await startJupyterSession(jupyterSession.id);
      fetchJupyterSession();
    } catch (error) {
      console.error('启动Jupyter失败:', error);
    } finally {
      setJupyterLoading(false);
    }
  };

  const handleStopJupyter = async () => {
    if (!jupyterSession) return;
    
    setJupyterLoading(true);
    try {
      await stopJupyterSession(jupyterSession.id);
      fetchJupyterSession();
    } catch (error) {
      console.error('停止Jupyter失败:', error);
    } finally {
      setJupyterLoading(false);
    }
  };

  const fetchStats = async () => {
    if (!id) return;
    
    setStatusLoading(true);
    try {
      const response = await getProjectStats(parseInt(id));
      if (response && response.data) {
        setStats(response.data);
      }
    } catch (error) {
      console.error('获取资源统计信息失败:', error);
    } finally {
      setStatusLoading(false);
    }
  };

  const handleStartProject = async () => {
    if (!id || !project) return;
    
    setStatusLoading(true);
    try {
      await startProject(parseInt(id));
      const response = await getProject(parseInt(id));
      if (response && response.data) {
        setProject(response.data as unknown as ProjectResponse);
        fetchStats();
        fetchJupyterSession();
      }
    } catch (error) {
      console.error('启动项目失败:', error);
    } finally {
      setStatusLoading(false);
    }
  };

  const handleStopProject = async () => {
    if (!id || !project) return;
    
    setStatusLoading(true);
    try {
      // 尝试停止项目，如果失败可能需要重试
      const stopProjectWithRetry = async (retries = 3) => {
        try {
          // 尝试停止项目
          await stopProject(parseInt(id));
          
          // 停止成功后获取更新的项目状态
          const response = await getProject(parseInt(id));
          if (response && response.data) {
            setProject(response.data as unknown as ProjectResponse);
            // 清除Jupyter会话状态
            setJupyterSession(null);
            return true;
          }
          return false;
        } catch (error) {
          console.error(`停止项目尝试失败 (剩余重试次数: ${retries-1}):`, error);
          if (retries > 1) {
            // 等待一秒后重试
            await new Promise(resolve => setTimeout(resolve, 1000));
            return stopProjectWithRetry(retries - 1);
          }
          throw error;
        }
      };
      
      await stopProjectWithRetry();
      
      message.success('项目已成功停止');
    } catch (error) {
      console.error('停止项目失败:', error);
      message.error('停止项目失败，请稍后重试');
    } finally {
      setStatusLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!project) return;
    
    setIsDeleting(true);
    try {
      await deleteProject(project.id);
      message.success(`项目 "${project.name}" 已成功删除`);
      navigate('/dashboard/projects');
    } catch (error: any) {
      console.error('删除项目失败:', error);
      message.error(error.message || '删除项目时出现错误');
    } finally {
      setIsDeleting(false);
      setDeleteDialogOpen(false);
    }
  };

  // 处理Jupyter会话错误
  const handleJupyterSessionError = () => {
    message.error('Jupyter会话发生错误，请尝试刷新页面或重启Jupyter');
    fetchJupyterSession(); // 重新获取会话状态
  };

  // 打开编辑项目模态框
  const handleOpenEditModal = () => {
    if (!project) return;
    
    form.setFieldsValue({
      name: project.name,
      description: project.description || '',
    });
    setEditModalVisible(true);
  };
  
  // 提交编辑项目
  const handleEditSubmit = async () => {
    if (!project || !id) return;
    
    try {
      setEditLoading(true);
      const values = await form.validateFields();
      
      console.log('提交编辑项目数据:', {
        id: project.id,
        values: values
      });
      
      const response = await updateProject(parseInt(id), {
        name: values.name,
        description: values.description
      });
      
      console.log('更新项目响应:', response);
      
      message.success('项目信息已成功更新');
      
      setEditModalVisible(false);
      
      // 刷新项目数据
      const updatedProject = await getProject(parseInt(id));
      if (updatedProject && updatedProject.data) {
        setProject(updatedProject.data as unknown as ProjectResponse);
      }
    } catch (error: any) {
      console.error('更新项目失败:', error);
      message.error(error.message || '更新项目信息失败');
    } finally {
      setEditLoading(false);
    }
  };

  // 获取项目版本列表
  const fetchSnapshots = async () => {
    if (!id) return;
    
    setSnapshotLoading(true);
    try {
      const response = await getProjectSnapshots(parseInt(id));
      if (response && response.data) {
        setSnapshots(response.data as SnapshotInfo[]);
      }
    } catch (error) {
      console.error('获取项目版本列表失败:', error);
      message.error('获取项目版本列表失败');
    } finally {
      setSnapshotLoading(false);
    }
  };

  // 处理创建版本
  const handleCreateSnapshot = async () => {
    if (!project) return;
    
    try {
      setCreateSnapshotLoading(true);
      const values = await createSnapshotForm.validateFields();
      
      await createProjectSnapshot(project.id, {
        version: values.version,
        description: values.description
      });
      
      message.success('项目版本创建成功');
      setCreateSnapshotModalVisible(false);
      createSnapshotForm.resetFields();
      
      // 刷新版本列表
      fetchSnapshots();
    } catch (error: any) {
      console.error('创建项目版本失败:', error);
      message.error(error.message || '创建项目版本失败');
    } finally {
      setCreateSnapshotLoading(false);
    }
  };

  // 处理恢复版本
  const handleRestoreSnapshot = async (snapshotId: string) => {
    if (!project) return;
    
    setRestoreLoading(snapshotId);
    try {
      await restoreProjectSnapshot(project.id, snapshotId);
      message.success('已成功恢复到选定版本');
      
      // 刷新版本列表
      fetchSnapshots();
    } catch (error: any) {
      console.error('恢复版本失败:', error);
      message.error(error.message || '恢复版本失败');
    } finally {
      setRestoreLoading(null);
    }
  };

  // 处理打开比较版本模态框
  const handleOpenCompareModal = (snapshotId: string) => {
    console.log('打开比较模态框, 源版本ID:', snapshotId);
    console.log('所有可用版本:', snapshots.map(s => `${s.id}:${s.version}`).join(', '));
    
    setCompareSourceId(snapshotId);
    setCompareModalVisible(true);
    setCompareWithCurrent(false); // 重置为不使用当前版本作为目标
    setCompareWithCurrentAsSource(false); // 重置为不使用当前版本作为源
    
    // 初始化表单
    compareForm.setFieldsValue({
      sourceVersion: snapshotId,
      targetVersion: null
    });
  };
  
  // 获取当前项目的文件列表
  const getCurrentProjectFiles = async (): Promise<{files: string[]}> => {
    if (!project) {
      throw new Error('项目不存在');
    }
    
    try {
      console.log('获取当前项目文件列表');
      // 使用新添加的服务函数
      const response = await services.getCurrentProjectFiles(project.id);
      
      if (!response || response.status === 'error') {
        throw new Error(response?.message || '获取当前项目文件列表失败');
      }
      
      return {
        files: response.data?.files || []
      };
    } catch (error: any) {
      console.error('获取当前项目文件列表失败:', error);
      message.error('获取当前项目文件列表失败');
      throw error;
    }
  };
  
  // 处理比较版本
  const handleCompareSnapshots = async () => {
    try {
      setCompareLoading(true);
      const values = await compareForm.validateFields();
      
      if (!project) return;

      let sourceFiles: string[] = [];
      let sourceSnapshot: SnapshotDetail | null = null;
      
      // 处理源版本 - 支持当前版本作为源
      if (compareWithCurrentAsSource) {
        // 当前版本作为源
        try {
          const currentFiles = await getCurrentProjectFiles();
          sourceFiles = currentFiles.files;
          
          // 创建一个虚拟的源快照描述
          sourceSnapshot = {
            id: 'current',
            version: '当前工作区',
            description: '未保存的当前工作区状态',
            files: sourceFiles,
            created_at: new Date().toISOString(),
            created_by: '当前用户'
          };
          
          setSelectedSourceSnapshot(sourceSnapshot);
        } catch (error) {
          console.error('获取当前项目文件失败:', error);
          message.error('获取当前项目文件失败，无法比较');
          return;
        }
      } else {
        // 历史版本作为源
        const sourceId = values.sourceVersion;
        
        if (!sourceId) {
          message.error('请选择源版本');
          return;
        }
        
        // 获取源版本详情
        const sourceResponse = await getProjectSnapshot(project.id, sourceId);
        if (!sourceResponse?.data) {
          message.error('获取源版本详情失败');
          return;
        } else {
          sourceSnapshot = sourceResponse.data as unknown as SnapshotDetail;
          setSelectedSourceSnapshot(sourceSnapshot);
          sourceFiles = sourceSnapshot.files;
        }
      }
      
      let targetFiles: string[] = [];
      let targetSnapshot: SnapshotDetail | null = null;
      
      // 处理目标版本 - 支持当前版本作为目标
      if (compareWithCurrent) {
        // 当前版本作为目标
        try {
          const currentFiles = await getCurrentProjectFiles();
          targetFiles = currentFiles.files;
          
          // 创建一个虚拟的目标快照描述
          targetSnapshot = {
            id: 'current',
            version: '当前工作区',
            description: '未保存的当前工作区状态',
            files: targetFiles,
            created_at: new Date().toISOString(),
            created_by: '当前用户'
          };
          
          setSelectedTargetSnapshot(targetSnapshot);
        } catch (error) {
          console.error('获取当前项目文件失败:', error);
          message.error('获取当前项目文件失败，无法比较');
          return;
        }
      } else {
        // 历史版本作为目标
        const targetId = values.targetVersion;
        
        if (!targetId) {
          message.error('请选择目标版本或选择与当前版本比较');
          return;
        }
        
        // 获取目标版本详情
        const targetResponse = await getProjectSnapshot(project.id, targetId);
        if (!targetResponse?.data) {
          message.error('获取目标版本详情失败');
          return;
        } else {
          targetSnapshot = targetResponse.data as unknown as SnapshotDetail;
          setSelectedTargetSnapshot(targetSnapshot);
          targetFiles = targetSnapshot.files;
        }
      }
      
      console.log('源文件总数（过滤前）:', sourceFiles.length);
      console.log('目标文件总数（过滤前）:', targetFiles.length);
      
      // 清理文件路径，移除可能的末尾斜杠
      const cleanedSourceFiles = sourceFiles
        .map(path => path.replace(/[/\\]+$/, ''))
        .filter(path => {
          const shouldIgnore = isIgnoredFile(path);
          if (shouldIgnore) console.log(`源版本忽略文件: ${path}`);
          return !shouldIgnore;
        });
        
      const cleanedTargetFiles = targetFiles
        .map(path => path.replace(/[/\\]+$/, ''))
        .filter(path => {
          const shouldIgnore = isIgnoredFile(path);
          if (shouldIgnore) console.log(`目标版本忽略文件: ${path}`);
          return !shouldIgnore;
        });
      
      console.log('源文件总数（过滤后）:', cleanedSourceFiles.length);
      console.log('目标文件总数（过滤后）:', cleanedTargetFiles.length);
      
      // 合并所有文件路径
      const allFiles = Array.from(new Set([...cleanedSourceFiles, ...cleanedTargetFiles]));
      
      console.log('比较文件总数:', allFiles.length);
      
      // 用于存储最终的差异结果
      const diffs: FileDiff[] = [];
      
      // 处理每个文件
      for (const filePath of allFiles) {
        console.log(`开始处理文件: ${filePath}`);
        
        // 确保使用正确格式的文件路径
        const cleanFilePath = filePath.replace(/[/\\]+$/, '');
        
        // 检查是否应该忽略文件
        if (isIgnoredFile(cleanFilePath)) {
          console.log(`文件 ${cleanFilePath} 在循环中被忽略，跳过`);
          continue;
        }
        
        // 检查文件在源版本和目标版本中是否存在
        const sourceExists = cleanedSourceFiles.includes(cleanFilePath);
        const targetExists = cleanedTargetFiles.includes(cleanFilePath);
        
        console.log(`文件 ${cleanFilePath} 在源版本中存在: ${sourceExists}, 在目标版本中存在: ${targetExists}`);
        
        // 只处理源版本或目标版本中至少有一个存在该文件的情况
        if (!sourceExists && !targetExists) {
          console.log(`文件 ${cleanFilePath} 在源版本和目标版本中都不存在，跳过`);
          continue;
        }
        
        // 处理文件内容比较
        try {
          // 如果文件在两个版本中都存在，获取文件内容并比较
          if (sourceExists && targetExists) {
            // 获取源版本文件内容
            console.log(`获取源版本文件内容: ${cleanFilePath}`);
            let sourceContent = '';
            let isBinarySource = false;
            let isLargeFileSource = false;
            let isNotebookSource = false;
            
            if (compareWithCurrentAsSource) {
              // 获取当前工作区的文件内容作为源
              try {
                const fileResponse = await services.getCurrentFileContent(project.id, cleanFilePath);
                if (!fileResponse || fileResponse.status === 'error') {
                  throw new Error(fileResponse?.message || '获取当前工作区文件内容失败');
                }
                sourceContent = fileResponse.data?.content || '';
                isBinarySource = fileResponse.data?.is_binary || false;
                isLargeFileSource = fileResponse.data?.is_large_file || false;
                isNotebookSource = fileResponse.data?.is_notebook || false;
              } catch (fileError: any) {
                console.error(`获取当前工作区文件内容失败: ${cleanFilePath}`, fileError);
                throw new Error(`获取当前工作区文件内容失败: ${fileError.message}`);
              }
            } else {
              // 获取历史快照的文件内容作为源
              const sourceId = values.sourceVersion;
              const sourceFileResponse = await getSnapshotFileContent(project.id, sourceId, cleanFilePath);
              sourceContent = sourceFileResponse.data?.content || '';
              isBinarySource = sourceFileResponse.data?.is_binary;
              isLargeFileSource = sourceFileResponse.data?.is_large_file;
              isNotebookSource = sourceFileResponse.data?.is_notebook;
            }
            
            // 获取目标版本文件内容
            let targetContent = '';
            let isBinaryTarget = false;
            let isLargeFileTarget = false;
            let isNotebookTarget = false;
            
            if (compareWithCurrent) {
              // 获取当前工作区的文件内容作为目标
              console.log(`获取当前工作区文件内容: ${cleanFilePath}`);
              try {
                const fileResponse = await services.getCurrentFileContent(project.id, cleanFilePath);
                if (!fileResponse || fileResponse.status === 'error') {
                  throw new Error(fileResponse?.message || '获取当前工作区文件内容失败');
                }
                targetContent = fileResponse.data?.content || '';
                isBinaryTarget = fileResponse.data?.is_binary || false;
                isLargeFileTarget = fileResponse.data?.is_large_file || false;
                isNotebookTarget = fileResponse.data?.is_notebook || false;
              } catch (fileError: any) {
                console.error(`获取当前工作区文件内容失败: ${cleanFilePath}`, fileError);
                throw new Error(`获取当前工作区文件内容失败: ${fileError.message}`);
              }
            } else {
              // 获取历史快照的文件内容作为目标
              console.log(`获取目标版本文件内容: ${cleanFilePath}`);
              const targetFileResponse = await getSnapshotFileContent(project.id, values.targetVersion, cleanFilePath);
              targetContent = targetFileResponse.data?.content || '';
              isBinaryTarget = targetFileResponse.data?.is_binary;
              isLargeFileTarget = targetFileResponse.data?.is_large_file;
              isNotebookTarget = targetFileResponse.data?.is_notebook;
            }
            
            // 检查是否是特殊文件类型
            if (isBinarySource || isBinaryTarget || isLargeFileSource || isLargeFileTarget || isNotebookSource || isNotebookTarget) {
              console.log(`文件 ${cleanFilePath} 是特殊类型文件，使用简化比较`);
              let displayMessage = '';
              
              if (isBinarySource || isBinaryTarget) {
                displayMessage = '二进制文件，无法比较内容差异';
              } else if (isLargeFileSource || isLargeFileTarget) {
                displayMessage = '文件过大，无法比较内容差异';
              } else if (isNotebookSource || isNotebookTarget) {
                displayMessage = 'Jupyter Notebook文件，比较可能不准确';
              }
              
              // 比较文件内容是否完全相同
              const areIdentical = sourceContent === targetContent;
              
              if (areIdentical) {
                console.log(`文件 ${cleanFilePath} 内容完全相同`);
                continue; // 跳过相同内容的文件
              }
              
              diffs.push({
                oldPath: cleanFilePath,
                newPath: cleanFilePath,
                hunks: [{
                  content: `@@ -1,1 +1,1 @@`,
                  oldStart: 1,
                  oldLines: 1,
                  newStart: 1,
                  newLines: 1,
                  changes: [
                    { type: 'normal', content: `${cleanFilePath} (${displayMessage})`, lineNumber: 1 }
                  ]
                }],
                type: 'special'
              });
              continue;
            }
            
            console.log(`文件内容长度 - 源: ${sourceContent.length}, 目标: ${targetContent.length}`);
            
            // 如果内容相同，则跳过
            if (sourceContent === targetContent) {
              console.log(`文件 ${cleanFilePath} 内容相同，跳过`);
              continue;
            }
            
            // 检查文件是否是JSON格式
            const isJson = isJsonFile(cleanFilePath, sourceContent) || isJsonFile(cleanFilePath, targetContent);
            
            // 如果是JSON文件，进行格式化
            let formattedSourceContent = sourceContent;
            let formattedTargetContent = targetContent;
            
            if (isJson) {
              console.log(`检测到JSON文件: ${cleanFilePath}，进行格式化`);
              try {
                formattedSourceContent = formatJsonContent(sourceContent, cleanFilePath);
                formattedTargetContent = formatJsonContent(targetContent, cleanFilePath);
                
                // 记录格式化后的行数，用于调试
                console.log(`格式化后文件行数 - 源: ${formattedSourceContent.split('\n').length}, 目标: ${formattedTargetContent.split('\n').length}`);
              } catch (error) {
                console.error(`格式化JSON内容失败:`, error);
              }
            }
            
            // 使用格式化后的内容进行比较
            const sourceLines = formattedSourceContent.split('\n');
            const targetLines = formattedTargetContent.split('\n');
            
            console.log(`文件行数 - 源: ${sourceLines.length}, 目标: ${targetLines.length}`);
            
            // 简单的行级别差异比较
            const changes: any[] = [];
            const maxLines = Math.max(sourceLines.length, targetLines.length);
            
            // 逐行比较内容
            for (let i = 0; i < maxLines; i++) {
              const sourceLine = i < sourceLines.length ? sourceLines[i] : '';
              const targetLine = i < targetLines.length ? targetLines[i] : '';
              
              if (i >= sourceLines.length) {
                // 新增的行
                changes.push({
                  type: 'insert',
                  content: targetLine,
                  lineNumber: i + 1
                });
              } else if (i >= targetLines.length) {
                // 删除的行
                changes.push({
                  type: 'delete',
                  content: sourceLine,
                  lineNumber: i + 1
                });
              } else if (sourceLine !== targetLine) {
                // 修改的行 - 先删除旧行，再添加新行
                changes.push({
                  type: 'delete',
                  content: sourceLine,
                  lineNumber: i + 1
                });
                changes.push({
                  type: 'insert',
                  content: targetLine,
                  lineNumber: i + 1
                });
              } else {
                // 未变化的行
                changes.push({
                  type: 'normal',
                  content: sourceLine,
                  lineNumber: i + 1
                });
              }
            }
            
            if (changes.length > 0) {
              console.log(`添加修改文件: ${cleanFilePath}, 变更行数: ${changes.length}`);
              diffs.push({
                oldPath: cleanFilePath,
                newPath: cleanFilePath,
                hunks: [{
                  content: `@@ -1,${sourceLines.length} +1,${targetLines.length} @@`,
                  oldStart: 1,
                  oldLines: sourceLines.length,
                  newStart: 1,
                  newLines: targetLines.length,
                  changes
                }],
                type: 'modified'
              });
            }
          } else if (sourceExists) {
            // 文件仅在源版本中存在 - 已被删除
            try {
              // 根据源版本类型获取文件内容
              console.log(`获取被删除文件内容: ${cleanFilePath}`);
              let sourceContent = '';
              
              if (compareWithCurrentAsSource) {
                // 当前工作区作为源版本时，直接从当前工作区获取文件内容
                try {
                  const fileResponse = await services.getCurrentFileContent(project.id, cleanFilePath);
                  if (!fileResponse || fileResponse.status === 'error') {
                    throw new Error(fileResponse?.message || '获取当前工作区文件内容失败');
                  }
                  sourceContent = fileResponse.data?.content || '';
                  
                  // 检查是否是特殊文件类型
                  if (fileResponse.data?.is_binary || fileResponse.data?.is_large_file || fileResponse.data?.is_notebook) {
                    console.log(`删除的文件 ${cleanFilePath} 是特殊类型文件`);
                    diffs.push({
                      oldPath: cleanFilePath,
                      newPath: '/dev/null',
                      hunks: [{
                        content: `@@ -1,1 +0,0 @@`,
                        oldStart: 1,
                        oldLines: 1,
                        newStart: 0,
                        newLines: 0,
                        changes: [
                          { type: 'delete', content: `${cleanFilePath} (特殊类型文件已删除)`, lineNumber: 1 }
                        ]
                      }],
                      type: 'delete'
                    });
                    continue;
                  }
                } catch (fileError: any) {
                  console.error(`获取当前工作区文件内容失败: ${cleanFilePath}`, fileError);
                  throw new Error(`获取当前工作区文件内容失败: ${fileError.message}`);
                }
              } else {
                // 历史版本作为源版本时，从快照获取文件内容
                const sourceId = values.sourceVersion;
                const sourceFileResponse = await getSnapshotFileContent(project.id, sourceId, cleanFilePath);
                sourceContent = sourceFileResponse.data?.content || '';
                
                // 检查是否是特殊文件类型
                if (sourceFileResponse.data?.is_binary || sourceFileResponse.data?.is_large_file || sourceFileResponse.data?.is_notebook) {
                  console.log(`删除的文件 ${cleanFilePath} 是特殊类型文件`);
                  diffs.push({
                    oldPath: cleanFilePath,
                    newPath: '/dev/null',
                    hunks: [{
                      content: `@@ -1,1 +0,0 @@`,
                      oldStart: 1,
                      oldLines: 1,
                      newStart: 0,
                      newLines: 0,
                      changes: [
                        { type: 'delete', content: `${cleanFilePath} (特殊类型文件已删除)`, lineNumber: 1 }
                      ]
                    }],
                    type: 'delete'
                  });
                  continue;
                }
              }
              
              // 检查文件是否是JSON格式并格式化
              let formattedSourceContent = sourceContent;
              if (isJsonFile(cleanFilePath, sourceContent)) {
                console.log(`检测到删除的JSON文件: ${cleanFilePath}，进行格式化`);
                try {
                  formattedSourceContent = formatJsonContent(sourceContent, cleanFilePath);
                  console.log(`格式化后删除文件行数: ${formattedSourceContent.split('\n').length}`);
                } catch (error) {
                  console.error(`格式化JSON内容失败:`, error);
                }
              }
              
              const sourceLines = formattedSourceContent.split('\n');
              
              const changes = sourceLines.map((line: string, index: number) => ({
                type: 'delete',
                content: line,
                lineNumber: index + 1
              }));
              
              console.log(`添加删除文件: ${cleanFilePath}, 行数: ${sourceLines.length}`);
              diffs.push({
                oldPath: cleanFilePath,
                newPath: '/dev/null',
                hunks: [{
                  content: `@@ -1,${sourceLines.length} +0,0 @@`,
                  oldStart: 1,
                  oldLines: sourceLines.length,
                  newStart: 0,
                  newLines: 0,
                  changes
                }],
                type: 'delete'
              });
            } catch (error: any) {
              console.error(`获取删除文件 ${cleanFilePath} 内容失败:`, error);
              
              // 提取错误信息
              let errorMessage = '未知错误';
              if (error.message) {
                errorMessage = error.message;
              } else if (typeof error === 'string') {
                errorMessage = error;
              } else if (error.response?.data?.detail) {
                errorMessage = error.response.data.detail;
              }
              
              diffs.push({
                oldPath: cleanFilePath,
                newPath: '/dev/null',
                hunks: [{
                  content: `@@ -1,1 +0,0 @@`,
                  oldStart: 1,
                  oldLines: 1,
                  newStart: 0,
                  newLines: 0,
                  changes: [
                    { 
                      type: 'delete', 
                      content: `${cleanFilePath} (已删除文件，获取内容失败: ${errorMessage})`, 
                      lineNumber: 1 
                    }
                  ]
                }],
                type: 'delete'
              });
            }
          } else if (targetExists) {
            // 文件仅在目标版本中存在 - 新增
            try {
              // 以下是获取目标文件内容的逻辑
              let targetContent = '';
              let isBinaryTarget = false;
              let isLargeFileTarget = false;
              let isNotebookTarget = false;
              
              if (compareWithCurrent) {
                // 获取当前工作区的文件内容
                console.log(`获取当前工作区新增文件内容: ${cleanFilePath}`);
                try {
                  const fileResponse = await services.getCurrentFileContent(project.id, cleanFilePath);
                  if (!fileResponse || fileResponse.status === 'error') {
                    throw new Error(fileResponse?.message || '获取当前工作区文件内容失败');
                  }
                  targetContent = fileResponse.data?.content || '';
                  isBinaryTarget = fileResponse.data?.is_binary || false;
                  isLargeFileTarget = fileResponse.data?.is_large_file || false;
                  isNotebookTarget = fileResponse.data?.is_notebook || false;
                } catch (fileError: any) {
                  console.error(`获取当前工作区文件内容失败: ${cleanFilePath}`, fileError);
                  throw new Error(`获取当前工作区文件内容失败: ${fileError.message}`);
                }
              } else {
                // 获取目标版本文件内容，以显示新增的内容
                console.log(`获取新增文件内容: ${cleanFilePath}`);
                const targetFileResponse = await getSnapshotFileContent(project.id, values.targetVersion, cleanFilePath);
                targetContent = targetFileResponse.data?.content || '';
                isBinaryTarget = targetFileResponse.data?.is_binary;
                isLargeFileTarget = targetFileResponse.data?.is_large_file;
                isNotebookTarget = targetFileResponse.data?.is_notebook;
              }
              
              // 保持原有的处理逻辑
              // ... existing code ...
              
              // 检查文件是否是特殊文件类型
              if (isBinaryTarget || isLargeFileTarget || isNotebookTarget) {
                console.log(`新增文件 ${cleanFilePath} 是特殊类型文件`);
                diffs.push({
                  oldPath: '/dev/null',
                  newPath: cleanFilePath,
                  hunks: [{
                    content: `@@ -0,0 +1,1 @@`,
                    oldStart: 0,
                    oldLines: 0,
                    newStart: 1,
                    newLines: 1,
                    changes: [
                      { type: 'insert', content: `${cleanFilePath} (特殊类型文件已新增)`, lineNumber: 1 }
                    ]
                  }],
                  type: 'add'
                });
                continue;
              }
              
              // 检查文件是否是JSON格式并格式化
              let formattedTargetContent = targetContent;
              if (isJsonFile(cleanFilePath, targetContent)) {
                console.log(`检测到新增的JSON文件: ${cleanFilePath}，进行格式化`);
                try {
                  formattedTargetContent = formatJsonContent(targetContent, cleanFilePath);
                  console.log(`格式化后新增文件行数: ${formattedTargetContent.split('\n').length}`);
                } catch (error) {
                  console.error(`格式化JSON内容失败:`, error);
                }
              }
              
              const targetLines = formattedTargetContent.split('\n');
              
              const changes = targetLines.map((line: string, index: number) => ({
                type: 'insert',
                content: line,
                lineNumber: index + 1
              }));
              
              console.log(`添加新增文件: ${cleanFilePath}, 行数: ${targetLines.length}`);
              diffs.push({
                oldPath: '/dev/null',
                newPath: cleanFilePath,
                hunks: [{
                  content: `@@ -0,0 +1,${targetLines.length} @@`,
                  oldStart: 0,
                  oldLines: 0,
                  newStart: 1,
                  newLines: targetLines.length,
                  changes
                }],
                type: 'add'
              });
            } catch (error: any) {
              console.error(`处理文件 ${cleanFilePath} 时发生错误:`, error);
              diffs.push({
                oldPath: cleanFilePath,
                newPath: cleanFilePath,
                hunks: [{
                  content: `@@ -1,1 +1,1 @@`,
                  oldStart: 1,
                  oldLines: 1,
                  newStart: 1,
                  newLines: 1,
                  changes: [
                    { type: 'normal', content: `${cleanFilePath} (处理文件时发生错误: ${error.message || '未知错误'})`, lineNumber: 1 }
                  ]
                }],
                type: 'error'
              });
            }
          }
        } catch (error: any) {
          console.error(`处理文件 ${cleanFilePath} 时发生错误:`, error);
          diffs.push({
            oldPath: cleanFilePath,
            newPath: cleanFilePath,
            hunks: [{
              content: `@@ -1,1 +1,1 @@`,
              oldStart: 1,
              oldLines: 1,
              newStart: 1,
              newLines: 1,
              changes: [
                { type: 'normal', content: `${cleanFilePath} (处理文件时发生错误: ${error.message || '未知错误'})`, lineNumber: 1 }
              ]
            }],
            type: 'error'
          });
        }
      }
      
      console.log(`比较结果数量: ${diffs.length}`);
      setCompareResult(diffs);
      setCompareModalVisible(false);
      setCompareResultModalVisible(true);
      
    } catch (error: any) {
      console.error('比较版本失败:', error);
      message.error(error.message || '比较版本失败');
    } finally {
      setCompareLoading(false);
    }
  };
  
  // 切换文件差异的收起/展开状态
  const toggleDiffCollapse = (diffKey: string) => {
    setCollapsedDiffs(prev => ({
      ...prev,
      [diffKey]: !prev[diffKey]
    }));
  };
  
  // 收起所有差异
  const collapseAllDiffs = () => {
    const allCollapsed: Record<string, boolean> = {};
    compareResult.forEach((_, index) => {
      allCollapsed[`diff_${index}`] = true;
    });
    setCollapsedDiffs(allCollapsed);
  };
  
  // 展开所有差异
  const expandAllDiffs = () => {
    const allExpanded: Record<string, boolean> = {};
    compareResult.forEach((_, index) => {
      allExpanded[`diff_${index}`] = false;
    });
    setCollapsedDiffs(allExpanded);
  };
  
  // 渲染版本比较结果模态框
  const renderCompareResultModal = () => {
    // 版本信息展示
    const renderVersionInfo = () => (
      <div className="grid grid-cols-2 gap-6 mb-6">
        <div className="bg-slate-700/30 rounded-lg p-4">
          <h3 className="text-sm font-medium text-blue-400 mb-2">源版本</h3>
          {selectedSourceSnapshot ? (
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-xs text-gray-400">版本号:</span>
                <span className="text-xs text-white">{selectedSourceSnapshot.version}</span>
              </div>
              <div className="flex justify-between mb-1">
                <span className="text-xs text-gray-400">创建时间:</span>
                <span className="text-xs text-white">
                  {new Date(selectedSourceSnapshot.created_at).toLocaleString('zh-CN')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-gray-400">文件数量:</span>
                <span className="text-xs text-white">{selectedSourceSnapshot.files.length}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400">未选择源版本</p>
          )}
        </div>
        
        <div className="bg-slate-700/30 rounded-lg p-4">
          <h3 className="text-sm font-medium text-green-400 mb-2">
            {compareWithCurrent ? "当前工作区" : "目标版本"}
          </h3>
          {selectedTargetSnapshot ? (
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-xs text-gray-400">版本号:</span>
                <span className="text-xs text-white">
                  {compareWithCurrent ? "当前未保存状态" : selectedTargetSnapshot.version}
                </span>
              </div>
              <div className="flex justify-between mb-1">
                <span className="text-xs text-gray-400">创建时间:</span>
                <span className="text-xs text-white">
                  {compareWithCurrent ? 
                    "当前时间" : 
                    new Date(selectedTargetSnapshot.created_at).toLocaleString('zh-CN')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-gray-400">文件数量:</span>
                <span className="text-xs text-white">{selectedTargetSnapshot.files.length}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400">
              {compareWithCurrent ? "无法获取当前工作区信息" : "未选择目标版本"}
            </p>
                )}
              </div>
            </div>
    );
    
    // 文件差异比较
    const renderDiffResult = () => {
      if (compareResult.length === 0) {
        return (
          <div className="flex justify-center items-center h-60 bg-slate-800 rounded-lg">
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={<span className="text-gray-400">没有发现任何差异</span>}
            />
          </div>
        );
      }
      
      return (
        <div className="space-y-6">
          {/* 添加全部收起/展开的控制按钮 */}
          <div className="flex justify-end mb-2 space-x-2">
              <Button 
              onClick={expandAllDiffs}
              className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600 text-xs flex items-center"
              size="sm"
            >
              <ChevronDown className="w-3 h-3 mr-1" />
              展开全部
            </Button>
            <Button 
              onClick={collapseAllDiffs}
              className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600 text-xs flex items-center"
              size="sm"
            >
              <ChevronUp className="w-3 h-3 mr-1" />
              收起全部
            </Button>
          </div>
          
          {compareResult.map((diff, index) => {
            const diffKey = `diff_${index}`;
            const isCollapsed = collapsedDiffs[diffKey] === true;
            
            // 确定文件变更类型的显示样式
            let fileStatusComponent;
            if (diff.type === 'add') {
              fileStatusComponent = <span className="text-green-400 flex items-center"><ChevronRight size={14} className="mr-1" />{diff.newPath} (新增)</span>;
            } else if (diff.type === 'delete') {
              fileStatusComponent = <span className="text-red-400 flex items-center"><ChevronRight size={14} className="mr-1" />{diff.oldPath} (删除)</span>;
            } else if (diff.type === 'special') {
              fileStatusComponent = <span className="text-yellow-400 flex items-center"><AlertCircle size={14} className="mr-1" />{diff.newPath}</span>;
            } else {
              fileStatusComponent = <span className="text-blue-400 flex items-center"><ChevronRight size={14} className="mr-1" />{diff.newPath} (修改)</span>;
            }
            
            // 确定变更行数和大小
            const changeCount = diff.hunks.reduce((total, hunk) => total + hunk.changes.length, 0);
            
            return (
              <div key={index} className="bg-slate-800 rounded-lg overflow-hidden">
                <div 
                  className="flex justify-between items-center p-3 cursor-pointer hover:bg-slate-700/50 transition-colors"
                  onClick={() => toggleDiffCollapse(diffKey)}
                >
                  <div className="flex items-center">
                    <FileText className="w-4 h-4 mr-2 text-blue-400" />
                    <h3 className="text-sm font-medium text-white">
                      {fileStatusComponent}
                    </h3>
                  </div>
                  
                  <div className="flex items-center">
                    {/* 显示变更信息 */}
                    <span className="text-xs text-gray-400 mr-3">
                      {changeCount} 行变更
                    </span>
                    
                    {/* 收起/展开按钮 */}
                    <Button 
                      variant="ghost"
                      size="icon"
                      className="text-gray-400 hover:text-white flex items-center"
                    >
                      {isCollapsed ? (
                        <Eye className="w-4 h-4" />
                      ) : (
                        <EyeOff className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>
                
                {/* 收起状态时隐藏内容 */}
                {!isCollapsed && (
                  <div className="text-xs bg-slate-700/50 custom-diff-wrapper">
                    <Diff
                      viewType="split"
                      diffType={diff.type}
                      hunks={diff.hunks}
                    >
                      {(hunks: any[]) => hunks.map((hunk: any) => <Hunk key={hunk.content} hunk={hunk} />)}
                    </Diff>
                  </div>
                )}
        </div>
      );
          })}
        </div>
      );
    };

        return (
      <Modal
        title={
          <div className="flex items-center text-white">
            <GitCompare className="w-5 h-5 mr-2 text-blue-400" />
            版本比较结果
              </div>
        }
        open={compareResultModalVisible}
        onCancel={() => setCompareResultModalVisible(false)}
        footer={[
          <Button
            key="close"
            onClick={() => setCompareResultModalVisible(false)}
            className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600"
          >
            关闭
          </Button>
        ]}
        width={1000}
        className="custom-dark-modal"
      >
        {renderVersionInfo()}
        
        <div className="mb-4">
          <h3 className="text-sm font-medium text-white mb-2">文件变更</h3>
          <div className="flex space-x-4 text-xs mb-2">
            <span className="flex items-center">
              <Badge color="green" className="mr-1" />
              <span className="text-gray-300">新增</span>
            </span>
            <span className="flex items-center">
              <Badge color="red" className="mr-1" />
              <span className="text-gray-300">删除</span>
            </span>
            <span className="flex items-center">
              <Badge color="blue" className="mr-1" />
              <span className="text-gray-300">修改</span>
            </span>
          </div>
                </div>
                
        {compareLoading ? (
          <div className="flex justify-center items-center h-60">
            <Spin tip="对比中..." />
          </div>
        ) : (
          renderDiffResult()
        )}
        
        <style>{`
          .custom-diff-wrapper .diff-gutter-col {
            background-color: rgba(30, 41, 59, 0.5);
            color: rgba(148, 163, 184, 0.8);
          }
          .custom-diff-wrapper .diff-code-col {
            background-color: rgba(15, 23, 42, 0.5);
          }
          .custom-diff-wrapper .diff-code {
            color: rgb(203, 213, 225);
          }
          .custom-diff-wrapper .diff-gutter {
            padding: 2px 10px;
            border-right: 1px solid rgba(51, 65, 85, 0.8);
          }
          .custom-diff-wrapper .diff-code {
            padding: 2px 10px;
          }
          .custom-diff-wrapper .diff-hunk-header {
            background-color: rgba(30, 41, 59, 0.8);
            color: rgba(148, 163, 184, 0.8);
            border-top: 1px solid rgba(51, 65, 85, 0.8);
            border-bottom: 1px solid rgba(51, 65, 85, 0.8);
          }
          .custom-diff-wrapper .diff-hunk-header-gutter {
            padding: 2px 10px;
          }
          .custom-diff-wrapper .diff-hunk-header-content {
            padding: 2px 10px;
          }
          .custom-diff-wrapper .diff-line-add {
            background-color: rgba(22, 101, 52, 0.3);
          }
          .custom-diff-wrapper .diff-line-add .diff-code {
            background-color: rgba(22, 101, 52, 0.3);
          }
          .custom-diff-wrapper .diff-line-del {
            background-color: rgba(153, 27, 27, 0.3);
          }
          .custom-diff-wrapper .diff-line-del .diff-code {
            background-color: rgba(153, 27, 27, 0.3);
          }
          .custom-diff-wrapper .diff-line-normal {
            background-color: transparent;
          }
        `}</style>
      </Modal>
    );
  };
  
  // 渲染选择比较版本的模态框
  const renderCompareModal = () => {
    return (
      <Modal
        title={
          <div className="flex items-center text-white">
            <GitCompare className="w-5 h-5 mr-2 text-blue-400" />
            比较版本
          </div>
        }
        open={compareModalVisible}
        onCancel={() => setCompareModalVisible(false)}
        footer={
          <div className="flex justify-end space-x-4">
            <Button 
              key="cancel"
              size="sm"
              variant="outline"
              onClick={() => setCompareModalVisible(false)}
            >
              取消
            </Button>
            <Button
              key="submit"
              size="sm"
              onClick={handleCompareSnapshots}
              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white border-0"
              disabled={compareLoading}
            >
              {compareLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  比较中...
                </>
              ) : (
                <>
                  <GitCompare className="mr-2 h-4 w-4" />
                  开始比较
                </>
              )}
            </Button>
          </div>
        }
        className="custom-dark-modal"
      >
        <Form
          form={compareForm}
          layout="vertical"
          className="mt-4"
        >
          <Form.Item
            name="sourceVersion"
            label={<span className="text-gray-300">源版本</span>}
            rules={[{ required: !compareWithCurrentAsSource, message: '请选择源版本或使用当前版本作为源' }]}
          >
            <Select
              placeholder="选择源版本"
              className="custom-dark-select"
              dropdownClassName="custom-dark-select-dropdown" // 应用自定义下拉菜单样式
              disabled={compareWithCurrentAsSource} // 当选择当前版本作为源时禁用
              onChange={(value) => {
                console.log('源版本选择变更为:', value);
                setSourceVersionForEffect(value);
              }}
              options={snapshots.map(snap => ({
                label: `${snap.version} (${formatDistance(new Date(snap.created_at), new Date(), { addSuffix: true, locale: zhCN })})`,
                value: snap.id
              }))}
            />
          </Form.Item>
          
          {/* 将当前工作区作为源版本的选项 */}
          <Form.Item>
            <div className="flex items-center mt-2 mb-4">
              <input 
                type="checkbox" 
                id="compareWithCurrentAsSource"
                checked={compareWithCurrentAsSource}
                onChange={(e) => {
                  setCompareWithCurrentAsSource(e.target.checked);
                  // 不能同时选择当前版本作为源和目标
                  if (e.target.checked && compareWithCurrent) {
                    setCompareWithCurrent(false);
                  }
                  
                  // 更新source version effect
                  if (e.target.checked) {
                    // 如果选择当前工作区作为源，设置一个特殊值
                    setSourceVersionForEffect('current');
                    // 清空表单中的源版本字段
                    compareForm.setFieldsValue({ sourceVersion: null });
                  } else {
                    // 如果取消选择，恢复到表单中的值
                    const formSourceVersion = compareForm.getFieldValue('sourceVersion');
                    setSourceVersionForEffect(formSourceVersion);
                  }
                }}
                className="w-4 h-4 text-blue-600 bg-slate-700 rounded border-slate-600 focus:ring-blue-500"
              />
              <label 
                htmlFor="compareWithCurrentAsSource" 
                className="ml-2 text-sm font-medium text-gray-300 cursor-pointer"
              >
                将当前工作区作为源版本
              </label>
            </div>
          </Form.Item>
          
          <Form.Item
            name="targetVersion"
            label={<span className="text-gray-300">目标版本</span>}
            rules={[
              { required: !compareWithCurrent, message: '请选择目标版本或使用当前版本' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (compareWithCurrent || !value) {
                    return Promise.resolve();
                  }
                  if (!compareWithCurrentAsSource && getFieldValue('sourceVersion') === value) {
                    return Promise.reject(new Error('源版本和目标版本不能相同'));
                  }
                  return Promise.resolve();
                },
              }),
            ]}
          >
            <Select
              placeholder="选择目标版本"
              className="custom-dark-select"
              dropdownClassName="custom-dark-select-dropdown" // 应用自定义下拉菜单样式
              disabled={compareWithCurrent}
              listHeight={300}
              optionFilterProp="label"
              showSearch={true}
              dropdownRender={(menu) => {
                // 获取当前源版本
                const currentSourceId = compareForm.getFieldValue('sourceVersion');
                // 调试信息
                console.log('渲染目标版本下拉列表');
                console.log('- 当前源版本ID:', currentSourceId);
                console.log('- compareWithCurrentAsSource:', compareWithCurrentAsSource);
                console.log('- 所有快照:', snapshots.map(s => `${s.id}:${s.version}`));
                
                return (
                  <>
                    <div style={{ padding: '4px 8px', color: 'white', fontSize: '12px' }}>
                      可用目标版本: {snapshots.filter(s => s.id !== currentSourceId).length} 项
                    </div>
                    {menu}
                  </>
                );
              }}
              options={snapshots
                .filter(snap => {
                  const currentSourceId = compareForm.getFieldValue('sourceVersion');
                  console.log(`检查版本 ${snap.id}:${snap.version} - 是否应该显示:`, snap.id !== currentSourceId);
                  
                  // 如果当前工作区是源，显示所有选项
                  if (compareWithCurrentAsSource) {
                    return true;
                  }
                  
                  // 排除与源版本相同的选项
                  return snap.id !== currentSourceId;
                })
                .map(snap => ({
                  label: `${snap.version} (${formatDistance(new Date(snap.created_at), new Date(), { addSuffix: true, locale: zhCN })})`,
                  value: snap.id
                }))}
            />
          </Form.Item>
          
          {/* 将当前工作区作为目标版本的选项 */}
          <Form.Item>
            <div className="flex items-center mt-2">
              <input 
                type="checkbox" 
                id="compareWithCurrent"
                checked={compareWithCurrent}
                onChange={(e) => {
                  setCompareWithCurrent(e.target.checked);
                  if (e.target.checked) {
                    compareForm.setFieldsValue({ targetVersion: null });
                    // 不能同时选择当前版本作为源和目标
                    if (compareWithCurrentAsSource) {
                      setCompareWithCurrentAsSource(false);
                    }
                  }
                }}
                className="w-4 h-4 text-blue-600 bg-slate-700 rounded border-slate-600 focus:ring-blue-500"
              />
              <label 
                htmlFor="compareWithCurrent" 
                className="ml-2 text-sm font-medium text-gray-300 cursor-pointer"
              >
                将当前工作区作为目标版本
              </label>
              </div>
          </Form.Item>
        </Form>
      </Modal>
        );
  };

  // 渲染基于项目类型的界面
  const renderProjectContent = () => {
    // 检查项目类型是否为 notebook
    if (project?.project_type === 'notebook') {
      // 如果项目状态不是 running，显示项目未运行的提示
      if (project.status !== 'running') {
        return (
          <div className="border border-slate-600 rounded-xl flex items-center justify-center flex-col p-8 bg-slate-800">
            {/* ... 省略未运行时的UI ... */}
            <div className="flex flex-col h-full w-full">
              <div className="bg-slate-800 p-2 flex items-center justify-between border-b border-slate-700">
                <h3 className="text-white font-medium flex items-center">
                  <img 
                    src="/jupyter-logo.svg" 
                    alt="Jupyter" 
                    className="w-5 h-5 mr-2" 
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = "https://jupyter.org/favicon.ico";
                    }} 
                  />
                  Jupyter
                </h3>
              </div>
              
              <div className="flex-grow flex items-center justify-center p-12">
                <div className="text-center max-w-xl w-full">
                  <div className="flex justify-center mb-8">
                    <img 
                      src="/jupyter-logo.svg" 
                      alt="Jupyter" 
                      className="w-20 h-20 opacity-50" 
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = "https://jupyter.org/favicon.ico";
                      }} 
                    />
                  </div>
                  
                  <h2 className="text-2xl font-bold text-white mb-6">Jupyter Notebook 未运行</h2>
                  <p className="text-slate-400 mb-10 px-4">
                    项目容器未运行，请先启动项目以使用Jupyter服务。
                  </p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10 px-6">
                    <div className="bg-slate-700/50 rounded-lg p-5 text-left">
                      <h3 className="text-sm font-medium text-slate-300 mb-3">项目状态</h3>
                      <p className="text-xs text-slate-400 mb-2">
                        状态: 
                        <span className={'text-amber-400 ml-1'}>
                          已停止
                        </span>
                      </p>
                    </div>
                    
                    <div className="bg-slate-700/50 rounded-lg p-5 text-left">
                      <h3 className="text-sm font-medium text-slate-300 mb-3">环境信息</h3>
                      {project?.image_details ? (
                        <>
                          <p className="text-xs text-slate-400 mb-2">Docker镜像: <span className="text-blue-400">{project.image_details.name}</span></p>
                          {project.image_details.pythonVersion && (
                            <p className="text-xs text-slate-400">Python版本: <span className="text-blue-400">{project.image_details.pythonVersion}</span></p>
                          )}
                        </>
                      ) : (
                        <p className="text-xs text-slate-400">镜像信息: <span className="text-amber-400">暂无信息</span></p>
                      )}
                    </div>
                  </div>
                  
                  {/* 添加按钮组 */}
                  <div className="flex justify-center space-x-4">
                    <Button 
                      className="bg-blue-600 hover:bg-blue-700 text-white py-3 px-6 rounded-md flex items-center"
                      // onClick={handleUploadData} // 暂时注释掉，后续实现
                    >
                      <Upload className="w-4 h-4 mr-2" />
                      上传数据
                    </Button>
                    <Button 
                      className="bg-green-600 hover:bg-green-700 text-white py-3 px-6 rounded-md flex items-center"
                      onClick={handleStartProject}
                      disabled={statusLoading}
                    >
                      {statusLoading ? (
                        <>
                          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          启动中...
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4 mr-2" />
                          启动项目
                        </>
                      )}
                    </Button>
                  </div>

                </div>
              </div>
            </div>
          </div>
        );
      } else {
        // 如果项目状态是 running，则直接渲染 JupyterNotebook 组件
        // 让 JupyterNotebook 组件自己处理加载状态和最终显示
        return (
          <div className="border border-slate-600 rounded-xl overflow-hidden bg-slate-800">
            <JupyterNotebook 
              projectId={parseInt(id || '0')}
              onSessionError={handleJupyterSessionError}
            />
          </div>
        );
      }
    } 
    // ... 省略其他项目类型的处理 ...
    else if (project?.project_type === 'canvas') {
      // ... canvas UI ...
      return (
        <div className="border border-slate-600 rounded-xl flex items-center justify-center flex-col p-8 bg-slate-800">
          <Image className="w-16 h-16 text-gray-500 mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">可视化拖拽编程</h3>
          <p className="text-gray-400 text-center mb-4">
            该功能正在开发中，敬请期待。
          </p>
        </div>
      );
    } else {
      // ... 未知类型 UI ...
      return (
        <div className="border border-slate-600 rounded-xl flex items-center justify-center p-8 bg-slate-800">
          <p className="text-gray-400">未知的项目类型: {project?.project_type}</p>
        </div>
      );
    }
  };

  // 项目详细信息部分
  const renderProjectDetails = () => {
    if (!project) return null;
    
    return (
      <div>
        <h2 className="text-lg font-bold mb-4 text-white">项目详情</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">项目类型:</span>
            <span className="text-white font-medium">
              {project.project_type === 'notebook' ? 'Jupyter Notebook' :
               project.project_type === 'canvas' ? '可视化拖拽编程' : 
               project.project_type}
            </span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-400">项目状态:</span>
            <span className="text-white font-medium">
              {project.status === 'running' ? '运行中' :
               project.status === 'stopped' ? '已停止' :
               project.status === 'error' ? '错误' :
               project.status === 'creating' ? '创建中' : project.status}
            </span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-400">资源使用:</span>
            <span className="text-white font-medium">
              {statusLoading ? (
                <span className="text-sm text-gray-400">加载中...</span>
              ) : stats ? (
                <span>{stats.cpu_usage?.toFixed(1)}% CPU | {stats.memory_usage?.toFixed(1)}MB 内存</span>
              ) : (
                <span className="text-sm text-gray-400">项目未运行</span>
              )}
            </span>
          </div>

          {project.image_details && (
            <div className="flex justify-between">
              <span className="text-gray-400">使用镜像:</span>
              <span className="text-white font-medium">
                {project.image_details.name}
                {project.image_details.pythonVersion && ` (Python ${project.image_details.pythonVersion})`}
              </span>
            </div>
          )}
        </div>
      </div>
    );
  };

  // 渲染版本列表
  const renderSnapshotsList = () => {
    // 移除原有的 columns 定义

    return (
      <div className="mt-6 bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center">
            <GitBranch className="w-5 h-5 mr-2 text-blue-400" />
            版本历史
          </h2>
          <Button
            onClick={() => setCreateSnapshotModalVisible(true)}
            className="bg-blue-600 hover:bg-blue-500 text-white"
            size="sm" // 统一按钮大小
          >
            <Save className="w-4 h-4 mr-2" />
            创建版本
          </Button>
        </div>
        
        {snapshotLoading ? (
          <div className="flex justify-center items-center py-8">
            <Spin tip="加载版本历史..." />
          </div>
        ) : snapshots.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={<span className="text-gray-400">暂无版本记录</span>}
          />
        ) : (
          <div className="space-y-3">
            {snapshots.map((record: SnapshotInfo) => (
              <div key={record.id} className="bg-slate-700/30 p-4 rounded-lg border border-slate-600/50 flex justify-between items-center hover:border-blue-500/30 transition-colors duration-200">
                <div className="flex-1 mr-4">
                  <div className="flex items-center mb-1">
                    <span className="font-medium text-white mr-2">{record.version}</span>
                    <Tooltip 
                      title={new Date(record.created_at).toLocaleString('zh-CN')}
                      overlayClassName="custom-dark-tooltip" // 应用自定义样式
                    >
                      <span className="text-xs text-gray-400 flex items-center">
                        <Clock className="w-3 h-3 mr-1" />
                        {formatDistance(new Date(record.created_at), new Date(), {
                          addSuffix: true,
                          locale: zhCN
                        })}
                      </span>
                    </Tooltip>
                  </div>
                  <p className="text-sm text-gray-300">{record.description || '无描述'}</p>
                </div>
                
                {/* 操作按钮区域 */}
                <div className="flex items-center space-x-1">
                  <Tooltip 
                    title="恢复到此版本"
                    overlayClassName="custom-dark-tooltip" // 应用自定义样式
                  >
                    <Popconfirm
                      title={<span className="text-white">恢复版本</span>}
                      description={<span className="text-gray-300">确定要恢复到这个版本吗？当前未保存的更改将丢失。</span>}
                      onConfirm={() => handleRestoreSnapshot(record.id)}
                      okText="确定"
                      cancelText="取消"
                      placement="left"
                      overlayClassName="custom-dark-popconfirm" // 应用自定义样式
                      okButtonProps={{ 
                        className: 'bg-blue-600 hover:bg-blue-500 border-blue-600 text-white', 
                        size: 'small' 
                      }} // 确定按钮样式
                      cancelButtonProps={{ 
                        className: 'custom-popconfirm-cancel-btn', // 添加特定类名
                        size: 'small' 
                      }} // 取消按钮样式
                    >
                      <Button size="icon" variant="ghost" className="text-blue-400 hover:text-blue-300 hover:bg-blue-900/30 w-7 h-7">
                        {restoreLoading === record.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <RotateCcw className="w-4 h-4" />
                        )}
                      </Button>
                    </Popconfirm>
                  </Tooltip>
                  
                  <Tooltip 
                    title="比较此版本"
                    overlayClassName="custom-dark-tooltip" // 应用自定义样式
                  >
                    <Button 
                      size="icon" 
                      variant="ghost" 
                      className="text-purple-400 hover:text-purple-300 hover:bg-purple-900/30 w-7 h-7"
                      onClick={() => handleOpenCompareModal(record.id)}
                    >
                      <GitCompare className="w-4 h-4" />
                    </Button>
                  </Tooltip>
                  
                  <Tooltip 
                    title="删除此版本"
                    overlayClassName="custom-dark-tooltip" // 应用自定义样式
                  >
                    <Popconfirm
                      title={<span className="text-white">删除版本</span>}
                      description={<span className="text-gray-300">确定要删除这个版本吗？此操作不可撤销。</span>}
                      onConfirm={() => handleDeleteSnapshot(record.id)}
                      okText="删除"
                      cancelText="取消"
                      placement="left"
                      overlayClassName="custom-dark-popconfirm" // 应用自定义样式
                      okButtonProps={{ 
                        className: 'bg-red-600 hover:bg-red-500 border-red-600 text-white',
                        size: 'small' 
                      }} // 确定按钮样式 (红色)
                      cancelButtonProps={{ 
                        className: 'custom-popconfirm-cancel-btn', // 添加特定类名
                        size: 'small' 
                      }} // 取消按钮样式
                    >
                      <Button size="icon" variant="ghost" className="text-red-400 hover:text-red-300 hover:bg-red-900/30 w-7 h-7">
                        {deleteSnapshotLoading === record.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </Button>
                    </Popconfirm>
                  </Tooltip>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* 移除原有的 Table 组件 */}
      </div>
    );
  };

  // 编辑项目模态框
  const renderEditModal = () => {
    return (
      <Modal
        title={<span className="text-white font-medium">编辑项目</span>}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={
          <div className="flex justify-end space-x-4">
            <Button
              key="cancel"
              size="sm"
              variant="outline"
              onClick={() => setEditModalVisible(false)}
            >
              取消
            </Button>
            <Button
              key="submit"
              size="sm"
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
                <>
                  <Save className="mr-2 h-4 w-4" />
                  保存
                </>
              )}
            </Button>
          </div>
        }
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

  // 创建版本模态框
  const renderCreateSnapshotModal = () => {
    return (
      <Modal
        title={
          <div className="flex items-center text-white">
            <GitBranch className="w-5 h-5 mr-2 text-blue-400" />
            创建项目版本
          </div>
        }
        open={createSnapshotModalVisible}
        onCancel={() => setCreateSnapshotModalVisible(false)}
        footer={
          <div className="flex justify-end space-x-4">
            <Button
              key="cancel"
              size="sm"
              variant="outline"
              onClick={() => setCreateSnapshotModalVisible(false)}
            >
              取消
            </Button>
            <Button
              key="submit"
              size="sm"
              onClick={handleCreateSnapshot}
              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white border-0"
              disabled={createSnapshotLoading}
            >
              {createSnapshotLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  保存中...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  创建版本
                </>
              )}
            </Button>
          </div>
        }
        className="custom-dark-modal"
      >
        <Form
          form={createSnapshotForm}
          layout="vertical"
          className="mt-4"
        >
          <Form.Item
            name="version"
            label={<span className="text-gray-300">版本号</span>}
            rules={[{ required: true, message: '请输入版本号' }]}
          >
            <Input 
              placeholder="例如: v1.0.0" 
              className="bg-slate-800/50 border-slate-700 text-white" 
            />
          </Form.Item>
          <Form.Item
            name="description"
            label={<span className="text-gray-300">版本描述</span>}
          >
            <Input.TextArea 
              placeholder="描述这个版本的变更内容（可选）" 
              className="bg-slate-800/50 border-slate-700 text-white"
              rows={4}
            />
          </Form.Item>
        </Form>
      </Modal>
    );
  };

  // 在renderProjectDetails后添加版本列表
  const renderProjectDetailsWithVersions = () => {
    return (
      <div className="flex-1 flex flex-col">
        {renderSnapshotsList()}
      </div>
    );
  };

  // 当模态框打开时更新源版本
  useEffect(() => {
    if (compareModalVisible) {
      const currentSourceVersion = compareForm.getFieldValue('sourceVersion');
      setSourceVersionForEffect(currentSourceVersion);
    }
  }, [compareModalVisible]);

  // 当源版本变化时触发此效果
  useEffect(() => {
    if (compareModalVisible && sourceVersionForEffect) {
      console.log('源版本已更改:', sourceVersionForEffect);
      // 当源版本变化时，强制重新渲染目标版本下拉列表
      compareForm.setFieldsValue({ targetVersion: null });
    }
  }, [sourceVersionForEffect, compareModalVisible]);

  // 处理删除快照
  const handleDeleteSnapshot = async (snapshotId: string) => {
    if (!project) return;
    
    try {
      setDeleteSnapshotLoading(snapshotId);
      
      // 调用删除快照API
      await deleteProjectSnapshot(project.id, snapshotId);
      
      // 删除成功后刷新快照列表
      await fetchSnapshots();
      message.success('版本删除成功');
    } catch (error: any) {
      console.error('删除快照失败:', error);
      message.error(error.message || '删除快照失败');
    } finally {
      setDeleteSnapshotLoading(null);
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      {/* 顶部导航栏 */}
      <div className="flex justify-between items-center mb-6 pb-4 border-b border-slate-600">
        <div className="flex items-center">
          <Button
            variant="ghost"
            className="mr-4 text-white hover:bg-slate-700"
            onClick={() => navigate('/dashboard/projects')}
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            返回项目列表
          </Button>
          <div className="flex items-center">
            <div>
              <h1 className="text-2xl font-bold text-white">{project?.name}</h1>
              <p className="text-gray-300">{project?.description || '无项目描述'}</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="ml-2 text-gray-400 hover:text-white hover:bg-slate-700"
              onClick={handleOpenEditModal}
            >
              <Edit2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* 添加创建版本按钮 */}
          <Button 
            variant="outline" 
            className="bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 border-blue-500/50"
            onClick={() => setCreateSnapshotModalVisible(true)}
          >
            <GitBranch className="w-4 h-4 mr-2" />
            创建版本
          </Button>
          
          {/* 添加上传数据按钮 */}
          <Button 
            variant="outline" 
            className="bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 border-teal-500/50"
            // onClick={handleUploadData} // 暂时注释掉，后续实现
          >
            <Upload className="w-4 h-4 mr-2" />
            上传数据
          </Button>
          
          {/* 现有的按钮 */}
          {project?.status === 'running' ? (
            <Button 
              variant="outline" 
              className="bg-red-500/10 hover:bg-red-500/20 text-red-300 border-red-500/50"
              onClick={handleStopProject} // 确保是函数引用
              disabled={statusLoading}
            >
              {statusLoading ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Square className="w-4 h-4 mr-2" />
              )}
              停止项目
            </Button>
          ) : (
            <Button 
              variant="outline" 
              className="bg-green-500/10 hover:bg-green-500/20 text-green-300 border-green-500/50"
              onClick={handleStartProject} // 确保是函数引用
              disabled={statusLoading}
            >
              {statusLoading ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              启动项目
            </Button>
          )}
          
          {/* Jupyter控制按钮 */}
          {project?.status === 'running' && jupyterSession && 
           jupyterSession.status !== 'running' && (
            <Button 
              variant="outline" 
              className="bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border-purple-500/50"
              onClick={handleStartJupyter}
              disabled={jupyterLoading}
            >
              {jupyterLoading ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <BookOpen className="w-4 h-4 mr-2" />
              )}
              启动Jupyter
            </Button>
          )}
          
          <Button 
            variant="outline"
            className="text-white border-slate-500 hover:bg-slate-700"
            onClick={handleOpenEditModal}
          >
            <Settings className="w-4 h-4 mr-2" />
            项目设置
          </Button>
          <Button 
            variant="outline"
            className="text-red-500 border-red-500 hover:bg-red-500/10"
            onClick={() => setDeleteDialogOpen(true)}
          >
            <Trash2 className="w-4 h-4 mr-2" />
            删除项目
          </Button>
        </div>
      </div>
      
      {/* 状态信息 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-slate-800 rounded-xl border border-slate-600 p-4">
          <div className="flex items-center">
            <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center mr-3">
              <Cpu className="w-5 h-5 text-blue-300" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-300">项目状态</h3>
              <div className="flex items-center">
                <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                  project?.status === 'running' ? 'bg-green-500' :
                  project?.status === 'stopped' ? 'bg-yellow-500' :
                  project?.status === 'error' ? 'bg-red-500' :
                  'bg-blue-500'
                }`}></span>
                <p className="text-lg font-semibold text-white">
                  {project?.status === 'running' ? '运行中' :
                  project?.status === 'stopped' ? '已停止' :
                  project?.status === 'error' ? '错误' :
                  project?.status === 'creating' ? '创建中' : project?.status}
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-slate-800 rounded-xl border border-slate-600 p-4">
          <div className="flex items-center">
            <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center mr-3">
              <HardDrive className="w-5 h-5 text-green-300" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-300">项目类型</h3>
              <p className="text-lg font-semibold text-white">
                {project?.project_type === 'notebook' ? 'Jupyter Notebook' :
                project?.project_type === 'canvas' ? '可视化拖拽编程' : project?.project_type}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-slate-800 rounded-xl border border-slate-600 p-4">
          <div className="flex items-center">
            <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center mr-3">
              <Image className="w-5 h-5 text-purple-300" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-300">Docker镜像</h3>
              <p className="text-lg font-semibold text-white">
                {project?.image_details ? (
                  <span>
                    {project.image_details.name}
                    {project.image_details.pythonVersion && ` (Python ${project.image_details.pythonVersion})`}
                  </span>
                ) : (
                  <span className="text-sm text-gray-400">未指定镜像</span>
                )}
              </p>
            </div>
          </div>
        </div>
      </div>
      
      {/* 主要内容区 */}
      <div className="flex flex-col space-y-6">
        {/* IDE/Jupyter 界面 */}
        {typeof renderProjectContent === 'function' && renderProjectContent()}
        
        {/* 版本历史区域 - 独立于Jupyter区域 */}
        {renderSnapshotsList()}
      </div>
      
      {/* 删除确认对话框 */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="bg-slate-800/75 backdrop-blur-sm border border-slate-700/50 shadow-lg">
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除项目</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-400">
              此操作将永久删除项目 "{project?.name}" 及其相关数据和容器。此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting} className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600" autoFocus={false}>取消</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDelete}
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
      {typeof renderEditModal === 'function' && renderEditModal()}
      
      {/* 创建版本模态框 */}
      {typeof renderCreateSnapshotModal === 'function' && renderCreateSnapshotModal()}
      
      {/* 比较版本模态框 */}
      {renderCompareModal()}
      
      {/* 比较结果模态框 */}
      {renderCompareResultModal()}
      
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
        /* 更新默认按钮样式以匹配shadcn/ui的outline变体 */
        .custom-dark-modal .ant-btn-default {
          color: rgb(209, 213, 219) !important;
          border-color: rgb(71, 85, 105) !important; /* 更深的边框色 */
          background-color: transparent !important; /* 透明背景 */
        }
        .custom-dark-modal .ant-btn-default:hover {
          color: white !important;
          border-color: rgb(59, 130, 246) !important; /* 悬停时边框变亮 */
          background-color: rgba(59, 130, 246, 0.1) !important; /* 悬停时淡蓝色背景 */
        }
        .custom-dark-modal .ant-form-item-label > label {
          color: rgb(209, 213, 219) !important; /* 确保label是浅灰色 */
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
        .custom-dark-modal .ant-input-textarea textarea::placeholder,
        /* 添加 Select placeholder 样式 */
        .custom-dark-modal .ant-select-selection-placeholder {
          color: rgba(148, 163, 184, 0.6) !important; /* 调整占位符颜色 */
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
        /* ... (省略 AlertDialog 样式) ... */

        /* 确保 Select 下拉菜单样式生效 */
        .custom-dark-select-dropdown {
          background-color: rgba(15, 23, 42, 0.9) !important; /* 更深的背景，减少透明度 */
          backdrop-filter: blur(12px);
          border: 1px solid rgba(51, 65, 85, 0.7) !important; /* 更清晰的边框 */
          border-radius: 0.5rem; /* 统一圆角 */
        }
        
        .custom-dark-select-dropdown .ant-select-item {
          color: rgb(209, 213, 219) !important; /* 浅灰色文字 */
          padding: 8px 12px !important;
          border-radius: 0.25rem; /* 为选项添加圆角 */
          margin: 2px 4px; /* 添加选项间距 */
        }
        
        .custom-dark-select-dropdown .ant-select-item-option-active {
          background-color: rgba(59, 130, 246, 0.2) !important; /* 悬停背景 */
        }
        
        .custom-dark-select-dropdown .ant-select-item-option-selected {
          background-color: rgba(59, 130, 246, 0.4) !important; /* 选中背景 */
          font-weight: 600; /* 选中加粗 */
          color: white !important; /* 选中文字变白 */
        }
        /* 覆盖空状态的文字颜色 */
        .custom-dark-select-dropdown .ant-empty-description {
           color: rgba(148, 163, 184, 0.8) !important;
        }

        /* 自定义 Popconfirm 样式 */
        .custom-dark-popconfirm .ant-popover-inner {
          background-color: rgba(30, 41, 59, 0.9) !important; /* 深色背景 */
          backdrop-filter: blur(8px);
          border: 1px solid rgba(51, 65, 85, 0.7) !important;
          border-radius: 0.5rem !important;
          box-shadow: 0 4px 15px -3px rgba(0, 0, 0, 0.2);
        }
        .custom-dark-popconfirm .ant-popover-inner-content {
            padding: 12px 16px !important; /* 调整内边距 */
        }
        .custom-dark-popconfirm .ant-popover-message-title {
          color: white !important; /* 标题白色 */
          padding-left: 24px !important; /* 为图标留出空间 */
          font-size: 0.9rem; /* 调整标题大小 */
        }
        .custom-dark-popconfirm .ant-popover-message-description {
          color: rgb(209, 213, 219) !important; /* 描述浅灰色 */
           margin-left: 24px !important; /* 与标题对齐 */
           margin-top: 4px !important; /* 增加与标题的间距 */
           font-size: 0.8rem; /* 调整描述大小 */
        }
        .custom-dark-popconfirm .ant-popover-message > .anticon {
           color: #facc15 !important; /* 图标黄色 */
           font-size: 16px; /* 调整图标大小 */
           top: 14px !important; /* 微调图标位置 */
        }
        .custom-dark-popconfirm .ant-popover-buttons {
          margin-top: 12px !important; /* 增加按钮与内容的间距 */
        }
        /* Popconfirm 按钮样式已通过 props 传入 */

        /* 自定义 Table 样式 (如果将来恢复使用) */
        .custom-dark-table .ant-table {
          background: transparent !important;
        }
        .custom-dark-table .ant-table-thead > tr > th {
          background: rgba(30, 41, 59, 0.5) !important;
          color: rgb(156, 163, 175) !important; /* 表头文字颜色 */
          border-bottom: 1px solid rgba(51, 65, 85, 0.8) !important;
        }
        .custom-dark-table .ant-table-tbody > tr > td {
          border-bottom: 1px solid rgba(51, 65, 85, 0.5) !important;
          color: rgb(209, 213, 219) !important; /* 表格内容文字颜色 */
        }
        .custom-dark-table .ant-table-tbody > tr.ant-table-row:hover > td {
          background: rgba(51, 65, 85, 0.3) !important; /* 悬停行背景色 */
        }
        .custom-dark-table .ant-pagination-item,
        .custom-dark-table .ant-pagination-prev,
        .custom-dark-table .ant-pagination-next {
          background: rgba(30, 41, 59, 0.5) !important;
          border-color: rgba(51, 65, 85, 0.8) !important;
        }
        .custom-dark-table .ant-pagination-item a,
        .custom-dark-table .ant-pagination-prev a,
        .custom-dark-table .ant-pagination-next a {
          color: rgb(156, 163, 175) !important;
        }
        .custom-dark-table .ant-pagination-item-active {
          background: rgba(59, 130, 246, 0.3) !important;
          border-color: rgba(59, 130, 246, 0.5) !important;
        }
        .custom-dark-table .ant-pagination-item-active a {
          color: white !important;
        }
        .custom-dark-table .ant-empty-description {
          color: rgb(156, 163, 175) !important; /* 空状态文字颜色 */
        }

        /* 自定义 Tooltip 样式 */
        .custom-dark-tooltip .ant-tooltip-inner {
          background-color: rgba(30, 41, 59, 0.95) !important; /* 深色背景 */
          color: white !important; /* 白色文字 */
          border-radius: 0.375rem !important; /* 圆角 */
          border: 1px solid rgba(51, 65, 85, 0.7) !important;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
          padding: 6px 10px !important; /* 内边距 */
          font-size: 0.8rem; /* 字体大小 */
        }
        .custom-dark-tooltip .ant-tooltip-arrow::before,
        .custom-dark-tooltip .ant-tooltip-arrow::after {
          background-color: rgba(30, 41, 59, 0.95) !important; /* 箭头颜色 */
        }
        
        /* 自定义 Popconfirm 样式 */
        .custom-dark-popconfirm .ant-popover-inner {
          background-color: rgba(30, 41, 59, 0.9) !important; /* 深色背景 */
          backdrop-filter: blur(8px);
          border: 1px solid rgba(51, 65, 85, 0.7) !important;
          border-radius: 0.5rem !important;
          box-shadow: 0 4px 15px -3px rgba(0, 0, 0, 0.2);
        }
        .custom-dark-popconfirm .ant-popover-inner-content {
            padding: 12px 16px !important; /* 调整内边距 */
        }
        .custom-dark-popconfirm .ant-popover-message-title {
          color: white !important; /* 标题白色 */
          padding-left: 24px !important; /* 为图标留出空间 */
          font-size: 0.9rem; /* 调整标题大小 */
        }
        .custom-dark-popconfirm .ant-popover-message-description {
          color: rgb(209, 213, 219) !important; /* 描述浅灰色 */
           margin-left: 24px !important; /* 与标题对齐 */
           margin-top: 4px !important; /* 增加与标题的间距 */
           font-size: 0.8rem; /* 调整描述大小 */
        }
        .custom-dark-popconfirm .ant-popover-message > .anticon {
           color: #facc15 !important; /* 图标黄色 */
           font-size: 16px; /* 调整图标大小 */
           top: 14px !important; /* 微调图标位置 */
        }
        .custom-dark-popconfirm .ant-popover-buttons {
          margin-top: 12px !important; /* 增加按钮与内容的间距 */
        }
        /* Popconfirm 取消按钮自定义悬停/聚焦样式 */
        .custom-popconfirm-cancel-btn {
          background-color: rgba(51, 65, 85, 0.5) !important;
          border-color: rgba(71, 85, 105, 0.5) !important;
          color: rgb(209, 213, 219) !important;
        }
        .custom-popconfirm-cancel-btn:hover,
        .custom-popconfirm-cancel-btn:focus {
          color: white !important;
          border-color: rgba(59, 130, 246, 0.5) !important; 
          background-color: rgba(59, 130, 246, 0.1) !important; 
          outline: none !important; /* 移除默认聚焦轮廓 */
          box-shadow: none !important; /* 移除默认聚焦阴影 */
        }
        /* Popconfirm 其他按钮样式已通过 props 传入 */

      `}</style>
    </div>
  );
};

export default ProjectDetailPage;