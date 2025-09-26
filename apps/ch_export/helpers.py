from io import StringIO


class SmarterStringIO:
    def __init__(self):
        self.buf = StringIO()

    def write(self, s, ending="\n"):
        self.buf.write(s + ending)

    def getvalue(self):
        return self.buf.getvalue()

    def isatty(self):
        return False
