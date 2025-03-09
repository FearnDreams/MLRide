import requests
import json

# 测试服务器地址
BASE_URL = 'http://localhost:8000/api'

def test_register():
    """测试用户注册"""
    url = f"{BASE_URL}/auth/register/"
    data = {
        "username": "testuser5",
        "password": "testpassword123",
        "password2": "testpassword123",
        "email": "test5@example.com"
    }
    response = requests.post(url, json=data)
    print(f"注册状态码: {response.status_code}")
    print(f"注册响应: {response.text}")
    return response.json() if response.status_code == 201 else None

def test_login(username, password):
    """测试用户登录"""
    url = f"{BASE_URL}/auth/login/"
    data = {
        "username": username,
        "password": password
    }
    response = requests.post(url, json=data)
    print(f"登录状态码: {response.status_code}")
    print(f"登录响应: {response.text}")
    return response.json() if response.status_code == 200 else None

def test_profile(token):
    """测试获取用户个人信息"""
    url = f"{BASE_URL}/auth/profile/"
    headers = {
        "Authorization": f"Token {token}"
    }
    response = requests.get(url, headers=headers)
    print(f"个人信息状态码: {response.status_code}")
    print(f"个人信息响应: {response.text}")
    return response.json() if response.status_code == 200 else None

def test_update_profile(token, data):
    """测试更新用户个人信息"""
    url = f"{BASE_URL}/auth/profile/update/"
    headers = {
        "Authorization": f"Token {token}"
    }
    response = requests.put(url, json=data, headers=headers)
    print(f"更新个人信息状态码: {response.status_code}")
    print(f"更新个人信息响应: {response.text}")
    return response.json() if response.status_code == 200 else None

def test_delete_account(token, password):
    """测试注销用户账户"""
    url = f"{BASE_URL}/auth/profile/delete/"
    headers = {
        "Authorization": f"Token {token}"
    }
    data = {
        "current_password": password
    }
    response = requests.post(url, json=data, headers=headers)
    print(f"注销账户状态码: {response.status_code}")
    print(f"注销账户响应: {response.text}")
    return response.json() if response.status_code == 200 else None

if __name__ == "__main__":
    # 注册新用户
    register_result = test_register()
    
    if register_result and register_result.get("status") == "success":
        # 获取token
        token = register_result.get("data", {}).get("token")
        username = register_result.get("data", {}).get("user", {}).get("username")
        
        # 测试获取个人信息
        profile_result = test_profile(token)
        
        # 测试更新个人信息
        update_data = {
            "nickname": "测试用户昵称"
        }
        update_result = test_update_profile(token, update_data)
        
        # 测试注销账户
        delete_result = test_delete_account(token, "testpassword123")
        
        # 测试注销后使用token获取个人信息（应该失败）
        if delete_result and delete_result.get("status") == "success":
            profile_result = test_profile(token)
    else:
        # 如果注册失败，尝试登录
        login_result = test_login("testuser5", "testpassword123")
        
        if login_result and login_result.get("status") == "success":
            # 获取token
            token = login_result.get("data", {}).get("token")
            
            # 测试获取个人信息
            profile_result = test_profile(token)
            
            # 测试更新个人信息
            update_data = {
                "nickname": "测试用户昵称"
            }
            update_result = test_update_profile(token, update_data)
            
            # 测试注销账户
            delete_result = test_delete_account(token, "testpassword123") 