# Generated by Django 3.2.12 on 2022-03-30 06:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0062_merge_20220325_1628'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportinterestmetric',
            name='interest_group',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to='logs.interestgroup'
            ),
        ),
    ]
