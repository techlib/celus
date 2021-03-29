from django.db import migrations


def remove_http_auth_from_c5(apps, schema_editor):
    SushiCredentials = apps.get_model('sushi', 'SushiCredentials')
    SushiCredentials.objects.filter(counter_version=5).update(http_password="", http_username="")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('sushi', '0038_jsonfield'),
    ]

    operations = [
        migrations.RunPython(remove_http_auth_from_c5, noop),
    ]
