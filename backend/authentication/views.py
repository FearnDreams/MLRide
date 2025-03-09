from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework.authtoken.models import Token
from .serializers import UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer, UserUpdateSerializer
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

class UserProfileView(APIView):
    """
    用户个人信息视图
    
    用于获取当前登录用户的个人信息
    
    权限：
    - 需要用户登录
    
    返回值：
    - 成功：返回用户个人信息
    - 失败：返回错误信息
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        获取当前登录用户的个人信息
        """
        try:
            serializer = UserProfileSerializer(request.user, context={'request': request})
            logger.info(f"获取用户个人信息成功: {request.user.username}")
            return Response({
                "status": "success",
                "message": "获取个人信息成功",
                "data": serializer.data
            })
        except Exception as e:
            logger.error(f"获取用户个人信息失败: {str(e)}")
            return Response({
                "status": "error",
                "message": f"获取个人信息失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CurrentUserView(APIView):
    """
    当前用户信息视图
    
    用于获取当前登录用户的基本信息
    
    权限：
    - 需要用户登录
    
    返回值：
    - 成功：返回用户基本信息
    - 失败：返回错误信息
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        获取当前登录用户的基本信息
        """
        try:
            user = request.user
            logger.info(f"获取当前用户信息成功: {user.username}")
            return Response({
                "status": "success",
                "message": "获取用户信息成功",
                "data": {
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email
                    }
                }
            })
        except Exception as e:
            logger.error(f"获取当前用户信息失败: {str(e)}")
            return Response({
                "status": "error",
                "message": f"获取用户信息失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class UserUpdateView(APIView):
    """
    用户信息更新视图
    
    用于更新当前登录用户的个人信息
    
    权限：
    - 需要用户登录
    
    返回值：
    - 成功：返回更新后的用户个人信息
    - 失败：返回错误信息
    """
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        """
        更新当前登录用户的个人信息
        """
        try:
            serializer = UserUpdateSerializer(request.user, data=request.data, context={'request': request}, partial=True)
            if serializer.is_valid():
                user = serializer.save()
                # 如果更新了密码，需要重新登录
                if 'new_password' in request.data:
                    # 删除旧的token
                    Token.objects.filter(user=user).delete()
                    # 创建新的token
                    token = Token.objects.create(user=user)
                    logger.info(f"用户密码更新成功，重新生成token: {user.username}")
                    return Response({
                        "status": "success",
                        "message": "个人信息更新成功，请使用新的token",
                        "data": {
                            "token": token.key
                        }
                    })
                
                # 获取更新后的用户信息
                profile_serializer = UserProfileSerializer(user, context={'request': request})
                logger.info(f"用户信息更新成功: {user.username}")
                return Response({
                    "status": "success",
                    "message": "个人信息更新成功",
                    "data": profile_serializer.data
                })
            
            # 处理验证错误
            logger.error(f"用户信息更新验证失败: {serializer.errors}")
            error_message = ""
            if "nickname" in serializer.errors:
                error_message = serializer.errors["nickname"][0]
            elif "avatar" in serializer.errors:
                error_message = serializer.errors["avatar"][0]
            elif "current_password" in serializer.errors:
                error_message = serializer.errors["current_password"][0]
            elif "new_password" in serializer.errors:
                error_message = serializer.errors["new_password"][0]
            else:
                error_message = "用户信息更新验证失败"
            
            return Response({
                "status": "error",
                "message": error_message
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"用户信息更新失败: {str(e)}")
            return Response({
                "status": "error",
                "message": f"用户信息更新失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class UserDeleteView(APIView):
    """
    用户账户注销视图
    
    用于注销当前登录用户的账户
    
    权限：
    - 需要用户登录
    
    返回值：
    - 成功：返回注销成功的消息
    - 失败：返回错误信息
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        注销当前登录用户的账户
        
        需要提供当前密码进行验证
        """
        try:
            # 验证当前密码
            current_password = request.data.get('current_password')
            if not current_password:
                return Response({
                    "status": "error",
                    "message": "请提供当前密码"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 检查密码是否正确
            if not request.user.check_password(current_password):
                return Response({
                    "status": "error",
                    "message": "密码不正确"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取用户名，用于日志记录
            username = request.user.username
            
            # 删除用户的token
            Token.objects.filter(user=request.user).delete()
            
            # 注销用户
            user = request.user
            logout(request)
            user.delete()
            
            logger.info(f"用户账户注销成功: {username}")
            return Response({
                "status": "success",
                "message": "账户注销成功"
            })
            
        except Exception as e:
            logger.error(f"用户账户注销失败: {str(e)}")
            return Response({
                "status": "error",
                "message": f"账户注销失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
