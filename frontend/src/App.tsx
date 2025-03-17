import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { useDispatch } from 'react-redux';
import { store } from './store';
import { AppDispatch } from './store';
import { checkAuth } from './store/authSlice';
import { Toaster } from "./components/ui/toaster";
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
import ProtectedRoute from './components/ProtectedRoute';
import RecentPage from './pages/dashboard/RecentPage';
import './App.css'

// 内部App组件，用于访问Redux的dispatch
const AppContent: React.FC = () => {
    const dispatch = useDispatch<AppDispatch>();

    // 在组件挂载时检查用户认证状态
    useEffect(() => {
        console.log('App mounted, checking auth...');
        dispatch(checkAuth());
    }, [dispatch]);

    return (
        <Router>
            <Toaster />
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
                        <Route path="projects/create-ide" element={<Navigate to="/dashboard/projects/create?type=ide" replace />} />
                        <Route path="projects/create-notebook" element={<Navigate to="/dashboard/projects/create?type=notebook" replace />} />
                        <Route path="projects/create-canvas" element={<Navigate to="/dashboard/projects/create?type=canvas" replace />} />
                        <Route path="projects/:id" element={<ProjectDetailPage />} />
                        <Route path="images" element={<ImagesPage />} />
                        <Route path="images/create" element={<CreateImagePage />} />
                        <Route path="models" element={<ProjectsPage />} />
                        <Route path="datasets" element={<ProjectsPage />} />
                        <Route path="deployments" element={<ProjectsPage />} />
                        <Route path="compute" element={<ProjectsPage />} />
                        <Route path="cases" element={<ProjectsPage />} />
                        <Route path="tasks" element={<ProjectsPage />} />
                        <Route path="services" element={<ProjectsPage />} />
                        <Route path="community" element={<ProjectsPage />} />
                        <Route path="profile" element={<ProfilePage />} />
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
