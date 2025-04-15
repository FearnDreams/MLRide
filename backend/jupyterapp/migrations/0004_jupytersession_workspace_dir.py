from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jupyterapp', '0003_jupytersession_container_id'),  # 依赖于最新的迁移
    ]

    operations = [
        migrations.AddField(
            model_name='jupytersession',
            name='workspace_dir',
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name='工作目录'
            ),
        ),
    ] 