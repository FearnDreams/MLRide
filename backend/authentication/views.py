from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.authtoken.models import Token
from .serializers import UserRegistrationSerializer, UserLoginSerializer
import logging

# 配置日志
logger = logging.getLogger(__name__)

# Create your views here.

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    """
    用户注册视图

    允许任何用户访问，不需要认证

    返回值：
    - 成功：返回用户信息和token
    - 失败：返回错误信息
    """
    serializer_class = UserRegistrationSerializer # 使用UserRegistrationSerializer验证和创建用户
    permission_classes = [AllowAny]  # 明确设置允许所有用户访问，即任何人都可以访问此视图

    def post(self, request, *args, **kwargs):
        """
        处理POST请求，实现用户注册功能

        Args:
            request (HttpRequest): 请求对象，包含用户注册数据
            *args: 额外的位置参数
            **kwargs: 额外的关键字参数

        Returns:
            Response: 注册成功或失败的响应
        """
        logger.info(f"收到注册请求，数据: {request.data}") # 记录收到的注册请求数据

        serializer = self.serializer_class(data=request.data) # 使用UserRegistrationSerializer反序列化请求数据
        if serializer.is_valid(): # 验证数据是否有效
            try:
                user = serializer.save() # 保存用户信息到数据库
                # 创建或获取用户的token
                token, _ = Token.objects.get_or_create(user=user) # 获取或创建用户的Token，用于后续的认证
                logger.info(f"用户注册成功: {user.username}") # 记录用户注册成功的日志
                return Response({
                    "status": "success",
                    "message": "注册成功",
                    "data": {
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email
                        },
                        "token": token.key # 返回用户的token
                    }
                }, status=status.HTTP_201_CREATED) # 返回201状态码，表示创建成功
            except Exception as e: # 捕获注册过程中的异常
                logger.error(f"用户注册失败: {str(e)}") # 记录用户注册失败的错误日志
                return Response({
                    "status": "error",
                    "message": str(e) # 返回具体的错误信息
                }, status=status.HTTP_400_BAD_REQUEST) # 返回400状态码，表示客户端请求错误

        # 处理验证错误
        logger.error(f"注册数据验证失败: {serializer.errors}") # 记录注册数据验证失败的错误日志
        error_message = "" # 初始化错误信息
        if "username" in serializer.errors: # 如果用户名验证错误
            error_message = serializer.errors["username"][0] # 获取用户名的错误信息
        elif "email" in serializer.errors: # 如果邮箱验证错误
            error_message = serializer.errors["email"][0] # 获取邮箱的错误信息
        elif "password" in serializer.errors: # 如果密码验证错误
            error_message = serializer.errors["password"][0] # 获取密码的错误信息
        else: # 其他验证错误
            error_message = "注册数据验证失败" # 设置通用的注册数据验证失败信息

        return Response({
            "status": "error",
            "message": error_message # 返回错误信息
        }, status=status.HTTP_400_BAD_REQUEST) # 返回400状态码，表示客户端请求错误

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    """
    用户登录视图

    允许任何用户访问，不需要认证

    返回值：
    - 成功：返回用户信息和token
    - 失败：返回错误信息
    """
    permission_classes = [AllowAny]  # 明确设置允许所有用户访问

    def post(self, request):
        """
        处理用户登录的POST请求。

        - 接收用户提交的用户名和密码。
        - 使用 `UserLoginSerializer` 验证用户输入的数据。
        - 如果数据验证通过，则使用 Django 的 `authenticate` 函数验证用户身份。
        - 如果用户验证成功，则使用 Django 的 `login` 函数进行登录，并创建或获取用户的 token。
        - 记录登录日志，并返回包含用户信息和 token 的成功响应。
        - 如果用户验证失败，记录警告日志，并返回错误响应。
        - 如果数据验证失败，记录错误日志，并返回包含错误信息的响应。

        Args:
            request (Request): HTTP 请求对象。

        Returns:
            Response: 登录成功或失败的响应，包含状态码、消息和数据。
        """
        logger.info(f"收到登录请求，用户名: {request.data.get('username')}") # 记录收到的登录请求，包含用户名

        serializer = UserLoginSerializer(data=request.data) # 使用 UserLoginSerializer 序列化器验证请求数据
        if serializer.is_valid(): # 检查序列化器验证是否通过
            username = serializer.validated_data['username'] # 从验证后的数据中获取用户名
            password = serializer.validated_data['password'] # 从验证后的数据中获取密码
            # 使用Django的authenticate函数来验证用户名和密码
            user = authenticate(username=username, password=password) # 使用 Django 的 authenticate 函数验证用户名和密码

            if user: # 如果用户验证成功
                # 使用Django的login函数来登录用户
                login(request, user) # 使用 Django 的 login 函数进行登录
                # 创建或获取用户的token
                token, _ = Token.objects.get_or_create(user=user) # 获取或创建用户的 token
                logger.info(f"用户登录成功: {username}") # 记录用户登录成功的日志
                return Response({
                    "status": "success", # 状态：成功
                    "message": "登录成功", # 消息：登录成功
                    "data": { # 数据
                        "user": { # 用户信息
                            "id": user.id, # 用户ID
                            "username": user.username, # 用户名
                            "email": user.email # 邮箱
                        },
                        "token": token.key # 用户的 token
                    }
                })
            logger.warning(f"登录失败，用户名或密码错误: {username}") # 记录登录失败的警告日志，用户名或密码错误
            return Response({
                "status": "error", # 状态：错误
                "message": "用户名或密码错误" # 消息：用户名或密码错误
            }, status=status.HTTP_401_UNAUTHORIZED) # 返回 401 未授权状态码

        # 处理验证错误
        logger.error(f"登录数据验证失败: {serializer.errors}") # 记录登录数据验证失败的错误日志
        error_message = "" # 初始化错误信息
        if "username" in serializer.errors: # 如果用户名验证错误
            error_message = serializer.errors["username"][0] # 获取用户名的错误信息
        elif "password" in serializer.errors: # 如果密码验证错误
            error_message = serializer.errors["password"][0] # 获取密码的错误信息
        else: # 其他验证错误
            error_message = "登录数据验证失败" # 设置通用的登录数据验证失败信息

        return Response({
            "status": "error", # 状态：错误
            "message": error_message # 消息：错误信息
        }, status=status.HTTP_400_BAD_REQUEST) # 返回 400 客户端错误状态码

@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    """
    用户登出视图

    返回值：
    - 成功：返回登出成功信息
    """
    permission_classes = [AllowAny]  # 明确设置允许所有用户访问
    
    def post(self, request):
        if request.user.is_authenticated:
            username = request.user.username
            # 删除用户的token
            Token.objects.filter(user=request.user).delete()
            logout(request)
            logger.info(f"用户登出成功: {username}")
            return Response({
                "status": "success",
                "message": "登出成功"
            })
        
        logger.warning("未登录用户尝试登出")
        return Response({
            "status": "error",
            "message": "用户未登录"
        }, status=status.HTTP_401_UNAUTHORIZED)
