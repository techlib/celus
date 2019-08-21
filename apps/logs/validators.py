import codecs
import csv

import magic

from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError

from logs.logic.custom_import import custom_data_import_precheck


class CSVValidator(object):

    def __call__(self, fileobj):
        self.check_mime_type(fileobj)
        self.check_can_parse(fileobj)

    @classmethod
    def check_mime_type(cls, fileobj):
        detected_type = magic.from_buffer(fileobj.read(16384), mime=True)
        fileobj.seek(0)
        if detected_type not in ('text/csv', 'text/plain', 'application/csv'):
            raise ValidationError(_("The uploaded file is not a CSV file or is corrupted. "
                                    "The file type seems to be '{detected_type}'. "
                                    "Please upload a CSV file.").
                                  format(detected_type=detected_type))

    @classmethod
    def check_can_parse(cls, fileobj):
        reader = csv.reader(codecs.iterdecode(fileobj, 'utf-8'))
        first_row = next(reader)
        try:
            second_row = next(reader)
        except StopIteration:
            raise ValidationError(_('Only one row in the uploaded file, there is not data to '
                                    'import'))
        fileobj.seek(0)
        problems = custom_data_import_precheck(first_row, [second_row])
        if problems:
            raise ValidationError(_('Errors understanding uploaded data: {}').
                                  format('; '.join(problems)))

