"""
Django管理命令：修复Jupyter配置文件语法错误

使用方法：
python manage.py fix_jupyter_configs
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import logging
from project.utils import cleanup_workspace_jupyter_configs

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """修复Jupyter配置文件语法错误的管理命令"""
    
    help = '修复所有工作空间中Jupyter配置文件的语法错误'
    
    def add_arguments(self, parser):
        """添加命令行参数"""
        parser.add_argument(
            '--workspace-dir',
            type=str,
            help='指定工作空间目录路径（默认为backend/workspaces）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只检查不修复（预览模式）'
        )
    
    def handle(self, *args, **options):
        """执行命令的主要逻辑"""
        # 获取工作空间目录
        workspace_base = options.get('workspace_dir')
        if not workspace_base:
            # 默认使用backend/workspaces目录
            workspace_base = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'workspaces'
            )
        
        if not os.path.exists(workspace_base):
            self.stdout.write(
                self.style.ERROR(f'工作空间目录不存在: {workspace_base}')
            )
            return
        
        self.stdout.write(f'开始扫描工作空间目录: {workspace_base}')
        
        total_fixed = 0
        project_count = 0
        
        # 遍历所有项目目录
        for item in os.listdir(workspace_base):
            if item.startswith('project_'):
                project_dir = os.path.join(workspace_base, item)
                if os.path.isdir(project_dir):
                    project_count += 1
                    self.stdout.write(f'检查项目目录: {item}')
                    
                    if options['dry_run']:
                        # 预览模式：只检查不修复
                        config_files = []
                        for root, dirs, files in os.walk(project_dir):
                            for file in files:
                                if file == 'jupyter_notebook_config.py':
                                    config_path = os.path.join(root, file)
                                    # 检查是否有语法错误
                                    try:
                                        with open(config_path, 'r', encoding='utf-8') as f:
                                            content = f.read()
                                        if 'CP=\\"' in content:
                                            config_files.append(config_path)
                                    except Exception as e:
                                        self.stdout.write(
                                            self.style.WARNING(f'  无法读取配置文件: {config_path}, 错误: {str(e)}')
                                        )
                        
                        if config_files:
                            self.stdout.write(
                                self.style.WARNING(f'  发现 {len(config_files)} 个需要修复的配置文件:')
                            )
                            for config_file in config_files:
                                self.stdout.write(f'    - {config_file}')
                            total_fixed += len(config_files)
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(f'  无需修复的配置文件')
                            )
                    else:
                        # 实际修复模式
                        try:
                            fixed_count = cleanup_workspace_jupyter_configs(project_dir)
                            if fixed_count > 0:
                                self.stdout.write(
                                    self.style.SUCCESS(f'  修复了 {fixed_count} 个配置文件')
                                )
                                total_fixed += fixed_count
                            else:
                                self.stdout.write(
                                    self.style.SUCCESS(f'  无需修复的配置文件')
                                )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'  修复配置文件时出错: {str(e)}')
                            )
        
        # 输出总结
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'\n预览完成：')
            )
            self.stdout.write(f'扫描了 {project_count} 个项目目录')
            self.stdout.write(f'发现 {total_fixed} 个需要修复的配置文件')
            self.stdout.write('使用 --no-dry-run 参数来实际执行修复')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n修复完成：')
            )
            self.stdout.write(f'扫描了 {project_count} 个项目目录')
            self.stdout.write(f'修复了 {total_fixed} 个配置文件')
        
        if total_fixed == 0:
            self.stdout.write(
                self.style.SUCCESS('所有Jupyter配置文件都正常，无需修复！')
            ) 