from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework.authtoken.models import Token
from .serializers import UserRegistrationSerializer, UserLoginSerializer
import logging

# 配置日志
logger = logging.getLogger(__name__)

@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(APIView):
    """
    获取CSRF Token的视图
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "status": "success",
            "message": "CSRF cookie set"
        })

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    """
    用户注册视图

    允许任何用户访问，不需要认证

    返回值：
    - 成功：返回用户信息和token
    - 失败：返回错误信息
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """
        处理POST请求，实现用户注册功能
        """
        logger.info(f"收到注册请求，数据: {request.data}")

        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                # 删除旧的token（如果存在）
                Token.objects.filter(user=user).delete()
                # 创建新的token
                token = Token.objects.create(user=user)
                
                logger.info(f"用户注册成功: {user.username}")
                return Response({
                    "status": "success",
                    "message": "注册成功",
                    "data": {
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email
                        },
                        "token": token.key
                    }
                }, status=status.HTTP_201_CREATED)

            # 处理验证错误
            logger.error(f"注册数据验证失败: {serializer.errors}")
            error_message = ""
            if "username" in serializer.errors:
                error_message = serializer.errors["username"][0]
            elif "email" in serializer.errors:
                error_message = serializer.errors["email"][0]
            elif "password" in serializer.errors:
                error_message = serializer.errors["password"][0]
            else:
                error_message = "注册数据验证失败"

            return Response({
                "status": "error",
                "message": error_message
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"用户注册失败: {str(e)}")
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    """
    用户登录视图
    """
    permission_classes = [AllowAny]

    def post(self, request):
        logger.info(f"收到登录请求，用户名: {request.data.get('username')}")

        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(username=username, password=password)

            if user:
                # 删除旧的token（如果存在）
                Token.objects.filter(user=user).delete()
                # 创建新的token
                token = Token.objects.create(user=user)
                # 登录用户
                login(request, user)
                
                logger.info(f"用户登录成功: {username}")
                return Response({
                    "status": "success",
                    "message": "登录成功",
                    "data": {
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email
                        },
                        "token": token.key
                    }
                })
            
            logger.warning(f"登录失败，用户名或密码错误: {username}")
            return Response({
                "status": "error",
                "message": "用户名或密码错误"
            }, status=status.HTTP_401_UNAUTHORIZED)

        logger.error(f"登录数据验证失败: {serializer.errors}")
        error_message = ""
        if "username" in serializer.errors:
            error_message = serializer.errors["username"][0]
        elif "password" in serializer.errors:
            error_message = serializer.errors["password"][0]
        else:
            error_message = "登录数据验证失败"

        return Response({
            "status": "error",
            "message": error_message
        }, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    """
    用户登出视图
    """
    permission_classes = [AllowAny]
    
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
