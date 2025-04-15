"""
使用mock对象测试Jupyter代理视图的隔离功能
"""

import unittest
from unittest import mock
import sys
import os
import django

# 配置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mlride.settings')
django.setup()

from django.http import HttpResponse
from django.test import RequestFactory

from jupyterapp.proxy import JupyterProxyView
from jupyterapp.models import JupyterSession
from rest_framework.exceptions import NotFound

class MockJupyterSession:
    """模拟的JupyterSession对象"""
    def __init__(self, project_id, port, token, status='running'):
        self.project_id = project_id
        self.port = port
        self.token = token
        self.status = status

class MockResponse:
    """模拟的HTTP响应对象"""
    def __init__(self, status_code=200, headers=None, content=b''):
        self.status_code = status_code
        self.headers = headers or {}
        self.raw = mock.MagicMock()
        self.raw.read.return_value = content

class TestProxyIsolation(unittest.TestCase):
    """测试JupyterProxyView路由隔离功能"""
    
    def setUp(self):
        """测试准备"""
        print("设置测试环境...")
        self.factory = RequestFactory()
        self.view = JupyterProxyView()
        
        # 设置模拟会话数据
        self.sessions = {
            '1': MockJupyterSession('1', 8801, 'token1'),
            '2': MockJupyterSession('2', 8802, 'token2')
        }
    
    @mock.patch('jupyterapp.proxy.JupyterSession.objects.get')
    @mock.patch('jupyterapp.proxy.requests.request')
    def test_project_isolation(self, mock_request, mock_get):
        """测试请求被正确路由到对应项目的端口"""
        print("\n测试项目路由隔离...")
        # 设置模拟会话查询
        def mock_get_session(project_id=None, status=None):
            if project_id in self.sessions:
                return self.sessions[project_id]
            raise JupyterSession.DoesNotExist()
        
        mock_get.side_effect = mock_get_session
        
        # 设置模拟响应
        mock_response = MockResponse(status_code=200, content=b'Project 1 Content')
        mock_request.return_value = mock_response
        
        # 发送针对项目1的请求
        request1 = self.factory.get('/api/jupyter/proxy/1/notebook')
        response1 = self.view.dispatch(request1, project_id='1', path='notebook')
        
        # 验证请求被路由到正确的端口
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs['url'], 'http://localhost:8801/notebook')
        print(f"✅ 项目1请求正确路由到端口8801")
        
        # 清除历史
        mock_request.reset_mock()
        
        # 设置新的模拟响应
        mock_response = MockResponse(status_code=200, content=b'Project 2 Content')
        mock_request.return_value = mock_response
        
        # 发送针对项目2的请求
        request2 = self.factory.get('/api/jupyter/proxy/2/notebook')
        response2 = self.view.dispatch(request2, project_id='2', path='notebook')
        
        # 验证请求被路由到正确的端口
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs['url'], 'http://localhost:8802/notebook')
        print(f"✅ 项目2请求正确路由到端口8802")
    
    @mock.patch('jupyterapp.proxy.JupyterSession.objects.get')
    @mock.patch('jupyterapp.proxy.requests.request')
    def test_token_isolation(self, mock_request, mock_get):
        """测试各项目使用独立的token"""
        print("\n测试项目Token隔离...")
        # 设置模拟会话查询
        def mock_get_session(project_id=None, status=None):
            if project_id in self.sessions:
                return self.sessions[project_id]
            raise JupyterSession.DoesNotExist()
        
        mock_get.side_effect = mock_get_session
        
        # 设置模拟响应
        mock_response = MockResponse(status_code=200)
        mock_request.return_value = mock_response
        
        # 发送针对项目1的请求
        request1 = self.factory.get('/api/jupyter/proxy/1/notebook')
        response1 = self.view.dispatch(request1, project_id='1', path='notebook')
        
        # 验证请求包含正确的token
        args, kwargs = mock_request.call_args
        self.assertIn('Cookie', kwargs['headers'])
        self.assertIn('token=token1', kwargs['headers']['Cookie'])
        print(f"✅ 项目1请求包含正确的token: token1")
        
        # 清除历史
        mock_request.reset_mock()
        
        # 发送针对项目2的请求
        request2 = self.factory.get('/api/jupyter/proxy/2/notebook')
        response2 = self.view.dispatch(request2, project_id='2', path='notebook')
        
        # 验证请求包含正确的token
        args, kwargs = mock_request.call_args
        self.assertIn('Cookie', kwargs['headers'])
        self.assertIn('token=token2', kwargs['headers']['Cookie'])
        print(f"✅ 项目2请求包含正确的token: token2")
    
    @mock.patch('jupyterapp.proxy.JupyterSession.objects.get')
    @mock.patch('jupyterapp.proxy.requests.request')
    def test_nonexistent_project(self, mock_request, mock_get):
        """测试访问不存在的项目时会正确拒绝"""
        print("\n测试访问不存在的项目...")
        # 设置模拟会话查询抛出异常
        mock_get.side_effect = JupyterSession.DoesNotExist()
        
        # 发送针对不存在项目的请求
        request = self.factory.get('/api/jupyter/proxy/999/notebook')
        
        # 验证视图抛出NotFound异常
        try:
            response = self.view.dispatch(request, project_id='999', path='notebook')
            self.fail("应当抛出NotFound异常")
        except NotFound:
            print(f"✅ 访问不存在的项目正确抛出NotFound异常")
        
        # 验证未发送请求
        mock_request.assert_not_called()
        print(f"✅ 未向不存在的项目发送请求")

if __name__ == '__main__':
    print("===== 开始测试Jupyter项目隔离机制 =====")
    unittest.main(argv=[sys.argv[0], '-v']) 