import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { ComponentDefinition, ComponentType, DataType } from '@/store/workflowStore';
import { cn } from '@/lib/utils';
import * as Icons from 'lucide-react';

interface ComponentNodeProps extends NodeProps {
  data: {
    label: string;
    component: ComponentDefinition;
    params: Record<string, any>;
    isSelected?: boolean;
    status?: 'idle' | 'running' | 'success' | 'error';
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
        return 'border-amber-500 bg-amber-500/10';
      case 'success':
        return 'border-green-500 bg-green-500/10';
      case 'error':
        return 'border-red-500 bg-red-500/10';
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

  return (
    <div className={cn(
      'min-w-[180px] rounded-md border-2 shadow-md backdrop-blur-sm bg-slate-800',
      selected ? 'border-blue-500 bg-blue-500/10' : getStatusColor()
    )}>
      {/* 标题 */}
      <div 
        className="px-3 py-2 bg-slate-700/70 rounded-t-sm text-white font-medium border-b border-slate-600 flex items-center"
        style={{ backgroundColor: component.color ? `${component.color}30` : 'rgba(51, 65, 85, 0.7)' }}
      >
        {getIcon()}
        {label}
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
          <div key={`output-${index}`} className="flex items-center justify-between px-2 py-1 relative">
            <span className="text-xs text-slate-400 opacity-60">{output.type.toString().toLowerCase()}</span>
            <span className="text-sm text-slate-300 ml-auto mr-2">{output.label}</span>
            <Handle
              type="source"
              position={Position.Right}
              id={output.id}
              className={`w-3 h-3 ${getPortColor(output.type)}`}
              style={{ right: -6, top: '50%' }}
            />
          </div>
        ))}
        {component.outputs.length === 0 && (
          <div className="px-3 py-1 text-sm text-slate-400">无输出</div>
        )}
      </div>
      
      {/* 状态指示器 */}
      {status !== 'idle' && (
        <div className={cn(
          "text-xs px-2 py-1 text-center",
          status === 'running' ? "text-amber-400" : 
          status === 'success' ? "text-green-400" : 
          "text-red-400"
        )}>
          {status === 'running' ? '运行中...' : 
           status === 'success' ? '完成' : 
           '错误'}
        </div>
      )}
    </div>
  );
});

ComponentNode.displayName = 'ComponentNode';

export default ComponentNode;
