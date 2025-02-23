from django.test import TestCase
import requests
import json

def test_register():
    """测试用户注册API"""
    # 定义注册接口的URL
    url = "http://127.0.0.1:8000/api/auth/register/"
    # 构造注册接口的请求数据，包括用户名、密码、确认密码和邮箱
    data = {
        "username": "testuser2",
        "password": "Test@123456",
        "password2": "Test@123456",
        "email": "test@example2.com"
    }
    # 定义请求头，指定Content-Type为application/json，表示发送JSON格式的数据
    headers = {"Content-Type": "application/json"}
    # 发送POST请求到注册接口，并传递请求数据和请求头
    response = requests.post(url, json=data, headers=headers)
    # 打印注册API的响应状态码，例如200表示成功，400表示客户端错误，500表示服务器错误
    print("注册响应:", response.status_code)
    # 打印注册API的响应内容，通常为JSON格式，包含服务器返回的具体信息
    print("响应内容:", response.json())
    # 返回响应对象，以便后续进一步处理，例如断言状态码或响应内容
    return response

def test_login():
    """测试用户登录API"""
    # 定义登录接口的URL
    url = "http://127.0.0.1:8000/api/auth/login/"
    # 构造登录接口的请求数据，包括用户名和密码
    data = {
        "username": "testuser",
        "password": "Test@123456"
    }
    # 定义请求头，指定Content-Type为application/json，表示发送JSON格式的数据
    headers = {"Content-Type": "application/json"}
    # 发送POST请求到登录接口，并传递请求数据和请求头
    response = requests.post(url, json=data, headers=headers)
    # 打印登录API的响应状态码
    print("登录响应:", response.status_code)
    # 打印登录API的响应内容
    print("响应内容:", response.json())
    # 返回响应对象
    return response

def test_logout():
    """测试用户登出API"""
    # 定义登出接口的URL
    url = "http://127.0.0.1:8000/api/auth/logout/"
    # 发送POST请求到登出接口，登出通常不需要请求数据
    response = requests.post(url)
    # 打印登出API的响应状态码
    print("登出响应:", response.status_code)
    # 打印登出API的响应内容
    print("响应内容:", response.json())
    # 返回响应对象
    return response

if __name__ == "__main__":
    print("=== 测试注册 ===")
    test_register()
    print("\n=== 测试登录 ===")
    test_login()
    print("\n=== 测试登出 ===")
    test_logout() 
