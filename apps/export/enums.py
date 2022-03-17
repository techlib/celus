from django.db import models


class FileFormat(models.TextChoices):
    XLSX = 'XLSX', 'XLSX'
    ZIP_CSV = 'ZIP_CSV', 'CSV files inside ZIP archive'

    @classmethod
    def file_extension(cls, value):
        if value == cls.XLSX:
            return 'xlsx'
        else:
            return 'zip'
