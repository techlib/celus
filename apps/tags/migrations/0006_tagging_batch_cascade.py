# Generated by Django 3.2.15 on 2022-09-15 17:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('tags', '0005_alter_tag_options')]

    operations = [
        migrations.AlterField(
            model_name='organizationtag',
            name='tagging_batch',
            field=models.ForeignKey(
                blank=True,
                help_text='If the tagging was done in a batch, this is the batch',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='tags.taggingbatch',
            ),
        ),
        migrations.AlterField(
            model_name='platformtag',
            name='tagging_batch',
            field=models.ForeignKey(
                blank=True,
                help_text='If the tagging was done in a batch, this is the batch',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='tags.taggingbatch',
            ),
        ),
        migrations.AlterField(
            model_name='titletag',
            name='tagging_batch',
            field=models.ForeignKey(
                blank=True,
                help_text='If the tagging was done in a batch, this is the batch',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='tags.taggingbatch',
            ),
        ),
    ]
