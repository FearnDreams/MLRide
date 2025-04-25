from django.apps import AppConfig


class DatasetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dataset'
    verbose_name = '数据集管理'
    
    def ready(self):
        """
        应用就绪时执行的操作
        """
        import dataset.signals  # 导入信号处理模块
