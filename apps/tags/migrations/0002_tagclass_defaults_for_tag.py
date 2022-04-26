# Generated by Django 3.2.14 on 2022-08-03 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tags', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(model_name='tagclass', name='tag_class_owner_not_null',),
        migrations.RemoveConstraint(model_name='tagclass', name='tag_class_owner_org_not_null',),
        migrations.AddField(
            model_name='tagclass',
            name='default_tag_can_assign',
            field=models.PositiveSmallIntegerField(
                choices=[
                    (10, 'Everybody'),
                    (20, 'Organization users'),
                    (30, 'Organization admins'),
                    (40, 'Consortium admins'),
                    (50, 'Owner'),
                    (100, 'System'),
                ],
                default=50,
                help_text='Default value for Tag.can_assign of tags of this class',
            ),
        ),
        migrations.AddField(
            model_name='tagclass',
            name='default_tag_can_see',
            field=models.PositiveSmallIntegerField(
                choices=[
                    (10, 'Everybody'),
                    (20, 'Organization users'),
                    (30, 'Organization admins'),
                    (40, 'Consortium admins'),
                    (50, 'Owner'),
                    (100, 'System'),
                ],
                default=50,
                help_text='Default value for Tag.can_see of tags of this class',
            ),
        ),
        migrations.AddConstraint(
            model_name='tagclass',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        models.Q(
                            ('can_modify', 50),
                            ('can_create_tags', 50),
                            ('default_tag_can_see', 50),
                            ('default_tag_can_assign', 50),
                            _connector='OR',
                        ),
                        ('owner__isnull', False),
                    ),
                    models.Q(
                        models.Q(
                            ('can_modify', 50),
                            ('can_create_tags', 50),
                            ('default_tag_can_see', 50),
                            ('default_tag_can_assign', 50),
                            _connector='OR',
                        ),
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
                            ('default_tag_can_see__in', [20, 30]),
                            ('default_tag_can_assign__in', [20, 30]),
                            _connector='OR',
                        ),
                        ('owner_org__isnull', False),
                    ),
                    models.Q(
                        models.Q(
                            models.Q(
                                ('can_create_tags__in', [20, 30]),
                                ('can_modify__in', [20, 30]),
                                ('default_tag_can_see__in', [20, 30]),
                                ('default_tag_can_assign__in', [20, 30]),
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
    ]
