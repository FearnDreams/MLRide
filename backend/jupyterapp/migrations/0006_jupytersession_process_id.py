from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jupyterapp', '0005_merge_20250414_2142'),  # 依赖于合并迁移
    ]

    operations = [
        migrations.AddField(
            model_name='jupytersession',
            name='process_id',
            field=models.IntegerField(
                blank=True,
                null=True,
                verbose_name='进程ID'
            ),
        ),
    ] 