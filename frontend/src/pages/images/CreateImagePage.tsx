// 导入必要的React组件和hooks
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, ArrowLeft } from "lucide-react";
import { imagesService } from '@/services/images';
import { toast } from 'sonner';
import axios from 'axios';

// Python版本选项
const PYTHON_VERSIONS = [
  { value: "3.8", label: "Python 3.8" },
  { value: "3.9", label: "Python 3.9" },
  { value: "3.10", label: "Python 3.10" },
  { value: "3.11", label: "Python 3.11" },
];

// PyTorch版本选项
const PYTORCH_VERSIONS = [
  { value: "none", label: "不使用PyTorch" },
  { value: "1.10", label: "PyTorch 1.10" },
  { value: "1.11", label: "PyTorch 1.11" },
  { value: "1.12", label: "PyTorch 1.12" },
  { value: "1.13", label: "PyTorch 1.13" },
  { value: "2.0", label: "PyTorch 2.0" },
  { value: "2.1", label: "PyTorch 2.1" },
  { value: "2.2", label: "PyTorch 2.2" },
  { value: "2.3", label: "PyTorch 2.3" },
  { value: "2.4", label: "PyTorch 2.4" },
  { value: "2.5", label: "PyTorch 2.5" },
  { value: "2.6", label: "PyTorch 2.6" },
  { value: "2.7", label: "PyTorch 2.7" },
];

// CUDA版本选项（根据PyTorch版本会动态过滤）
const CUDA_VERSIONS = [
  { value: "none", label: "不使用CUDA" },
  { value: "11.0", label: "CUDA 11.0" },
  { value: "11.1", label: "CUDA 11.1" },
  { value: "11.2", label: "CUDA 11.2" },
  { value: "11.3", label: "CUDA 11.3" },
  { value: "11.6", label: "CUDA 11.6" },
  { value: "11.7", label: "CUDA 11.7" },
  { value: "11.8", label: "CUDA 11.8" },
  { value: "12.1", label: "CUDA 12.1" },
  { value: "12.4", label: "CUDA 12.4" },
  { value: "12.6", label: "CUDA 12.6" },
];

// PyTorch和CUDA版本兼容性映射
const COMPATIBILITY_MAP: Record<string, string[]> = {
  // PyTorch 2.7
  "2.7": ['11.8', '12.6'],
  // PyTorch 2.6
  "2.6": ['11.8', '12.4'],
  // PyTorch 2.5
  "2.5": ['11.8', '12.1', '12.4'],
  // PyTorch 2.4
  "2.4": ['11.8', '12.1'],
  // PyTorch 2.3
  "2.3": ['11.8', '12.1'],
  // PyTorch 2.2
  "2.2": ['11.8', '12.1'],
  // PyTorch 2.1
  "2.1": ['11.8', '12.1'],
  // PyTorch 2.0
  "2.0": ['11.7', '11.8'],
  // PyTorch 1.13
  "1.13": ['11.6', '11.7'],
  // PyTorch 1.12
  "1.12": ['11.3', '11.6'],
  // PyTorch 1.11
  "1.11": ['11.1', '11.2', '11.3'],
  // PyTorch 1.10
  "1.10": ['11.0', '11.1', '11.3']
};

// 定义验证规则类型
type ValidationRule = {
  required?: boolean;
  maxLength?: number;
  pattern?: RegExp;
};

type ValidationRules = {
  [key: string]: ValidationRule;
};

// 定义错误消息类型
type ErrorMessages = {
  [key: string]: {
    required?: string;
    maxLength?: string;
    pattern?: string;
  };
};

// 表单验证规则
const VALIDATION_RULES: ValidationRules = {
  name: {
    required: true,
    maxLength: 50,
    pattern: /^[a-zA-Z0-9-_]+$/,
  },
  description: {
    maxLength: 140,
  },
  pythonVersion: {
    required: true,
  },
  pytorchVersion: {},
  cudaVersion: {},
};

// 错误提示信息
const ERROR_MESSAGES: ErrorMessages = {
  name: {
    required: "镜像名称不能为空",
    maxLength: "镜像名称不能超过50个字符",
    pattern: "镜像名称只能包含字母、数字、下划线和连字符",
  },
  description: {
    maxLength: "镜像描述不能超过140个字符",
  },
  pythonVersion: {
    required: "请选择Python版本",
  },
  pytorchVersion: {},
  cudaVersion: {},
};

