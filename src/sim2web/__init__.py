"""Sim2Web: browser review packages for geotechnical simulation results.

Typical use::

    from sim2web import load_config, build, validate_package
    cfg = load_config("case.yaml")
    build(cfg)
    report = validate_package(cfg)

or, from a shell, ``sim2web build case.yaml``.
"""
from ._version import __version__

__all__ = ["__version__", "load_config", "build", "validate_package"]


def __getattr__(name):  # lazy imports keep ``import sim2web`` light
    if name == "load_config":
        from .config import load_config

        return load_config
    if name == "build":
        from .pipeline import build

        return build
    if name == "validate_package":
        from .validate import validate_package

        return validate_package
    raise AttributeError(name)
