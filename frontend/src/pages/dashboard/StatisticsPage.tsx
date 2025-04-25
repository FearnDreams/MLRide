import React from 'react';
import { BarChart, Wrench } from 'lucide-react';

const StatisticsPage: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center h-full text-center bg-slate-800/30 backdrop-blur-sm rounded-xl border border-slate-700/50">
      <div className="w-16 h-16 rounded-full bg-yellow-500/10 flex items-center justify-center mb-6 ring-4 ring-yellow-500/20">
        <BarChart className="w-8 h-8 text-yellow-400" />
      </div>
      <h2 className="text-2xl font-bold text-white mb-3">统计面板</h2>
      <p className="text-gray-400 max-w-md mx-auto mb-6">
        这里将展示项目资源使用情况、任务执行状态、模型性能等关键指标的统计图表。
      </p>
      <div className="flex items-center gap-2 text-orange-400 bg-orange-500/10 px-4 py-2 rounded-full border border-orange-500/30">
        <Wrench className="w-4 h-4" />
        <span className="text-sm font-medium">该功能正在开发中，敬请期待！</span>
      </div>
    </div>
  );
};

export default StatisticsPage; 