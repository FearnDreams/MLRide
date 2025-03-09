from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    自定义用户模型，继承自 Django 的 AbstractUser。

    AbstractUser 默认提供了 username, password, email, first_name, last_name, is_active, is_staff, is_superuser, last_login, date_joined 等字段。
    我们在这里扩展了 AbstractUser，添加了额外的字段和 Meta 信息。
    """
    email = models.EmailField(unique=True, verbose_name='邮箱')
    """
    邮箱地址字段。

    - unique=True: 确保邮箱地址在数据库中是唯一的。
    - verbose_name='邮箱': 在 Django Admin 后台和表单中显示的字段名称为"邮箱"。
    """
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='头像')
    """
    用户头像字段。
    
    - upload_to='avatars/': 指定上传的头像文件存储在media目录下的avatars子目录中。
    - null=True: 允许数据库中该字段为NULL。
    - blank=True: 允许表单中该字段为空。
    - verbose_name='头像': 在Django Admin后台和表单中显示的字段名称为"头像"。
    """
    nickname = models.CharField(max_length=50, null=True, blank=True, verbose_name='昵称')
    """
    用户昵称字段。
    
    - max_length=50: 限制昵称最大长度为50个字符。
    - null=True: 允许数据库中该字段为NULL。
    - blank=True: 允许表单中该字段为空。
    - verbose_name='昵称': 在Django Admin后台和表单中显示的字段名称为"昵称"。
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    """
    创建时间字段。

    - auto_now_add=True:  在对象第一次被创建时自动设置当前时间，后续不会被修改。
    - verbose_name='创建时间': 在 Django Admin 后台和表单中显示的字段名称为"创建时间"。
    """
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    """
    更新时间字段。

    - auto_now=True: 每次对象被保存时自动更新为当前时间。
    - verbose_name='更新时间': 在 Django Admin 后台和表单中显示的字段名称为"更新时间"。
    """

    class Meta:
        """
        Meta 类用于配置模型的元数据。
        """
        verbose_name = '用户'
        """
        verbose_name 用于设置模型的单数形式名称，在 Django Admin 后台中显示为"用户"。
        """
        verbose_name_plural = verbose_name
        """
        verbose_name_plural 用于设置模型的复数形式名称，这里设置为与 verbose_name 相同，表示单复数形式相同，在 Django Admin 后台中也显示为"用户"。
        """
        ordering = ['-created_at']
        """
        ordering 用于设置模型对象的默认排序方式。
        ['-created_at'] 表示按照 'created_at' 字段倒序排列，即最新创建的用户排在前面。
        """

    def __str__(self):
        """
        定义模型的字符串表示形式。

        当在 Django Admin 后台或者在代码中打印 User 对象时，会显示这个方法返回的值。
        这里返回 self.username，表示显示用户的用户名。
        """
        return self.username
