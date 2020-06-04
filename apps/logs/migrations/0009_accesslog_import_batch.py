# Generated by Django 2.2.4 on 2019-08-16 07:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0008_importbatch'),
    ]

    operations = [
        migrations.AddField(
            model_name='accesslog',
            name='import_batch',
            field=models.ForeignKey(
                default=None, on_delete=django.db.models.deletion.CASCADE, to='logs.ImportBatch'
            ),
            preserve_default=False,
        ),
    ]
