"""
Admin configuration for the project app.
"""

from django.contrib import admin
from .models import Project, ProjectFile

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    项目管理员配置
    """
    list_display = ('name', 'project_type', 'user', 'status', 'created_at')
    list_filter = ('project_type', 'status', 'is_public')
    search_fields = ('name', 'description', 'user__username')
    date_hierarchy = 'created_at'

@admin.register(ProjectFile)
class ProjectFileAdmin(admin.ModelAdmin):
    """
    项目文件管理员配置
    """
    list_display = ('name', 'path', 'project', 'content_type', 'size', 'created_at')
    list_filter = ('content_type', 'project__project_type')
    search_fields = ('name', 'path', 'project__name')
    date_hierarchy = 'created_at'
