# Generated by Django 2.2.4 on 2019-08-02 15:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [('publications', '0006_no_null_title_text_attrs')]

    operations = [
        migrations.AlterUniqueTogether(
            name='title', unique_together={('name', 'isbn', 'issn', 'eissn', 'doi')}
        )
    ]
