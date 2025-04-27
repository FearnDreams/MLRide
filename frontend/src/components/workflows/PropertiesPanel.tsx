import React, { useEffect, useState } from 'react';
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

const PropertiesPanel: React.FC = () => {
  const { selectedNode, updateNodeParameters } = useWorkflowStore();
  const [localParams, setLocalParams] = useState<Record<string, any>>({});
  
  // 当选中节点变化时，更新本地参数
  useEffect(() => {
    if (selectedNode && selectedNode.data.params) {
      setLocalParams(selectedNode.data.params);
    } else {
      setLocalParams({});
    }
  }, [selectedNode]);

  // 处理参数变化
  const handleParamChange = (paramName: string, value: any) => {
    setLocalParams(prev => ({
      ...prev,
      [paramName]: value
    }));
  };

  // 应用参数到节点
  const handleApplyChanges = () => {
    if (selectedNode) {
      updateNodeParameters(selectedNode.id, localParams);
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
        // TODO: 实现文件选择组件
        return (
          <div className="text-slate-400 text-sm">文件选择组件尚未实现</div>
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
  const params: ParamDefinition[] = selectedNode.data.component.params || [];

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
                  return (
                    <div key={param.name} className="space-y-2">
                      <Label htmlFor={param.name} className="text-slate-300">
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
