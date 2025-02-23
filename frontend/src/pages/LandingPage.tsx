import React from 'react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

const LandingPage: React.FC = () => {
  return (
    <div className="w-full min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 overflow-y-auto">
      {/* Navigation */}
      <header className="w-full px-6 lg:px-8 h-16 flex items-center fixed top-0 bg-gray-900/80 backdrop-blur-sm z-50">
        <Link className="flex items-center justify-center" to="/">
          <span className="text-xl font-bold text-white">MLRide</span>
        </Link>
        <nav className="ml-auto flex gap-4 sm:gap-6">
          <Link className="text-sm font-medium text-gray-200 hover:text-white hover:underline underline-offset-4" to="/features">
            功能
          </Link>
          <Link className="text-sm font-medium text-gray-200 hover:text-white hover:underline underline-offset-4" to="/docs">
            文档
          </Link>
          <Link className="text-sm font-medium text-gray-200 hover:text-white hover:underline underline-offset-4" to="/about">
            关于
          </Link>
          <Link className="text-sm font-medium text-gray-200 hover:text-white hover:underline underline-offset-4" to="/contact">
            联系我们
          </Link>
        </nav>
        <div className="ml-4 flex items-center gap-2">
          <Link to="/login">
            <Button variant="ghost" className="text-sm text-gray-200 hover:text-white">
              登录
            </Button>
          </Link>
          <Link to="/register">
            <Button className="text-sm">注册</Button>
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="w-full flex flex-col">
        {/* Hero Section */}
        <section className="w-full min-h-screen flex items-center justify-center pt-16">
          <div className="container mx-auto px-4 md:px-6 flex flex-col items-center">
            <div className="flex flex-col items-center space-y-8 text-center">
              <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl md:text-6xl lg:text-7xl text-white">
                智能机器学习生产平台
              </h1>
              <p className="mx-auto max-w-[700px] text-gray-400 text-lg md:text-xl">
                MLRide 提供一站式机器学习解决方案。容器化环境、在线编程、版本控制，让您的 AI 之旅更轻松。
              </p>
              <div className="flex gap-4 mt-8">
                <Link to="/login">
                  <Button size="lg" className="text-lg px-8">
                    立即体验
                  </Button>
                </Link>
                <Link to="/docs">
                  <Button size="lg" variant="outline" className="text-lg px-8">
                    了解更多
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="w-full py-12 md:py-24 lg:py-32 bg-gray-900/50">
          <div className="container px-4 md:px-6">
            <h2 className="text-3xl font-bold tracking-tighter text-center mb-12 text-white">
              核心功能
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="flex flex-col p-6 bg-gray-800/50 rounded-lg">
                <div className="flex items-center mb-4">
                  <svg
                    className="w-6 h-6 mr-2 text-blue-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                    />
                  </svg>
                  <h3 className="text-xl font-bold text-white">容器化开发环境</h3>
                </div>
                <p className="text-gray-400">
                  提供隔离、一致且可定制的开发环境，支持 CPU 和 GPU 资源动态分配。
                </p>
              </div>
              <div className="flex flex-col p-6 bg-gray-800/50 rounded-lg">
                <div className="flex items-center mb-4">
                  <svg
                    className="w-6 h-6 mr-2 text-green-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    />
                  </svg>
                  <h3 className="text-xl font-bold text-white">在线编程与调试</h3>
                </div>
                <p className="text-gray-400">
                  集成 Jupyter Notebook，支持实时代码编写、运行和调试，提供资源监控和日志查看。
                </p>
              </div>
              <div className="flex flex-col p-6 bg-gray-800/50 rounded-lg">
                <div className="flex items-center mb-4">
                  <svg
                    className="w-6 h-6 mr-2 text-purple-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <h3 className="text-xl font-bold text-white">版本控制追踪</h3>
                </div>
                <p className="text-gray-400">
                  使用 MLflow 和 DVC 进行模型和数据版本控制，确保开发过程的可追溯性。
                </p>
              </div>
              <div className="flex flex-col p-6 bg-gray-800/50 rounded-lg">
                <div className="flex items-center mb-4">
                  <svg
                    className="w-6 h-6 mr-2 text-yellow-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
                    />
                  </svg>
                  <h3 className="text-xl font-bold text-white">可视化拖拽编程</h3>
                </div>
                <p className="text-gray-400">
                  通过图形化界面简化机器学习管道的构建，支持算法模块的拖拽组合。
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="w-full py-12 md:py-24 lg:py-32">
          <div className="container px-4 md:px-6">
            <div className="flex flex-col items-center space-y-4 text-center">
              <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl text-white">
                准备开始您的 AI 之旅了吗？
              </h2>
              <p className="mx-auto max-w-[700px] text-gray-400 md:text-xl">
                加入 MLRide，让我们一起探索 AI 的无限可能。
              </p>
              <div className="space-x-4">
                <Link to="/register">
                  <Button className="text-lg">免费注册</Button>
                </Link>
                <Link to="/contact">
                  <Button variant="outline" className="text-lg">
                    联系我们
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="w-full py-6 bg-gray-900">
          <div className="container px-4 md:px-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-white">平台</h4>
                <ul className="space-y-2">
                  <li>
                    <Link className="text-sm text-gray-400 hover:text-white" to="/features">
                      功能
                    </Link>
                  </li>
                  <li>
                    <Link className="text-sm text-gray-400 hover:text-white" to="/pricing">
                      价格
                    </Link>
                  </li>
                </ul>
              </div>
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-white">资源</h4>
                <ul className="space-y-2">
                  <li>
                    <Link className="text-sm text-gray-400 hover:text-white" to="/docs">
                      文档
                    </Link>
                  </li>
                  <li>
                    <Link className="text-sm text-gray-400 hover:text-white" to="/tutorials">
                      教程
                    </Link>
                  </li>
                </ul>
              </div>
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-white">公司</h4>
                <ul className="space-y-2">
                  <li>
                    <Link className="text-sm text-gray-400 hover:text-white" to="/about">
                      关于我们
                    </Link>
                  </li>
                  <li>
                    <Link className="text-sm text-gray-400 hover:text-white" to="/contact">
                      联系我们
                    </Link>
                  </li>
                </ul>
              </div>
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-white">法律</h4>
                <ul className="space-y-2">
                  <li>
                    <Link className="text-sm text-gray-400 hover:text-white" to="/privacy">
                      隐私政策
                    </Link>
                  </li>
                  <li>
                    <Link className="text-sm text-gray-400 hover:text-white" to="/terms">
                      服务条款
                    </Link>
                  </li>
                </ul>
              </div>
            </div>
            <div className="mt-8 pt-8 border-t border-gray-800">
              <p className="text-xs text-gray-400 text-center">
                2025 MLRide. 保留所有权利。
              </p>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
};

export default LandingPage;
