import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/lib/utils';
import useWorkflowStore, { ComponentDefinition, ComponentCategory } from '@/store/workflowStore';
import * as LucideIcons from 'lucide-react';

const ComponentPanel: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeCategory, setActiveCategory] = useState<ComponentCategory>(ComponentCategory.ALL);
  const { components } = useWorkflowStore();

  // 组件分类
  const categories = [
    { id: ComponentCategory.ALL, name: '全部' },
    { id: ComponentCategory.DATA_INPUT, name: '数据输入' },
    { id: ComponentCategory.DATA_PREPROCESSING, name: '数据处理' },
    { id: ComponentCategory.MODEL_TRAINING, name: '模型训练' },
    { id: ComponentCategory.EVALUATION, name: '评估' },
    { id: ComponentCategory.VISUALIZATION, name: '可视化' },
  ];

  // 过滤组件
  const filteredComponents = components.filter(component => {
    const matchesSearch = component.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          component.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = activeCategory === ComponentCategory.ALL || component.category === activeCategory;
    return matchesSearch && matchesCategory;
  });

  // 获取组件图标
  const getComponentIcon = (iconName?: string) => {
    if (!iconName) return null;
    
    const IconComponent = (LucideIcons as any)[iconName];
    if (IconComponent) {
      return <IconComponent className="w-5 h-5 mr-2 text-white opacity-80" />;
    }
    return null;
  };

  // 处理组件拖拽开始
  const handleDragStart = (event: React.DragEvent, component: ComponentDefinition) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify(component));
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="h-full w-full flex flex-col bg-slate-800/30 backdrop-blur-sm">
      {/* 固定的搜索区域 */}
      <div className="p-4 border-b border-slate-700/50 shrink-0">
        <h3 className="text-lg font-semibold text-white mb-3">组件库</h3>
        <div className="relative">
          <Search className="absolute top-2.5 left-3 h-4 w-4 text-slate-400" />
          <Input
            placeholder="搜索组件..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 bg-slate-700/50 border-slate-600/50 text-gray-300 focus:border-blue-500/50"
          />
        </div>
      </div>

      {/* 固定的标签区域 */}
      <div className="px-4 py-2 bg-slate-800/50 border-b border-slate-700/30 shrink-0">
        <div className="flex flex-wrap gap-2">
          {categories.map(category => (
            <button
              key={category.id}
              onClick={() => setActiveCategory(category.id)}
              className={`px-3 py-1 rounded-md text-sm transition-colors ${
                activeCategory === category.id
                  ? "bg-blue-600/70 text-white"
                  : "bg-slate-700/50 text-gray-400 hover:bg-slate-700/70 hover:text-gray-300"
              }`}
            >
              {category.name}
            </button>
          ))}
        </div>
      </div>

      {/* 可滚动的组件列表区域 */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full w-full custom-scrollbar">
          <div className="p-4 grid grid-cols-1 gap-3">
            {filteredComponents.length > 0 ? (
              filteredComponents.map((component) => (
                <div
                  key={component.id}
                  draggable
                  onDragStart={(event) => handleDragStart(event, component)}
                  className="p-3 rounded-md bg-slate-700/50 border border-slate-600/50 cursor-move hover:border-blue-500/50 transition-colors"
                >
                  <div className="font-medium text-white flex items-center">
                    {getComponentIcon(component.icon)}
                    <span>{component.name}</span>
                  </div>
                  <div className="text-sm text-gray-400 mt-1">{component.description}</div>
                  <div className="flex gap-1 mt-2">
                    <span className="px-2 py-0.5 text-xs rounded-full bg-blue-600/30 text-blue-300">
                      {categories.find(c => c.id === component.category)?.name || component.category}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-6 text-center">
                <p className="text-gray-400">未找到匹配的组件</p>
                {searchTerm && (
                  <Button
                    variant="link"
                    className="mt-2 text-blue-400"
                    onClick={() => setSearchTerm('')}
                  >
                    清除搜索
                  </Button>
                )}
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
};

export default ComponentPanel;
