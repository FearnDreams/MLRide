# MLRide - 机器学习生产平台

## 项目概述
MLRide是一个现代化的机器学习生产平台，旨在提供一站式的机器学习开发和部署解决方案。该平台集成了容器化开发环境、在线编程调试、版本控制追踪以及可视化拖拽编程等功能，使机器学习工作流程更加高效和便捷。

## 功能模块

### 1. 用户认证模块
- 用户注册
- 用户登录
- 用户登出
- 会话管理

### 2. 容器化开发环境
- Docker容器管理
- 资源分配（CPU、内存、GPU）
- 环境配置管理

### 3. 在线编程与调试
- Jupyter Notebook集成
- 实时日志查看
- 资源监控
- 动态资源分配

### 4. 版本控制追踪
- 模型版本控制（MLflow）
- 数据版本控制（DVC）
- 代码版本控制（Git）
- 可视化版本比较

### 5. 可视化拖拽编程
- 图形化工作流设计
- 预置算法组件
- 实时工作流监控
- 配置导出与复用

## 技术栈

### 后端
- Python 3.9
- Django 4.2.18
- Django REST Framework 3.15.2
- MySQL 8.0.36

### 前端（计划中）
- React
- Ant Design
- Axios

### 开发工具
- Docker
- Kubernetes
- MLflow
- DVC
- Jupyter Notebook

## 项目结构
```
MLRide/
├── backend/                # 后端项目目录
│   ├── authentication/     # 用户认证应用
│   │   ├── migrations/    # 数据库迁移文件
│   │   ├── __init__.py
│   │   ├── admin.py      # 管理界面配置
│   │   ├── apps.py       # 应用配置
│   │   ├── models.py     # 数据模型
│   │   ├── serializers.py # 序列化器
│   │   ├── urls.py       # URL路由
│   │   └── views.py      # 视图函数
│   ├── mlride/           # 项目主配置
│   └── manage.py         # Django管理脚本
├── frontend/             # 前端项目目录（计划中）
├── README.md            # 项目文档
└── requirements.txt     # Python依赖
```

## API文档

### 认证API
- POST `/api/auth/register/` - 用户注册
  - 请求体：username, password, password2, email
  - 响应：用户信息

- POST `/api/auth/login/` - 用户登录
  - 请求体：username, password
  - 响应：登录状态

- POST `/api/auth/logout/` - 用户登出
  - 响应：登出状态

## 数据库设计

### 用户表 (auth_user)
- id: 主键
- username: 用户名
- email: 电子邮件
- password: 密码（加密存储）
- is_active: 账户状态
- date_joined: 注册时间

## 依赖要求
```
django==4.2.18
djangorestframework==3.15.2
django-cors-headers==4.6.0
mysqlclient==2.2.7
requests==2.32.3
```

## 开发进度
- [x] 项目初始化
- [x] 数据库设计
- [x] 用户认证API
- [ ] 前端开发
- [ ] 容器化环境
- [ ] 在线编程模块
- [ ] 版本控制集成
- [ ] 可视化编程界面

## 安装和运行
1. 克隆项目
2. 安装依赖：`pip install -r requirements.txt`
3. 配置数据库
4. 运行迁移：`python manage.py migrate`
5. 启动服务：`python manage.py runserver`
