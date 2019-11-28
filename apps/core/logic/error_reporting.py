import socket
import traceback
from functools import wraps
from django.conf import settings
from django.core.mail import mail_admins


def email_if_fails(fn):
    @wraps(fn)
    def decorated(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if not settings.DEBUG:
                try:
                    fn_name = fn.func_name
                except AttributeError:
                    fn_name = fn.__name__
                send_error_email(fn_name, args, kwargs, socket.gethostname(),
                                 traceback.format_exc())
            raise e
    return decorated


def send_error_email(fn_name, args, kwargs, host, formatted_exc):
    formatted_exc = formatted_exc.strip()
    contents = 'Task: {fnName}\nArgs: {args}\nKwargs: {kwargs}\nHost: {host}\nError: {error}'
    message = contents.format(fnName=fn_name, args=args, kwargs=kwargs, host=host,
                              error=formatted_exc)
    short_exc = formatted_exc.rsplit('\n')[-1]
    subject = '[celery-error] {host} {fnName} {short_exc}'.format(host=host, fnName=fn_name,
                                                                  short_exc=short_exc)
    mail_admins(subject=subject, message=message)
