import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './store';
import { Toaster } from 'sonner';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import Home from './pages/Home';
import LandingPage from './pages/LandingPage';
import ImagesPage from './pages/images/ImagesPage';
import CreateImagePage from './pages/images/CreateImagePage';
import ProjectsPage from './pages/projects/ProjectsPage';
import './App.css'

const App: React.FC = () => {
    return (
        <Provider store={store}>
            <Router>
                <Toaster richColors position="top-right" />
                <Routes>
                    {/* 公开路由 */}
                    <Route path="/" element={<LandingPage />} />
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/register" element={<RegisterPage />} />
                    
                    {/* 需要认证的路由 */}
                    <Route path="/dashboard" element={<Home />}>
                        <Route index element={<Navigate to="/dashboard/projects" replace />} />
                        <Route path="projects" element={<ProjectsPage />} />
                        <Route path="images" element={<ImagesPage />} />
                        <Route path="images/create" element={<CreateImagePage />} />
                        <Route path="models" element={<ProjectsPage />} />
                        <Route path="datasets" element={<ProjectsPage />} />
                        <Route path="deployments" element={<ProjectsPage />} />
                        <Route path="recent" element={<ProjectsPage />} />
                        <Route path="my-space" element={<ProjectsPage />} />
                        <Route path="compute" element={<ProjectsPage />} />
                        <Route path="cases" element={<ProjectsPage />} />
                        <Route path="tasks" element={<ProjectsPage />} />
                        <Route path="services" element={<ProjectsPage />} />
                        <Route path="community" element={<ProjectsPage />} />
                    </Route>
                    
                    {/* 重定向未匹配的路由到项目页 */}
                    <Route path="*" element={<Navigate to="/dashboard/projects" replace />} />
                </Routes>
            </Router>
        </Provider>
    );
};

export default App;
