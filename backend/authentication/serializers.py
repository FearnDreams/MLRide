from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

"""
serializers.ModelSerializer 是 Django REST framework 提供的一个用于序列化和反序列化模型实例的类。
它简化了创建序列化器的过程，特别是当你需要与 Django 模型直接关联时。
"""

# 用户注册序列化器
class UserRegistrationSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    # 元数据类，用于定义序列化器的元数据
    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email')

    # 验证密码是否匹配
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "两次密码不匹配"})
        return attrs

    # 创建用户
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

# 用户登录序列化器
class UserLoginSerializer(serializers.Serializer):
    """用户登录序列化器"""
    username = serializers.CharField(required=True)#用户名      
    password = serializers.CharField(required=True, write_only=True) #密码
