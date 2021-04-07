# Generated by Django 3.1.6 on 2021-03-29 08:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('export', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flexibledataexport',
            name='export_params',
            field=models.JSONField(
                blank=True, default=dict, help_text='Serialized parameters of the export'
            ),
        ),
        migrations.AlterField(
            model_name='flexibledataexport',
            name='extra_info',
            field=models.JSONField(blank=True, default=dict, help_text='Internal stuff'),
        ),
        migrations.AlterField(
            model_name='flexibledataexport',
            name='output_file',
            field=models.FileField(blank=True, null=True, upload_to='export'),
        ),
    ]
