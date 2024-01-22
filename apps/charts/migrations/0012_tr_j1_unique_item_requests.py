import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def update_tr_j1_view(apps, schema_editor):
    ReportDataView = apps.get_model("charts", "ReportDataView")
    if rdv := ReportDataView.objects.filter(short_name__iexact="TR_JR1").last():
        rdv.metric_allowed_values = ["Total_Item_Requests", "Unique_Item_Requests"]
        rdv.save()


class Migration(migrations.Migration):
    dependencies = [
        ("charts", "0011_remove_reportdataview_primary_dimension"),
    ]

    operations = [
        migrations.RunPython(update_tr_j1_view, migrations.RunPython.noop),
    ]
