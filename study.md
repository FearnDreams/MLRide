# Django REST Framework 学习笔记

## 序列化器（Serializer）

1. **什么是序列化器？**
   - 序列化器负责在Django模型对象和JSON/Dict等数据格式之间进行转换
   - 提供数据验证功能
   - 控制数据的展示方式

2. **ModelSerializer vs Serializer**
   - ModelSerializer: 
     * 自动根据模型生成字段
     * 自动生成验证器
     * 包含默认的create()和update()实现
   - Serializer:
     * 更灵活，完全自定义
     * 适用于不直接对应模型的数据结构

3. **重要属性和方法**
   - write_only: 字段只用于反序列化（如密码）
   - read_only: 字段只用于序列化
   - validators: 字段级别的验证器
   - validate_字段名: 单个字段的验证方法
   - validate: 多个字段的交叉验证

4. **最佳实践**
   - 敏感信息使用write_only=True
   - 使用Django内置的密码验证器
   - 在create方法中使用create_user而不是create
   - 为每个序列化器添加清晰的文档字符串

## 视图（Views）

1. **基于类的视图**
   - APIView: 最基础的视图类，提供HTTP方法处理
   - generics.CreateAPIView: 专门用于创建资源的视图
   - 每个视图类都可以定义permission_classes控制访问权限

2. **认证与权限**
   - permission_classes = []: 允许任何用户访问
   - authenticate(): Django提供的用户认证函数
   - login(): 创建用户会话
   - logout(): 清除用户会话

3. **响应处理**
   - Response: DRF的响应类，自动处理JSON序列化
   - status: HTTP状态码常量（如201 CREATED, 400 BAD_REQUEST）
   - validated_data: 序列化器验证后的数据

4. **最佳实践**
   - 使用适当的HTTP状态码
   - 提供清晰的错误消息
   - 注意认证和权限设置
   - 使用文档字符串说明视图用途

## API测试与开发流程

1. **为什么先测试API？**
   - 确保基础功能的正确性
   - 及早发现并修复问题
   - 为前端开发提供稳定基础
   - 符合微服务架构设计理念

2. **测试工具选择**
   - Postman：图形化界面，易于使用
   - curl：命令行工具，适合脚本化测试
   - Python requests：编程方式测试，可集成到自动化测试中

3. **开发流程最佳实践**
   - 先完成并测试后端API
   - 再进行前端开发
   - 最后进行集成测试
   - 遵循渐进式开发原则

4. **注意事项**
   - 测试不同的输入场景
   - 验证错误处理机制
   - 检查返回的状态码和消息
   - 确保数据的一致性

## HTTP请求方法基础

1. **HTTP请求方法概述**
   - GET: 获取资源，参数在URL中，不改变服务器状态
   - POST: 创建资源，参数在请求体中，会改变服务器状态
   - PUT: 更新资源，替换整个资源
   - DELETE: 删除资源
   
2. **POST请求详解**
   - 用途：创建新资源（如用户注册）
   - 特点：
     * 数据在请求体中传输，更安全
     * 数据大小无限制
     * 支持复杂数据结构（JSON等）
   - 请求组成：
     * 请求头（Headers）：包含Content-Type等信息
     * 请求体（Body）：包含实际数据

3. **Content-Type**
   - application/json：JSON格式数据
   - application/x-www-form-urlencoded：表单数据
   - multipart/form-data：文件上传

4. **状态码含义**
   - 2xx：成功（如201 Created）
   - 4xx：客户端错误（如400 Bad Request）
   - 5xx：服务器错误

## 数据库管理

1. **数据库配置**
   - 配置文件：`settings.py`
   - 关键设置：
     * ENGINE: 数据库引擎
     * NAME: 数据库名
     * USER: 用户名
     * PASSWORD: 密码
     * HOST: 主机地址
     * PORT: 端口号

2. **数据库操作命令**
   - 查看所有数据库：`SHOW DATABASES;`
   - 查看所有表：`SHOW TABLES;`
   - 查看表结构：`DESCRIBE table_name;`
   - 查询数据：`SELECT * FROM table_name;`

3. **Django数据库命令**
   - `python manage.py makemigrations`: 创建数据库迁移文件
   - `python manage.py migrate`: 应用数据库迁移
   - `python manage.py createsuperuser`: 创建管理员用户
   - `python manage.py dbshell`: 打开数据库命令行

4. **最佳实践**
   - 定期备份数据库
   - 使用迁移文件管理数据库变更
   - 在修改模型后及时创建和应用迁移
   - 在生产环境中使用安全的数据库配置
