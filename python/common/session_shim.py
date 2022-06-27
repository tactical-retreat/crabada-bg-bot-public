import requests

DEFAULT_TIMEOUT = 12


def shim_session_send():
    """This is a hack that sets up a default timeout on all HTTP requests."""
    old_send = requests.Session.send

    def new_send(*args, **kwargs):
        if kwargs.get("timeout", None) is None:
            kwargs["timeout"] = DEFAULT_TIMEOUT
        return old_send(*args, **kwargs)

    requests.Session.send = new_send
