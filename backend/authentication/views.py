from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from .serializers import UserRegistrationSerializer, UserLoginSerializer

# Create your views here.

class RegisterView(generics.CreateAPIView):
    """
    用户注册视图
    
    允许任何用户访问，不需要认证

    返回值：
    - 成功：返回用户名和邮箱
    - 失败：返回错误信息
    """
    # 使用UserRegistrationSerializer验证和创建用户
    serializer_class = UserRegistrationSerializer
    # 使用permission_classes来设置权限,允许未认证用户访问
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "注册成功",
                "username": user.username,
                "email": user.email
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    """
    用户登录视图
    
    允许任何用户访问，不需要认证

    返回值：
    - 成功：返回用户名和邮箱
    - 失败：返回错误信息
    """
    permission_classes = []  # 允许未认证用户访问

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            # 使用Django的authenticate函数来验证用户名和密码
            user = authenticate(username=username, password=password)
            
            if user:
                # 使用Django的login函数来登录用户
                login(request, user)
                return Response({
                    "message": "登录成功",
                    "username": user.username
                })
            return Response({
                "message": "用户名或密码错误"
            }, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    """
    用户登出视图

    返回值：
    - 成功：返回登出成功信息
    """
    
    def post(self, request):
        # 使用Django的logout函数来登出用户
        logout(request)
        return Response({"message": "登出成功"})
