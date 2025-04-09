"""
This module contains tests for the container management functionality.
包含容器管理功能的测试用例。
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import DockerImage, ContainerInstance, ResourceQuota
from .serializers import DockerImageSerializer
from unittest.mock import patch, MagicMock

User = get_user_model()

class DockerImageSerializerTest(TestCase):
    """测试Docker镜像序列化器"""
    
    def setUp(self):
        """测试设置"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.serializer_data = {
            'name': 'test-image',
            'description': '测试镜像',
            'python_version': '3.9',
            'pytorch_version': '2.0',
            'cuda_version': '11.8'
        }
        
        self.context = {'request': MagicMock(user=self.user)}
        
    def test_valid_data(self):
        """测试有效数据"""
        serializer = DockerImageSerializer(data=self.serializer_data, context=self.context)
        self.assertTrue(serializer.is_valid())
        
    def test_invalid_python_version(self):
        """测试无效的Python版本"""
        data = self.serializer_data.copy()
        data['python_version'] = '2.7'  # 无效版本
        
        serializer = DockerImageSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('python_version', serializer.errors)
        
    def test_invalid_pytorch_version(self):
        """测试无效的PyTorch版本"""
        data = self.serializer_data.copy()
        data['pytorch_version'] = '1.0'  # 无效版本
        
        serializer = DockerImageSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('pytorch_version', serializer.errors)
        
    def test_invalid_cuda_version(self):
        """测试无效的CUDA版本"""
        data = self.serializer_data.copy()
        data['cuda_version'] = '9.0'  # 无效版本
        
        serializer = DockerImageSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('cuda_version', serializer.errors)
        
    def test_incompatible_versions(self):
        """测试不兼容的版本组合"""
        data = self.serializer_data.copy()
        data['pytorch_version'] = '1.12'  # 与CUDA 11.8不兼容
        data['cuda_version'] = '11.8'
        
        serializer = DockerImageSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        
    def test_compatible_versions(self):
        """测试兼容的版本组合"""
        # 测试多组兼容的版本组合
        compatible_combinations = [
            {'pytorch_version': '2.0', 'cuda_version': '11.8', 'python_version': '3.9'},
            {'pytorch_version': '2.1', 'cuda_version': '12.1', 'python_version': '3.10'},
            {'pytorch_version': '2.6', 'cuda_version': '12.4', 'python_version': '3.11'}
        ]
        
        for combo in compatible_combinations:
            data = self.serializer_data.copy()
            data.update(combo)
            
            serializer = DockerImageSerializer(data=data, context=self.context)
            self.assertTrue(serializer.is_valid(), f"版本组合应该兼容: {combo}")

class DockerImageAPITest(APITestCase):
    """测试Docker镜像API"""
    
    def setUp(self):
        """测试前准备工作"""
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # 设置认证
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
    @patch('container.views.DockerClient')
    def test_create_image_with_pytorch_cuda(self, mock_docker_client):
        """测试创建包含PyTorch和CUDA的镜像"""
        # 模拟Docker操作
        mock_instance = mock_docker_client.return_value
        mock_instance.pull_image.return_value = {
            'id': 'test_image_id',
            'tags': ['python:3.9'],
            'size': 1000,
            'created': '2022-01-01'
        }
        mock_instance.build_image_from_dockerfile.return_value = {
            'id': 'test_custom_image_id',
            'tags': ['mlride-testuser-pytorch-test:py3.9-pt2.0-cuda11.8'],
            'size': 2000,
            'created': '2022-01-02'
        }
        
        # 创建请求数据
        data = {
            'name': 'pytorch-test',
            'description': 'PyTorch测试镜像',
            'python_version': '3.9',
            'pytorch_version': '2.0',
            'cuda_version': '11.8'
        }
        
        # 发送请求
        response = self.client.post('/api/container/images/', data, format='json')
        
        # 检查响应
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DockerImage.objects.count(), 1)
        
        # 验证创建的镜像
        image = DockerImage.objects.first()
        self.assertEqual(image.name, 'pytorch-test')
        self.assertEqual(image.python_version, '3.9')
        self.assertEqual(image.pytorch_version, '2.0')
        self.assertEqual(image.cuda_version, '11.8')
        
        # 验证mock对象被正确调用
        mock_instance.build_image_from_dockerfile.assert_called_once()
        # 检查Dockerfile内容是否包含PyTorch安装命令
        dockerfile_arg = mock_instance.build_image_from_dockerfile.call_args[1]['dockerfile_content']
        self.assertIn('pip install --no-cache-dir torch==2.0', dockerfile_arg)
        self.assertIn('https://download.pytorch.org/whl/cu118', dockerfile_arg) 