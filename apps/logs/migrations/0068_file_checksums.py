import logging
import os
from hashlib import blake2b

from django.db import migrations

logger = logging.getLogger(__name__)


def compute_checksum(fileobj):
    hasher = blake2b(digest_size=32)
    size = 0
    while chunk := fileobj.read(1024 * 1024):
        if isinstance(chunk, str):
            chunk = chunk.encode('utf-8')
        hasher.update(chunk)
        size += len(chunk)
    return hasher.hexdigest(), size


def add_missing_checksums(apps, schema_editor):
    ManualDataUpload = apps.get_model('logs', 'ManualDataUpload')
    to_update = []
    missing_files = 0
    updated = 0
    for mdu in ManualDataUpload.objects.filter(checksum='').exclude(data_file=''):
        if os.path.isfile(mdu.data_file.path):
            mdu.checksum, mdu.file_size = compute_checksum(mdu.data_file)
            mdu.data_file.close()
            to_update.append(mdu)
        else:
            missing_files += 1
        if len(to_update) >= 1000:
            ManualDataUpload.objects.bulk_update(to_update, ['checksum', 'file_size'])
            updated += len(to_update)
            to_update = []
    ManualDataUpload.objects.bulk_update(to_update, ['checksum', 'file_size'])
    updated += len(to_update)
    logger.info('Updated checkums of %d MDUs, %d files missing', updated, missing_files)


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0067_mdu_sourcefile_mixin'),
    ]

    operations = [
        migrations.RunPython(add_missing_checksums, migrations.RunPython.noop),
    ]
