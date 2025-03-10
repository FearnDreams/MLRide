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
import { ImageService } from '@/services/images';
import { toast } from 'sonner';
import axios from 'axios';

// Python版本选项
const PYTHON_VERSIONS = [
  { value: "3.8", label: "Python 3.8" },
  { value: "3.9", label: "Python 3.9" },
  { value: "3.10", label: "Python 3.10" },
  { value: "3.11", label: "Python 3.11" },
];

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
};

export default function CreateImagePage() {
  const navigate = useNavigate();
  const [formData, setFormData] = React.useState({
    name: "",
    description: "",
    pythonVersion: "",
  });

  const [errors, setErrors] = React.useState<{
    name?: string;
    description?: string;
    pythonVersion?: string;
  }>({});

  const [isSubmitting, setIsSubmitting] = React.useState(false);

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

  // 验证整个表单
  const validateForm = () => {
    const newErrors = {
      name: validateField("name", formData.name),
      description: validateField("description", formData.description),
      pythonVersion: validateField("pythonVersion", formData.pythonVersion),
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
      await ImageService.createImage({
        name: formData.name,
        description: formData.description,
        pythonVersion: formData.pythonVersion,
      });
      
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
          className="border-slate-700 bg-slate-800/50 hover:bg-slate-700/50 text-gray-300 hover:text-white transition-all duration-200 flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" /> 返回
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

            {/* 添加构建时间提示 */}
            <div className="mt-2 p-4 bg-blue-900/20 backdrop-blur-sm rounded-lg border border-blue-500/30 shadow-sm">
              <p className="text-sm text-blue-400 flex items-start space-x-3">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-blue-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="leading-relaxed">
                  <strong className="font-medium">提示：</strong>
                  <br />
                  不同版本的镜像构建时间可能不同：
                  <ul className="mt-1 ml-4 list-disc space-y-1">
                    <li>Python 3.8和3.9版本：约1-2分钟</li>
                    <li>Python 3.10和3.11版本：约2-4分钟</li>
                  </ul>
                  请耐心等待构建完成。
                </span>
              </p>
            </div>

            {/* 提交按钮 */}
            <div className="flex justify-end">
              <Button 
                type="submit"
                disabled={isSubmitting || Object.keys(errors).some((key) => Boolean(errors[key as keyof typeof errors]))}
                className={`min-w-[100px] bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 shadow-md shadow-blue-900/20 text-gray-100 transition-all duration-200 ${isSubmitting ? 'opacity-70 cursor-not-allowed' : ''}`}
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