import React, { useState, useEffect } from 'react';
import { Search, Info, AlertCircle, Trash2, Plus, Edit2, UploadCloud, Download, Eye, Globe, Lock, FileText, Upload, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { datasetsService, Dataset } from '@/services/datasets'; // 引入服务和类型
import { message, Spin, Empty, Modal, Tooltip, Badge, Form, Input, Tag, Select, Upload as AntUpload } from 'antd';
import { filesize } from "filesize"; // 用于格式化文件大小
import _ from 'lodash'; // 引入 lodash 用于 debounce

// 定义模拟用户数据集
const mockUserDatasets: Dataset[] = [
  {
    id: 1,
    name: '用户数据集 A',
    description: '这是我的第一个测试数据集，包含一些基本的用户行为数据。',
    file_size: 1024 * 1024 * 5, // 5MB
    file_type: 'csv',
    created: '2024-07-28T10:00:00Z',
    updated: '2024-07-28T11:30:00Z',
    status: 'ready',
    creator: 1,
    creator_name: '当前用户',
    visibility: 'private',
    tags: ['用户行为', '测试数据'],
    preview_available: true,
  },
  {
    id: 2,
    name: '图像标注数据',
    description: '包含1000张已标注的猫狗图片。',
    file_size: 1024 * 1024 * 150, // 150MB
    file_type: 'zip',
    created: '2024-07-27T15:20:00Z',
    updated: '2024-07-27T15:20:00Z',
    status: 'processing',
    creator: 1,
    creator_name: '当前用户',
    visibility: 'private',
    tags: ['图像识别', '标注数据', '猫狗'],
    preview_available: false,
  },
];

// 定义模拟官方数据集
const mockOfficialDatasets: Dataset[] = [
  {
    id: 101,
    name: 'MNIST 手写数字数据集',
    description: '经典的机器学习入门数据集，包含手写数字图片及其标签。',
    file_size: 1024 * 1024 * 11, // 11MB
    file_type: 'gz',
    created: '2023-01-15T09:00:00Z',
    updated: '2023-01-15T09:00:00Z',
    status: 'ready',
    creator: 0,
    creator_name: '官方团队',
    downloads: 15000,
    visibility: 'public',
    tags: ['图像分类', '手写数字', '基准'],
    license: 'CC BY-SA 3.0',
    preview_available: true,
  },
  {
    id: 102,
    name: 'Iris 鸢尾花数据集',
    description: '包含三种鸢尾花的四个特征测量值，常用于分类任务。',
    file_size: 1024 * 4, // 4KB
    file_type: 'csv',
    created: '2022-11-01T14:00:00Z',
    updated: '2022-11-01T14:00:00Z',
    status: 'ready',
    creator: 0,
    creator_name: '官方团队',
    downloads: 25000,
    visibility: 'public',
    tags: ['分类', '经典数据集', '花卉'],
    license: 'Public Domain',
    preview_available: true,
  },
];

const DatasetsPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState("我的数据集");
  const [userDatasets, setUserDatasets] = useState<Dataset[]>(mockUserDatasets);
  const [officialDatasets, setOfficialDatasets] = useState<Dataset[]>(mockOfficialDatasets);
  const [filteredUserDatasets, setFilteredUserDatasets] = useState<Dataset[]>(mockUserDatasets);
  const [filteredOfficialDatasets, setFilteredOfficialDatasets] = useState<Dataset[]>(mockOfficialDatasets);
  const [loading, setLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [form] = Form.useForm();
  const [searchTerm, setSearchTerm] = useState('');
  
  // 新增状态
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [uploadForm] = Form.useForm();
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [fileList, setFileList] = useState<any[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);

  // 过滤逻辑
  useEffect(() => {
    const handleFilter = () => {
      const terms = searchTerm
        .toLowerCase()
        .split(',')
        .map(t => t.trim())
        .filter(t => t !== '');

      const filterDataset = (dataset: Dataset) => {
        if (terms.length === 0) return true; // 如果没有搜索词，显示所有

        const nameMatch = terms.every(term => dataset.name.toLowerCase().includes(term));
        const tagsMatch = dataset.tags 
          ? terms.every(term => 
              dataset.tags?.some(tag => tag.toLowerCase().includes(term))
            )
          : false;
          
        // 修改逻辑：名称或标签中包含所有搜索词即可
        return terms.every(term => 
            dataset.name.toLowerCase().includes(term) ||
            (dataset.tags && dataset.tags.some(tag => tag.toLowerCase().includes(term)))
        );
      };

      if (selectedTab === "我的数据集") {
        setFilteredUserDatasets(userDatasets.filter(filterDataset));
      } else {
        setFilteredOfficialDatasets(officialDatasets.filter(filterDataset));
      }
    };
    
    // 使用 debounce 避免过于频繁的过滤
    const debouncedFilter = _.debounce(handleFilter, 300);
    debouncedFilter();

    // 清理 debounce
    return () => {
      debouncedFilter.cancel();
    };
  }, [searchTerm, selectedTab, userDatasets, officialDatasets]);

  // 处理搜索输入变化
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  };
  
  // 获取数据集状态对应的中文
  const getStatusText = (status: string) => {
    const statusMap: Record<string, string> = {
      'pending': '等待中',
      'processing': '处理中',
      'ready': '就绪',
      'failed': '失败'
    };
    return statusMap[status] || status;
  };

  // 获取状态对应的样式
  const getStatusStyle = (status: string) => {
    const styleMap: Record<string, { bg: string, text: string, border: string }> = {
      'pending': { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30' },
      'processing': { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
      'ready': { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
      'failed': { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' }
    };
    return styleMap[status] || { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/30' };
  };
  
  // 格式化文件大小
  const formatFileSize = (size: number) => {
    return filesize(size, { base: 2, standard: "jedec" });
  };

  // 渲染数据集卡片公共部分
  const renderDatasetCard = (dataset: Dataset, isOfficial: boolean) => (
    <div key={dataset.id} className={`bg-slate-800/30 backdrop-blur-sm p-5 rounded-xl border border-slate-700/50 hover:border-${isOfficial ? 'purple' : 'blue'}-500/30 transition-all duration-300 hover:shadow-md hover:shadow-${isOfficial ? 'purple' : 'blue'}-500/5`}>
      <div className="flex justify-between items-start">
        <div className="flex-1 mr-4">
          {/* 名称和操作按钮 */}
          <div className="flex items-center gap-2 mb-2">
            <h3 className="font-medium text-white text-lg">{dataset.name}</h3>
            <Tooltip title="查看详情">
              <Info
                className="w-4 h-4 text-gray-400 hover:text-blue-400 cursor-pointer transition-colors"
                aria-label="查看数据集详情"
                onClick={() => handleViewDatasetDetail(dataset)}
              />
            </Tooltip>
            {!isOfficial && (
              <>
                <Tooltip title="编辑数据集">
                  <Edit2
                    className="w-4 h-4 text-gray-400 hover:text-amber-400 cursor-pointer transition-colors ml-1"
                    aria-label="编辑数据集"
                    onClick={(e) => handleEditDataset(dataset, e)}
                  />
                </Tooltip>
                <Tooltip title="删除数据集">
                  <Trash2
                    className="w-4 h-4 text-gray-400 hover:text-red-400 cursor-pointer transition-colors ml-1"
                    aria-label="删除数据集"
                    onClick={(e) => handleDeleteDataset(dataset.id, e)}
                  />
                </Tooltip>
              </>
            )}
          </div>
          {/* 描述 */}
          <p className="text-gray-400 text-sm mb-3 break-words">{dataset.description || '暂无描述'}</p>

          {/* 详细信息 */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm mb-3">
            <div className="flex items-center gap-1.5 text-gray-300">
              <UploadCloud className="w-4 h-4 text-cyan-400" /> 大小: {formatFileSize(dataset.file_size)}
            </div>
            <div className="flex items-center gap-1.5 text-gray-300">
              <FileText className="w-4 h-4 text-red-400" /> 文件类型:
              <Tag className="bg-gray-700 border-gray-600 text-gray-300">{dataset.file_type.toUpperCase()}</Tag>
            </div>
            <div className="flex items-center gap-1.5 text-gray-300">
              <AlertCircle className="w-4 h-4 text-yellow-400" /> 状态:
              <span className={`font-medium ${getStatusStyle(dataset.status).text}`}>
                {getStatusText(dataset.status)}
              </span>
            </div>
             <div className="flex items-center gap-1.5 text-gray-300">
              {dataset.visibility === 'public' ? <Globe className="w-4 h-4 text-green-400" /> : <Lock className="w-4 h-4 text-orange-400" />}
              可见性: {dataset.visibility === 'public' ? '公开' : '私有'}
            </div>
             <div className="flex items-center gap-1.5 text-gray-300 col-span-2">
              <Info className="w-4 h-4 text-gray-400" /> 创建于: {new Date(dataset.created).toLocaleDateString()}
            </div>
             {isOfficial && dataset.downloads && (
               <div className="flex items-center gap-1.5 text-gray-300">
                 <Download className="w-4 h-4 text-blue-400" /> 下载次数: {dataset.downloads.toLocaleString()}
               </div>
             )}
          </div>

          {/* 标签 */}
          {dataset.tags && dataset.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {dataset.tags.map((tag, index) => (
                <Tag key={index} className="text-xs px-1.5 py-0.5 bg-slate-700/60 text-gray-300 rounded border border-slate-600/70">
                  {tag}
                </Tag>
              ))}
            </div>
          )}
        </div>

        {/* 右侧操作按钮 */}
        <div className="flex flex-col items-end gap-2">
          {dataset.preview_available && (
             <Tooltip title="预览数据">
              <Button
                variant="outline"
                size="sm"
                className="text-gray-300 border-slate-600 hover:bg-slate-700/50 hover:text-white"
                onClick={() => handlePreviewDataset(dataset)}
              >
                <Eye className="w-4 h-4 mr-1" /> 预览
              </Button>
            </Tooltip>
           )}
          <Tooltip title="下载数据集">
            <Button
              variant="outline"
              size="sm"
              className="text-gray-300 border-slate-600 hover:bg-slate-700/50 hover:text-white"
              onClick={() => handleDownloadDataset(dataset.id)}
            >
              <Download className="w-4 h-4 mr-1" /> 下载
            </Button>
          </Tooltip>
        </div>
      </div>
    </div>
  );

  // 渲染用户数据集列表（使用过滤后的数据）
  const renderUserDatasets = () => {
    if (loading) {
      return <div className="flex justify-center items-center py-12"><Spin size="large" tip="加载中..." /></div>;
    }
    // 修改这里，使用 filteredUserDatasets
    if (filteredUserDatasets.length === 0) {
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <div className="flex flex-col items-center">
              <div className="flex items-center text-gray-300 mb-2">
                <AlertCircle className="w-5 h-5 mr-2" /> 
                <span>{searchTerm ? '未找到匹配的数据集' : '暂未上传任何数据集'}</span>
              </div>
              {!searchTerm && <p className="text-gray-400 text-sm">您可以点击"上传数据集"按钮开始</p>}
            </div>
          }
        >
          {!searchTerm && (
            <Button
              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-4 py-2 rounded-lg shadow-md shadow-blue-900/20 border-0 transition-all duration-200 mt-4"
              onClick={handleUploadClick}
            >
              <UploadCloud className="w-5 h-5 mr-2" /> 上传数据集
            </Button>
          )}
        </Empty>
      );
    }
    // 修改这里，使用 filteredUserDatasets
    return <div className="space-y-4">{filteredUserDatasets.map(ds => renderDatasetCard(ds, false))}</div>;
  };

  // 渲染官方数据集列表（使用过滤后的数据）
  const renderOfficialDatasets = () => {
    if (loading) {
      return <div className="flex justify-center items-center py-12"><Spin size="large" tip="加载中..." /></div>;
    }
    // 修改这里，使用 filteredOfficialDatasets
    if (filteredOfficialDatasets.length === 0) {
       return (
         <Empty 
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
                <div className="flex items-center text-gray-300">
                    <AlertCircle className="w-5 h-5 mr-2" />
                    <span>{searchTerm ? '未找到匹配的数据集' : '暂无官方数据集'}</span>
                </div>
            }
        />
       );
    }
    // 修改这里，使用 filteredOfficialDatasets
    return <div className="space-y-4">{filteredOfficialDatasets.map(ds => renderDatasetCard(ds, true))}</div>;
  };
  
  // --- Placeholder Handlers (需要后续实现) ---
  const handleViewDatasetDetail = (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setDetailModalVisible(true);
    console.log("查看详情:", dataset.name);
    message.info("查看详情功能待实现");
  };

  const handleEditDataset = (dataset: Dataset, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSelectedDataset(dataset);
    form.setFieldsValue({ // 假设编辑表单包含这些字段
      name: dataset.name,
      description: dataset.description || '',
      visibility: dataset.visibility,
      tags: dataset.tags || [],
    });
    setEditModalVisible(true);
    console.log("编辑:", dataset.name);
    message.info("编辑功能待实现");
  };

  const handleDeleteDataset = (id: number, e?: React.MouseEvent) => {
     if (e) e.stopPropagation();
    Modal.confirm({
      title: <span className="text-white">确认删除</span>,
      content: <span className="text-gray-300">确定要删除这个数据集吗？此操作不可恢复。</span>,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      className: 'custom-dark-modal', // 确保应用暗色主题样式
      onOk: async () => {
        console.log("删除:", id);
        message.info("删除功能待实现");
        // setDeleteLoading(true);
        // try {
        //   await datasetsService.deleteDataset(id);
        //   message.success('数据集删除成功');
        //   fetchUserDatasets(); // 重新加载数据
        // } catch (error: any) {
        //   message.error(error.message || '删除数据集失败');
        // } finally {
        //   setDeleteLoading(false);
        // }
      }
    });
  };
  
   const handlePreviewDataset = (dataset: Dataset) => {
    console.log("预览:", dataset.name);
    message.info("预览功能待实现");
  };

  const handleDownloadDataset = (id: number) => {
    console.log("下载:", id);
    message.info("下载功能待实现");
    // try {
    //   await datasetsService.downloadDataset(id);
    // } catch (error: any) {
    //   message.error(error.message || '下载失败');
    // }
  };

  const handleUploadClick = () => {
    setUploadModalVisible(true);
    uploadForm.resetFields();
    setFileList([]);
    setUploadFile(null);
  };
  
  // 处理文件上传前的验证
  const beforeUpload = (file: File) => {
    // 可接受的文件类型列表
    const acceptedTypes = ['text/csv', 'application/json', 'application/zip', 'application/x-zip-compressed', 'application/x-gzip'];
    
    // 检查文件类型
    const isAcceptedType = acceptedTypes.includes(file.type) || 
                          file.name.endsWith('.csv') || 
                          file.name.endsWith('.json') || 
                          file.name.endsWith('.zip') || 
                          file.name.endsWith('.gz');
                          
    if (!isAcceptedType) {
      message.error('只能上传CSV、JSON、ZIP或GZ格式的文件!');
      return AntUpload.LIST_IGNORE;
    }
    
    // 检查文件大小，限制为500MB
    const isLt500M = file.size / 1024 / 1024 < 500;
    if (!isLt500M) {
      message.error('文件必须小于500MB!');
      return AntUpload.LIST_IGNORE;
    }

    // 保存文件到状态
    setUploadFile(file);
    setFileList([file]);
    
    // 返回false阻止自动上传
    return false;
  };

  // 处理文件移除
  const handleRemoveFile = () => {
    setUploadFile(null);
    setFileList([]);
  };

  // 处理上传表单提交
  const handleUploadSubmit = async () => {
    try {
      // 表单验证
      const values = await uploadForm.validateFields();
      
      // 检查是否有文件
      if (!uploadFile) {
        message.error('请选择要上传的数据集文件!');
        return;
      }
      
      // 构建FormData
      const formData = new FormData();
      formData.append('name', values.name);
      formData.append('visibility', values.visibility);
      
      if (values.description) {
        formData.append('description', values.description);
      }
      
      if (values.tags && values.tags.length > 0) {
        // 将标签数组转为JSON字符串
        formData.append('tags', JSON.stringify(values.tags));
      }
      
      if (values.license) {
        formData.append('license', values.license);
      }
      
      // 添加文件
      formData.append('file', uploadFile);
      
      // 设置上传状态
      setUploadLoading(true);
      
      // 调用上传API
      const response = await datasetsService.createDataset(formData);
      
      // 处理成功响应
      message.success('数据集上传成功!');
      
      // 重置表单和状态
      uploadForm.resetFields();
      setFileList([]);
      setUploadFile(null);
      setUploadModalVisible(false);
      
      // 刷新数据集列表 - 这里暂时使用模拟数据
      // 真实环境应该调用fetchUserDatasets()
      const newDataset: Dataset = {
        id: Date.now(), // 临时ID
        name: values.name,
        description: values.description || '',
        file_size: uploadFile.size,
        file_type: uploadFile.name.split('.').pop() || '',
        created: new Date().toISOString(),
        updated: new Date().toISOString(),
        status: 'processing', // 新上传的数据集通常需要处理
        creator: 1, // 假设当前用户ID为1
        creator_name: '当前用户',
        visibility: values.visibility,
        tags: values.tags || [],
        preview_available: false // 初始设置为不可预览
      };
      
      // 更新用户数据集列表
      setUserDatasets(prevDatasets => [newDataset, ...prevDatasets]);
      
    } catch (error: any) {
      // 处理表单验证错误
      if (error.errorFields) {
        return;
      }
      
      // 处理API错误
      message.error(error.message || '上传数据集失败');
    } finally {
      setUploadLoading(false);
    }
  };
  
  // 渲染上传模态框
  const renderUploadModal = () => (
    <Modal
      title={<span className="text-white">上传数据集</span>}
      open={uploadModalVisible}
      onCancel={() => setUploadModalVisible(false)}
      footer={[
        <Button 
          key="cancel"
          variant="outline"
          onClick={() => setUploadModalVisible(false)}
          className="mr-2"
        >
          取消
        </Button>,
        <Button
          key="submit"
          onClick={handleUploadSubmit}
          disabled={uploadLoading || !uploadFile}
          className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white border-0"
        >
          {uploadLoading ? '上传中...' : '上传'}
        </Button>
      ]}
      className="custom-dark-modal"
      width={600}
    >
      <Form
        form={uploadForm}
        layout="vertical"
        initialValues={{ visibility: 'private' }}
      >
        <Form.Item
          name="name"
          label={<span className="text-gray-300">数据集名称</span>}
          rules={[{ required: true, message: '请输入数据集名称!' }]}
        >
          <Input placeholder="输入一个描述性的数据集名称" />
        </Form.Item>
        
        <Form.Item
          name="description"
          label={<span className="text-gray-300">描述</span>}
        >
          <Input.TextArea 
            placeholder="描述这个数据集的内容和用途" 
            rows={3}
          />
        </Form.Item>
        
        <Form.Item
          name="visibility"
          label={<span className="text-gray-300">可见性</span>}
          rules={[{ required: true, message: '请选择可见性!' }]}
        >
          <Select>
            <Select.Option value="private">
              <div className="flex items-center">
                <Lock className="w-4 h-4 mr-2 text-orange-400" />
                <span>私有 (仅自己可见)</span>
              </div>
            </Select.Option>
            <Select.Option value="public">
              <div className="flex items-center">
                <Globe className="w-4 h-4 mr-2 text-green-400" />
                <span>公开 (所有人可见)</span>
              </div>
            </Select.Option>
          </Select>
        </Form.Item>
        
        <Form.Item
          name="tags"
          label={<span className="text-gray-300">标签</span>}
        >
          <Select
            mode="tags"
            placeholder="添加描述性标签，回车确认"
            open={false}
          />
        </Form.Item>
        
        <Form.Item
          name="file"
          label={<span className="text-gray-300">数据集文件</span>}
        >
          <div className="border border-dashed border-slate-600 rounded-lg p-4 hover:border-blue-500 transition-colors">
            <AntUpload.Dragger
              name="file"
              fileList={fileList}
              beforeUpload={beforeUpload}
              onRemove={handleRemoveFile}
              maxCount={1}
              multiple={false}
              showUploadList={false}
              className="bg-transparent border-0"
            >
              <div className="flex flex-col items-center">
                <UploadCloud className="w-10 h-10 text-blue-500 mb-2" />
                <p className="text-gray-300">点击或拖拽文件到此区域上传</p>
                <p className="text-gray-400 text-sm">支持 CSV, JSON, ZIP, GZ 格式，最大500MB</p>
              </div>
            </AntUpload.Dragger>
            
            {/* 显示已选文件 */}
            {fileList.length > 0 && (
              <div className="mt-4 bg-slate-800/50 p-3 rounded-md">
                <div className="flex justify-between items-center">
                  <div className="flex items-center">
                    <FileText className="w-5 h-5 text-blue-400 mr-2" />
                    <div>
                      <div className="text-gray-300 text-sm font-medium truncate max-w-sm">{fileList[0].name}</div>
                      <div className="text-gray-400 text-xs">{formatFileSize(fileList[0].size)}</div>
                    </div>
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm"
                    className="text-gray-400 hover:text-red-400 border-0 p-1 h-8 w-8"
                    onClick={handleRemoveFile}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        </Form.Item>
      </Form>
    </Modal>
  );

  return (
    <div className="flex-1 flex flex-col">
      {/* Search and Upload Button */}
      <div className="flex justify-between mb-6">
        <div className="relative flex-1 max-w-2xl">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="搜索数据集名称或标签，逗号分隔多标签"
            className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
            value={searchTerm} // 绑定 value
            onChange={handleSearchChange} // 添加 onChange
          />
        </div>
        <Button
          className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-4 py-2 rounded-lg shadow-md shadow-blue-900/20 border-0 transition-all duration-200 flex items-center gap-2"
          onClick={handleUploadClick}
        >
          <UploadCloud className="w-5 h-5" /> 上传数据集
        </Button>
      </div>

      {/* Filters / Tabs */}
      <div className="mb-6">
        <div className="border-b border-slate-700/50 mb-6">
          <div className="flex gap-6">
            <button
              className={`pb-2 text-gray-300 hover:text-white transition-colors duration-200 ${selectedTab === "我的数据集" ? "border-b-2 border-blue-500 text-blue-400 font-medium" : ""}`}
              onClick={() => setSelectedTab("我的数据集")}
            >
              我的数据集
            </button>
            <button
              className={`pb-2 text-gray-300 hover:text-white transition-colors duration-200 ${selectedTab === "官方数据集" ? "border-b-2 border-purple-500 text-purple-400 font-medium" : ""}`}
              onClick={() => setSelectedTab("官方数据集")}
            >
              官方数据集
            </button>
          </div>
        </div>
      </div>

      {/* Datasets List */}
      <div className="flex-1 overflow-y-auto pb-6 pr-1"> {/* 添加一些padding */}
        {selectedTab === "我的数据集" ? renderUserDatasets() : renderOfficialDatasets()}
      </div>

      {/* Add Upload Modal */}
      {renderUploadModal()}

      {/* TODO: Add Modals for Details and Edit */}
      {/* {renderDetailModal()} */}
      {/* {renderEditModal()} */}
      
       {/* Add global styles for dark modal (similar to ImagesPage) */}
       <style>{`
        .custom-dark-modal .ant-modal-content {
          background-color: rgba(15, 23, 42, 0.85); /* 更深一点的背景 */
          backdrop-filter: blur(10px);
          border: 1px solid rgba(51, 65, 85, 0.6);
          border-radius: 0.75rem;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        }
        .custom-dark-modal .ant-modal-header {
          background-color: transparent;
          border-bottom: 1px solid rgba(51, 65, 85, 0.6);
        }
        .custom-dark-modal .ant-modal-title {
          color: #e2e8f0; /* Slightly brighter white */
           font-weight: 500;
        }
        .custom-dark-modal .ant-modal-close {
          color: rgba(148, 163, 184, 0.8);
        }
        .custom-dark-modal .ant-modal-close:hover {
          color: white;
        }
        .custom-dark-modal .ant-modal-body {
           padding: 24px;
        }
        .custom-dark-modal .ant-btn-primary {
          color: white !important;
          /* Use gradient from button */
          background: linear-gradient(to right, #2563eb, #4f46e5) !important;
          border: none !important;
        }
         .custom-dark-modal .ant-btn-primary:hover {
           background: linear-gradient(to right, #1d4ed8, #4338ca) !important;
         }
         .custom-dark-modal .ant-btn-dangerous {
             color: white !important;
             background: linear-gradient(to right, #dc2626, #ec4899) !important;
             border: none !important;
         }
         .custom-dark-modal .ant-btn-dangerous:hover {
              background: linear-gradient(to right, #b91c1c, #db2777) !important;
         }
        .custom-dark-modal .ant-btn-default {
          color: rgb(209, 213, 219) !important;
          border-color: rgba(71, 85, 105, 0.7) !important;
          background-color: rgba(51, 65, 85, 0.6) !important;
        }
        .custom-dark-modal .ant-btn-default:hover {
          color: white !important;
          border-color: rgba(59, 130, 246, 0.6) !important;
          background-color: rgba(71, 85, 105, 0.7) !important;
        }
         /* Input/Form styles */
         .custom-dark-modal .ant-form-item-label > label {
          color: rgb(203, 213, 225) !important; /* Lighter gray */
        }
        .custom-dark-modal .ant-input,
        .custom-dark-modal .ant-input-affix-wrapper,
        .custom-dark-modal .ant-select-selector,
        .custom-dark-modal .ant-input-textarea textarea {
          background-color: rgba(30, 41, 59, 0.7) !important;
          border-color: rgba(51, 65, 85, 0.8) !important;
          color: rgb(226, 232, 240) !important; /* Lightest gray */
        }
        .custom-dark-modal .ant-input::placeholder,
        .custom-dark-modal .ant-input-textarea textarea::placeholder {
          color: rgba(100, 116, 139, 0.7) !important; /* Muted placeholder */
        }
         .custom-dark-modal .ant-input:hover,
         .custom-dark-modal .ant-input-affix-wrapper:hover,
         .custom-dark-modal .ant-select-selector:hover,
         .custom-dark-modal .ant-input-textarea:hover {
          border-color: rgba(59, 130, 246, 0.6) !important;
        }
         .custom-dark-modal .ant-input:focus,
         .custom-dark-modal .ant-input-affix-wrapper:focus,
         .custom-dark-modal .ant-select-selector:focus,
         .custom-dark-modal .ant-input-textarea:focus {
          border-color: rgba(59, 130, 246, 0.8) !important;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
        }
        .custom-dark-modal .ant-form-item-explain-error {
          color: #f87171 !important; /* Brighter red for errors */
        }
        /* Tag styles inside modal */
         .custom-dark-modal .ant-tag {
           background-color: rgba(51, 65, 85, 0.6) !important;
           border-color: rgba(71, 85, 105, 0.7) !important;
           color: rgb(203, 213, 225) !important;
         }
      `}</style>
    </div>
  );
};

export default DatasetsPage; 