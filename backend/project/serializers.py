"""
This module contains the serializers for the project management functionality.
包含项目管理功能的序列化器。
"""

from rest_framework import serializers
from django.utils import timezone
from .models import Project, ProjectFile, Workflow, WorkflowExecution, WorkflowComponentExecution
from container.serializers import DockerImageSerializer, ContainerInstanceSerializer


class ProjectFileSerializer(serializers.ModelSerializer):
    """项目文件序列化器
    
    用于序列化和反序列化项目文件信息
    
    Fields:
        id: 文件ID
        project: 关联项目
        name: 文件名称
        path: 文件路径
        content_type: 内容类型
        size: 文件大小(字节)
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    class Meta:
        model = ProjectFile
        fields = ['id', 'project', 'name', 'path', 'content_type', 'size', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    """项目序列化器
    
    用于序列化和反序列化项目信息
    
    Fields:
        id: 项目ID
        name: 项目名称
        description: 项目描述
        project_type: 项目类型
        created_at: 创建时间
        updated_at: 更新时间
        user: 创建者ID
        image: 使用的镜像ID
        container: 关联的容器ID
        is_public: 是否公开
        status: 项目状态
        image_details: 镜像详情
        container_details: 容器详情
        files: 项目文件列表
    """
    
    image_details = DockerImageSerializer(source='image', read_only=True)
    container_details = ContainerInstanceSerializer(source='container', read_only=True)
    files = ProjectFileSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'project_type', 'created_at', 'updated_at', 
            'user', 'image', 'container', 'is_public', 'status', 'image_details', 
            'container_details', 'files', 'username'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'status', 'container', 'user']
    
    def validate_name(self, value):
        """
        验证项目名称
        """
        if not value:
            raise serializers.ValidationError("项目名称不能为空")
        if len(value) > 100:
            raise serializers.ValidationError("项目名称不能超过100个字符")
        # 检查当前用户是否已有同名项目
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if Project.objects.filter(user=request.user, name=value).exists():
                if self.instance and self.instance.name == value:
                    return value
                raise serializers.ValidationError("您已有同名项目，请更换名称")
        return value
    
    def create(self, validated_data):
        """
        创建项目
        """
        # 设置用户
        request = self.context.get('request')
        validated_data['user'] = request.user
        
        # 创建项目
        project = Project.objects.create(**validated_data)
        return project 


class WorkflowComponentExecutionSerializer(serializers.ModelSerializer):
    """工作流组件执行记录序列化器
    
    用于序列化和反序列化工作流组件执行记录
    
    Fields:
        id: 执行记录ID
        execution: 关联工作流执行ID
        node_id: 组件节点ID
        component_id: 组件类型ID
        component_name: 组件名称
        status: 执行状态
        start_time: 开始时间
        end_time: 结束时间
        inputs: 输入参数
        outputs: 输出结果
        error: 错误信息
    """
    
    class Meta:
        model = WorkflowComponentExecution
        fields = [
            'id', 'execution', 'node_id', 'component_id', 'component_name', 
            'status', 'start_time', 'end_time', 'inputs', 'outputs', 'error'
        ]
        read_only_fields = ['id', 'execution']


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    """工作流执行记录序列化器
    
    用于序列化和反序列化工作流执行记录
    
    Fields:
        id: 执行记录ID
        workflow: 关联工作流ID
        status: 执行状态
        start_time: 开始时间
        end_time: 结束时间
        logs: 执行日志
        result: 执行结果
        component_executions: 组件执行记录列表
    """
    
    component_executions = WorkflowComponentExecutionSerializer(many=True, read_only=True)
    
    class Meta:
        model = WorkflowExecution
        fields = [
            'id', 'workflow', 'status', 'start_time', 'end_time', 
            'logs', 'result', 'component_executions'
        ]
        read_only_fields = ['id', 'workflow', 'start_time']


class WorkflowSerializer(serializers.ModelSerializer):
    """工作流序列化器
    
    用于序列化和反序列化工作流信息
    
    Fields:
        id: 工作流ID
        project: 关联项目ID
        name: 工作流名称
        description: 工作流描述
        definition: 工作流定义
        created_at: 创建时间
        updated_at: 更新时间
        version: 版本号
    """
    
    executions = WorkflowExecutionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Workflow
        fields = [
            'id', 'project', 'name', 'description', 'definition', 
            'created_at', 'updated_at', 'version', 'executions'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']
    
    def validate_name(self, value):
        """
        验证工作流名称
        """
        if not value:
            raise serializers.ValidationError("工作流名称不能为空")
        if len(value) > 100:
            raise serializers.ValidationError("工作流名称不能超过100个字符")
        
        # 检查同一项目中是否已有同名工作流
        project_id = self.initial_data.get('project')
        if project_id:
            if Workflow.objects.filter(project_id=project_id, name=value).exists():
                if self.instance and self.instance.name == value:
                    return value
                raise serializers.ValidationError("该项目中已有同名工作流，请更换名称")
        return value
    
    def create(self, validated_data):
        """
        创建工作流
        """
        workflow = Workflow.objects.create(**validated_data)
        return workflow
    
    def update(self, instance, validated_data):
        """
        更新工作流，如果定义有变化则创建新版本
        """
        definition = validated_data.get('definition')
        
        # 如果工作流定义发生变化，创建新版本
        if definition and instance.definition != definition:
            instance.version += 1
        
        return super().update(instance, validated_data)


class WorkflowListSerializer(serializers.ModelSerializer):
    """工作流列表序列化器
    
    用于展示工作流列表，不包含详细的定义和执行记录
    
    Fields:
        id: 工作流ID
        project: 关联项目ID
        name: 工作流名称
        description: 工作流描述
        created_at: 创建时间
        updated_at: 更新时间
        version: 版本号
    """
    
    class Meta:
        model = Workflow
        fields = [
            'id', 'project', 'name', 'description', 
            'created_at', 'updated_at', 'version'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']