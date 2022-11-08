# Generated by Django 3.2.15 on 2022-10-11 13:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tags', '0006_tagging_batch_cascade'),
    ]

    operations = [
        migrations.AddField(
            model_name='taggingbatch',
            name='internal_name',
            field=models.CharField(
                blank=True,
                help_text='When given, it marks the batch as internal. Such batches are not shown in the UI. It also serves as identification of such batches internally.',
                max_length=64,
            ),
        ),
        migrations.AddConstraint(
            model_name='taggingbatch',
            constraint=models.UniqueConstraint(
                condition=models.Q(('internal_name', ''), _negated=True),
                fields=('internal_name',),
                name='internal_name_unique',
            ),
        ),
    ]