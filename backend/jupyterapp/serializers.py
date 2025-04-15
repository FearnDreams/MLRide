from rest_framework import serializers
from .models import JupyterSession

class JupyterSessionSerializer(serializers.ModelSerializer):
    """Jupyter会话序列化器"""
    direct_access_url = serializers.CharField(read_only=True, required=False)
    
    class Meta:
        model = JupyterSession
        fields = ['id', 'project', 'token', 'url', 'port', 'workspace_dir', 'process_id', 'status', 'created_at', 'updated_at', 'direct_access_url']
        read_only_fields = ['id', 'token', 'created_at', 'updated_at', 'workspace_dir', 'process_id', 'direct_access_url']
