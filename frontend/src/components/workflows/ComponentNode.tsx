import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { ComponentDefinition, ComponentType, DataType } from '@/store/workflowStore';
import { cn } from '@/lib/utils';
import * as Icons from 'lucide-react';
import { Button } from "../ui/button";
import { useState } from "react";
import { Modal } from 'antd';

interface ComponentNodeProps extends NodeProps {
  data: {
    label: string;
    component: ComponentDefinition;
    params: Record<string, any>;
    isSelected?: boolean;
    status?: 'idle' | 'running' | 'success' | 'error' | 'cancelled';
    outputs: Record<string, any>;
  };
}

// 根据数据类型获取端口颜色
const getPortColor = (type: DataType): string => {
  switch (type) {
    case DataType.DATAFRAME:
      return 'bg-blue-500';
    case DataType.MODEL:
      return 'bg-orange-500';
    case DataType.IMAGE:
      return 'bg-purple-500';
    case DataType.NUMBER:
    case DataType.ARRAY:
      return 'bg-green-500';
    case DataType.STRING:
    case DataType.OBJECT:
      return 'bg-yellow-500';
    case DataType.FILE:
      return 'bg-cyan-500';
    default:
      return 'bg-gray-500';
  }
};

// 定义结果查看按钮组件
interface ResultViewButtonProps {
  outputs: {
    image?: string;
    chart?: string;
    chart_type?: string;
    title?: string;
    auc?: number;
    accuracy?: number;
    roc_data?: {
      auc: number[];
      image: string;
    };
    confusion_matrix?: {
      confusion_matrix: {
        image: string;
      };
      accuracy?: number;
    };
    [key: string]: any; // 添加索引签名以支持任意属性
  };
  nodeLabel: string; // 添加节点标签作为属性，用于显示在结果对话框中
}

