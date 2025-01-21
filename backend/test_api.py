import requests
import json

def test_register():
    """测试用户注册API"""
    url = "http://127.0.0.1:8000/api/auth/register/"
    data = {
        "username": "testuser2",
        "password": "Test@123456",
        "password2": "Test@123456",
        "email": "test@example2.com"
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=data, headers=headers)
    print("注册响应:", response.status_code)
    print("响应内容:", response.json())
    return response

def test_login():
    """测试用户登录API"""
    url = "http://127.0.0.1:8000/api/auth/login/"
    data = {
        "username": "testuser",
        "password": "Test@123456"
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=data, headers=headers)
    print("登录响应:", response.status_code)
    print("响应内容:", response.json())
    return response

def test_logout():
    """测试用户登出API"""
    url = "http://127.0.0.1:8000/api/auth/logout/"
    response = requests.post(url)
    print("登出响应:", response.status_code)
    print("响应内容:", response.json())
    return response

if __name__ == "__main__":
    print("=== 测试注册 ===")
    test_register()
    print("\n=== 测试登录 ===")
    test_login()
    print("\n=== 测试登出 ===")
    test_logout() 