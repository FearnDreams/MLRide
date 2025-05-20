import React, { useState, useEffect, useCallback } from 'react';
import { Search, AlertCircle, Trash2, Plus, Edit2, UploadCloud, Download, Eye, FileText, Upload, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { datasetsService, Dataset } from '@/services/datasets';
import { message, Spin, Empty, Modal, Tooltip, Badge, Form, Input, Tag, Select, Upload as AntUpload, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { filesize } from "filesize";
import _ from 'lodash';

interface PreviewData {
  type: 'csv' | 'excel' | 'json' | 'txt' | 'error' | 'unsupported';
  headers?: string[];
  rows?: any[][];
  content?: any;
  message?: string;
}

const DatasetsPage: React.FC = () => {
  const navigate = useNavigate();
  const [userDatasets, setUserDatasets] = useState<Dataset[]>([]);
  const [filteredUserDatasets, setFilteredUserDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [form] = Form.useForm();
  const [searchTerm, setSearchTerm] = useState('');

  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [uploadForm] = Form.useForm();
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [fileList, setFileList] = useState<any[]>([]);

  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [previewDatasetName, setPreviewDatasetName] = useState<string>('');

  const fetchUserDatasets = useCallback(async () => {
    setLoading(true);
    try {
      const response = await datasetsService.getUserDatasets();
      if (response.status === 'success') {
        setUserDatasets(response.data as Dataset[]);
        applyFilter(searchTerm, response.data as Dataset[]);
      } else {
        message.error(response.message || '获取用户数据集失败');
        setUserDatasets([]);
        setFilteredUserDatasets([]);
      }
    } catch (error: any) {
      message.error(error.message || '获取用户数据集失败');
      setUserDatasets([]);
      setFilteredUserDatasets([]);
    } finally {
      setLoading(false);
    }
  }, [searchTerm]);

  useEffect(() => {
    fetchUserDatasets();
  }, [fetchUserDatasets]);

  const applyFilter = (term: string, datasets: Dataset[]) => {
    const terms = term
      .toLowerCase()
      .split(',')
      .map(t => t.trim())
      .filter(t => t !== '');

    const filterDataset = (dataset: Dataset) => {
      if (terms.length === 0) return true;
      return terms.every(term =>
          dataset.name.toLowerCase().includes(term) ||
          (dataset.tags && dataset.tags.some(tag => tag.toLowerCase().includes(term)))
      );
    };
    setFilteredUserDatasets(datasets.filter(filterDataset));
  };

  useEffect(() => {
    const debouncedFilter = _.debounce(() => applyFilter(searchTerm, userDatasets), 300);
    debouncedFilter();
    return () => {
      debouncedFilter.cancel();
    };
  }, [searchTerm, userDatasets]);

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  };

  const getStatusText = (status: string) => {
    const statusMap: Record<string, string> = {
      'pending': '等待中',
      'processing': '处理中',
      'ready': '就绪',
      'failed': '失败'
    };
    return statusMap[status] || status;
  };

  const getStatusStyle = (status: string) => {
    const styleMap: Record<string, { bg: string, text: string, border: string }> = {
      'pending': { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30' },
      'processing': { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
      'ready': { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
      'failed': { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' }
    };
    return styleMap[status] || { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/30' };
  };

  const formatFileSize = (size: number | string | null | undefined) => {
    if (typeof size === 'number') {
      return filesize(size, { base: 2, standard: "jedec" });
    } else if (typeof size === 'string') {
        const numSize = parseInt(size, 10);
        if (!isNaN(numSize)) {
            return filesize(numSize, { base: 2, standard: "jedec" });
        }
    }
    return 'N/A';
  };

  const renderDatasetCard = (dataset: Dataset) => (
    <div key={dataset.id} className={`bg-slate-800/30 backdrop-blur-sm p-5 rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5`}>
      <div className="flex justify-between items-start">
        <div className="flex-1 mr-4 min-w-0">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="font-medium text-white text-lg truncate" title={dataset.name}>{dataset.name}</h3>
            {dataset.tags && dataset.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {dataset.tags.map((tag, index) => (
                  <Tag key={index} className="text-xs px-1.5 py-0.5 bg-slate-700/60 text-gray-300 rounded border border-slate-600/70">
                    {tag}
                  </Tag>
                ))}
              </div>
            )}
            <div className="flex items-center gap-1 flex-shrink-0 ml-auto">
              <Tooltip title="编辑数据集">
                <Edit2
                  className="w-4 h-4 text-gray-400 hover:text-amber-400 cursor-pointer transition-colors"
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
            </div>
          </div>
          <p className="text-gray-400 text-sm mb-3 break-words">{dataset.description || '暂无描述'}</p>

          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm mb-3">
            <div className="flex items-center gap-1.5 text-gray-300">
              <UploadCloud className="w-4 h-4 text-cyan-400" /> 大小: {formatFileSize(dataset.file_size)}
            </div>
            <div className="flex items-center gap-1.5 text-gray-300">
              <FileText className="w-4 h-4 text-red-400" /> 文件类型:
              <Tag className="bg-gray-700 border-gray-600 text-gray-300 ml-1">{(dataset.file_type || 'N/A').toUpperCase()}</Tag>
            </div>
            <div className="flex items-center gap-1.5 text-gray-300">
              <AlertCircle className="w-4 h-4 text-yellow-400" /> 状态:
              <span className={`font-medium ${getStatusStyle(dataset.status).text}`}>
                {getStatusText(dataset.status)}
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-300">
              <AlertCircle className="w-4 h-4 text-gray-400" /> 创建于: {new Date(dataset.created).toLocaleString()}
            </div>
          </div>
        </div>

        <div className="flex flex-col items-end gap-2 flex-shrink-0 ml-2">
          {dataset.status === 'ready' && dataset.preview_available && (
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
              disabled={!dataset.id || dataset.status !== 'ready'}
            >
              <Download className="w-4 h-4 mr-1" /> 下载
            </Button>
          </Tooltip>
        </div>
      </div>
    </div>
  );

  const renderUserDatasets = () => {
    if (loading) {
      return <div className="flex justify-center items-center py-12"><Spin size="large" tip="加载用户数据集中..." /></div>;
    }
    if (!loading && filteredUserDatasets.length === 0) {
      return (
        <div className="flex justify-center items-center py-12"> 
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
        </div>
      );
    }
    return <div className="space-y-4">{filteredUserDatasets.map(ds => renderDatasetCard(ds))}</div>;
  };

  const handleEditDataset = (dataset: Dataset, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSelectedDataset(dataset);
    form.setFieldsValue({
      name: dataset.name,
      description: dataset.description || '',
      tags: dataset.tags || [],
    });
    setEditModalVisible(true);
  };

  const handleEditSubmit = async () => {
    if (!selectedDataset) return;

    try {
      const values = await form.validateFields();
      setEditLoading(true);

      const dataToUpdate = {
        name: values.name,
        description: values.description,
        tags: values.tags || [],
      };

      const response = await datasetsService.updateDataset(selectedDataset.id, dataToUpdate);

      if (response.status === 'success') {
        message.success('数据集更新成功');
        setEditModalVisible(false);
        fetchUserDatasets();
      } else {
        message.error(response.message || '更新数据集失败');
      }
    } catch (error: any) {
      if (!error.errorFields) {
         message.error(error.message || '更新数据集失败');
      }
       console.error('更新数据集错误:', error);
    } finally {
      setEditLoading(false);
    }
  };

  const handleDeleteDataset = (id: number, e?: React.MouseEvent) => {
     if (e) e.stopPropagation();
    Modal.confirm({
      title: <span className="text-white">确认删除</span>,
      content: <span className="text-gray-300">确定要删除这个数据集吗？此操作不可恢复。</span>,
      okText: deleteLoading ? '删除中...' : '删除',
      okType: 'danger',
      cancelText: '取消',
      className: 'custom-dark-modal',
      okButtonProps: { disabled: deleteLoading },
      onOk: async () => {
        setDeleteLoading(true);
        try {
          const response = await datasetsService.deleteDataset(id);
          if (response.status === 'success') {
            message.success('数据集删除成功');
            fetchUserDatasets(); 
          } else {
            message.error(response.message || '删除数据集失败');
          }
        } catch (error: any) {
          message.error(error.message || '删除数据集失败');
        } finally {
          setDeleteLoading(false);
        }
      }
    });
  };

  const handlePreviewDataset = async (dataset: Dataset) => {
    setPreviewDatasetName(dataset.name);
    setPreviewLoading(true);
    setPreviewModalVisible(true);
    setPreviewData(null);

    try {
      const response = await datasetsService.previewDataset(dataset.id);
      console.log('Preview response:', response);
      
      if (response.status === 'success') {
        if (response.data && typeof response.data === 'object') {
          const responseData = response.data;
          
          let previewData: PreviewData;
          
          const fileType = responseData.file_type || '';
          
          if (fileType === 'csv') {
            const columns = responseData.columns || [];
            const rows = responseData.rows || [];
            
            if (columns.length === 0 && rows.length > 0 && Array.isArray(rows[0])) {
              const columnCount = rows[0].length;
              const defaultColumns = Array.from({ length: columnCount }, (_, i) => `列 ${i + 1}`);
              
              previewData = {
                type: 'csv',
                headers: defaultColumns,
                rows: rows,
                message: responseData.error || undefined
              };
            } else {
              previewData = {
                type: 'csv',
                headers: columns,
                rows: rows,
                message: (columns.length === 0 || rows.length === 0) ? 
                  '未能读取CSV数据，可能为空文件或格式错误' : responseData.error
              };
            }
          } else if (fileType === 'xlsx' || fileType === 'xls') {
            const sheetNames = responseData.sheet_names || [];
            const sheetsPreview = responseData.sheets_preview || {};
            const firstSheet = sheetNames.length > 0 ? sheetsPreview[sheetNames[0]] || {} : {};
            
            previewData = {
              type: 'excel',
              headers: firstSheet.columns || [],
              rows: firstSheet.rows || [],
              message: responseData.error || undefined
            };
          } else if (fileType === 'json') {
            previewData = {
              type: 'json',
              content: responseData.content,
              message: responseData.error || undefined
            };
          } else if (fileType === 'txt') {
            previewData = {
              type: 'txt',
              content: responseData.content || '',
              message: responseData.error || undefined
            };
          } else if (responseData.error) {
            previewData = {
              type: 'error',
              message: responseData.error
            };
          } else {
            previewData = {
              type: 'unsupported',
              message: `不支持预览此类型的文件: ${fileType}`
            };
          }
          
          console.log('Processed preview data:', previewData);
          
          setPreviewData(previewData);
        } else {
          console.error('Invalid response data structure:', response.data);
          setPreviewData({ type: 'error', message: '获取预览数据失败：响应格式不正确' });
        }
      } else {
        setPreviewData({ type: 'error', message: response.message || '获取预览数据失败' });
      }
    } catch (error: any) {
      console.error('Preview error:', error);
      setPreviewData({ type: 'error', message: error.message || '获取预览数据时发生错误' });
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleDownloadDataset = async (id: number) => {
    message.loading({ content: '开始下载...', key: 'download' });
    try {
      await datasetsService.downloadDataset(id);
      message.success({ content: '下载成功!', key: 'download', duration: 2 });
    } catch (error: any) {
      message.error({ content: error.message || '下载失败', key: 'download', duration: 2 });
    }
  };

  const handleUploadClick = () => {
    setUploadModalVisible(true);
    uploadForm.resetFields();
    setFileList([]);
    setUploadFile(null);
  };

  const beforeUpload = (file: File) => {
    const acceptedTypes = [
      'text/csv', 'application/json', 'text/plain', 'application/zip', 
      'application/x-zip-compressed', 'application/x-gzip', 'image/jpeg', 
      'image/png', 'image/gif', 'image/webp', 'image/bmp', 
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
      'application/vnd.ms-excel'
    ];
    const acceptedExtensions = [
        '.csv', '.json', '.txt', '.zip', '.gz', '.jpg', '.jpeg', '.png', '.gif',
        '.webp', '.bmp', '.xlsx', '.xls'
    ];
    const fileExtension = `.${file.name.split('.').pop()?.toLowerCase()}`;
    const isAcceptedType = acceptedTypes.includes(file.type) || acceptedExtensions.includes(fileExtension);
    if (!isAcceptedType) {
      message.error(`不支持的文件类型: ${fileExtension || file.type}。请上传 ${acceptedExtensions.join(', ')} 格式的文件。`);
      return AntUpload.LIST_IGNORE;
    }
    const isLt10G = file.size / 1024 / 1024 / 1024 < 10;
    if (!isLt10G) {
      message.error('文件必须小于10GB!');
      return AntUpload.LIST_IGNORE;
    }
    setUploadFile(file);
    setFileList([file]);
    return false;
  };

  const handleRemoveFile = () => {
    setUploadFile(null);
    setFileList([]);
  };

  const handleUploadSubmit = async () => {
    try {
      const values = await uploadForm.validateFields();
      if (!uploadFile) {
        message.error('请选择要上传的数据集文件!');
        return;
      }
      const formData = new FormData();
      formData.append('name', values.name);
      if (values.description) {
        formData.append('description', values.description);
      }
      if (values.tags && values.tags.length > 0) {
        formData.append('tags', JSON.stringify(values.tags));
      }
      formData.append('file', uploadFile);
      setUploadLoading(true);
      const response = await datasetsService.createDataset(formData);
      if (response.status === 'success') {
        message.success('数据集上传成功! 后台处理中...');
        uploadForm.resetFields();
        setFileList([]);
        setUploadFile(null);
        setUploadModalVisible(false);
        fetchUserDatasets();
      } else {
        message.error(response.message || '上传数据集失败');
      }
    } catch (error: any) {
      if (error.errorFields) {
        return;
      }
      message.error(error.message || '上传数据集失败');
    } finally {
      setUploadLoading(false);
    }
  };

  const renderEditModal = () => (
    <Modal
      title={<span className="text-white">编辑数据集</span>}
      open={editModalVisible}
      onCancel={() => {
        setEditModalVisible(false);
        form.resetFields();
      }}
      footer={[
        <Button
          key="cancel"
          variant="outline"
          onClick={() => {
            setEditModalVisible(false);
            form.resetFields();
          }}
          className="mr-2"
          disabled={editLoading}
        >
          取消
        </Button>,
        <Button
          key="submit"
          onClick={handleEditSubmit}
          disabled={editLoading}
          className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-white border-0 transition-opacity duration-200"
        >
          {editLoading ? '保存中...' : '保存'}
        </Button>
      ]}
      className="custom-dark-modal"
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
      >
        <Form.Item
          name="name"
          label={<span className="text-gray-300">数据集名称</span>}
          rules={[{ required: true, message: '请输入数据集名称!' }]}
        >
          <Input placeholder="输入一个描述性的数据集名称" disabled={editLoading}/>
        </Form.Item>

        <Form.Item
          name="description"
          label={<span className="text-gray-300">描述</span>}
        >
          <Input.TextArea
            placeholder="描述这个数据集的内容和用途"
            rows={3}
             disabled={editLoading}
          />
        </Form.Item>

        <Form.Item
          name="tags"
          label={<span className="text-gray-300">标签</span>}
        >
          <Select
            mode="tags"
            placeholder="添加描述性标签，回车确认"
            open={false}
            tokenSeparators={[',', ' ']}
             disabled={editLoading}
          />
        </Form.Item>
      </Form>
    </Modal>
  );

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
           disabled={uploadLoading}
        >
          取消
        </Button>,
        <Button
          key="submit"
          onClick={handleUploadSubmit}
          disabled={uploadLoading || !uploadFile}
          className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white border-0 transition-opacity duration-200"
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
      >
         <Form.Item
          name="name"
          label={<span className="text-gray-300">数据集名称</span>}
          rules={[{ required: true, message: '请输入数据集名称!' }]}
        >
          <Input placeholder="输入一个描述性的数据集名称" disabled={uploadLoading} />
        </Form.Item>
        <Form.Item
          name="description"
          label={<span className="text-gray-300">描述</span>}
        >
          <Input.TextArea
            placeholder="描述这个数据集的内容和用途"
            rows={3}
             disabled={uploadLoading}
          />
        </Form.Item>
        <Form.Item
          name="tags"
          label={<span className="text-gray-300">标签</span>}
        >
          <Select
            mode="tags"
            placeholder="添加描述性标签，回车确认"
            open={false}
            tokenSeparators={[',', ' ']}
             disabled={uploadLoading}
          />
        </Form.Item>
        <Form.Item
          name="file"
          label={<span className="text-gray-300">数据集文件</span>}
          rules={[{ required: true, message: '请选择数据集文件!', validator: () => uploadFile ? Promise.resolve() : Promise.reject() }]}
        >
          <div className={`border border-dashed border-slate-600 rounded-lg p-4 ${uploadLoading ? 'opacity-50 cursor-not-allowed' : 'hover:border-blue-500 transition-colors'}`}>
            <AntUpload.Dragger
              name="file"
              fileList={fileList}
              beforeUpload={beforeUpload}
              onRemove={handleRemoveFile}
              maxCount={1}
              multiple={false}
              showUploadList={false}
              className="bg-transparent border-0 p-0 m-0"
               disabled={uploadLoading}
            >
              <div className="flex flex-col items-center py-4">
                <UploadCloud className="w-10 h-10 text-blue-500 mb-2" />
                <p className="text-gray-300">点击或拖拽文件到此区域上传</p>
                <p className="text-gray-400 text-sm">
                  支持上传: CSV, JSON, TXT, Excel, 图片, ZIP, GZ (最大10GB)
                </p>
                 <p className="text-gray-400 text-xs mt-1">
                   支持预览: CSV, JSON, TXT, Excel
                </p>
              </div>
            </AntUpload.Dragger>
            {fileList.length > 0 && (
              <div className={`mt-4 bg-slate-800/50 p-3 rounded-md ${uploadLoading ? 'opacity-50' : ''}`}>
                <div className="flex justify-between items-center">
                  <div className="flex items-center min-w-0">
                    <FileText className="w-5 h-5 text-blue-400 mr-2 flex-shrink-0" />
                    <div className="overflow-hidden">
                      <div className="text-gray-300 text-sm font-medium truncate" title={fileList[0].name}>{fileList[0].name}</div>
                      <div className="text-gray-400 text-xs">{formatFileSize(fileList[0].size)}</div>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-gray-400 hover:text-red-400 border-0 p-1 h-8 w-8 ml-2 flex-shrink-0"
                    onClick={handleRemoveFile}
                     disabled={uploadLoading}
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

  const renderPreviewModal = () => {
    let content = null;

    if (previewLoading) {
      content = <div className="flex justify-center items-center min-h-[300px]"><Spin tip="加载预览数据中..." size="large" /></div>;
    } else if (previewData) {
      switch (previewData.type) {
        case 'csv':
        case 'excel':
          if (previewData.headers && previewData.rows) {
            const columns: ColumnsType<any> = previewData.headers.map((header, index) => ({
              title: <span className="text-gray-300 font-medium">{header}</span>,
              dataIndex: index,
              key: header,
              render: (text: any) => <span className="text-gray-400 text-xs">{String(text)}</span>
            }));
            const dataSource = previewData.rows.map((row, rowIndex) => {
              const rowObj: { [key: string]: any; key: React.Key } = { key: rowIndex };
              previewData.headers!.forEach((header, colIndex) => {
                rowObj[colIndex] = row[colIndex];
              });
              return rowObj;
            });
            content = (
              <Table
                columns={columns}
                dataSource={dataSource}
                size="small"
                pagination={{ pageSize: 10, size: 'small' }}
                scroll={{ x: 'max-content' }}
                className="preview-table-dark"
                rowClassName={() => "preview-table-row-dark"}
              />
            );
          } else {
            content = <p className="text-red-400">预览数据格式错误 (缺少 headers 或 rows)</p>;
          }
          break;
        case 'json':
          content = (
            <pre className="bg-slate-900 p-4 rounded overflow-auto max-h-[60vh] text-xs text-gray-300">
              <code>{JSON.stringify(previewData.content, null, 2)}</code>
            </pre>
          );
          break;
        case 'txt':
          content = (
            <pre className="bg-slate-900 p-4 rounded overflow-auto max-h-[60vh] text-sm text-gray-300 whitespace-pre-wrap break-words">
              {previewData.content}
            </pre>
          );
          break;
        case 'unsupported':
             content = <p className="text-yellow-400 flex items-center"><AlertCircle className="w-4 h-4 mr-2"/>{previewData.message || '不支持预览此文件类型'}</p>;
             break;
        case 'error':
        default:
          content = <p className="text-red-400 flex items-center"><AlertCircle className="w-4 h-4 mr-2"/>{previewData.message || '加载预览失败'}</p>;
          break;
      }
    }

    return (
      <Modal
        title={<span className="text-white">预览: {previewDatasetName}</span>}
        open={previewModalVisible}
        onCancel={() => setPreviewModalVisible(false)}
        footer={[
          <Button key="close" variant="outline" onClick={() => setPreviewModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={"80vw"}
        className="custom-dark-modal preview-modal-dark"
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
      >
        {content}
      </Modal>
    );
  };

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex justify-between items-center mb-6 gap-4 flex-wrap"> 
        <div className="relative flex-grow max-w-2xl"> 
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="搜索名称或标签 (逗号分隔)"
            className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
            value={searchTerm}
            onChange={handleSearchChange}
          />
        </div>
        <Button
          className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-4 py-2 rounded-lg shadow-md shadow-blue-900/20 border-0 transition-all duration-200 flex items-center gap-2 flex-shrink-0" 
          onClick={handleUploadClick}
        >
          <UploadCloud className="w-5 h-5" /> 上传数据集
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto pb-6 pr-1 -mr-1">
        {renderUserDatasets()}
      </div>

      {renderUploadModal()}
      {renderEditModal()}
      {renderPreviewModal()} 

       <style>{`
        .custom-dark-modal .ant-modal-content {
          background-color: rgba(15, 23, 42, 0.9);
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
          color: #e2e8f0;
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
          background: linear-gradient(to right, #2563eb, #4f46e5) !important;
          border: none !important;
        }
         .custom-dark-modal .ant-btn-primary:hover {
           background: linear-gradient(to right, #1d4ed8, #4338ca) !important;
         }
         .custom-dark-modal button.bg-gradient-to-r.from-amber-500 {
            color: white !important;
            background: linear-gradient(to right, #f59e0b, #f97316) !important; 
            border: none !important;
         }
          .custom-dark-modal button.bg-gradient-to-r.from-amber-500:hover {
            background: linear-gradient(to right, #d97706, #ea580c) !important; 
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
         .custom-dark-modal .ant-form-item-label > label {
          color: rgb(203, 213, 225) !important;
        }
        .custom-dark-modal .ant-input,
        .custom-dark-modal .ant-input-affix-wrapper,
        .custom-dark-modal .ant-select-selector,
        .custom-dark-modal .ant-input-textarea textarea,
        .custom-dark-modal .ant-select-selection-item {
          background-color: rgba(30, 41, 59, 0.7) !important;
          border-color: rgba(51, 65, 85, 0.8) !important;
          color: rgb(226, 232, 240) !important;
        }
        .custom-dark-modal .ant-select-selection-item {
            background-color: rgba(51, 65, 85, 0.6) !important;
            border-color: rgba(71, 85, 105, 0.7) !important;
            color: rgb(203, 213, 225) !important;
        }
        .custom-dark-modal .ant-input::placeholder,
        .custom-dark-modal .ant-input-textarea textarea::placeholder,
        .custom-dark-modal .ant-select-selection-placeholder {
          color: rgba(100, 116, 139, 0.7) !important;
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
          color: #f87171 !important;
        }
         .custom-dark-modal .ant-tag {
           background-color: rgba(51, 65, 85, 0.6) !important;
           border-color: rgba(71, 85, 105, 0.7) !important;
           color: rgb(203, 213, 225) !important;
         }
         .custom-dark-modal .ant-upload-drag {
           background: rgba(30, 41, 59, 0.3) !important;
           border: 1px dashed rgba(51, 65, 85, 0.8) !important;
         }
         .custom-dark-modal .ant-upload-drag:hover {
           border-color: rgba(59, 130, 246, 0.6) !important;
         }
         .custom-dark-modal .ant-upload-drag p {
            color: #9ca3af;
         }

         .preview-modal-dark .ant-table {
          background: transparent;
        }
        .preview-modal-dark .ant-table-thead > tr > th {
          background: rgba(30, 41, 59, 0.7) !important;
          border-color: rgba(51, 65, 85, 0.8) !important;
          color: #cbd5e1 !important;
        }
        .preview-modal-dark .ant-table-tbody > tr > td {
          border-color: rgba(51, 65, 85, 0.6) !important;
          background: transparent !important;
        }
         .preview-modal-dark .ant-table-tbody > tr.ant-table-row:hover > td {
           background: rgba(51, 65, 85, 0.4) !important;
        }
        .preview-modal-dark .ant-pagination-item,
        .preview-modal-dark .ant-pagination-prev .ant-pagination-item-link,
        .preview-modal-dark .ant-pagination-next .ant-pagination-item-link,
        .preview-modal-dark .ant-pagination-jump-prev .ant-pagination-item-link-icon,
        .preview-modal-dark .ant-pagination-jump-next .ant-pagination-item-link-icon {
          background-color: rgba(51, 65, 85, 0.6) !important;
          border-color: rgba(71, 85, 105, 0.7) !important;
          color: #cbd5e1 !important;
        }
        .preview-modal-dark .ant-pagination-item a {
           color: #cbd5e1 !important;
        }
        .preview-modal-dark .ant-pagination-item-active {
          background-color: #2563eb !important;
          border-color: #2563eb !important;
        }
        .preview-modal-dark .ant-pagination-item-active a {
           color: white !important;
        }
        .preview-modal-dark .ant-pagination-disabled .ant-pagination-item-link {
           color: rgba(100, 116, 139, 0.5) !important;
           border-color: rgba(51, 65, 85, 0.5) !important;
           background-color: rgba(30, 41, 59, 0.4) !important;
        }
        .preview-modal-dark .ant-select-selector {
           background-color: rgba(51, 65, 85, 0.6) !important;
           border-color: rgba(71, 85, 105, 0.7) !important;
           color: #cbd5e1 !important;
        }
         .preview-modal-dark .ant-select-arrow {
             color: #cbd5e1 !important;
         }
      `}</style>
    </div>
  );
};

export default DatasetsPage;
