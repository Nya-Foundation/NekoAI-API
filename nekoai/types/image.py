from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel


class Image(BaseModel):
    """
    A single image object in the return of `generate_image` method or director tools.
    """

    filename: str
    data: bytes

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


class EventType(StrEnum):
    """
    Enum for event types in the msgpack event.
    """

    INTERMEDIATE = "intermediate"
    FINAL = "final"


class MsgpackEvent(BaseModel):
    """
    A single msgpack event object in the return of `generate_image` method or director tools.
    """

    event_type: EventType
    samp_ix: int
    step_ix: int
    gen_id: str
    sigma: float

    # event_type: intermediate: jpeg image, final: png image
    image: Image

    def __str__(self):
        return f"MsgpackEvent(event_type={self.event_type}, step_ix={self.step_ix}, gen_id={self.gen_id})"

    __repr__ = __str__
