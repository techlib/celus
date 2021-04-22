import pytest


@pytest.mark.django_db
class TestMigrations:
    def test_accesslog_0045_dimension_type_migration(self, migrator):
        old_state = migrator.apply_initial_migration(
            ('logs', '0044_better_source_related_constraints')
        )
        ReportType = old_state.apps.get_model('logs', 'ReportType')
        ReportTypeToDimension = old_state.apps.get_model('logs', 'ReportTypeToDimension')
        Dimension = old_state.apps.get_model('logs', 'Dimension')
        DimensionText = old_state.apps.get_model('logs', 'DimensionText')
        AccessLog = old_state.apps.get_model('logs', 'AccessLog')
        Metric = old_state.apps.get_model('logs', 'Metric')
        ImportBatch = old_state.apps.get_model('logs', 'ImportBatch')
        Platform = old_state.apps.get_model('publications', 'Platform')
        Organization = old_state.apps.get_model('organizations', 'Organization')
        rt = ReportType.objects.create(short_name='X')
        dim1 = Dimension.objects.create(short_name='text dim', type=2)
        dim2 = Dimension.objects.create(short_name='int dim', type=1)
        ReportTypeToDimension.objects.create(dimension=dim1, report_type=rt, position=0)
        ReportTypeToDimension.objects.create(dimension=dim2, report_type=rt, position=1)
        m1 = Metric.objects.create(short_name='m1')
        p1 = Platform.objects.create(short_name='p1', ext_id=1234)
        dt1 = DimensionText.objects.create(text='dim1text', dimension=dim1)
        org = Organization.objects.create(
            short_name='org',
            name='org',
            parent=None,
            internal_id='aaa',
            # mptt related fields which are not auto-populated for some reason
            lft=0,
            rght=1000,
            tree_id=1,
            level=0,
        )
        ib = ImportBatch.objects.create(report_type=rt, platform=p1, organization=org)
        al = AccessLog.objects.create(
            report_type=rt,
            metric=m1,
            platform=p1,
            organization=org,
            date='2020-01-01',
            value=100,
            dim1=dt1.pk,
            dim2=1000,
            import_batch=ib,
        )
        assert DimensionText.objects.count() == 1
        # create a materialized report to test that these are converted as well
        # because they do not have their own links to dimensions but use the ones from parent
        ReportMaterializationSpec = old_state.apps.get_model('logs', 'ReportMaterializationSpec')
        rms = ReportMaterializationSpec.objects.create(base_report_type=rt, name="foo")
        mrt = ReportType.objects.create(short_name='materialized', materialization_spec=rms)
        # materialization does not work with old_state, so we create the materialized accesslog
        # manually from the original
        mal = AccessLog.objects.create(
            report_type=mrt,
            metric=m1,
            platform=p1,
            organization=org,
            date='2020-01-01',
            value=100,
            dim1=dt1.pk,
            dim2=1000,
            import_batch=ib,
        )
        # now migrate and check
        new_state = migrator.apply_tested_migration(('logs', '0045_dimension_int_to_str'))
        DimensionText = new_state.apps.get_model('logs', 'DimensionText')
        AccessLog = new_state.apps.get_model('logs', 'AccessLog')
        Dimension = new_state.apps.get_model('logs', 'Dimension')
        assert DimensionText.objects.count() == 2
        dt2 = DimensionText.objects.exclude(pk=dt1.pk).get()
        assert dt2.text == '1000'
        al2 = AccessLog.objects.get(pk=al.pk)
        assert al2.dim2 == dt2.pk, 'dim2 is remapped'
        assert al2.dim1 == dt1.pk, 'dim1 stays the same'
        assert Dimension.objects.get(pk=dim2.pk).type == 2, 'type of dim2 must change to 2'
        # materialized record
        mal2 = AccessLog.objects.get(pk=mal.pk)
        assert mal2.dim2 == dt2.pk, 'dim2 is remapped'
        assert mal2.dim1 == dt1.pk, 'dim1 stays the same'
