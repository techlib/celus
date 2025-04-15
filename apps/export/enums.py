from django.db import models


class FileFormat(models.TextChoices):
    XLSX = "XLSX", "XLSX"
    XLSX_NO_CHARTS = "XLSX_NO_CHARTS", "XLSX without charts"
    ZIP_CSV = "ZIP_CSV", "CSV files inside ZIP archive"

    @classmethod
    def file_extension(cls, value):
        if value in (cls.XLSX, cls.XLSX_NO_CHARTS):
            return "xlsx"
        else:
            return "zip"

    @classmethod
    def content_type(cls, value):
        if value in (cls.XLSX, cls.XLSX_NO_CHARTS):
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            return "application/zip"
