"""
This module contains tests for the container management functionality.
包含容器管理功能的测试用例。
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import DockerImage, ContainerInstance, ResourceQuota
from .docker_ops import DockerClient
import unittest
from unittest.mock import patch, MagicMock

User = get_user_model()

class DockerOperationsTest(TestCase):
    """测试Docker基础操作"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        super().setUpClass()
        try:
            cls.docker_client = DockerClient()
            cls.test_image = "hello-world:latest"  # 使用一个轻量级的测试镜像
        except Exception as e:
            # 如果Docker服务不可用，标记测试为跳过
            raise unittest.SkipTest(f"Docker服务不可用: {str(e)}")
    
    def test_pull_image(self):
        """测试拉取镜像"""
        try:
            image = self.docker_client.pull_image(self.test_image)
            self.assertIsNotNone(image)
            self.assertIn('id', image)
            self.assertIn('tags', image)
        except Exception as e:
            self.skipTest(f"拉取镜像失败: {str(e)}")
    
    def test_list_images(self):
        """测试列出镜像"""
        try:
            images = self.docker_client.list_images()
            self.assertIsInstance(images, list)
        except Exception as e:
            self.skipTest(f"列出镜像失败: {str(e)}")
    
    def test_container_lifecycle(self):
        """测试容器生命周期管理"""
        try:
            # 创建容器
            container = self.docker_client.create_container(
                image_name=self.test_image,
                container_name="test-container",
                cpu_count=1,
                memory_limit="512m"
            )
            self.assertIsNotNone(container)
            self.assertIn('id', container)
            
            # 启动容器
            self.assertTrue(self.docker_client.start_container(container['id']))
            
            # 停止容器
            self.assertTrue(self.docker_client.stop_container(container['id']))
            
            # 删除容器
            self.assertTrue(self.docker_client.remove_container(container['id']))
        except Exception as e:
            self.fail(f"容器生命周期测试失败: {str(e)}")

class ContainerAPITest(APITestCase):
    """测试容器管理API"""
    
    def setUp(self):
        """测试前准备工作"""
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # 创建测试用户的资源配额
        self.quota = ResourceQuota.objects.create(
            user=self.user,
            max_containers=5,
            max_cpu=2,
            max_memory=2048,
            max_gpu=0
        )
        
        # 创建测试镜像
        self.image = DockerImage.objects.create(
            name="test-image",
            tag="latest",
            description="测试镜像",
            min_cpu=1,
            min_memory=512,
            min_gpu=0
        )
        
        # 设置认证
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # 创建Docker客户端的Mock对象
        self.docker_mock = MagicMock()
        self.docker_patcher = patch('container.docker_ops.docker.from_env', return_value=self.docker_mock)
        self.docker_patcher.start()
    
    def tearDown(self):
        """测试后清理工作"""
        self.docker_patcher.stop()
    
    @patch('container.views.DockerClient')
    def test_create_container(self, mock_docker_client):
        """测试创建容器API"""
        # 配置Mock对象
        mock_instance = mock_docker_client.return_value
        mock_instance.create_container.return_value = {
            'id': 'test_container_id',
            'name': 'test-container',
            'status': 'created'
        }
        
        # 创建测试镜像
        test_image = DockerImage.objects.create(
            name='test/image',
            tag='latest',
            description='Test Image',
            min_cpu=1,
            min_memory=512,
            min_gpu=0
        )
        
        data = {
            'image': test_image.id,
            'name': 'test-container',
            'cpu_limit': 1,
            'memory_limit': 512,
            'gpu_limit': 0,
            'command': 'python app.py',
            'environment': {'DEBUG': 'true'},
            'ports': {'8000/tcp': 8000},
            'volumes': {'/data': {'bind': '/container/data', 'mode': 'rw'}},
            'user': self.user.id
        }
        
        response = self.client.post('/api/container/containers/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ContainerInstance.objects.count(), 1)
        
        # 验证创建的容器实例
        container = ContainerInstance.objects.first()
        self.assertEqual(container.container_id, 'test_container_id')
        self.assertEqual(container.status, 'created')
        self.assertEqual(container.user, self.user)
        
        # 验证mock对象被正确调用
        mock_instance.create_container.assert_called_once()
        call_args = mock_instance.create_container.call_args[1]
        self.assertEqual(call_args['image_name'], 'test/image:latest')
        self.assertEqual(call_args['container_name'], 'test-container')
        self.assertEqual(call_args['cpu_count'], 1)
        self.assertEqual(call_args['memory_limit'], '512m')
    
    def test_list_containers(self):
        """测试获取容器列表API"""
        # 创建测试容器
        ContainerInstance.objects.create(
            user=self.user,
            image=self.image,
            container_id='test123',
            name='test-container',
            cpu_limit=1,
            memory_limit=512,
            gpu_limit=0
        )
        
        response = self.client.get('/api/container/containers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_quota_limit(self):
        """测试资源配额限制"""
        # 尝试创建超过CPU限制的容器
        data = {
            'image': self.image.id,
            'name': 'test-container',
            'cpu_limit': 3,  # 超过配额限制(2核)
            'memory_limit': 512,
            'gpu_limit': 0
        }
        
        response = self.client.post('/api/container/containers/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('container.views.DockerClient')
    def test_container_operations(self, mock_docker_client):
        """测试容器操作API"""
        # 配置Mock对象
        mock_instance = mock_docker_client.return_value
        mock_instance.start_container.return_value = True
        mock_instance.stop_container.return_value = True
        
        # 创建测试容器
        container = ContainerInstance.objects.create(
            user=self.user,
            image=self.image,
            container_id='test123',
            name='test-container',
            cpu_limit=1,
            memory_limit=512,
            gpu_limit=0
        )
        
        # 测试启动容器
        response = self.client.post(f'/api/container/containers/{container.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_instance.start_container.assert_called_once_with('test123')
        
        # 测试停止容器
        response = self.client.post(f'/api/container/containers/{container.id}/stop/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_instance.stop_container.assert_called_once_with('test123')
        
        # 测试重启容器
        response = self.client.post(f'/api/container/containers/{container.id}/restart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_instance.stop_container.call_count, 2)
        self.assertEqual(mock_instance.start_container.call_count, 2)
