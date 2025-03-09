import React from 'react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

const LandingPage: React.FC = () => {
  return (
    <div className="w-full min-h-screen bg-gradient-to-br from-slate-950 via-gray-900 to-slate-900 overflow-y-auto relative">
      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl"></div>
        <div className="absolute top-1/3 -left-20 w-60 h-60 bg-purple-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-1/4 w-60 h-60 bg-emerald-500/10 rounded-full blur-3xl"></div>
      </div>

      {/* Navigation */}
      <header className="w-full px-6 lg:px-8 h-16 flex items-center fixed top-0 bg-slate-950/80 backdrop-blur-md z-50 border-b border-slate-800/50">
        <Link className="flex items-center justify-center" to="/">
          <span className="text-xl font-bold text-white">MLRide</span>
        </Link>
        <nav className="ml-auto flex gap-4 sm:gap-6">
          <Link className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200" to="/features">
            功能
          </Link>
          <Link className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200" to="/docs">
            文档
          </Link>
          <Link className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200" to="/about">
            关于
          </Link>
          <Link className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200" to="/contact">
            联系我们
          </Link>
        </nav>
        <div className="ml-4 flex items-center gap-2">
          <Link to="/login">
            <Button variant="ghost" className="text-sm text-gray-300 hover:text-white hover:bg-slate-800/50">
              登录
            </Button>
          </Link>
          <Link to="/register">
            <Button className="text-sm bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 shadow-md shadow-blue-900/20">注册</Button>
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="w-full flex flex-col">
        {/* Hero Section */}
        <section className="w-full min-h-screen flex items-center justify-center pt-16 relative">
          <div className="container mx-auto px-4 md:px-6 flex flex-col items-center">
            <div className="flex flex-col items-center space-y-8 text-center">
              <div className="inline-block px-3 py-1 rounded-full bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 text-blue-400 text-xs font-medium mb-2">
                全新发布 v1.0
              </div>
              <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl md:text-6xl lg:text-7xl text-white">
                智能<span className="bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">机器学习</span>生产平台
              </h1>
              <p className="mx-auto max-w-[700px] text-gray-400 text-lg md:text-xl leading-relaxed">
                MLRide 提供一站式机器学习解决方案。容器化环境、在线编程、版本控制，让您的 AI 之旅更轻松。
              </p>
              <div className="flex flex-wrap gap-4 mt-8 justify-center">
                <Link to="/login">
                  <Button size="lg" className="text-lg px-8 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 shadow-lg shadow-blue-900/20">
                    立即体验
                  </Button>
                </Link>
                <Link to="/docs">
                  <Button size="lg" variant="outline" className="text-lg px-8 border-slate-700 hover:bg-slate-800/50 text-gray-300">
                    了解更多
                  </Button>
                </Link>
              </div>
            </div>

            {/* Features Section */}
        <section className="w-full py-24 lg:py-32 relative">
          <div className="container px-4 md:px-6 relative">
            <div className="flex flex-col items-center text-center mb-12">
              <div className="inline-block px-3 py-1 rounded-full bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 text-emerald-400 text-xs font-medium mb-4">
                强大功能
              </div>
              <h2 className="text-3xl font-bold tracking-tighter text-center mb-4 text-white">
                核心功能
              </h2>
              <p className="text-gray-400 max-w-[700px] mx-auto">
                我们提供全面的机器学习开发工具，帮助您从数据处理到模型部署的全流程
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="flex flex-col p-6 bg-slate-800/30 backdrop-blur-sm rounded-xl border border-slate-700/50 hover:border-blue-500/30 transition-all duration-300 hover:shadow-md hover:shadow-blue-500/5">
                <div className="flex items-center mb-4">
                  <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center mr-3">
                    <svg
                      className="w-5 h-5 text-blue-500"
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
                  </div>
                  <h3 className="text-xl font-bold text-white">容器化开发环境</h3>
                </div>
                <p className="text-gray-400 leading-relaxed">
                  提供隔离、一致且可定制的开发环境，支持 CPU 和 GPU 资源动态分配。确保您的项目在任何环境中都能稳定运行。
                </p>
              </div>
              
              <div className="flex flex-col p-6 bg-slate-800/30 backdrop-blur-sm rounded-xl border border-slate-700/50 hover:border-green-500/30 transition-all duration-300 hover:shadow-md hover:shadow-green-500/5">
                <div className="flex items-center mb-4">
                  <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center mr-3">
                    <svg
                      className="w-5 h-5 text-green-500"
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
                  </div>
                  <h3 className="text-xl font-bold text-white">在线编程与调试</h3>
                </div>
                <p className="text-gray-400 leading-relaxed">
                  集成 Jupyter Notebook，支持实时代码编写、运行和调试，提供资源监控和日志查看。随时随地进行开发工作。
                </p>
              </div>
              
              <div className="flex flex-col p-6 bg-slate-800/30 backdrop-blur-sm rounded-xl border border-slate-700/50 hover:border-purple-500/30 transition-all duration-300 hover:shadow-md hover:shadow-purple-500/5">
                <div className="flex items-center mb-4">
                  <div className="w-10 h-10 rounded-full bg-purple-500/10 flex items-center justify-center mr-3">
                    <svg
                      className="w-5 h-5 text-purple-500"
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
                  </div>
                  <h3 className="text-xl font-bold text-white">版本控制追踪</h3>
                </div>
                <p className="text-gray-400 leading-relaxed">
                  使用 MLflow 和 DVC 进行模型和数据版本控制，确保开发过程的可追溯性。轻松比较不同版本的模型性能。
                </p>
              </div>
              
              <div className="flex flex-col p-6 bg-slate-800/30 backdrop-blur-sm rounded-xl border border-slate-700/50 hover:border-yellow-500/30 transition-all duration-300 hover:shadow-md hover:shadow-yellow-500/5">
                <div className="flex items-center mb-4">
                  <div className="w-10 h-10 rounded-full bg-yellow-500/10 flex items-center justify-center mr-3">
                    <svg
                      className="w-5 h-5 text-yellow-500"
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
                  </div>
                  <h3 className="text-xl font-bold text-white">可视化拖拽编程</h3>
                </div>
                <p className="text-gray-400 leading-relaxed">
                  通过图形化界面简化机器学习管道的构建，支持算法模块的拖拽组合。无需编写复杂代码即可构建完整工作流。
                </p>
              </div>
            </div>
          </div>
        </section>
            
            {/* 替换为技术栈展示和平台界面预览 */}
            <div className="mt-16 w-full max-w-4xl mx-auto">
              {/* 技术栈展示 */}
              <div className="mt-12 text-center">
                <h3 className="text-xl font-semibold text-white mb-6">强大技术栈支持</h3>
                <div className="flex flex-wrap justify-center items-center gap-8">
                  {/* Docker */}
                  <div className="flex flex-col items-center">
                    <div className="w-16 h-16 bg-slate-800/50 rounded-lg flex items-center justify-center mb-2 border border-slate-700/50">
                      <svg className="w-10 h-10 text-blue-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M13 5.5H11V7.5H13V5.5Z" fill="currentColor" />
                        <path d="M13 8.5H11V10.5H13V8.5Z" fill="currentColor" />
                        <path d="M10 8.5H8V10.5H10V8.5Z" fill="currentColor" />
                        <path d="M7 8.5H5V10.5H7V8.5Z" fill="currentColor" />
                        <path d="M10 5.5H8V7.5H10V5.5Z" fill="currentColor" />
                        <path d="M7 5.5H5V7.5H7V5.5Z" fill="currentColor" />
                        <path d="M16 5.5H14V7.5H16V5.5Z" fill="currentColor" />
                        <path d="M13 11.5H11V13.5H13V11.5Z" fill="currentColor" />
                        <path d="M10 11.5H8V13.5H10V11.5Z" fill="currentColor" />
                        <path d="M7 11.5H5V13.5H7V11.5Z" fill="currentColor" />
                        <path d="M16 11.5H14V13.5H16V11.5Z" fill="currentColor" />
                        <path d="M19 11.5H17V13.5H19V11.5Z" fill="currentColor" />
                        <path d="M16 8.5H14V10.5H16V8.5Z" fill="currentColor" />
                        <path d="M19 8.5H17V10.5H19V8.5Z" fill="currentColor" />
                        <path d="M22 13.5C22 13.5 21.5 15.5 19.5 15.5H3.5C2.5 15.5 2 14.5 2 14C2 13.5 2.5 11 5.5 11C5.5 11 6 8 9 7.5C12 7 13 9 13 9C13 9 14 6 17.5 6.5C21 7 22 9.5 22 13.5Z" stroke="currentColor" strokeWidth="1.5" />
                      </svg>
                    </div>
                    <span className="text-sm text-gray-400">Docker</span>
                  </div>
                  
                  {/* Kubernetes */}
                  <div className="flex flex-col items-center">
                    <div className="w-16 h-16 bg-slate-800/50 rounded-lg flex items-center justify-center mb-2 border border-slate-700/50">
                      <svg className="w-10 h-10 text-blue-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 2L3 7V17L12 22L21 17V7L12 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M12 22V17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M21 7L12 12L3 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M3 17L12 12L21 17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M12 2V7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                    <span className="text-sm text-gray-400">Kubernetes</span>
                  </div>
                  
                  {/* MLflow */}
                  <div className="flex flex-col items-center">
                    <div className="w-16 h-16 bg-slate-800/50 rounded-lg flex items-center justify-center mb-2 border border-slate-700/50">
                      <svg className="w-10 h-10 text-green-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M20 4L12 12L4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M4 4V20H20V4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        <circle cx="9" cy="15" r="2" stroke="currentColor" strokeWidth="1.5" />
                        <circle cx="15" cy="9" r="2" stroke="currentColor" strokeWidth="1.5" />
                      </svg>
                    </div>
                    <span className="text-sm text-gray-400">MLflow</span>
                  </div>
                  
                  {/* DVC */}
                  <div className="flex flex-col items-center">
                    <div className="w-16 h-16 bg-slate-800/50 rounded-lg flex items-center justify-center mb-2 border border-slate-700/50">
                      <svg className="w-10 h-10 text-purple-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 3L4 7.5V16.5L12 21L20 16.5V7.5L12 3Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M12 12L4 7.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M12 12V21" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M12 12L20 7.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                    <span className="text-sm text-gray-400">DVC</span>
                  </div>
                  
                  {/* Jupyter */}
                  <div className="flex flex-col items-center">
                    <div className="w-16 h-16 bg-slate-800/50 rounded-lg flex items-center justify-center mb-2 border border-slate-700/50">
                      <svg className="w-10 h-10 text-orange-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2Z" stroke="currentColor" strokeWidth="1.5" />
                        <path d="M7 8H9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        <path d="M15 8H17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        <path d="M9 16C9 16 10 18 12 18C14 18 15 16 15 16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                      </svg>
                    </div>
                    <span className="text-sm text-gray-400">Jupyter</span>
                  </div>
                </div>
              </div>
              
              {/* 平台数据统计 */}
              <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-white mb-1">99.9%</div>
                  <div className="text-sm text-gray-400">运行稳定性</div>
                </div>
                
                <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-white mb-1">50+</div>
                  <div className="text-sm text-gray-400">预置算法模型</div>
                </div>
                
                <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-white mb-1">10x</div>
                  <div className="text-sm text-gray-400">开发效率提升</div>
                </div>
                
                <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-white mb-1">24/7</div>
                  <div className="text-sm text-gray-400">全天候技术支持</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="w-full py-24 lg:py-32 relative">
          <div className="container px-4 md:px-6 relative">
            <div className="max-w-3xl mx-auto bg-slate-800/30 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-8 md:p-12 text-center">
              <div className="inline-block px-3 py-1 rounded-full bg-slate-700/50 backdrop-blur-sm border border-slate-600/50 text-indigo-400 text-xs font-medium mb-4">
                开始您的旅程
              </div>
              <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl text-white mb-4">
                准备开始您的 AI 之旅了吗？
              </h2>
              <p className="mx-auto max-w-[700px] text-gray-400 md:text-xl mb-8 leading-relaxed">
                加入 MLRide，让我们一起探索 AI 的无限可能。从今天开始，构建未来的智能应用。
              </p>
              <div className="flex flex-wrap gap-4 justify-center">
                <Link to="/register">
                  <Button className="text-lg px-8 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 shadow-lg shadow-blue-900/20">
                    免费注册
                  </Button>
                </Link>
                <Link to="/contact">
                  <Button variant="outline" className="text-lg px-8 border-slate-700 hover:bg-slate-800/50 text-gray-300">
                    联系我们
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="w-full py-12 bg-slate-950 border-t border-slate-900">
          <div className="container px-4 md:px-6">
            <div className="flex flex-col md:flex-row justify-between">
              <div className="mb-8 md:mb-0">
                <div className="text-xl font-bold text-white mb-4">MLRide</div>
                <p className="text-gray-400 max-w-xs">
                  一站式机器学习生产平台，让AI开发更简单
                </p>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                <div className="space-y-4">
                  <h4 className="text-sm font-medium text-white">平台</h4>
                  <ul className="space-y-3">
                    <li>
                      <Link className="text-sm text-gray-400 hover:text-white transition-colors duration-200" to="/features">
                        功能
                      </Link>
                    </li>
                    <li>
                      <Link className="text-sm text-gray-400 hover:text-white transition-colors duration-200" to="/pricing">
                        价格
                      </Link>
                    </li>
                  </ul>
                </div>
                
                <div className="space-y-4">
                  <h4 className="text-sm font-medium text-white">资源</h4>
                  <ul className="space-y-3">
                    <li>
                      <Link className="text-sm text-gray-400 hover:text-white transition-colors duration-200" to="/docs">
                        文档
                      </Link>
                    </li>
                    <li>
                      <Link className="text-sm text-gray-400 hover:text-white transition-colors duration-200" to="/tutorials">
                        教程
                      </Link>
                    </li>
                  </ul>
                </div>
                
                <div className="space-y-4">
                  <h4 className="text-sm font-medium text-white">公司</h4>
                  <ul className="space-y-3">
                    <li>
                      <Link className="text-sm text-gray-400 hover:text-white transition-colors duration-200" to="/about">
                        关于我们
                      </Link>
                    </li>
                    <li>
                      <Link className="text-sm text-gray-400 hover:text-white transition-colors duration-200" to="/contact">
                        联系我们
                      </Link>
                    </li>
                  </ul>
                </div>
                
                <div className="space-y-4">
                  <h4 className="text-sm font-medium text-white">法律</h4>
                  <ul className="space-y-3">
                    <li>
                      <Link className="text-sm text-gray-400 hover:text-white transition-colors duration-200" to="/privacy">
                        隐私政策
                      </Link>
                    </li>
                    <li>
                      <Link className="text-sm text-gray-400 hover:text-white transition-colors duration-200" to="/terms">
                        服务条款
                      </Link>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            
            <div className="mt-12 pt-8 border-t border-slate-900 flex flex-col md:flex-row justify-between items-center">
              <p className="text-sm text-gray-500">
                © 2023 MLRide. 保留所有权利。
              </p>
              <div className="flex space-x-6 mt-4 md:mt-0">
                <a href="#" className="text-gray-400 hover:text-white transition-colors duration-200">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                  </svg>
                </a>
                <a href="#" className="text-gray-400 hover:text-white transition-colors duration-200">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path fillRule="evenodd" d="M12.315 2c2.43 0 2.784.013 3.808.06 1.064.049 1.791.218 2.427.465a4.902 4.902 0 011.772 1.153 4.902 4.902 0 011.153 1.772c.247.636.416 1.363.465 2.427.048 1.067.06 1.407.06 4.123v.08c0 2.643-.012 2.987-.06 4.043-.049 1.064-.218 1.791-.465 2.427a4.902 4.902 0 01-1.153 1.772 4.902 4.902 0 01-1.772 1.153c-.636.247-1.363.416-2.427.465-1.067.048-1.407.06-4.123.06h-.08c-2.643 0-2.987-.012-4.043-.06-1.064-.049-1.791-.218-2.427-.465a4.902 4.902 0 01-1.772-1.153 4.902 4.902 0 01-1.153-1.772c-.247-.636-.416-1.363-.465-2.427-.047-1.024-.06-1.379-.06-3.808v-.63c0-2.43.013-2.784.06-3.808.049-1.064.218-1.791.465-2.427a4.902 4.902 0 011.153-1.772A4.902 4.902 0 015.45 2.525c.636-.247 1.363-.416 2.427-.465C8.901 2.013 9.256 2 11.685 2h.63zm-.081 1.802h-.468c-2.456 0-2.784.011-3.807.058-.975.045-1.504.207-1.857.344-.467.182-.8.398-1.15.748-.35.35-.566.683-.748 1.15-.137.353-.3.882-.344 1.857-.047 1.023-.058 1.351-.058 3.807v.468c0 2.456.011 2.784.058 3.807.045.975.207 1.504.344 1.857.182.466.399.8.748 1.15.35.35.683.566 1.15.748.353.137.882.3 1.857.344 1.054.048 1.37.058 4.041.058h.08c2.597 0 2.917-.01 3.96-.058.976-.045 1.505-.207 1.858-.344.466-.182.8-.398 1.15-.748.35-.35.566-.683.748-1.15.137-.353.3-.882.344-1.857.048-1.055.058-1.37.058-4.041v-.08c0-2.597-.01-2.917-.058-3.96-.045-.976-.207-1.505-.344-1.858a3.097 3.097 0 00-.748-1.15 3.098 3.098 0 00-1.15-.748c-.353-.137-.882-.3-1.857-.344-1.023-.047-1.351-.058-3.807-.058zM12 6.865a5.135 5.135 0 110 10.27 5.135 5.135 0 010-10.27zm0 1.802a3.333 3.333 0 100 6.666 3.333 3.333 0 000-6.666zm5.338-3.205a1.2 1.2 0 110 2.4 1.2 1.2 0 010-2.4z" clipRule="evenodd" />
                  </svg>
                </a>
                <a href="#" className="text-gray-400 hover:text-white transition-colors duration-200">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84" />
                  </svg>
                </a>
              </div>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
};

export default LandingPage;
