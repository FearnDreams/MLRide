# 详细数据库设计

## 1. 用户认证相关表

### authentication_user（用户表）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BigInt | 用户ID | 主键，自增 |
| password | Varchar(128) | 密码哈希值 | 非空 |
| last_login | Datetime | 最后登录时间 | 可空 |
| is_superuser | Boolean | 是否超级用户 | 非空，默认False |
| username | Varchar(150) | 用户名 | 唯一，非空 |
| email | Varchar(254) | 电子邮件 | 非空 |
| is_staff | Boolean | 是否工作人员 | 非空，默认False |
| is_active | Boolean | 是否激活 | 非空，默认True |
| date_joined | Datetime | 注册时间 | 非空 |
| avatar | Varchar(100) | 用户头像路径 | 可空 |
| nickname | Varchar(50) | 用户昵称 | 可空 |
| created_at | Datetime | 创建时间 | 非空，自动添加 |
| updated_at | Datetime | 更新时间 | 非空，自动更新 |

### authentication_user_groups（用户组关联表）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BigInt | 关联ID | 主键，自增 |
| user_id | BigInt | 用户ID | 外键，关联authentication_user |
| group_id | Int | 组ID | 外键，关联auth_group |

### authentication_user_user_permissions（用户权限关联表）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BigInt | 关联ID | 主键，自增 |
| user_id | BigInt | 用户ID | 外键，关联authentication_user |
| permission_id | Int | 权限ID | 外键，关联auth_permission |

## 2. 权限相关表

### auth_permission（权限表）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Int | 权限ID | 主键，自增 |
| name | Varchar(255) | 权限名称 | 非空 |
| content_type_id | Int | 内容类型ID | 外键，关联django_content_type |
| codename | Varchar(100) | 权限代码 | 非空 |

### auth_group（用户组表）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Int | 组ID | 主键，自增 |
| name | Varchar(150) | 组名称 | 唯一，非空 |

### auth_group_permissions（组权限关联表）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BigInt | 关联ID | 主键，自增 |
| group_id | Int | 组ID | 外键，关联auth_group |
| permission_id | Int | 权限ID | 外键，关联auth_permission |

## 3. 系统表

### django_content_type（内容类型表）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Int | 内容类型ID | 主键，自增 |
| app_label | Varchar(100) | 应用标签 | 非空 |
| model | Varchar(100) | 模型名称 | 非空 |

### django_migrations（迁移记录表）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BigInt | 迁移ID | 主键，自增 |
| app | Varchar(255) | 应用名称 | 非空 |
| name | Varchar(255) | 迁移文件名 | 非空 |
| applied | Datetime | 应用时间 | 非空 |

### django_session（会话表）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| session_key | Varchar(40) | 会话键 | 主键 |
| session_data | Text | 会话数据 | 非空 |
| expire_date | Datetime | 过期时间 | 非空 |

## 4. 管理日志表

### django_admin_log（管理操作日志表）
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Int | 日志ID | 主键，自增 |
| action_time | Datetime | 操作时间 | 非空 |
| object_id | Text | 对象ID | 可空 |
| object_repr | Varchar(200) | 对象描述 | 非空 |
| action_flag | SmallInt | 操作类型 | 非空 |
| change_message | Text | 变更信息 | 非空 |
| content_type_id | Int | 内容类型ID | 外键，可空 |
| user_id | BigInt | 用户ID | 外键，关联authentication_user |

## 数据库查询示例

1. 查询所有用户：
```sql
SELECT * FROM authentication_user;
```

2. 查询用户权限：
```sql
SELECT p.codename, p.name 
FROM authentication_user_user_permissions up
JOIN auth_permission p ON up.permission_id = p.id
WHERE up.user_id = [用户ID];
```

3. 查询用户组：
```sql
SELECT g.name 
FROM authentication_user_groups ug
JOIN auth_group g ON ug.group_id = g.id
WHERE ug.user_id = [用户ID];
```