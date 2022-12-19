# Generated by Django 2.2.16 on 2020-10-27 15:48

from django.db import migrations, models
import django.db.models.expressions


class Migration(migrations.Migration):

    dependencies = [('scheduler', '0004_automatic')]

    operations = [
        migrations.AddConstraint(
            model_name='fetchintention',
            constraint=models.CheckConstraint(
                check=models.Q(start_date__lt=django.db.models.expressions.F('end_date')),
                name='timeline',
            ),
        )
    ]
