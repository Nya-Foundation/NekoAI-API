from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from .metadata import Metadata


class Image(BaseModel):
    """
    A single image object in the return of `generate_image` method or director tools.
    """

    filename: str
    data: bytes
    metadata: Optional[Metadata] = None

    def __str__(self):
        return f"Image(filename={self.filename})"

    __repr__ = __str__

    def save(self, path: str = "temp", filename: str | None = None):
        """
        Save image to local file.

        Parameters
        ----------
        path : `str`, optional
            Path to save the image, by default will save to ./temp
        filename : `str`, optional
            Filename of the saved file, by default will use `self.filename`
            If provided, `self.filename` will also be updated to match this value
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        self.filename = filename or self.filename
        dest = path / self.filename
        dest.write_bytes(self.data)
