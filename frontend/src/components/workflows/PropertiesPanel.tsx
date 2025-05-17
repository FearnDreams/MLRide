import React, { useEffect, useState, useRef } from 'react';
import { ScrollArea } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Sliders, X } from 'lucide-react';
import useWorkflowStore, { ParamDefinition } from '@/store/workflowStore';
import { toast } from 'sonner';
import { useParams } from 'react-router-dom';

// 获取CSRF token的辅助函数
function getCookie(name: string): string | null {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// 从URL获取项目ID
function getProjectIdFromUrl(): string | null {
  // 从URL中提取项目ID
  const pathname = window.location.pathname;
  const matches = pathname.match(/\/projects\/([^/]+)/);
  return matches ? matches[1] : null;
}

// 声明全局autoSaveWorkflow函数接口，以避免类型错误
declare global {
  interface Window {
    autoSaveWorkflow?: () => Promise<any>;
  }
}

const PropertiesPanel: React.FC = () => {
  const { selectedNode, updateNodeParameters } = useWorkflowStore();
  const [localParams, setLocalParams] = useState<Record<string, any>>({});
  
  // 添加文件输入引用
  const fileInputRef = useRef<Record<string, HTMLInputElement | null>>({});
  
  // 当选中节点变化时，更新本地参数
  useEffect(() => {
    if (selectedNode) {
      console.log('[PropertiesPanel] Selected Node ID:', selectedNode.data.id);
      console.log('[PropertiesPanel] Selected Node Component Label:', selectedNode.data.label);
      console.log('[PropertiesPanel] Params from selectedNode.data.component.params:', selectedNode.data.component?.params);
      if (selectedNode.data.params) {
        setLocalParams(selectedNode.data.params);
      } else {
        setLocalParams({});
      }
    } else {
      setLocalParams({});
    }
  }, [selectedNode]);

  // 处理参数变化
  const handleParamChange = (paramName: string, value: any) => {
    console.log('[PropertiesPanel] handleParamChange:', { paramName, value, type: typeof value });
    if (value instanceof File) {
      console.log('[PropertiesPanel] File selected:', { name: value.name, size: value.size, type: value.type });
    }
    setLocalParams(prev => ({
      ...prev,
      [paramName]: value
    }));
  };

  // 应用参数到节点
  const handleApplyChanges = () => {
    if (selectedNode) {
      console.log('[PropertiesPanel] handleApplyChanges - Node ID:', selectedNode.id);
      console.log('[PropertiesPanel] handleApplyChanges - Local params to apply:', localParams);
      
      // 处理更新的参数，特别是对文件类型的处理
      const processedParams = { ...localParams };
      
      // 如果是CSV组件，确保文件参数保存了足够的信息
      if (selectedNode.data.component?.id === 'csv-input') {
        const fileParam = processedParams.file_path;
        
        // 如果是File对象，保存文件信息
        if (fileParam instanceof File) {
          console.log(`[PropertiesPanel] Processing File object for CSV input:`, fileParam);
          
          // 保存文件的关键信息，确保更新后能被前端代码识别
          processedParams._file_info = {
            name: fileParam.name,
            size: fileParam.size,
            type: fileParam.type,
            lastModified: fileParam.lastModified
          };
        }
      }
      
      // 更新节点参数
      updateNodeParameters(selectedNode.id, processedParams);
      toast.success('参数已应用!');
    } else {
      console.warn('[PropertiesPanel] handleApplyChanges - No node selected.');
      toast.info('没有选中的节点可应用参数。');
    }
  };

  // 查找文件上传处理相关的代码
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>, paramName: string) => {
    if (!e.target.files || e.target.files.length === 0) return;
    
    const file = e.target.files[0];
    console.log(`[PropertiesPanel] File selected for ${paramName}:`, file.name);
    
    // 将文件对象存储在节点参数中
    const updatedParams = {
      ...localParams,
      [paramName]: file,
      // 添加文件信息以便在服务器路径可用后保存
      _file_info: {
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified,
        // serverPath会在上传后填充
      }
    };
    
    // 更新节点参数
    handleParamChange(paramName, updatedParams[paramName]);
    
    // 如果是CSV组件的文件上传，尝试立即预上传文件以获取服务器路径
    if (selectedNode?.data?.component?.id === 'csv-input' && paramName === 'file_path') {
      try {
        // 获取projectId
        const projectId = getProjectIdFromUrl();
        if (!projectId) {
          toast.error('无法获取项目ID，无法预上传文件');
          return;
        }
        
        console.log(`[PropertiesPanel] 开始预上传CSV文件到项目 ${projectId}`);
        
        // 创建FormData
        const formData = new FormData();
        formData.append('file', file);
        
        // 获取CSRF token
        const csrftoken = getCookie('csrftoken');
        const headers: HeadersInit = {};
        if (csrftoken) {
          headers['X-CSRFToken'] = csrftoken;
        }
        
        // 先确保uploads目录存在 - 修复API路径
        try {
          const checkDirResponse = await fetch(`/api/project/projects/${projectId}/ensure-uploads-directory/`, {
            method: 'POST',
            headers: {
              ...headers,
              'Content-Type': 'application/json',
            },
          });
          
          if (checkDirResponse.ok) {
            console.log('[PropertiesPanel] 已确认uploads目录存在');
          } else {
            console.warn('[PropertiesPanel] 无法确认uploads目录，但将继续尝试上传文件');
          }
        } catch (dirErr) {
          console.warn('[PropertiesPanel] 确认uploads目录时出错，但将继续尝试上传文件:', dirErr);
        }
        
        // 发送上传请求
        const response = await fetch(`/api/project/projects/${projectId}/upload-file/`, {
          method: 'POST',
          headers: headers,
          body: formData,
        });
        
        if (!response.ok) {
          toast.error(`文件预上传失败: ${response.statusText}`);
          return;
        }
        
        const uploadData = await response.json();
        console.log(`[PropertiesPanel] 文件预上传成功，服务器路径: ${uploadData.file_path}`);
        
        // 规范化路径（将反斜杠转为正斜杠）
        const normalizedServerPath = uploadData.file_path.replace(/\\/g, '/');
        
        // 更新节点参数中的文件信息和服务器路径
        const finalParams = {
          ...updatedParams,
          // 重要：实际路径使用服务器返回的路径，而不是File对象
          [paramName]: normalizedServerPath,
          _file_info: {
            ...updatedParams._file_info,
            serverPath: normalizedServerPath
          }
        };
        
        // 更新节点参数
        updateNodeParameters(selectedNode.id, finalParams);
        
        // 成功提示
        toast.success(`文件 ${file.name} 已成功上传`);
        
        // 确保工作流自动保存
        if (typeof window !== 'undefined' && 
            window.autoSaveWorkflow && 
            typeof window.autoSaveWorkflow === 'function') {
          try {
            console.log('[PropertiesPanel] 尝试自动保存工作流...');
            await window.autoSaveWorkflow();
          } catch (e) {
            console.error('[PropertiesPanel] 自动保存工作流失败:', e);
          }
        }
      } catch (error) {
        console.error('[PropertiesPanel] 文件预上传出错:', error);
        toast.error(`文件预上传失败: ${error instanceof Error ? error.message : '未知错误'}`);
      }
    }
  };

  // 渲染参数编辑器
  const renderParamEditor = (param: ParamDefinition, value: any) => {
    switch (param.type) {
      case 'string':
        return (
          <Input
            id={param.name}
            value={value || ''}
            placeholder={param.placeholder || `请输入${param.label}`}
            onChange={(e) => handleParamChange(param.name, e.target.value)}
            className="bg-slate-700/50 border-slate-600/50 text-gray-300"
          />
        );
      case 'number':
        return (
          <Input
            id={param.name}
            type="number"
            value={value || 0}
            min={param.min}
            max={param.max}
            step={param.step}
            onChange={(e) => handleParamChange(param.name, Number(e.target.value))}
            className="bg-slate-700/50 border-slate-600/50 text-gray-300"
          />
        );
      case 'boolean':
        return (
          <Switch
            id={param.name}
            checked={!!value}
            onCheckedChange={(checked) => handleParamChange(param.name, checked)}
          />
        );
      case 'text':
        return (
          <Textarea
            id={param.name}
            value={value || ''}
            placeholder={param.placeholder || `请输入${param.label}`}
            onChange={(e) => handleParamChange(param.name, e.target.value)}
            className="min-h-24 bg-slate-700/50 border-slate-600/50 text-gray-300"
          />
        );
      case 'select':
        return (
          <Select
            value={value || param.defaultValue}
            onValueChange={(val) => handleParamChange(param.name, val)}
          >
            <SelectTrigger className="bg-slate-700/50 border-slate-600/50 text-gray-300">
              <SelectValue placeholder={`请选择${param.label}`} />
            </SelectTrigger>
            <SelectContent className="bg-slate-800/90 border-slate-700/50 text-gray-300">
              {(param.options || []).map(
                (option) => (
                  <SelectItem
                    key={option.value}
                    value={option.value}
                    className="focus:bg-slate-700/50 focus:text-white"
                  >
                    {option.label}
                  </SelectItem>
                )
              )}
            </SelectContent>
          </Select>
        );
      case 'multiselect':
        // TODO: 实现多选组件
        return (
          <div className="text-slate-400 text-sm">多选组件尚未实现</div>
        );
      case 'color':
        return (
          <Input
            id={param.name}
            type="color"
            value={value || '#000000'}
            onChange={(e) => handleParamChange(param.name, e.target.value)}
            className="h-10 w-full bg-slate-700/50 border-slate-600/50"
          />
        );
      case 'file':
        const inputId = `file-input-${param.name}`;
        const selectedFile = value as File | null;
        return (
          <div className="flex items-center space-x-2 mb-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => fileInputRef.current?.[param.name]?.click()}
              className="w-full"
            >
              {localParams[param.name] instanceof File
                ? (localParams[param.name] as File).name
                : localParams._file_info?.name || '选择文件'}
            </Button>
            <input
              key={`file-input-${param.name}`}
              ref={(el) => { if (fileInputRef.current) fileInputRef.current[param.name] = el; }}
              type="file"
              accept={param.accept || '.csv'} // 使用param.accept或默认值
              onChange={(e) => handleFileChange(e, param.name)}
              className="hidden" // Hide the actual input
            />
          </div>
        );
      default:
        return (
          <Input
            id={param.name}
            value={String(value) || ''}
            onChange={(e) => handleParamChange(param.name, e.target.value)}
            className="bg-slate-700/50 border-slate-600/50 text-gray-300"
          />
        );
    }
  };

  // 如果没有选中节点，显示提示信息
  if (!selectedNode) {
    return (
      <div className="h-full w-full bg-slate-800/30 backdrop-blur-sm flex flex-col">
        <div className="p-4 border-b border-slate-700/50 flex justify-between items-center shrink-0">
          <h3 className="text-lg font-semibold text-white flex items-center">
            <Sliders className="w-5 h-5 mr-2" />
            属性面板
          </h3>
        </div>
        <div className="flex-1 flex items-center justify-center p-6 text-center">
          <div className="text-slate-400">
            <p>请选择一个节点</p>
            <p className="text-sm mt-2">选中节点后可在此处编辑其属性</p>
          </div>
        </div>
      </div>
    );
  }

  // 获取参数列表和类型
  const params: ParamDefinition[] = selectedNode?.data?.component?.params || [];

  return (
    <div className="h-full w-full bg-slate-800/30 backdrop-blur-sm flex flex-col">
      <div className="p-4 border-b border-slate-700/50 flex justify-between items-center shrink-0">
        <h3 className="text-lg font-semibold text-white flex items-center">
          <Sliders className="w-5 h-5 mr-2" />
          属性面板
        </h3>
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={() => useWorkflowStore.getState().setSelectedNode(null)}
          className="h-8 w-8 text-slate-400 hover:text-white"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1 w-full custom-scrollbar">
        <div className="p-4">
          <Card className="bg-slate-800/50 border-slate-700/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-white">{selectedNode.data.label}</CardTitle>
            </CardHeader>
            <CardContent className="custom-scrollbar">
              <div className="space-y-4">
                {params.map((param: ParamDefinition) => {
                  // 检查是否应该显示该参数（条件显示）
                  if (param.showWhen) {
                    const { field, value } = param.showWhen;
                    // 如果条件字段的值不匹配，则不显示此参数
                    if (localParams[field] !== value) {
                      return null;
                    }
                  }
                  
                  return (
                    <div key={param.name} className="space-y-2">
                      <Label 
                        htmlFor={param.name} 
                        className="text-slate-300"
                      >
                        {param.label}
                      </Label>
                      {renderParamEditor(param, localParams[param.name])}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <div className="mt-4 flex justify-end">
            <Button 
              onClick={handleApplyChanges}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              应用更改
            </Button>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
};

export default PropertiesPanel;
