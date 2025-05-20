import React, { useState, useEffect } from 'react';
import { 
  BarChart, 
  HardDrive, 
  BookOpen, 
  FolderOpen, 
  Image as ImageIcon, 
  Database, 
  Clock, 
  Activity, 
  AlertCircle, 
  PlayCircle, 
  StopCircle,
  Layers,
  RefreshCw,
  PieChart,
  TrendingUp,
  UserCircle2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, Spin, Empty, Tooltip, Progress } from 'antd';
import { Chart as ChartJS, ArcElement, Tooltip as ChartTooltip, Legend, CategoryScale, LinearScale, BarElement, Title, PointElement, LineElement } from 'chart.js';
import { Pie, Bar, Line } from 'react-chartjs-2';
import { getProjects } from '@/services/projects';
import { imagesService } from '@/services/images';
import { datasetsService } from '@/services/datasets';
import { authService } from '@/services/auth';

// 注册 Chart.js 组件
ChartJS.register(
  ArcElement, 
  ChartTooltip, 
  Legend, 
  CategoryScale, 
  LinearScale, 
  BarElement, 
  Title,
  PointElement,
  LineElement
);

// Helper function to format date to YYYY-MM-DD using UTC
const formatDateToYyyyMmDd = (dateString: string | Date): string => {
  const date = new Date(dateString);
  const year = date.getUTCFullYear();
  const month = (date.getUTCMonth() + 1).toString().padStart(2, '0'); // getUTCMonth is 0-indexed
  const day = date.getUTCDate().toString().padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// Helper function to get the last N days as YYYY-MM-DD strings using UTC
const getLastNDays = (n: number): string[] => {
  const dates: string[] = [];
  for (let i = 0; i < n; i++) {
    const d = new Date();
    // Set date to i days ago in UTC
    d.setUTCDate(d.getUTCDate() - i);
    dates.push(formatDateToYyyyMmDd(d)); // This now uses the UTC-aware version
  }
  return dates.reverse(); // oldest to newest
};

const StatisticsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [projectStats, setProjectStats] = useState<any>(null);
  const [imageStats, setImageStats] = useState<any>(null);
  const [datasetStats, setDatasetStats] = useState<any>(null);
  const [userStats, setUserStats] = useState<any>(null);
  const [dailyActivityStats, setDailyActivityStats] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  // 获取所有统计数据
  const fetchAllStats = async () => {
    setLoading(true);
    try {
      const projectsResponse = await getProjects();
      let rawProjects: any[] = [];
      if (projectsResponse && projectsResponse.data) {
        rawProjects = Array.isArray(projectsResponse.data) 
          ? projectsResponse.data 
          : projectsResponse.data.results || [];
        
        const projectTypes: Record<string, number> = {};
        const projectStatuses: Record<string, number> = {};
        let runningProjects = 0;
        let totalProjects = rawProjects.length;
        
        rawProjects.forEach((project: any) => {
          const type = project.project_type || 'unknown';
          projectTypes[type] = (projectTypes[type] || 0) + 1;
          const status = project.status || 'unknown';
          projectStatuses[status] = (projectStatuses[status] || 0) + 1;
          if (status === 'running') {
            runningProjects++;
          }
        });
        
        setProjectStats({
          total: totalProjects,
          running: runningProjects,
          types: projectTypes,
          statuses: projectStatuses,
          projects: rawProjects 
        });
      }
      
      const imagesResponse = await imagesService.getUserImages();
      let rawImages: any[] = [];
      if (imagesResponse && imagesResponse.status === 'success' && imagesResponse.data) {
        rawImages = Array.isArray(imagesResponse.data) ? imagesResponse.data : [];
        const imageStatuses: Record<string, number> = {};
        let totalImages = rawImages.length;
        let readyImages = 0;
        
        rawImages.forEach(image => {
          const status = image.status || 'unknown';
          imageStatuses[status] = (imageStatuses[status] || 0) + 1;
          if (status === 'ready') {
            readyImages++;
          }
        });
        
        setImageStats({
          total: totalImages,
          ready: readyImages,
          statuses: imageStatuses,
          images: rawImages 
        });
      }
      
      const datasetsResponse = await datasetsService.getUserDatasets();
      let rawDatasets: any[] = [];
      if (datasetsResponse && datasetsResponse.status === 'success' && datasetsResponse.data) {
        rawDatasets = Array.isArray(datasetsResponse.data) ? datasetsResponse.data : [];
        const datasetTypes: Record<string, number> = {};
        let totalSize = 0;
        
        rawDatasets.forEach(dataset => {
          const fileType = dataset.file_type || 'unknown';
          datasetTypes[fileType] = (datasetTypes[fileType] || 0) + 1;
          totalSize += dataset.file_size || 0;
        });
        
        setDatasetStats({
          total: rawDatasets.length,
          totalSize: totalSize,
          types: datasetTypes,
          datasets: rawDatasets 
        });
      }
      
      // Process data for daily activity chart (last 7 days)
      const last7Days = getLastNDays(7); // This will now use UTC days
      const activityData: {
        dates: string[];
        projects: number[];
        images: number[];
        datasets: number[];
      } = {
        dates: last7Days,
        projects: Array(7).fill(0),
        images: Array(7).fill(0),
        datasets: Array(7).fill(0),
      };

      rawProjects.forEach(p => {
        if (p.created_at) {
          const creationDate = formatDateToYyyyMmDd(p.created_at); // This will now use UTC
          const index = last7Days.indexOf(creationDate);
          if (index !== -1) {
            activityData.projects[index]++;
          }
        }
      });

      rawImages.forEach(img => {
        // Assuming images have a 'created_at' field. If not, this won't work.
        // Replace 'created_at' with actual field name if different.
        // CORRECTED: Image interface uses 'created' field for creation timestamp
        if (img.created) { 
          const creationDate = formatDateToYyyyMmDd(img.created); // Use img.created
          const index = last7Days.indexOf(creationDate);
          if (index !== -1) {
            activityData.images[index]++;
          }
        }
      });
      
      rawDatasets.forEach(ds => {
        // Assuming datasets have a 'created_at' field. If not, this won't work.
        // Replace 'created_at' with actual field name if different.
        // CORRECTED: Dataset interface uses 'created' field for creation timestamp
        if (ds.created) { 
          const creationDate = formatDateToYyyyMmDd(ds.created); // Use ds.created
          const index = last7Days.indexOf(creationDate);
          if (index !== -1) {
            activityData.datasets[index]++;
          }
        }
      });
      setDailyActivityStats(activityData);

      const userProfileResponse = await authService.getUserProfile();
      if (userProfileResponse && userProfileResponse.status === 'success' && userProfileResponse.data) {
        setUserStats({
          username: userProfileResponse.data.username,
          email: userProfileResponse.data.email,
          createdAt: userProfileResponse.data.created_at
        });
      }
      
    } catch (error) {
      console.error('获取统计数据失败:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };
  
  // 初始加载数据
  useEffect(() => {
    fetchAllStats();
  }, []);
  
  // 处理刷新
  const handleRefresh = () => {
    setRefreshing(true);
    fetchAllStats();
  };

  // 生成项目类型图表数据
  const getProjectTypeChartData = () => {
    if (!projectStats || !projectStats.types) return null;
    
    const types = projectStats.types;
    const typeLabels: Record<string, string> = {
      'notebook': 'Jupyter Notebook',
      'canvas': '可视化画布',
      'unknown': '未知类型'
    };
    
    return {
      labels: Object.keys(types).map(type => typeLabels[type] || type),
      datasets: [
        {
          label: '项目数量',
          data: Object.values(types),
          backgroundColor: [
            'rgba(54, 162, 235, 0.6)',
            'rgba(153, 102, 255, 0.6)',
            'rgba(255, 159, 64, 0.6)',
            'rgba(75, 192, 192, 0.6)',
          ],
          borderColor: [
            'rgba(54, 162, 235, 1)',
            'rgba(153, 102, 255, 1)',
            'rgba(255, 159, 64, 1)',
            'rgba(75, 192, 192, 1)',
          ],
          borderWidth: 1,
        },
      ],
    };
  };

  // 生成项目状态图表数据
  const getProjectStatusChartData = () => {
    if (!projectStats || !projectStats.statuses) return null;
    
    const statuses = projectStats.statuses;
    const statusLabels: Record<string, string> = {
      'running': '运行中',
      'stopped': '已停止',
      'error': '错误',
      'creating': '创建中',
      'unknown': '未知状态'
    };
    
    return {
      labels: Object.keys(statuses).map(status => statusLabels[status] || status),
      datasets: [
        {
          label: '项目数量',
          data: Object.values(statuses),
          backgroundColor: [
            'rgba(75, 192, 192, 0.6)',
            'rgba(201, 203, 207, 0.6)',
            'rgba(255, 99, 132, 0.6)',
            'rgba(255, 205, 86, 0.6)',
            'rgba(54, 162, 235, 0.6)',
          ],
          borderColor: [
            'rgba(75, 192, 192, 1)',
            'rgba(201, 203, 207, 1)',
            'rgba(255, 99, 132, 1)',
            'rgba(255, 205, 86, 1)',
            'rgba(54, 162, 235, 1)',
          ],
          borderWidth: 1,
        },
      ],
    };
  };

  // 生成镜像状态图表数据
  const getImageStatusChartData = () => {
    if (!imageStats || !imageStats.statuses) return null;
    
    const statuses = imageStats.statuses;
    const statusLabels: Record<string, string> = {
      'ready': '就绪',
      'building': '构建中',
      'pending': '等待中',
      'failed': '失败',
      'unknown': '未知状态'
    };
    
    return {
      labels: Object.keys(statuses).map(status => statusLabels[status] || status),
      datasets: [
        {
          label: '镜像数量',
          data: Object.values(statuses),
          backgroundColor: [
            'rgba(75, 192, 192, 0.6)',
            'rgba(54, 162, 235, 0.6)',
            'rgba(255, 205, 86, 0.6)',
            'rgba(255, 99, 132, 0.6)',
            'rgba(201, 203, 207, 0.6)',
          ],
          borderColor: [
            'rgba(75, 192, 192, 1)',
            'rgba(54, 162, 235, 1)',
            'rgba(255, 205, 86, 1)',
            'rgba(255, 99, 132, 1)',
            'rgba(201, 203, 207, 1)',
          ],
          borderWidth: 1,
        },
      ],
    };
  };

  // 生成数据集类型图表数据
  const getDatasetTypeChartData = () => {
    if (!datasetStats || !datasetStats.types) return null;
    
    const types = datasetStats.types;
    const colors = [
      'rgba(255, 99, 132, 0.6)',
      'rgba(54, 162, 235, 0.6)',
      'rgba(255, 206, 86, 0.6)',
      'rgba(75, 192, 192, 0.6)',
      'rgba(153, 102, 255, 0.6)',
      'rgba(255, 159, 64, 0.6)',
      'rgba(201, 203, 207, 0.6)'
    ];
    const borderColors = colors.map(c => c.replace('0.6', '1'));
    
    return {
      labels: Object.keys(types),
      datasets: [
        {
          label: '文件数量',
          data: Object.values(types),
          backgroundColor: colors.slice(0, Object.keys(types).length),
          borderColor: borderColors.slice(0, Object.keys(types).length),
          borderWidth: 1,
        },
      ],
    };
  };

  // 生成最近活动趋势图表数据
  const getDailyActivityChartData = () => {
    if (!dailyActivityStats) return null;

    return {
      labels: dailyActivityStats.dates,
      datasets: [
        {
          label: '项目创建数',
          data: dailyActivityStats.projects,
          borderColor: 'rgba(54, 162, 235, 0.8)',
          backgroundColor: 'rgba(54, 162, 235, 0.2)',
          tension: 0.3,
          fill: true,
        },
        {
          label: '镜像创建数',
          data: dailyActivityStats.images,
          borderColor: 'rgba(153, 102, 255, 0.8)',
          backgroundColor: 'rgba(153, 102, 255, 0.2)',
          tension: 0.3,
          fill: true,
        },
        {
          label: '数据集上传数',
          data: dailyActivityStats.datasets,
          borderColor: 'rgba(75, 192, 192, 0.8)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          tension: 0.3,
          fill: true,
        },
      ],
    };
  };

  // 图表样式选项
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          color: 'rgba(255, 255, 255, 0.8)',
          padding: 16,
          font: {
            size: 12
          }
        }
      }
    }
  };

  // 表格样式选项（带标题）
  const chartOptionsWithTitle = {
    ...chartOptions,
    plugins: {
      ...chartOptions.plugins,
      title: {
        display: true,
        text: '',
        color: 'rgba(255, 255, 255, 0.8)',
        font: {
          size: 16,
          weight: 'normal' as const
        }
      }
    }
  };

  // 渲染加载中状态
  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Spin size="large" tip="加载统计数据中..." />
      </div>
    );
  }

  // 渲染没有数据的状态
  if (!projectStats && !imageStats && !datasetStats) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <div className="text-gray-300">暂无统计数据</div>
        }
      >
        <Button
          onClick={handleRefresh}
          className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white"
        >
          <RefreshCw className="w-4 h-4 mr-2" /> 刷新数据
        </Button>
      </Empty>
    );
  }

  return (
    <div className="flex-1 space-y-6">
      {/* 顶部控制栏 */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">数据统计面板</h1>
        <Button
          onClick={handleRefresh}
          disabled={refreshing}
          className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white"
        >
          {refreshing ? (
            <>
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> 刷新中...
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4 mr-2" /> 刷新数据
            </>
          )}
        </Button>
      </div>

      {/* 概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* 项目统计卡片 */}
        <Card
          className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 shadow-md"
          bodyStyle={{ padding: 0 }}
        >
          <div className="p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                <FolderOpen className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-gray-400 text-sm">项目总数</p>
                <h3 className="text-2xl font-bold text-white">
                  {projectStats?.total || 0}
                </h3>
              </div>
            </div>
            <div className="flex items-center mt-4 gap-2 text-sm text-gray-400">
              <div className="flex items-center">
                <PlayCircle className="w-4 h-4 text-green-400 mr-1" />
                <span>运行中: {projectStats?.running || 0}</span>
              </div>
              <span className="text-gray-600">|</span>
              <div className="flex items-center">
                <StopCircle className="w-4 h-4 text-gray-400 mr-1" />
                <span>已停止: {(projectStats?.total || 0) - (projectStats?.running || 0)}</span>
              </div>
            </div>
          </div>
        </Card>

        {/* 镜像统计卡片 */}
        <Card
          className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 shadow-md"
          bodyStyle={{ padding: 0 }}
        >
          <div className="p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center">
                <ImageIcon className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <p className="text-gray-400 text-sm">镜像总数</p>
                <h3 className="text-2xl font-bold text-white">
                  {imageStats?.total || 0}
                </h3>
              </div>
            </div>
            <div className="flex items-center mt-4 gap-1 text-sm text-gray-400">
              <div className="flex-1 ready-images-progress-container">
                <span className="block mb-1">就绪镜像比例</span>
                <Progress 
                  percent={Math.round((imageStats?.ready || 0) / (imageStats?.total || 1) * 100)}
                  size="small"
                  status="active" 
                  strokeColor="#A78BFA"
                />
              </div>
            </div>
          </div>
        </Card>

        {/* 数据集统计卡片 */}
        <Card
          className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 shadow-md"
          bodyStyle={{ padding: 0 }}
        >
          <div className="p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center">
                <Database className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <p className="text-gray-400 text-sm">数据集总数</p>
                <h3 className="text-2xl font-bold text-white">
                  {datasetStats?.total || 0}
                </h3>
              </div>
            </div>
            <div className="flex items-center mt-4 gap-2 text-sm text-gray-400">
              <div className="flex items-center">
                <HardDrive className="w-4 h-4 text-green-400 mr-1" />
                <span>总存储: {formatBytes(datasetStats?.totalSize || 0)}</span>
              </div>
            </div>
          </div>
        </Card>

        {/* 用户信息卡片 (Previously System Resource Card) */}
        <Card
          className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 shadow-md"
          bodyStyle={{ padding: 0 }}
        >
          <div className="p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-full bg-sky-500/20 flex items-center justify-center">
                <UserCircle2 className="w-6 h-6 text-sky-400" />
              </div>
              <div>
                <p className="text-gray-400 text-sm">用户信息</p>
                <h3 className="text-xl font-bold text-white">
                  {userStats?.username || 'N/A'}
                </h3>
              </div>
            </div>
            <div className="mt-4 space-y-2 text-sm text-gray-300">
              <div><span className="font-medium text-gray-400">邮箱:</span> {userStats?.email || 'N/A'}</div>
              <div>
                <span className="font-medium text-gray-400">注册时间:</span> {userStats?.createdAt ? new Date(userStats.createdAt).toLocaleDateString() : 'N/A'}
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* 项目类型分布 */}
        <Card
          title={
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-blue-400" />
              <span className="text-white">项目类型分布</span>
            </div>
          }
          className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 shadow-md"
          headStyle={{ borderBottom: '1px solid rgba(71, 85, 105, 0.5)', backgroundColor: 'transparent' }}
        >
          <div className="h-64">
            {getProjectTypeChartData() ? (
              <Pie data={getProjectTypeChartData()!} options={chartOptions} />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                <AlertCircle className="w-5 h-5 mr-2" />
                <span>无项目类型数据</span>
              </div>
            )}
          </div>
        </Card>

        {/* 项目状态分布 */}
        <Card
          title={
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-green-400" />
              <span className="text-white">项目状态分布</span>
            </div>
          }
          className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 shadow-md"
          headStyle={{ borderBottom: '1px solid rgba(71, 85, 105, 0.5)', backgroundColor: 'transparent' }}
        >
          <div className="h-64">
            {getProjectStatusChartData() ? (
              <Pie data={getProjectStatusChartData()!} options={chartOptions} />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                <AlertCircle className="w-5 h-5 mr-2" />
                <span>无项目状态数据</span>
              </div>
            )}
          </div>
        </Card>

        {/* 镜像状态分布 */}
        <Card
          title={
            <div className="flex items-center gap-2">
              <ImageIcon className="w-5 h-5 text-purple-400" />
              <span className="text-white">镜像状态分布</span>
            </div>
          }
          className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 shadow-md"
          headStyle={{ borderBottom: '1px solid rgba(71, 85, 105, 0.5)', backgroundColor: 'transparent' }}
        >
          <div className="h-64">
            {getImageStatusChartData() ? (
              <Pie data={getImageStatusChartData()!} options={chartOptions} />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                <AlertCircle className="w-5 h-5 mr-2" />
                <span>无镜像状态数据</span>
              </div>
            )}
          </div>
        </Card>

        {/* 数据集类型分布 */}
        <Card
          title={
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-green-400" />
              <span className="text-white">数据集类型分布</span>
            </div>
          }
          className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 shadow-md"
          headStyle={{ borderBottom: '1px solid rgba(71, 85, 105, 0.5)', backgroundColor: 'transparent' }}
        >
          <div className="h-64">
            {getDatasetTypeChartData() ? (
              <Pie data={getDatasetTypeChartData()!} options={chartOptions} />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                <AlertCircle className="w-5 h-5 mr-2" />
                <span>无数据集类型数据</span>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* 新增：最近活动趋势图 */}
      <Card
        title={
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-amber-400" />
            <span className="text-white">最近7日活动趋势</span>
          </div>
        }
        className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 shadow-md col-span-1 xl:col-span-2"
        headStyle={{ borderBottom: '1px solid rgba(71, 85, 105, 0.5)', backgroundColor: 'transparent' }}
      >
        <div className="h-72 md:h-80">
          {getDailyActivityChartData() ? (
            <Line 
              data={getDailyActivityChartData()!} 
              options={{
                ...chartOptions,
                scales: {
                  y: {
                    beginAtZero: true,
                    grid: {
                      color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                      color: 'rgba(255, 255, 255, 0.7)',
                      stepSize: 1,
                    }
                  },
                  x: {
                    grid: {
                      color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                      color: 'rgba(255, 255, 255, 0.7)'
                    }
                  }
                },
                plugins: {
                  ...chartOptions.plugins,
                  tooltip: {
                    mode: 'index' as const,
                    intersect: false,
                    callbacks: {
                    }
                  }
                }
              }} 
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <AlertCircle className="w-5 h-5 mr-2" />
              <span>无法加载活动数据或暂无活动。</span>
              <Tooltip title="确保项目、镜像和数据集对象包含 'created_at' 字段，并且后端已提供此数据。">
                <AlertCircle className="w-4 h-4 ml-2 text-yellow-500 cursor-help" />
              </Tooltip>
            </div>
          )}
        </div>
      </Card>

      {/* 添加自定义样式 */}
      <style>
        {`
          .ant-card-head-title {
            color: white;
          }
          .ant-progress-text {
            color: rgba(255, 255, 255, 0.85); /* General progress text to white-ish */
          }
          /* More specific selector for the ready images progress text */
          .ready-images-progress-container .ant-progress-text {
            color: #E0E0E0 !important; /* Light gray for better visibility, !important if needed */
          }
          .ant-empty-description {
            color: rgba(255, 255, 255, 0.65);
          }
        `}
      </style>
    </div>
  );
};

// 格式化字节大小
const formatBytes = (bytes: number, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

export default StatisticsPage; 