from django.contrib.auth.middleware import RemoteUserMiddleware


class EDUIdHeaderMiddleware(RemoteUserMiddleware):
    header = 'X_IDENTITY'
