# Generated by Django 2.2.12 on 2020-05-25 08:02

from django.db import migrations, models


def fill_version_hash(apps, schema_editor):
    """
    The `save` method takes care of storing the version_hash, so we just need to run `save` on
    all instances
    """
    SushiCredentials = apps.get_model('sushi', 'SushiCredentials')
    for credentials in SushiCredentials.objects.all():
        credentials.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('sushi', '0028_sushifetchattempt_credentials_version_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='sushicredentials',
            name='version_hash',
            field=models.CharField(
                default='', help_text='Current hash of model attributes', max_length=32
            ),
            preserve_default=False,
        ),
        migrations.RunPython(fill_version_hash, noop),
    ]
