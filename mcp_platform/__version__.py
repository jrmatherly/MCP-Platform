try:
    from setuptools_scm import get_version

    __version__ = get_version(root="..", relative_to=__file__)
except (ImportError, LookupError, Exception):
    # Fallback for installed packages: try to get version from package metadata
    try:
        from importlib.metadata import version

        __version__ = version("mcp-platform")
    except Exception:
        # Final fallback
        __version__ = "0.0.0"
