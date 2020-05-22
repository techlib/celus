# Generated by Django 2.2.10 on 2020-05-15 08:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0032_optimize_accesslog_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='importbatch',
            name='interest_timestamp',
            field=models.DateTimeField(
                blank=True, help_text='When was interest processed for this batch', null=True
            ),
        ),
        migrations.CreateModel(
            name='ReportMaterializationSpec',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('name', models.CharField(max_length=100)),
                ('note', models.TextField(blank=True)),
                ('keep_metric', models.BooleanField(default=True)),
                ('keep_organization', models.BooleanField(default=True)),
                ('keep_platform', models.BooleanField(default=True)),
                ('keep_target', models.BooleanField(default=True)),
                ('keep_dim1', models.BooleanField(default=True)),
                ('keep_dim2', models.BooleanField(default=True)),
                ('keep_dim3', models.BooleanField(default=True)),
                ('keep_dim4', models.BooleanField(default=True)),
                ('keep_dim5', models.BooleanField(default=True)),
                ('keep_dim6', models.BooleanField(default=True)),
                ('keep_dim7', models.BooleanField(default=True)),
                ('keep_date', models.BooleanField(default=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                (
                    'base_report_type',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='logs.ReportType'
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name='reporttype',
            name='materialization_spec',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='logs.ReportMaterializationSpec',
            ),
        ),
    ]
