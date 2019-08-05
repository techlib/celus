class SushiException(Exception):

    def __init__(self, text, content=None):
        self.text = text
        self.content = content

    def __str__(self):
        return 'Sushi exception: {}'.format(self.text)
