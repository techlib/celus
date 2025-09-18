import os
from io import StringIO
from tempfile import mkstemp

from rest_framework import status
from rest_framework.renderers import BaseRenderer

RESPONSE_ERROR = "Response data is a %s, not a DataFrame!"


class PandasBaseRenderer(BaseRenderer):
    """
    Renders DataFrames using their built in pandas implementation.
    Only works with serializers that return DataFrames as their data object.
    Uses a StringIO to capture the output of dataframe.to_[format]()
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        from pandas import DataFrame  # noqa - slow import

        if renderer_context and "response" in renderer_context:
            status_code = renderer_context["response"].status_code
            if not status.is_success(status_code):
                return "Error: %s" % data.get("detail", status_code)

        if not isinstance(data, DataFrame):
            raise Exception(RESPONSE_ERROR % type(data).__name__)

        name = getattr(self, "function", "to_%s" % self.format)
        if not hasattr(data, name):
            raise Exception("Data frame is missing %s property!" % name)

        self.init_output()
        args = self.get_pandas_args(data)
        kwargs = self.get_pandas_kwargs(data, renderer_context)
        self.render_dataframe(data, name, *args, **kwargs)
        return self.get_output()

    def render_dataframe(self, data, name, *args, **kwargs):
        function = getattr(data, name)
        function(*args, **kwargs)

    def init_output(self):
        self.output = StringIO()

    def get_output(self):
        return self.output.getvalue()

    def get_pandas_args(self, data):
        return [self.output]

    def get_pandas_kwargs(self, data, renderer_context):
        return {}


class PandasFileRenderer(PandasBaseRenderer):
    """
    Renderer for output formats that absolutely must use a file (i.e. Excel)
    """

    def init_output(self):
        file, filename = mkstemp(suffix="." + self.format)
        self.filename = filename
        os.close(file)

    def get_pandas_args(self, data):
        return [self.filename]

    def get_output(self):
        with open(self.filename, "rb") as file:
            result = file.read()
        os.unlink(self.filename)
        return result


class PandasCSVRenderer(PandasBaseRenderer):
    """
    Renders data frame as CSV
    """

    media_type = "text/csv"
    format = "csv"

    def get_pandas_kwargs(self, data, renderer_context):
        return {"encoding": self.charset}


class PandasExcelRenderer(PandasFileRenderer):
    """
    Renders data frame as Excel (.xlsx)
    """

    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  # noqa
    format = "xlsx"
    function = "to_excel"