export default function CreateImagePage() {
  const navigate = useNavigate();
  const [formData, setFormData] = React.useState({
    name: "",
    description: "",
    pythonVersion: "",
    pytorchVersion: "",
    cudaVersion: "",
  });

  const [errors, setErrors] = React.useState<{
    name?: string;
    description?: string;
    pythonVersion?: string;
    pytorchVersion?: string;
    cudaVersion?: string;
  }>({});

  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // 根据当前选择的PyTorch版本，获取兼容的CUDA版本
  const getCompatibleCudaVersions = () => {
    if (!formData.pytorchVersion) {
      return [];
    }
    
    return COMPATIBILITY_MAP[formData.pytorchVersion] || [];
  };

  // 获取可用的CUDA版本选项
  const availableCudaVersions = React.useMemo(() => {
    if (!formData.pytorchVersion) {
      return [{ value: "not_applicable", label: "请先选择PyTorch版本" }];
    }
    
    const compatibleVersions = getCompatibleCudaVersions();
    if (compatibleVersions.length === 0) {
      return [{ value: "not_compatible", label: "所选PyTorch版本没有兼容的CUDA版本" }];
    }
    
    return [
      { value: "none", label: "不使用CUDA" },
      ...CUDA_VERSIONS.filter(v => compatibleVersions.includes(v.value))
    ];
  }, [formData.pytorchVersion]);

  // 当PyTorch版本变更时，重置CUDA版本
  React.useEffect(() => {
    if (formData.pytorchVersion) {
      const compatibleCudaVersions = getCompatibleCudaVersions();
      // 如果当前CUDA版本不兼容，则重置它
      if (
        formData.cudaVersion && 
        compatibleCudaVersions.length > 0 && 
        !compatibleCudaVersions.includes(formData.cudaVersion)
      ) {
        setFormData((prev) => ({
          ...prev,
          cudaVersion: "",
        }));
      }
    } else {
      // 如果没有选PyTorch，也清空CUDA选择
      if (formData.cudaVersion) {
        setFormData((prev) => ({
          ...prev,
          cudaVersion: "",
        }));
      }
    }
  }, [formData.pytorchVersion]);

  // 验证表单字段
  const validateField = (name: string, value: string) => {
    const rules = VALIDATION_RULES[name as keyof typeof VALIDATION_RULES];
    if (!rules) return "";

    if (rules.required && !value) {
      return ERROR_MESSAGES[name as keyof typeof ERROR_MESSAGES].required;
    }

    if (rules.maxLength && value.length > rules.maxLength) {
      return ERROR_MESSAGES[name as keyof typeof ERROR_MESSAGES].maxLength;
    }

    if (rules.pattern && !rules.pattern.test(value)) {
      return ERROR_MESSAGES[name as keyof typeof ERROR_MESSAGES].pattern;
    }

    return "";
  };

  // 处理表单输入变化
  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    // 验证字段
    const error = validateField(name, value);
    setErrors((prev) => ({
      ...prev,
      [name]: error,
    }));
  };

  // 处理Python版本选择
  const handlePythonVersionChange = (version: string) => {
    setFormData((prev) => ({
      ...prev,
      pythonVersion: version,
    }));

    // 验证字段
    const error = validateField("pythonVersion", version);
    setErrors((prev) => ({
      ...prev,
      pythonVersion: error,
    }));
  };

  // 处理PyTorch版本选择
  const handlePytorchVersionChange = (version: string) => {
    setFormData((prev) => ({
      ...prev,
      pytorchVersion: version,
    }));

    // 验证字段
    const error = validateField("pytorchVersion", version);
    setErrors((prev) => ({
      ...prev,
      pytorchVersion: error,
    }));
  };

  // 处理CUDA版本选择
  const handleCudaVersionChange = (version: string) => {
    setFormData((prev) => ({
      ...prev,
      cudaVersion: version,
    }));

    // 验证字段
    const error = validateField("cudaVersion", version);
    setErrors((prev) => ({
      ...prev,
      cudaVersion: error,
    }));
  };

  // 验证整个表单
  const validateForm = () => {
    const newErrors = {
      name: validateField("name", formData.name),
      description: validateField("description", formData.description),
      pythonVersion: validateField("pythonVersion", formData.pythonVersion),
      pytorchVersion: validateField("pytorchVersion", formData.pytorchVersion),
      cudaVersion: validateField("cudaVersion", formData.cudaVersion),
    };

    setErrors(newErrors);

    // 如果有任何错误消息，表单无效
    return !Object.values(newErrors).some(Boolean);
  };

  // 处理表单提交
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // 验证表单
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // 准备要发送的数据
      const submitData = {
        name: formData.name,
        description: formData.description,
        python_version: formData.pythonVersion,
        pythonVersion: formData.pythonVersion,
        use_slim: false,
        // 仅当有选择PyTorch版本且不是"none"时才添加相关字段
        ...(formData.pytorchVersion && formData.pytorchVersion !== "none" ? { pytorch_version: formData.pytorchVersion } : {}),
        // 仅当有选择CUDA版本且不是"none"时才添加相关字段
        ...(formData.cudaVersion && formData.cudaVersion !== "none" ? { cuda_version: formData.cudaVersion } : {}),
      };
      
      // 记录发送到API的数据，方便调试
      console.log('发送到API的数据:', submitData);
      
      await imagesService.createImage(submitData);
      
      // 显示成功提示
      toast.success('镜像创建成功！');
      
      // 成功后跳转到镜像列表页
      navigate("/dashboard/images");
    } catch (error) {
      // 详细记录错误信息
      console.error("创建镜像失败:", error);
      if (axios.isAxiosError(error)) {
        console.error("API错误详情:", {
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data,
          headers: error.response?.headers,
        });
        // 显示具体的错误信息
        toast.error(error.response?.data?.message || error.response?.data?.error || '创建镜像失败，请重试');
      } else {
        console.error("非API错误:", error);
        toast.error('创建镜像失败，请重试');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container mx-auto py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-white">新建镜像</h1>
        <Button 
          variant="outline"
          onClick={() => navigate("/dashboard/images")}
          disabled={isSubmitting}
        >
          <ArrowLeft className="w-4 h-4 mr-2" /> 返回
        </Button>
      </div>

      <Card className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 shadow-md rounded-xl">
        <CardHeader className="border-b border-slate-700/50">
          <CardTitle className="text-white">基本设置</CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* 镜像名称 */}
            <div className="space-y-2">
              <Label htmlFor="name" className="text-gray-300">
                镜像名称
                <span className="text-red-400 ml-1">*</span>
              </Label>
              <Input
                id="name"
                name="name"
                placeholder="请输入镜像名称，不超过50个字符"
                value={formData.name}
                onChange={handleInputChange}
                required
                className={`bg-slate-700/50 border-slate-600/50 text-gray-300 focus:border-blue-500/50 hover:border-blue-500/30 transition-colors ${errors.name ? "border-red-500" : ""}`}
                disabled={isSubmitting}
              />
              {errors.name && (
                <p className="text-sm text-red-400">{errors.name}</p>
              )}
            </div>

            {/* 镜像描述 */}
            <div className="space-y-2">
              <Label htmlFor="description" className="text-gray-300">镜像描述</Label>
              <Textarea
                id="description"
                name="description"
                placeholder="请输入镜像描述，不超过140个字符"
                value={formData.description}
                onChange={handleInputChange}
                className={`h-20 bg-slate-700/50 border-slate-600/50 text-gray-300 focus:border-blue-500/50 hover:border-blue-500/30 transition-colors ${errors.description ? "border-red-500" : ""}`}
                disabled={isSubmitting}
              />
              {errors.description && (
                <p className="text-sm text-red-400">{errors.description}</p>
              )}
            </div>

            {/* Python版本选择 */}
            <div className="space-y-2">
              <Label className="text-gray-300">
                工具包及版本
                <span className="text-red-400 ml-1">*</span>
              </Label>
              <Select
                value={formData.pythonVersion}
                onValueChange={handlePythonVersionChange}
                disabled={isSubmitting}
              >
                <SelectTrigger className={`bg-slate-700/50 border-slate-600/50 text-gray-300 focus:border-blue-500/50 hover:border-blue-500/30 transition-colors ${errors.pythonVersion ? "border-red-500" : ""}`}>
                  <SelectValue placeholder="选择Python版本" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800/90 backdrop-blur-md border border-slate-700/50 text-gray-300">
                  {PYTHON_VERSIONS.map((version) => (
                    <SelectItem 
                      key={version.value} 
                      value={version.value}
                      className="focus:bg-slate-700/50 focus:text-white text-gray-300"
                    >
                      {version.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.pythonVersion && (
                <p className="text-sm text-red-400">{errors.pythonVersion}</p>
              )}
            </div>

            {/* PyTorch版本选择 */}
            <div className="space-y-2">
              <Label className="text-gray-300">
                PyTorch版本
              </Label>
              <Select
                value={formData.pytorchVersion}
                onValueChange={handlePytorchVersionChange}
                disabled={isSubmitting}
              >
                <SelectTrigger className={`bg-slate-700/50 border-slate-600/50 text-gray-300 focus:border-blue-500/50 hover:border-blue-500/30 transition-colors ${errors.pytorchVersion ? "border-red-500" : ""}`}>
                  <SelectValue placeholder="选择PyTorch版本" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800/90 backdrop-blur-md border border-slate-700/50 text-gray-300">
                  {PYTORCH_VERSIONS.map((version) => (
                    <SelectItem 
                      key={version.value} 
                      value={version.value}
                      className="focus:bg-slate-700/50 focus:text-white text-gray-300"
                    >
                      {version.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.pytorchVersion && (
                <p className="text-sm text-red-400">{errors.pytorchVersion}</p>
              )}
            </div>

            {/* CUDA版本选择 */}
            <div className="space-y-2">
              <Label className="text-gray-300">
                CUDA版本
              </Label>
              <Select
                value={formData.cudaVersion}
                onValueChange={handleCudaVersionChange}
                disabled={isSubmitting}
              >
                <SelectTrigger className={`bg-slate-700/50 border-slate-600/50 text-gray-300 focus:border-blue-500/50 hover:border-blue-500/30 transition-colors ${errors.cudaVersion ? "border-red-500" : ""}`}>
                  <SelectValue placeholder="选择CUDA版本" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800/90 backdrop-blur-md border border-slate-700/50 text-gray-300">
                  {availableCudaVersions.map((version) => (
                    <SelectItem 
                      key={version.value} 
                      value={version.value}
                      className="focus:bg-slate-700/50 focus:text-white text-gray-300"
                    >
                      {version.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.cudaVersion && (
                <p className="text-sm text-red-400">{errors.cudaVersion}</p>
              )}
            </div>

            {/* 添加构建时间提示 */}
            <div className="mt-2 p-4 bg-blue-900/20 backdrop-blur-sm rounded-lg border border-blue-500/30 shadow-sm">
              <div className="text-sm text-blue-400 flex items-start space-x-3">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-blue-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="leading-relaxed">
                  <strong className="font-medium">提示：</strong>
                  <br />
                  不同版本的镜像构建时间可能不同：
                  <ul className="mt-1 ml-4 list-disc space-y-1">
                    <li>Python 3.8和3.9版本：约2-4分钟</li>
                    <li>Python 3.10和3.11版本：约3-5分钟</li>
                  </ul>
                  系统将直接使用标准Python版本构建镜像（非slim版本），请耐心等待构建完成。
                </div>
              </div>
            </div>

            {/* 提交按钮 */}
            <div className="flex justify-end">
              <Button 
                type="submit"
                variant="default"
                disabled={isSubmitting || Object.keys(errors).some((key) => Boolean(errors[key as keyof typeof errors]))}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    创建中...
                  </>
                ) : (
                  "创建镜像"
                )}
              </Button>
            </div>
          </form>
          
          {/* 添加全局样式确保输入框文字颜色 */}
          <style>{`
            input, textarea, select {
              color: rgb(209, 213, 219) !important;
              background-color: rgba(51, 65, 85, 0.5) !important;
            }
            input::placeholder, textarea::placeholder {
              color: rgba(148, 163, 184, 0.6) !important;
            }
            input:focus, 
            input:hover, 
            input:active,
            textarea:focus,
            textarea:hover,
            textarea:active,
            select:focus,
            select:hover,
            select:active {
              background-color: rgba(51, 65, 85, 0.5) !important;
              border-color: rgba(59, 130, 246, 0.5) !important;
              box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1) !important;
            }
          `}</style>
        </CardContent>
      </Card>
    </div>
  );
}