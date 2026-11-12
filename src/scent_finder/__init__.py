try:
    from ._version import version
except ModuleNotFoundError as error:
    if error.name != __name__ + "._version":
        raise
    from importlib.metadata import version as installed_version
    version = installed_version(__name__)

__version__ = version
