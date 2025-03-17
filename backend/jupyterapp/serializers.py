from rest_framework import serializers
from .models import JupyterSession

class JupyterSessionSerializer(serializers.ModelSerializer):
    """Jupyter会话序列化器"""
    
    class Meta:
        model = JupyterSession
        fields = ['id', 'project', 'token', 'url', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'token', 'created_at', 'updated_at']