const ResultViewButton: React.FC<ResultViewButtonProps> = ({ outputs, nodeLabel }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  // 检查是否有可以显示的输出内容
  const hasVisualOutput = () => {
    // 输出调试信息
    console.log("[ResultViewButton] Checking outputs:", outputs);
    
    // 直接图像输出
    if (outputs.image) return true;
    
    // 标准图表格式
    if (outputs.chart) return true;
    
    // 折线图数据
    if (outputs.roc_data && outputs.roc_data.image) return true;
    
    // 混淆矩阵数据 - 扩展检测路径
    if (outputs.confusion_matrix) {
      console.log("[ResultViewButton] Found confusion_matrix:", outputs.confusion_matrix);
      
      // 嵌套在confusion_matrix属性中的情况
      if (
        outputs.confusion_matrix.confusion_matrix && 
        outputs.confusion_matrix.confusion_matrix.image
      ) {
        return true;
      }
    }
    
    // 检查是否有嵌套的输出格式
    if (typeof outputs === 'object') {
      // 尝试在顶层查找chart或image键
      for (const key in outputs) {
        const value = outputs[key];
        if (value && typeof value === 'object') {
          // 使用类型守卫检查属性是否存在
          const item = value as Record<string, unknown>;
          if ('chart' in item && typeof item.chart === 'string') return true;
          if ('image' in item && typeof item.image === 'string') return true;
        }
      }
    }
    
    // 如果节点执行成功但没有图像，仍返回true，总是显示结果按钮
    return true;
  };
  
  // 获取要显示的图像数据
  const getImageData = () => {
    // 输出调试信息
    console.log("[ResultViewButton] getImageData processing outputs:", outputs);
    
    // 直接图像输出
    if (outputs.image) return outputs.image;
    
    // 标准图表格式
    if (outputs.chart) return outputs.chart;
    
    // 折线图数据
    if (outputs.roc_data && outputs.roc_data.image) return outputs.roc_data.image;
    
    // 混淆矩阵数据
    if (outputs.confusion_matrix && 
        outputs.confusion_matrix.confusion_matrix && 
        outputs.confusion_matrix.confusion_matrix.image) {
      return outputs.confusion_matrix.confusion_matrix.image;
    }
    
    // 检查嵌套输出格式
    if (typeof outputs === 'object') {
      for (const key in outputs) {
        const value = outputs[key];
        if (value && typeof value === 'object') {
          const item = value as Record<string, unknown>;
          if ('chart' in item && typeof item.chart === 'string') return item.chart as string;
          if ('image' in item && typeof item.image === 'string') return item.image as string;
        }
      }
    }
    
    // 如果没有找到图像，返回空字符串，此时UI会显示纯文本结果
    console.log("[ResultViewButton] No image found in outputs:", outputs);
    return '';
  };
  
  // 检查是否找到图像
  const imageData = getImageData();
  const hasImageData = imageData !== '';
  
  // 获取图表类型
  const getChartType = () => {
    if (outputs.roc_data) return 'line';
    if (outputs.confusion_matrix) return 'heatmap';
    if (outputs.chart_type === 'heatmap' && outputs.computation === 'confusion_matrix') return 'heatmap';
    return outputs.chart_type || 'generic';
  };
  
  // 获取精度指标
  const getAccuracy = () => {
    // 热力图组件直接输出的准确率
    if (outputs.accuracy !== undefined) {
      return outputs.accuracy;
    }
    // 混淆矩阵嵌套的准确率
    if (outputs.confusion_matrix && outputs.confusion_matrix.accuracy !== undefined) {
      return outputs.confusion_matrix.accuracy;
    }
    // 从结果中提取准确率（处理结果被截断的情况）
    try {
      if (typeof outputs === 'object') {
        for (const key in outputs) {
          const value = outputs[key];
          if (value && typeof value === 'object' && 'accuracy' in value) {
            return value.accuracy;
          }
        }
      }
    } catch (e) {
      console.error("Error extracting accuracy:", e);
    }
    
    return null;
  };
  
  // 获取AUC值
  const getAUC = () => {
    if (outputs.roc_data && outputs.roc_data.auc) {
      return outputs.roc_data.auc[0];
    }
    return outputs.auc;
  };
  
  const chartType = getChartType();
  const accuracy = getAccuracy();
  const auc = getAUC();
  
  return (
    <>
      <Button 
        variant="default" 
        size="sm" 
        onClick={() => setIsOpen(true)}
        className="ml-2"
      >
        查看结果
      </Button>
      
      <Modal
        title={
          <div className="flex items-center">
            <span>{outputs.title || nodeLabel || "可视化结果"}</span>
              {chartType === 'line' && auc !== undefined && (
                <span className="ml-2 text-xs bg-green-600 text-white px-2 py-1 rounded-md">
                  AUC: {auc.toFixed(4)}
                </span>
              )}
              {chartType === 'heatmap' && accuracy !== undefined && (
                <span className="ml-2 text-xs bg-green-600 text-white px-2 py-1 rounded-md">
                  准确率: {accuracy.toFixed(4)}
                </span>
              )}
          </div>
        }
        open={isOpen}
        onCancel={() => setIsOpen(false)}
        destroyOnClose
        className="custom-dark-modal results-modal"
        width="90%"
        style={{ 
          maxWidth: '1200px', 
          top: '40px',
          margin: '0 auto 40px'
        }}
        bodyStyle={{ maxHeight: '80vh', overflow: 'auto', padding: '16px' }}
        footer={(
          <div className="flex justify-end space-x-3 pt-3">
            <Button
              key="close"
              variant="outline"
              size="sm"
              onClick={() => setIsOpen(false)}
              className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white"
            >
              关闭
            </Button>
          </div>
        )}
      >
        <div className="py-4 max-h-[65vh] overflow-y-auto custom-scrollbar">
            {hasImageData ? (
            <div className="flex flex-col items-center">
              <img 
                src={`data:image/png;base64,${imageData}`} 
                alt="可视化结果" 
                className="max-w-full" 
              />
            
            {/* 显示额外信息 */}
            {chartType === 'line' && auc !== undefined && (
                <div className="mt-4 p-3 border border-slate-700 rounded-md w-full max-w-xl">
                <p className="font-bold text-white">ROC曲线详情:</p>
                <p className="text-slate-300">AUC值: {auc.toFixed(4)}</p>
                <p className="text-slate-400 text-sm">该值表示分类器的性能，值越接近1表示分类效果越好</p>
              </div>
            )}
            
            {chartType === 'heatmap' && accuracy !== undefined && (
                <div className="mt-4 p-3 border border-slate-700 rounded-md w-full max-w-xl">
                <p className="font-bold text-white">混淆矩阵详情:</p>
                <p className="text-slate-300">准确率: {accuracy.toFixed(4)}</p>
                <p className="text-slate-400 text-sm">热力图颜色越深表示相应的预测数量越多</p>
              </div>
            )}
          </div>
          ) : (
            <div className="p-4 bg-slate-800 rounded-md">
              <p className="text-slate-300">该组件已执行成功，但没有生成可视化图像。</p>
              <pre className="mt-4 p-3 bg-slate-900 rounded-md overflow-auto text-xs text-slate-300 max-h-60 custom-scrollbar">
                {JSON.stringify(outputs, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </Modal>
    </>
  );
};

const ComponentNode = memo(({ data, selected }: ComponentNodeProps) => {
  const { label, component, status = 'idle' } = data;
  
  // 获取组件的默认颜色
  const getComponentDefaultColor = () => {
    const typeColors = {
      [ComponentType.INPUT]: 'border-green-500 bg-green-500/10',
      [ComponentType.PROCESS]: 'border-blue-500 bg-blue-500/10',
      [ComponentType.MODEL]: 'border-orange-500 bg-orange-500/10',
      [ComponentType.EVALUATION]: 'border-purple-500 bg-purple-500/10',
      [ComponentType.VISUALIZATION]: 'border-pink-500 bg-pink-500/10',
      [ComponentType.EXPORT]: 'border-cyan-500 bg-cyan-500/10',
      [ComponentType.CUSTOM]: 'border-slate-500 bg-slate-800/50',
    };
    return typeColors[component.type] || 'border-slate-500 bg-slate-800/50';
  };
  
  // 根据状态设置节点样式
  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return 'border-amber-500 bg-amber-500/10 shadow-md shadow-amber-500/20';
      case 'success':
        return 'border-green-500 bg-green-500/10 shadow-md shadow-green-500/20';
      case 'error':
        return 'border-red-500 bg-red-500/10 shadow-md shadow-red-500/20';
      case 'cancelled':
        return 'border-slate-500 bg-slate-500/10 shadow-md shadow-slate-500/20';
      default:
        return getComponentDefaultColor();
    }
  };

  // 动态获取图标
  const getIcon = () => {
    if (component.icon && typeof component.icon === 'string') {
      const IconComponent = (Icons as any)[component.icon];
      if (IconComponent) {
        return <IconComponent className="w-4 h-4 mr-2" />;
      }
    }
    return null;
  };

  // 获取状态图标
  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return <div className="animate-spin h-3 w-3 border-2 border-amber-500 border-t-transparent rounded-full" />;
      case 'success':
        return <Icons.CheckCircle className="w-3 h-3 text-green-400" />;
      case 'error':
        return <Icons.XCircle className="w-3 h-3 text-red-400" />;
      case 'cancelled':
        return <Icons.Ban className="w-3 h-3 text-slate-400" />;
      default:
        return <Icons.Circle className="w-3 h-3 text-slate-400" />;
    }
  };

  // 获取状态文本
  const getStatusText = () => {
    switch (status) {
      case 'running':
        return '执行中';
      case 'success':
        return '已完成';
      case 'error':
        return '失败';
      case 'cancelled':
        return '已取消';
      default:
        return '未执行';
    }
  };

  return (
    <div className={cn(
      'min-w-[180px] rounded-md border-2 shadow-md backdrop-blur-sm bg-slate-800 status-indicator',
      selected ? 'border-blue-500 bg-blue-500/10' : getStatusColor(),
      status === 'running' ? 'status-running' : 
      status === 'success' ? 'status-success' : 
      status === 'error' ? 'status-error' : 
      status === 'cancelled' ? 'status-cancelled' : ''
    )}>
      {/* 标题 */}
      <div 
        className="px-3 py-2 bg-slate-700/70 rounded-t-sm text-white font-medium border-b border-slate-600 flex items-center"
        style={{ backgroundColor: component.color ? `${component.color}30` : 'rgba(51, 65, 85, 0.7)' }}
      >
        {getIcon()}
        {label}
        
        {/* 添加小状态指示器在右侧 */}
        {status !== 'idle' && (
          <div className="ml-auto">
            {getStatusIcon()}
          </div>
        )}
      </div>
      
      {/* 输入句柄 */}
      <div className="py-2 border-b border-slate-600/50">
        {component.inputs.map((input, index) => (
          <div key={`input-${index}`} className="flex items-center px-2 py-1 relative">
            <Handle
              type="target"
              position={Position.Left}
              id={input.id}
              className={`w-3 h-3 ${getPortColor(input.type)}`}
              style={{ left: -6, top: '50%' }}
            />
            <span className="text-sm text-slate-300 ml-2">{input.label}</span>
            <span className="text-xs text-slate-400 ml-auto opacity-60">{input.type.toString().toLowerCase()}</span>
          </div>
        ))}
        {/* 特殊处理 CSV 输入组件的文件状态显示 */}
        {component.id === 'csv-input' && (
          <div className="px-3 py-1 text-sm text-slate-300">
            {data.params?.file_path ? (
              typeof data.params.file_path === 'string' ? (
                (() => {
                  const filePathString = data.params.file_path as string;
                  const fileName = filePathString.split('\\').pop()?.split('/').pop() || filePathString;
                  return <span title={filePathString}>文件: {fileName}</span>;
                })()
              ) : data.params.file_path instanceof File ? (
                <span title={data.params.file_path.name}>已选: {data.params.file_path.name}</span>
              ) : (
                '无文件指定'
              )
            ) : (
              '无文件指定'
            )}
          </div>
        )}
        {/* 对于非CSV输入组件，如果 inputs 为空，则显示无输入 */}
        {component.id !== 'csv-input' && component.inputs.length === 0 && (
          <div className="px-3 py-1 text-sm text-slate-400">无输入</div>
        )}
      </div>
      
      {/* 输出句柄 */}
      <div className="py-2">
        {component.outputs.map((output, index) => (
          <div key={`output-${index}`} className="flex items-center px-2 py-1 relative">
            <span className="text-sm text-slate-300 mr-auto">{output.label}</span>
            <span className="text-xs text-slate-400 opacity-60">{output.type.toString().toLowerCase()}</span>
            <Handle
              type="source"
              position={Position.Right}
              id={output.id}
              className={`w-3 h-3 ${getPortColor(output.type)}`}
              style={{ right: -6, top: '50%' }}
            />
          </div>
        ))}
      </div>
      
      {/* 状态指示器和结果查看按钮 */}
      <div className="flex items-center justify-between px-2 py-1 border-t border-slate-600/50">
          <div className={cn(
          "text-xs py-1 flex items-center gap-1",
            status === 'running' ? "text-amber-400" : 
            status === 'success' ? "text-green-400" : 
            status === 'error' ? "text-red-400" :
            status === 'cancelled' ? "text-slate-400" :
            "text-slate-400"
          )}>
          {getStatusIcon()}
          {getStatusText()}
          </div>
        
        {status === 'success' && (
          <div>
            {/* 总是在状态为success时显示查看结果按钮，不关心outputs是否为空 */}
            <ResultViewButton outputs={data.outputs || {}} nodeLabel={label} />
          </div>
        )}
      </div>
    </div>
  );
});

ComponentNode.displayName = 'ComponentNode';

export default ComponentNode;
