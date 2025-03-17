import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Code, BookOpen, Layers, Check, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getDockerImages, DockerImage } from '@/services/images';
import { createProject } from '@/services/projects';
import { useToast } from '@/components/ui/use-toast';

// 备注: 直接使用services/images.ts中定义的DockerImage接口

const CreateProjectPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();

  // 从URL参数读取项目类型
  const getProjectTypeFromUrl = (): 'ide' | 'notebook' | 'canvas' => {
    const params = new URLSearchParams(location.search);
    const type = params.get('type');
    if (type === 'ide' || type === 'notebook' || type === 'canvas') {
      return type;
    }
    return 'ide'; // 默认类型
  };

  const [projectType, setProjectType] = useState<'ide' | 'notebook' | 'canvas'>(getProjectTypeFromUrl());
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [selectedImageId, setSelectedImageId] = useState<number | null>(null);
  const [images, setImages] = useState<DockerImage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 监听URL参数变化
  useEffect(() => {
    setProjectType(getProjectTypeFromUrl());
  }, [location.search]);

  // 加载镜像列表
  useEffect(() => {
    const fetchImages = async () => {
      try {
        const response = await getDockerImages();
        console.log('镜像API响应:', response);
        
        // 确保有镜像数据
        if (response && response.data) {
          let imagesList = response.data;
          console.log('原始镜像数据:', imagesList);
          
          // 详细检查第一个镜像的数据结构
          if(imagesList.length > 0) {
            console.log('第一个镜像详情:', JSON.stringify(imagesList[0], null, 2));
            console.log('Python版本字段:', imagesList[0].python_version, imagesList[0].pythonVersion);
          }
          
          // 处理数据，确保能够正确显示Python版本
          const processedImages = imagesList.map(image => {
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
          
          // 不应该过滤镜像状态，显示所有可用镜像
          // 如果镜像列表为空，显示一个提示
          if (processedImages.length > 0) {
            setImages(processedImages);
            setSelectedImageId(processedImages[0].id);
          } else {
            console.warn('没有找到可用镜像');
            setImages([]);
            setError('没有可用的镜像，请先创建镜像');
          }
        } else {
          console.warn('镜像响应数据格式不符合预期:', response);
          setImages([]);
          setError('获取镜像列表失败，请稍后重试');
        }
      } catch (err) {
        console.error('获取镜像列表失败:', err);
        setError('获取镜像列表失败，请稍后重试');
      }
    };

    fetchImages();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!projectName.trim()) {
      toast({
        title: "错误",
        description: "项目名称不能为空",
        variant: "destructive",
      });
      return;
    }

    if (!selectedImageId) {
      toast({
        title: "错误",
        description: "请选择一个镜像",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await createProject({
        name: projectName,
        description: projectDescription,
        project_type: projectType,
        image: selectedImageId,
        is_public: isPublic
      });

      toast({
        title: "成功",
        description: "项目创建成功",
      });

      // 导航到项目详情页
      if (response && response.data && response.data.id) {
        navigate(`/dashboard/projects/${response.data.id}`);
      } else {
        // 如果没有获取到ID，导航到项目列表页
        navigate('/dashboard/projects');
      }
    } catch (err: any) {
      console.error('创建项目失败:', err);
      console.log('错误详情:', {
        response: err.response,
        data: err.response?.data,
        message: err.response?.data?.message || err.message
      });
      
      // 使用API拦截器统一处理后的错误信息
      const errorMessage = err.response?.data?.message || err.message || '创建项目失败，请稍后重试';
      setError(errorMessage);
      toast({
        title: "错误",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const projectTypes = [
    {
      value: 'ide',
      title: 'IDE开发环境',
      description: '使用Eclipse Theia在线编程环境进行代码开发',
      icon: <Code className="w-5 h-5" />
    },
    {
      value: 'notebook',
      title: 'Jupyter Notebook',
      description: '使用Jupyter Notebook进行数据分析和代码执行',
      icon: <BookOpen className="w-5 h-5" />
    },
    {
      value: 'canvas',
      title: '可视化拖拽编程',
      description: '使用图形化界面构建机器学习工作流',
      icon: <Layers className="w-5 h-5" />
    }
  ];

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="flex items-center mb-8">
        <Button
          variant="ghost"
          className="mr-4 text-white hover:bg-slate-700"
          onClick={() => navigate('/dashboard/projects')}
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          返回项目列表
        </Button>
        <h1 className="text-2xl font-bold text-white">创建新项目</h1>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6 border-red-500 bg-red-500/20 text-red-300">
          <AlertTitle>错误</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 gap-8 mb-8">
          {/* 项目类型选择 */}
          <Card className="bg-slate-800 border-slate-600">
            <CardHeader>
              <CardTitle className="text-white">选择项目类型</CardTitle>
              <CardDescription className="text-gray-300">根据您的需求选择适合的项目类型</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {projectTypes.map((type) => (
                  <div
                    key={type.value}
                    className={`relative rounded-lg border-2 p-4 cursor-pointer transition-all ${
                      projectType === type.value
                        ? 'border-blue-500 bg-blue-500/20'
                        : 'border-slate-600 hover:border-slate-500'
                    }`}
                    onClick={() => setProjectType(type.value as 'ide' | 'notebook' | 'canvas')}
                  >
                    {projectType === type.value && (
                      <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center">
                        <Check className="w-4 h-4 text-white" />
                      </div>
                    )}
                    <div className="flex flex-col items-center text-center">
                      <div className="w-12 h-12 rounded-full bg-slate-700 flex items-center justify-center mb-3">
                        {type.icon}
                      </div>
                      <h3 className="font-medium text-lg mb-2 text-white">{type.title}</h3>
                      <p className="text-sm text-gray-300">{type.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 项目基本信息 */}
          <Card className="bg-slate-800 border-slate-600">
            <CardHeader>
              <CardTitle className="text-white">项目基本信息</CardTitle>
              <CardDescription className="text-gray-300">填写项目的基本信息</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="project-name" className="text-white">项目名称 <span className="text-red-400">*</span></Label>
                  <Input
                    id="project-name"
                    placeholder="输入项目名称"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    required
                    className="bg-slate-700 border-slate-600 text-white placeholder:text-gray-400"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="project-description" className="text-white">项目描述</Label>
                  <Textarea
                    id="project-description"
                    placeholder="简要描述项目的用途和目标"
                    value={projectDescription}
                    onChange={(e) => setProjectDescription(e.target.value)}
                    className="resize-none h-24 bg-slate-700 border-slate-600 text-white placeholder:text-gray-400"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="public-mode"
                    checked={isPublic}
                    onCheckedChange={setIsPublic}
                  />
                  <Label htmlFor="public-mode" className="text-gray-300">公开项目</Label>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 镜像选择 */}
          <Card className="bg-slate-800 border-slate-600">
            <CardHeader>
              <CardTitle className="text-white">选择环境镜像</CardTitle>
              <CardDescription className="text-gray-300">选择适合项目的运行环境镜像</CardDescription>
            </CardHeader>
            <CardContent>
              {images.length > 0 ? (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="image" className="mb-1 text-white text-sm">选择镜像</Label>
                    <Select 
                      value={selectedImageId ? String(selectedImageId) : ''}
                      onValueChange={(value) => setSelectedImageId(Number(value))}
                    >
                      <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                        <SelectValue placeholder="请选择镜像" />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-700 text-white">
                        {images.map((image) => (
                          <SelectItem 
                            key={image.id} 
                            value={String(image.id)} 
                            className="hover:bg-slate-700 focus:bg-slate-700"
                          >
                            {image.name}{image.pythonVersion ? ` - Python ${image.pythonVersion}` : ''}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {selectedImageId && (
                    <div className="p-4 rounded-md bg-slate-700 border border-slate-600">
                      <h4 className="font-semibold mb-2 text-white">镜像详情:</h4>
                      <p className="text-sm text-gray-200 mb-1">
                        {images.find(img => img.id === selectedImageId)?.description || '无描述'}
                      </p>
                      <div className="flex items-center gap-1">
                        <p className="text-sm text-gray-300 mb-1">Python版本:</p>
                        <span className="text-sm text-white px-2 py-0.5 rounded-full bg-blue-500/20 border border-blue-500/30">
                          {images.find(img => img.id === selectedImageId)?.pythonVersion || '未指定'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-6">
                  <p className="text-gray-300 mb-4">您还没有可用的镜像</p>
                  <Button
                    onClick={() => navigate('/dashboard/images/create')}
                    variant="outline"
                    className="border-blue-500/50 text-blue-400 hover:bg-blue-500/10 hover:text-blue-300"
                  >
                    创建新镜像
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-end space-x-4">
          <Button 
            type="button" 
            variant="outline" 
            onClick={() => navigate('/dashboard/projects')}
            disabled={loading}
          >
            取消
          </Button>
          <Button 
            type="submit" 
            variant="default" 
            disabled={loading || !selectedImageId || !projectName.trim()}
          >
            {loading ? '创建中...' : '创建项目'}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default CreateProjectPage; 