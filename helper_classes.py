from pydantic import BaseModel
from pymupdf import Rect


class MyPoint(BaseModel):

    x: float
    y: float

    @classmethod
    def custom_constructor(cls, x: float, y: float) -> "MyPoint":
        return cls(x=x, y=y)


class MyRect(BaseModel):

    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def custom_constructor(cls, x0: float, y0: float, x1: float, y1: float) -> "MyRect":
        return cls(x0=x0, y0=y0, x1=x1, y1=y1)

    def get_height(self):
        return self.y1 - self.y0

    def get_width(self):
        return self.x1 - self.x0