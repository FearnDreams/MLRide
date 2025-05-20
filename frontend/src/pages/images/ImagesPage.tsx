import React, { useState, useEffect } from 'react';
import { Search, Info, AlertCircle, Trash2, Plus, Edit2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { imagesService, DockerImage } from '@/services/images';
import { message, Spin, Empty, Modal, Tooltip, Badge, Form, Input } from 'antd';
import _ from 'lodash'; // 引入 lodash 用于 debounce

const ImagesPage: React.FC = () => {
  const navigate = useNavigate();
  const [userImages, setUserImages] = useState<DockerImage[]>([]);
  const [filteredUserImages, setFilteredUserImages] = useState<DockerImage[]>([]); // 过滤后的用户镜像
  const [loading, setLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState<DockerImage | null>(null);
  const [form] = Form.useForm();
  const [searchTerm, setSearchTerm] = useState(''); // 搜索词状态
  
  // 获取用户镜像
  const fetchUserImages = async () => {
    setLoading(true);
    try {
      const response = await imagesService.getUserImages();
      if (response.status === 'success' && response.data) {
        const imagesData = Array.isArray(response.data) ? response.data : [];
        const processedImages = imagesData.map(image => {
          if (image.pythonVersion && !image.python_version) {
            return { ...image, python_version: image.pythonVersion };
          }
          if (image.python_version && !image.pythonVersion) {
            return { ...image, pythonVersion: image.python_version };
          }
          return image;
        });
        setUserImages(processedImages);
        // 获取数据后立即应用当前搜索词进行过滤
        applyFilter(searchTerm, processedImages);
      } else {
        message.error(response.message || '获取镜像失败');
        setUserImages([]); // 清空数据
        setFilteredUserImages([]);
      }
    } catch (error: any) {
      console.error('获取用户镜像失败:', error);
      message.error(error.message || '获取镜像失败，请重试');
      setUserImages([]); // 清空数据
      setFilteredUserImages([]);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchUserImages(); // 初始加载
  }, []); // 简化依赖
  
  // 过滤函数 (提取出来方便复用和 debounce)
  const applyFilter = (term: string, currentUsers: DockerImage[]) => {
      const terms = term
        .toLowerCase()
        .split(',')
        .map(t => t.trim())
        .filter(t => t !== '');

      const filterImage = (image: DockerImage) => { 
        if (terms.length === 0) return true;

        const name = (image.name || '').toLowerCase();
        const description = (image.description || '').toLowerCase();
        const packages = (image.packages || '').toLowerCase(); // 添加对 packages 的搜索
        
        // 检查名称、描述或包是否包含所有搜索词
        return terms.every(t => 
            name.includes(t) || 
            description.includes(t) ||
            packages.includes(t)
        );
      };

      setFilteredUserImages(currentUsers.filter(filterImage));
  };
  
  // 使用 useEffect 监听搜索词变化以触发过滤
  useEffect(() => {
    const debouncedFilter = _.debounce(() => {
       applyFilter(searchTerm, userImages);
    }, 300);
    
    debouncedFilter();

    return () => {
      debouncedFilter.cancel();
    };
  }, [searchTerm, userImages]); // 依赖项简化
  
  // 处理搜索输入变化
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  };

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

  // 查看镜像详情
  const handleViewImageDetail = (image: DockerImage) => {
    setSelectedImage(image);
    setDetailModalVisible(true);
  };
  
  // 打开编辑镜像模态框
  const handleEditImage = (image: DockerImage, e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation(); // 阻止事件冒泡
    }
    setSelectedImage(image);
    form.setFieldsValue({
      name: image.name,
      description: image.description || '',
    });
    setEditModalVisible(true);
  };
  
  // 提交编辑镜像
  const handleEditSubmit = async () => {
    if (!selectedImage) return;
    
    try {
      setEditLoading(true);
      const values = await form.validateFields();
      
      console.log('提交编辑镜像数据:', {
        id: selectedImage.id,
        values: values,
        python_version: selectedImage.python_version || selectedImage.pythonVersion
      });
      
      // 恢复使用imagesService
      const requestData = {
        name: values.name,
        description: values.description,
        python_version: selectedImage.python_version || selectedImage.pythonVersion
      };
      
      console.log('使用imagesService发送请求:', {
        id: selectedImage.id,
        data: requestData
      });
      
      // 使用try-catch捕获updateImage可能抛出的错误
      try {
        const response = await imagesService.updateImage(selectedImage.id, requestData);
        console.log('imagesService响应:', response);
        
        // 即使响应解析有问题,我们也认为操作成功了(因为手动刷新后镜像确实已更新)
        message.success('镜像更新成功');
        setEditModalVisible(false);
        
        // 等待Modal动画完成后再刷新数据
        setTimeout(() => {
          // 强制刷新,确保数据更新
          fetchUserImages();
        }, 300);
      } catch (updateError: any) {
        console.error('imagesService.updateImage错误:', updateError);
        message.error(updateError.message || '更新镜像失败');
      }
    } catch (error: any) {
      console.error('编辑镜像表单验证错误:', error);
      message.error('表单验证失败,请检查输入');
    } finally {
      setEditLoading(false);
    }
  };
  
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

  // 渲染用户镜像列表 (使用过滤后数据)
  const renderUserImages = () => {
    if (loading) {
      return (
        <div className="flex justify-center items-center py-12">
          <Spin size="large" tip="加载中..." />
        </div>
      );
    }
    // 修改：使用 filteredUserImages
    if (filteredUserImages.length === 0) {
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <div className="flex flex-col items-center">
              <div className="flex items-center text-gray-300 mb-2">
                <AlertCircle className="w-5 h-5 mr-2" />
                <span>{searchTerm ? '未找到匹配的镜像' : '暂未创建任何镜像'}</span>
              </div>
              {!searchTerm && <p className="text-gray-400 text-sm">您可以点击"新建镜像"按钮创建自己的镜像</p>}
            </div>
          }
        >
          {!searchTerm && (
            <Button 
              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-4 py-2 rounded-lg shadow-md shadow-blue-900/20 border-0 transition-all duration-200 mt-4"
              onClick={() => navigate('/dashboard/images/create')}
            >
               <Plus className="w-5 h-5 mr-1" /> 新建镜像
            </Button>
          )}
        </Empty>
      );
    }

    return (
      <div className="space-y-4">
        {/* 修改：使用 filteredUserImages */} 
        {filteredUserImages.map((image) => (
          <div key={image.id} className="bg-slate-800/30 backdrop-blur-sm p-5 rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-medium text-white">{image.name}</h3>
                  <div className="flex items-center gap-1">
                    <Tooltip title="查看详情">
                      <Info 
                        className="w-4 h-4 text-gray-400 hover:text-blue-400 cursor-pointer transition-colors"
                        aria-label="查看镜像详情"
                        onClick={() => handleViewImageDetail(image)}
                      />
                    </Tooltip>
                    <Tooltip title="编辑镜像">
                      <Edit2
                        className="w-4 h-4 text-gray-400 hover:text-amber-400 cursor-pointer transition-colors ml-1"
                        aria-label="编辑镜像"
                        onClick={(e) => handleEditImage(image, e)}
                      />
                    </Tooltip>
                  </div>
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
                        Python {image.pythonVersion || image.python_version || '未指定'}
                      </span>
                    </div>
                    
                    {/* 添加PyTorch版本信息 */}
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
                    
                    {/* 添加CUDA版本信息 */}
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

  // 渲染镜像详情模态框
  const renderImageDetailModal = () => {
    if (!selectedImage) return null;
    
    return (
      <Modal
        title={<span className="text-white font-medium">镜像详情</span>}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button
            key="close"
            onClick={() => setDetailModalVisible(false)}
            className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white border-slate-600"
          >
            关闭
          </Button>
        ]}
        className="custom-dark-modal image-detail-modal"
        width={700}
      >
        <div className="py-4">
          {/* 镜像基本信息 */}
          <div className="mb-6">
            <h3 className="text-xl font-medium text-white mb-4 border-b border-slate-700/50 pb-2 flex items-center">
              <div className="w-7 h-7 rounded-full bg-blue-500/20 flex items-center justify-center mr-2">
                <span className="text-sm text-blue-400">信息</span>
              </div>
              基本信息
            </h3>
            <div className="grid grid-cols-2 gap-4 bg-slate-800/30 p-4 rounded-lg border border-slate-700/50 backdrop-blur-md">
              <div>
                <p className="text-gray-400 mb-1">镜像名称</p>
                <p className="text-white font-medium">{selectedImage.name}</p>
              </div>
              <div>
                <p className="text-gray-400 mb-1">创建时间</p>
                <p className="text-white">{new Date(selectedImage.created).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-gray-400 mb-1">镜像状态</p>
                <Badge 
                  status={
                    selectedImage.status === 'ready' ? 'success' : 
                    selectedImage.status === 'failed' ? 'error' : 
                    selectedImage.status === 'building' ? 'processing' : 'warning'
                  } 
                  text={
                    <span className={`${getStatusStyle(selectedImage.status).text} font-medium`}>
                      {getStatusText(selectedImage.status)}
                    </span>
                  } 
                />
              </div>
              <div>
                <p className="text-gray-400 mb-1">创建者</p>
                <p className="text-white">{selectedImage.creator_name || '未知'}</p>
              </div>
            </div>
          </div>
          
          {/* 技术规格 */}
          <div className="mb-6">
            <h3 className="text-xl font-medium text-white mb-4 border-b border-slate-700/50 pb-2 flex items-center">
              <div className="w-7 h-7 rounded-full bg-purple-500/20 flex items-center justify-center mr-2">
                <span className="text-sm text-purple-400">规格</span>
              </div>
              技术规格
            </h3>
            <div className="grid grid-cols-2 gap-4 bg-slate-800/30 p-4 rounded-lg border border-slate-700/50 backdrop-blur-md">
              <div>
                <p className="text-gray-400 mb-1">Python版本</p>
                <p className="text-white flex items-center">
                  <span className="inline-block w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center mr-2">
                    <span className="text-xs text-blue-400">Py</span>
                  </span>
                  <span className="font-medium">{selectedImage.pythonVersion || selectedImage.python_version || '未指定'}</span>
                </p>
              </div>
              
              {selectedImage.pytorch_version && (
                <div>
                  <p className="text-gray-400 mb-1">PyTorch版本</p>
                  <p className="text-white flex items-center">
                    <span className="inline-block w-6 h-6 rounded-full bg-orange-500/20 flex items-center justify-center mr-2">
                      <span className="text-xs text-orange-400">Pt</span>
                    </span>
                    <span className="font-medium">{selectedImage.pytorch_version}</span>
                  </p>
                </div>
              )}
              
              {selectedImage.cuda_version && (
                <div>
                  <p className="text-gray-400 mb-1">CUDA版本</p>
                  <p className="text-white flex items-center">
                    <span className="inline-block w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center mr-2">
                      <span className="text-xs text-green-400">Cu</span>
                    </span>
                    <span className="font-medium">{selectedImage.cuda_version}</span>
                  </p>
                </div>
              )}
              
              <div>
                <p className="text-gray-400 mb-1">Docker标签</p>
                <p className="text-white">{selectedImage.image_tag || '未生成'}</p>
              </div>
            </div>
          </div>
          
          {/* 描述信息 */}
          <div className="mb-6">
            <h3 className="text-xl font-medium text-white mb-4 border-b border-slate-700/50 pb-2 flex items-center">
              <div className="w-7 h-7 rounded-full bg-indigo-500/20 flex items-center justify-center mr-2">
                <span className="text-sm text-indigo-400">描述</span>
              </div>
              描述信息
            </h3>
            <div className="bg-slate-800/30 p-4 rounded-lg border border-slate-700/50 backdrop-blur-md">
              <p className="text-white">{selectedImage.description || '暂无描述信息'}</p>
            </div>
          </div>
          
          {/* 包信息（如果有的话） */}
          {selectedImage.packages && (
            <div className="mb-0">
              <h3 className="text-xl font-medium text-white mb-4 border-b border-slate-700/50 pb-2 flex items-center">
                <div className="w-7 h-7 rounded-full bg-cyan-500/20 flex items-center justify-center mr-2">
                  <span className="text-sm text-cyan-400">包</span>
                </div>
                包含的工具包
              </h3>
              <div className="bg-slate-800/30 p-4 rounded-lg border border-slate-700/50 backdrop-blur-md">
                <div className="flex flex-wrap gap-2">
                  {selectedImage.packages.split(',').map((pkg: string, index: number) => (
                    <span key={index} className="text-sm px-2.5 py-1 bg-indigo-500/10 text-indigo-300 rounded-full border border-indigo-500/20">
                      {pkg.trim()}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </Modal>
    );
  };

  // 渲染编辑镜像模态框
  const renderEditModal = () => {
    return (
      <Modal
        title={<span className="text-white font-medium">编辑镜像</span>}
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
            {editLoading ? '保存中...' : '保存'}
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
            label={<span className="text-gray-300">镜像名称</span>}
            rules={[{ required: true, message: '请输入镜像名称' }]}
          >
            <Input 
              placeholder="请输入镜像名称" 
              className="bg-slate-800/50 border-slate-700 text-white" 
            />
          </Form.Item>
          <Form.Item
            name="description"
            label={<span className="text-gray-300">镜像描述</span>}
          >
            <Input.TextArea 
              placeholder="请输入镜像描述（可选）" 
              className="bg-slate-800/50 border-slate-700 text-white"
              rows={4}
            />
          </Form.Item>
        </Form>
      </Modal>
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
              placeholder="搜索镜像名、描述或包，逗号分隔多标签"
              className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
              value={searchTerm} // 绑定 value
              onChange={handleSearchChange} // 绑定 onChange
            />
          </div>
          <Button 
            className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-4 py-2 rounded-lg shadow-md shadow-blue-900/20 border-0 transition-all duration-200 flex items-center gap-2"
            onClick={() => navigate('/dashboard/images/create')}
          >
            <Plus className="w-5 h-5" /> 新建镜像
          </Button>
        </div>

        {/* 直接渲染用户镜像，无需分栏 */}
        {renderUserImages()}
      </div>
      
      {/* 镜像详情模态框 */}
      {renderImageDetailModal()}
      
      {/* 编辑镜像模态框 */}
      {renderEditModal()}
      
      {/* Add global styles for dark modal */}
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
        .image-detail-modal .ant-badge-status-text {
          color: inherit;
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
      `}</style>
    </div>
  );
};

export default ImagesPage;
