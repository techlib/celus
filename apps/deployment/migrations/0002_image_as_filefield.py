# Generated by Django 2.2.14 on 2020-07-21 14:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deployment', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='footerimage', name='img', field=models.FileField(upload_to='deployment'),
        ),
        migrations.AlterField(
            model_name='sitelogo', name='img', field=models.FileField(upload_to='deployment'),
        ),
    ]
