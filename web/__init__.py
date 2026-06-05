"""Eden seed decoder web UI."""

__all__ = ["run_server"]


def run_server(*args, **kwargs):
    from web.server import run_server as _run

    return _run(*args, **kwargs)
