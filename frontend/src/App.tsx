import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { useDispatch } from 'react-redux';
import { store } from './store';
import { AppDispatch } from './store';
import { checkAuth, logout } from './store/authSlice';
import { Toaster } from 'sonner';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import ProfilePage from './pages/auth/ProfilePage';
import Home from './pages/Home';
import LandingPage from './pages/LandingPage';
import ImagesPage from './pages/images/ImagesPage';
import CreateImagePage from './pages/images/CreateImagePage';
import ProjectsPage from './pages/projects/ProjectsPage';
import CreateProjectPage from './pages/projects/CreateProjectPage';
import ProjectDetailPage from './pages/projects/ProjectDetailPage';
import WorkflowDesignerPage from './pages/workflows/WorkflowDesignerPage';
import ProtectedRoute from './components/ProtectedRoute';
import RecentPage from './pages/dashboard/RecentPage';
import DatasetsPage from './pages/datasets/DatasetsPage';
import StatisticsPage from './pages/dashboard/StatisticsPage';
import CommunityPage from './pages/community/CommunityPage';
import '@/styles/globals.css';
import '@/styles/scrollbar.css';
import './App.css'

// 内部App组件，用于访问Redux的dispatch
const AppContent: React.FC = () => {
    const dispatch = useDispatch<AppDispatch>();

    // 在组件挂载时检查用户认证状态
    useEffect(() => {
        console.log('App mounted, checking auth...');
        dispatch(checkAuth());
    }, [dispatch]);

    // 监听localStorage的变化，以处理多标签页认证冲突
    useEffect(() => {
        const handleStorageChange = (event: StorageEvent) => {
            if (event.key === 'token') {
                console.log('Token changed in another tab/window. Re-checking auth.');
                // 如果新值为null（表示在其他标签页登出），则也登出当前标签页
                if (event.newValue === null) {
                    dispatch(logout());
                } else {
                    // 否则，重新验证当前token
                    dispatch(checkAuth());
                }
            }
        };

        window.addEventListener('storage', handleStorageChange);

        return () => {
            window.removeEventListener('storage', handleStorageChange);
        };
    }, [dispatch]);

    return (
        <Router>
            <Toaster richColors position="top-right" />
            <Routes>
                {/* 公开路由 */}
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                
                {/* 需要认证的路由 */}
                <Route element={<ProtectedRoute />}>
                    <Route path="/dashboard" element={<Home />}>
                        <Route index element={<Navigate to="/dashboard/recent" replace />} />
                        <Route path="recent" element={<RecentPage />} />
                        <Route path="projects" element={<ProjectsPage />} />
                        <Route path="projects/create" element={<CreateProjectPage />} />
                        <Route path="projects/create-notebook" element={<Navigate to="/dashboard/projects/create?type=notebook" replace />} />
                        <Route path="projects/create-canvas" element={<Navigate to="/dashboard/projects/create?type=canvas" replace />} />
                        <Route path="projects/:id" element={<ProjectDetailPage />} />
                        <Route path="projects/:id/workflow" element={<WorkflowDesignerPage />} />
                        <Route path="projects/:id/workflows/:workflowId" element={<WorkflowDesignerPage />} />
                        <Route path="images" element={<ImagesPage />} />
                        <Route path="images/create" element={<CreateImagePage />} />
                        <Route path="datasets" element={<DatasetsPage />} />
                        <Route path="datasets/create" element={<DatasetsPage />} />
                        <Route path="workflows" element={<WorkflowDesignerPage />} />
                        <Route path="tasks" element={<StatisticsPage />} />
                        <Route path="profile" element={<ProfilePage />} />
                        <Route path="community" element={<CommunityPage />} />
                    </Route>
                </Route>
                
                {/* 重定向未匹配的路由到最近页面 */}
                <Route path="*" element={<Navigate to="/dashboard/recent" replace />} />
            </Routes>
        </Router>
    );
};

// 主App组件
const App: React.FC = () => {
    return (
        <Provider store={store}>
            <AppContent />
        </Provider>
    );
};

export default App;
