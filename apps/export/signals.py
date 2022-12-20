from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import FlexibleDataExport


@receiver(post_delete, sender=FlexibleDataExport)
def delete_export_file_from_direcotry(sender, instance, **kwargs):
    instance.output_file.delete(save=False)
