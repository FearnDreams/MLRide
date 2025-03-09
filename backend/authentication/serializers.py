from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
import logging

# 配置日志
logger = logging.getLogger(__name__)

User = get_user_model()

"""
serializers.ModelSerializer 是 Django REST framework 提供的一个用于序列化和反序列化模型实例的类。
它简化了创建序列化器的过程，特别是当你需要与 Django 模型直接关联时。
"""

# 用户注册序列化器
class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    用户注册序列化器。

    该序列化器继承自 `serializers.ModelSerializer`，用于处理用户注册的数据验证和创建。
    它定义了注册时需要接收和验证的字段，包括用户名、密码、确认密码和邮箱。
    """
    password = serializers.CharField(
        write_only=True, # password 字段仅用于写入操作，不会在序列化输出中返回
        required=True, # password 字段为必填字段
        style={'input_type': 'password'}, # 设置 password 字段在 API 界面中的样式为密码输入框
        validators=[validate_password] # 使用 Django 内置的密码验证器来验证密码强度
    )
    password2 = serializers.CharField(
        write_only=True, # password2 字段仅用于写入操作，不会在序列化输出中返回
        required=True, # password2 字段为必填字段
        style={'input_type': 'password'} # 设置 password2 字段在 API 界面中的样式为密码输入框
    )

    # 元数据类，用于定义序列化器的元数据
    class Meta:
        """
        Meta 类用于配置 UserRegistrationSerializer 的元数据。

        - model: 指定序列化器关联的模型为 User 模型。
        - fields: 指定序列化器需要处理的模型字段，这里包括 'username', 'password', 'password2', 'email'。
        - extra_kwargs:  用于为字段添加额外的关键字参数，这里设置 'email' 字段为必填。
        """
        model = User # 关联的模型为 User 模型
        fields = ('username', 'password', 'password2', 'email') # 需要序列化的字段
        extra_kwargs = {
            'email': {'required': True} # 邮箱字段为必填
        }

    def validate_username(self, value):
        """
        验证用户名。

        - 检查用户名长度是否小于 3 个字符，如果小于则抛出验证错误。
        - 检查用户名是否已存在于数据库中，如果已存在则抛出验证错误。
        - 如果用户名验证通过，则返回用户名。

        Args:
            value (str): 用户输入的用户名。

        Returns:
            str: 验证通过的用户名。

        Raises:
            serializers.ValidationError: 如果用户名长度小于 3 个字符或用户名已存在。
        """
        if len(value) < 3: # 检查用户名长度是否小于 3 个字符
            raise serializers.ValidationError("用户名长度至少为3个字符") # 抛出验证错误，提示用户名长度过短
        if User.objects.filter(username=value).exists(): # 检查用户名是否已存在于数据库中
            raise serializers.ValidationError("该用户名已被使用") # 抛出验证错误，提示用户名已被使用
        return value # 返回验证通过的用户名

    def validate_email(self, value):
        """
        验证邮箱。

        - 检查邮箱是否已存在于数据库中，如果已存在则抛出验证错误。
        - 如果邮箱验证通过，则返回邮箱。

        Args:
            value (str): 用户输入的邮箱。

        Returns:
            str: 验证通过的邮箱。

        Raises:
            serializers.ValidationError: 如果邮箱已存在。
        """
        if User.objects.filter(email=value).exists(): # 检查邮箱是否已存在于数据库中
            raise serializers.ValidationError("该邮箱已被注册") # 抛出验证错误，提示邮箱已被注册
        return value # 返回验证通过的邮箱

    def validate(self, attrs):
        """
        验证密码。

        - 检查两次输入的密码是否一致，如果不一致则抛出验证错误。
        - 调用 Django 内置的 `validate_password` 函数验证密码强度，如果密码不符合强度要求则捕获异常并抛出验证错误。
        - 如果密码验证通过，则返回所有验证属性。

        Args:
            attrs (dict): 包含所有需要验证的字段的字典，这里包括 'password' 和 'password2'。

        Returns:
            dict: 验证通过的所有属性字典。

        Raises:
            serializers.ValidationError: 如果两次输入的密码不匹配或密码强度不符合要求。
        """
        if attrs['password'] != attrs['password2']: # 检查两次输入的密码是否一致
            raise serializers.ValidationError({"password": "两次输入的密码不匹配"}) # 抛出验证错误，提示两次密码不一致
        
        try:
            validate_password(attrs['password']) # 调用 Django 内置的密码验证器验证密码强度
        except Exception as e: # 捕获密码验证器抛出的异常
            raise serializers.ValidationError({"password": list(e.messages)}) # 抛出验证错误，并将密码验证器的错误信息列表作为错误详情
        
        return attrs # 返回验证通过的所有属性

    def create(self, validated_data):
        """
        创建用户。

        - 从验证后的数据 `validated_data` 中移除 `password2` 字段，因为该字段仅用于注册时的密码确认，不需要保存到数据库中。
        - 调用 `User.objects.create_user` 方法创建用户，使用验证后的用户名、邮箱和密码。
        - 记录用户创建成功的日志信息。
        - 如果创建用户过程中发生任何异常，捕获异常并记录错误日志，然后抛出验证错误。

        Args:
            validated_data (dict): 验证通过的数据字典，包含用户名、邮箱和密码。

        Returns:
            User: 创建成功的 User 模型实例。

        Raises:
            serializers.ValidationError: 如果创建用户失败。
        """
        try:
            validated_data.pop('password2') # 移除 password2 字段，因为 User 模型不需要 password2 字段
            user = User.objects.create_user( # 调用 User 模型的 create_user 方法创建用户
                username=validated_data['username'], # 使用验证后的用户名
                email=validated_data['email'], # 使用验证后的邮箱
                password=validated_data['password'] # 使用验证后的密码
            )
            logger.info(f"成功创建用户: {user.username}") # 记录用户创建成功的日志
            return user # 返回创建成功的用户实例
        except Exception as e: # 捕获创建用户过程中可能发生的任何异常
            logger.error(f"创建用户失败: {str(e)}") # 记录用户创建失败的错误日志
            raise serializers.ValidationError({"message": f"创建用户失败: {str(e)}"}) # 抛出验证错误，提示用户创建失败，并将错误信息返回给前端

# 用户登录序列化器
class UserLoginSerializer(serializers.Serializer):
    """
    用户登录序列化器。

    该序列化器用于验证用户登录时提交的用户名和密码，
    并确保用户名和密码符合最小长度要求。
    """
    username = serializers.CharField(required=True, help_text="用户名") # 用户名字段，必填
    password = serializers.CharField(
        required=True, # 密码字段，必填
        write_only=True, # 密码字段仅用于写入，不进行序列化输出
        style={'input_type': 'password'}, # 设置密码字段的输入类型为 password，在前端显示为密码输入框
        help_text="密码" # 密码字段的帮助文本
    )

    def validate(self, attrs):
        """
        验证用户名和密码。

        - 检查用户名长度是否小于 3 个字符，如果小于则抛出验证错误。
        - 检查密码长度是否小于 6 个字符，如果小于则抛出验证错误。
        - 如果用户名和密码都通过验证，则返回验证后的属性字典。

        Args:
            attrs (dict): 包含用户名和密码的字典。

        Returns:
            dict: 验证通过的属性字典。

        Raises:
            serializers.ValidationError: 如果用户名或密码不符合长度要求。
        """
        if len(attrs['username']) < 3: # 检查用户名长度是否小于 3 个字符
            raise serializers.ValidationError({"username": "用户名长度至少为3个字符"}) # 抛出验证错误，提示用户名长度过短
        if len(attrs['password']) < 6: # 检查密码长度是否小于 6 个字符
            raise serializers.ValidationError({"password": "密码长度至少为6个字符"}) # 抛出验证错误，提示密码长度过短
        return attrs # 返回验证通过的属性字典

# 用户个人信息序列化器
class UserProfileSerializer(serializers.ModelSerializer):
    """
    用户个人信息序列化器。

    该序列化器用于获取和更新用户的个人信息，包括用户名、邮箱、头像和昵称。
    """
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        """
        Meta 类用于配置 UserProfileSerializer 的元数据。

        - model: 指定序列化器关联的模型为 User 模型。
        - fields: 指定序列化器需要处理的模型字段，这里包括 'id', 'username', 'email', 'avatar', 'avatar_url', 'nickname', 'created_at', 'updated_at'。
        - read_only_fields: 指定只读字段，这些字段在更新时不会被修改。
        """
        model = User
        fields = ('id', 'username', 'email', 'avatar', 'avatar_url', 'nickname', 'created_at', 'updated_at')
        read_only_fields = ('id', 'username', 'email', 'created_at', 'updated_at')
    
    def get_avatar_url(self, obj):
        """
        获取头像URL。

        如果用户有头像，则返回头像的完整URL；否则返回None。

        Args:
            obj (User): 用户对象。

        Returns:
            str or None: 头像的完整URL或None。
        """
        if obj.avatar and hasattr(obj.avatar, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

# 用户信息更新序列化器
class UserUpdateSerializer(serializers.ModelSerializer):
    """
    用户信息更新序列化器。

    该序列化器用于更新用户的个人信息，包括昵称和头像。
    """
    current_password = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'},
        help_text="当前密码，修改密码时需要提供"
    )
    new_password = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'},
        help_text="新密码"
    )
    
    class Meta:
        """
        Meta 类用于配置 UserUpdateSerializer 的元数据。

        - model: 指定序列化器关联的模型为 User 模型。
        - fields: 指定序列化器需要处理的模型字段，这里包括 'nickname', 'avatar', 'current_password', 'new_password'。
        """
        model = User
        fields = ('nickname', 'avatar', 'current_password', 'new_password')
    
    def validate(self, attrs):
        """
        验证用户提交的数据。

        - 如果提供了新密码，则检查是否也提供了当前密码。
        - 如果提供了当前密码，则验证当前密码是否正确。
        - 如果提供了新密码，则验证新密码的强度。

        Args:
            attrs (dict): 包含用户提交的数据的字典。

        Returns:
            dict: 验证通过的属性字典。

        Raises:
            serializers.ValidationError: 如果验证失败。
        """
        # 如果提供了新密码，则检查是否也提供了当前密码
        if attrs.get('new_password') and not attrs.get('current_password'):
            raise serializers.ValidationError({"current_password": "修改密码时需要提供当前密码"})
        
        # 如果提供了当前密码，则验证当前密码是否正确
        user = self.context['request'].user
        if attrs.get('current_password'):
            if not user.check_password(attrs.get('current_password')):
                raise serializers.ValidationError({"current_password": "当前密码不正确"})
        
        # 如果提供了新密码，则验证新密码的强度
        if attrs.get('new_password'):
            try:
                validate_password(attrs.get('new_password'), user)
            except Exception as e:
                raise serializers.ValidationError({"new_password": list(e.messages)})
        
        return attrs
    
    def update(self, instance, validated_data):
        """
        更新用户信息。

        - 如果提供了新密码，则更新用户密码。
        - 更新用户的昵称和头像。

        Args:
            instance (User): 要更新的用户实例。
            validated_data (dict): 验证通过的数据字典。

        Returns:
            User: 更新后的用户实例。
        """
        # 如果提供了新密码，则更新用户密码
        if validated_data.get('new_password'):
            instance.set_password(validated_data.pop('new_password'))
        
        # 移除current_password字段，因为不需要保存到数据库
        validated_data.pop('current_password', None)
        
        # 更新用户的昵称和头像
        return super().update(instance, validated_data)
