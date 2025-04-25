"""
Admin configuration for the dataset app.
数据集应用的管理员配置。
"""

from django.contrib import admin
from .models import Dataset, DatasetPreview

@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """
    数据集管理员配置
    """
    list_display = ('name', 'file_type', 'file_size_display', 'creator', 'status', 'visibility', 'created')
    list_filter = ('status', 'visibility', 'file_type', 'preview_available')
    search_fields = ('name', 'description', 'creator__username', 'tags')
    date_hierarchy = 'created'
    readonly_fields = ('file_size', 'downloads', 'preview_available', 'file_type')
    
    def file_size_display(self, obj):
        """
        格式化文件大小显示
        """
        # 转换为KB/MB/GB
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.2f} KB"
        elif obj.file_size < 1024 * 1024 * 1024:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
        else:
            return f"{obj.file_size / (1024 * 1024 * 1024):.2f} GB"
    
    file_size_display.short_description = '文件大小'

@admin.register(DatasetPreview)
class DatasetPreviewAdmin(admin.ModelAdmin):
    """
    数据集预览管理员配置
    """
    list_display = ('dataset', 'preview_type', 'created', 'updated')
    list_filter = ('preview_type',)
    search_fields = ('dataset__name',)
    date_hierarchy = 'created'
