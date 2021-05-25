# Generated by Django 2.2.16 on 2020-10-19 11:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sushi', '0037_broken_credentials'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Scheduler',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('url', models.URLField(unique=True)),
                ('when_ready', models.DateTimeField(default=django.utils.timezone.now)),
                (
                    'cooldown',
                    models.PositiveSmallIntegerField(
                        default=5,
                        help_text='Required number of seconds before between queries (to be sure that the queries are not run in parallel)',
                    ),
                ),
                ('too_many_requests_delay', models.IntegerField(default=3600)),
                ('service_not_available_delay', models.IntegerField(default=3600)),
                ('service_busy_delay', models.IntegerField(default=60)),
            ],
        ),
        migrations.CreateModel(
            name='FetchIntention',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                (
                    'not_before',
                    models.DateTimeField(
                        default=django.utils.timezone.now, help_text="Don't plan before"
                    ),
                ),
                ('priority', models.SmallIntegerField(default=50),),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                (
                    'when_processed',
                    models.DateTimeField(help_text='When fetch unit was processed', null=True),
                ),
                (
                    'group_id',
                    models.UUIDField(
                        help_text='every fetchattempt is planned as a part of a group'
                    ),
                ),
                ('data_not_ready_retry', models.SmallIntegerField(default=0)),
                ('service_not_available_retry', models.SmallIntegerField(default=0)),
                ('service_busy_retry', models.SmallIntegerField(default=0)),
                (
                    'attempt',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to='sushi.SushiFetchAttempt',
                    ),
                ),
                (
                    'counter_report',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='sushi.CounterReportType'
                    ),
                ),
                (
                    'credentials',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='sushi.SushiCredentials'
                    ),
                ),
                (
                    'last_updated_by',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'scheduler',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='intentions',
                        to='scheduler.Scheduler',
                    ),
                ),
            ],
            options={'abstract': False,},
        ),
    ]