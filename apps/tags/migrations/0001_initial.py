# Generated by Django 3.2.14 on 2022-07-29 08:55

import colorfield.fields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('organizations', '0021_alter_organization_options'),
        ('publications', '0032_counter_registry_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganizationTag',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('_exclusive', models.BooleanField()),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='PlatformTag',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('_exclusive', models.BooleanField()),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                (
                    'text_color',
                    colorfield.fields.ColorField(
                        default='#303030', image_field=None, max_length=18, samples=None
                    ),
                ),
                (
                    'bg_color',
                    colorfield.fields.ColorField(
                        default='#E2E2E2', image_field=None, max_length=18, samples=None
                    ),
                ),
                ('desc', models.CharField(blank=True, max_length=160)),
                (
                    'can_see',
                    models.PositiveSmallIntegerField(
                        choices=[
                            (10, 'Everybody'),
                            (20, 'Organization users'),
                            (30, 'Organization admins'),
                            (40, 'Consortium admins'),
                            (50, 'Owner'),
                            (100, 'System'),
                        ],
                        default=50,
                        help_text='Who can see the tags on the tagged items',
                    ),
                ),
                (
                    'can_assign',
                    models.PositiveSmallIntegerField(
                        choices=[
                            (10, 'Everybody'),
                            (20, 'Organization users'),
                            (30, 'Organization admins'),
                            (40, 'Consortium admins'),
                            (50, 'Owner'),
                            (100, 'System'),
                        ],
                        default=50,
                        help_text='Who can assign the tags to items',
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
                    'organizations',
                    models.ManyToManyField(
                        related_name='tags',
                        through='tags.OrganizationTag',
                        to='organizations.Organization',
                    ),
                ),
                (
                    'owner',
                    models.ForeignKey(
                        blank=True,
                        help_text='When "can_see" or "can_assign" is set to "owner", this specifies the one',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='owned_tags',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'owner_org',
                    models.ForeignKey(
                        blank=True,
                        help_text='When "can_see" or "can_assign" is set to "organization users" or "organization admins", this is the organization',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='organizations.organization',
                    ),
                ),
                (
                    'platforms',
                    models.ManyToManyField(
                        related_name='tags', through='tags.PlatformTag', to='publications.Platform'
                    ),
                ),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='TagClass',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('internal', models.BooleanField(default=False)),
                (
                    'scope',
                    models.CharField(
                        choices=[
                            ('title', 'Title'),
                            ('platform', 'Platform'),
                            ('organization', 'Organization'),
                        ],
                        max_length=16,
                    ),
                ),
                ('name', models.CharField(max_length=200)),
                (
                    'exclusive',
                    models.BooleanField(
                        default=False,
                        help_text='An item may be only tagged by one tag from an exclusive tag class',
                    ),
                ),
                (
                    'text_color',
                    colorfield.fields.ColorField(
                        default='#303030', image_field=None, max_length=18, samples=None
                    ),
                ),
                (
                    'bg_color',
                    colorfield.fields.ColorField(
                        default='#E2E2E2', image_field=None, max_length=18, samples=None
                    ),
                ),
                ('desc', models.CharField(blank=True, max_length=160)),
                (
                    'can_modify',
                    models.PositiveSmallIntegerField(
                        choices=[
                            (10, 'Everybody'),
                            (20, 'Organization users'),
                            (30, 'Organization admins'),
                            (40, 'Consortium admins'),
                            (50, 'Owner'),
                            (100, 'System'),
                        ],
                        default=50,
                        help_text='Who can modify the parameters of this class',
                    ),
                ),
                (
                    'can_create_tags',
                    models.PositiveSmallIntegerField(
                        choices=[
                            (10, 'Everybody'),
                            (20, 'Organization users'),
                            (30, 'Organization admins'),
                            (40, 'Consortium admins'),
                            (50, 'Owner'),
                            (100, 'System'),
                        ],
                        default=50,
                        help_text='Who can create tags of this class',
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
                    'owner',
                    models.ForeignKey(
                        blank=True,
                        help_text='When an access level is set to "owner", this specifies the one',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='owned_tagclasses',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'owner_org',
                    models.ForeignKey(
                        blank=True,
                        help_text='When an access level is set to "organization users" or "organization admin", this is the organization',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='organizations.organization',
                    ),
                ),
            ],
            options={'verbose_name_plural': 'Tag classes', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='TitleTag',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('_exclusive', models.BooleanField()),
                (
                    '_tag_class',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='tags.tagclass'
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
                    'tag',
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tags.tag'),
                ),
                (
                    'target',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='publications.title'
                    ),
                ),
            ],
            options={'abstract': False},
        ),
        migrations.AddField(
            model_name='tag',
            name='tag_class',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to='tags.tagclass'
            ),
        ),
        migrations.AddField(
            model_name='tag',
            name='titles',
            field=models.ManyToManyField(
                related_name='tags', through='tags.TitleTag', to='publications.Title'
            ),
        ),
        migrations.AddField(
            model_name='platformtag',
            name='_tag_class',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to='tags.tagclass'
            ),
        ),
        migrations.AddField(
            model_name='platformtag',
            name='last_updated_by',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='platformtag',
            name='tag',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tags.tag'),
        ),
        migrations.AddField(
            model_name='platformtag',
            name='target',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to='publications.platform'
            ),
        ),
        migrations.AddField(
            model_name='organizationtag',
            name='_tag_class',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to='tags.tagclass'
            ),
        ),
        migrations.AddField(
            model_name='organizationtag',
            name='last_updated_by',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='organizationtag',
            name='tag',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tags.tag'),
        ),
        migrations.AddField(
            model_name='organizationtag',
            name='target',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to='organizations.organization'
            ),
        ),
        migrations.AddConstraint(
            model_name='titletag',
            constraint=models.UniqueConstraint(
                condition=models.Q(('_exclusive', True)),
                fields=('target', '_tag_class'),
                name='titletag_unique_tag_class_for_exclusive',
            ),
        ),
        migrations.AlterUniqueTogether(name='titletag', unique_together={('tag', 'target')}),
        migrations.AddConstraint(
            model_name='tagclass',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        models.Q(('can_modify', 50), ('can_create_tags', 50), _connector='OR'),
                        ('owner__isnull', False),
                    ),
                    models.Q(
                        models.Q(('can_modify', 50), ('can_create_tags', 50), _connector='OR'),
                        _negated=True,
                    ),
                    _connector='OR',
                ),
                name='tag_class_owner_not_null',
            ),
        ),
        migrations.AddConstraint(
            model_name='tagclass',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        models.Q(
                            ('can_create_tags__in', [20, 30]),
                            ('can_modify__in', [20, 30]),
                            _connector='OR',
                        ),
                        ('owner_org__isnull', False),
                    ),
                    models.Q(
                        models.Q(
                            models.Q(
                                ('can_create_tags__in', [20, 30]),
                                ('can_modify__in', [20, 30]),
                                _connector='OR',
                            ),
                            _negated=True,
                        ),
                        ('owner_org__isnull', True),
                    ),
                    _connector='OR',
                ),
                name='tag_class_owner_org_not_null',
            ),
        ),
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        models.Q(('can_see', 50), ('can_assign', 50), _connector='OR'),
                        ('owner__isnull', False),
                    ),
                    models.Q(
                        models.Q(('can_see', 50), ('can_assign', 50), _connector='OR'),
                        _negated=True,
                    ),
                    _connector='OR',
                ),
                name='tag_owner_not_null',
            ),
        ),
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        models.Q(
                            ('can_see__in', [20, 30]), ('can_assign__in', [20, 30]), _connector='OR'
                        ),
                        ('owner_org__isnull', False),
                    ),
                    models.Q(
                        models.Q(
                            models.Q(
                                ('can_see__in', [20, 30]),
                                ('can_assign__in', [20, 30]),
                                _connector='OR',
                            ),
                            _negated=True,
                        ),
                        ('owner_org__isnull', True),
                    ),
                    _connector='OR',
                ),
                name='tag_owner_org_not_null',
            ),
        ),
        migrations.AddConstraint(
            model_name='platformtag',
            constraint=models.UniqueConstraint(
                condition=models.Q(('_exclusive', True)),
                fields=('target', '_tag_class'),
                name='platformtag_unique_tag_class_for_exclusive',
            ),
        ),
        migrations.AlterUniqueTogether(name='platformtag', unique_together={('tag', 'target')}),
        migrations.AddConstraint(
            model_name='organizationtag',
            constraint=models.UniqueConstraint(
                condition=models.Q(('_exclusive', True)),
                fields=('target', '_tag_class'),
                name='organizationtag_unique_tag_class_for_exclusive',
            ),
        ),
        migrations.AlterUniqueTogether(name='organizationtag', unique_together={('tag', 'target')}),
    ]
