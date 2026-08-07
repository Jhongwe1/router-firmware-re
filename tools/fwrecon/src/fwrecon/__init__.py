"""fwrecon — structured reconnaissance for Realtek-SDK router firmware.

Built for the TOTOLINK N150RT teardown, but nothing here is model-specific:
the Realtek ``IMG_HEADER_T`` container, Boa ``form*`` handler naming and
SquashFS-on-read-only-flash layout are shared across a large family of
consumer devices.
"""

from .cli import __version__

__all__ = ["__version__"]
