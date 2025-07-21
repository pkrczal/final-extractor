from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
from venv import logger

import fitz
from traits.trait_types import false

from helper_classes import MyRect

MIN_LENGTH_X = 2
MIN_LENGTH_Y = 2

MIN_WIDTH_FOR_BOX = 2
MIN_HEIGHT_FOR_BOX = 2

MIN_CELLS = 3


@dataclass
class DocumentWrapper:
    document: fitz.Document
    vertical_lines: List[Tuple[int, float, float, float]] = field(default_factory=list)
    horizontal_lines: List[Tuple[int, float, float, float]] = field(default_factory=list)
    rects: List[Tuple["MyRect", int]] = field(default_factory=list)
    rows: List[Tuple["MyRect", int]] = field(default_factory=list)

    @classmethod
    def from_document(cls, document: fitz.Document) -> "DocumentWrapper":
        return cls(document=document)

    @property
    def has_table(self) -> bool:
        for page_num, page in enumerate(self.document, start=1):
            drawings = page.get_drawings()
            for entry in drawings:
                for item in entry["items"]:
                    # ToDo: for now only drawing with type 're' can be processed || Check for optimisations
                    if item[0] != "re":
                        continue

                    x0, y0, x1, y1 = item[1]

                    # only add drawings with min length in order to precent vector graphics from being processed
                    if x1 - x0 > 2 or y1 - y0 > 2:
                        my_rect = MyRect(x0=x0, y0=y0, x1=x1, y1=y1)
                        try:
                            self.rects.append((my_rect, int(page_num)))
                        except TypeError as e:
                            logger.error(e)

                    # fill horizontal / vertical for now ToDo: change if needed

                    if abs(y1 - y0) >= 0:
                        try:
                            # left
                            self.vertical_lines.append((int(page_num), float(x0), float(y0), float(y1)))
                            # right
                            self.vertical_lines.append((int(page_num), float(x1), float(y0), float(y1)))
                        except TypeError as e:
                            logger.error(e)

                    if abs(x1 - x0) >= 0:
                        try:
                            # top
                            self.horizontal_lines.append((int(page_num), float(y0), float(x0), float(x1)))
                            # bottom
                            self.horizontal_lines.append((int(page_num), float(y1), float(x0), float(x1)))
                        except TypeError as e:
                            logger.error(e)

        # no drawings mean table cant be detected ==> false
        if len(self.rects) == 0:
            return False

        # this flag is used so that the last element in the iteration is also appended
        append_prev = False
        row_boxes: List[MyRect] = []

        for curr_row, next_row in zip(self.rects, self.rects[1:]):
            # assume two boxes are in the same row if their y1 is the same
            same_row = curr_row[0].y1 == next_row[0].y1
            if same_row and next_row[0].x0 > curr_row[0].x0 and curr_row[0].get_height() > MIN_HEIGHT_FOR_BOX:
                row_boxes.append(curr_row[0])
                append_prev = True
            elif append_prev and same_row and curr_row[0].get_height() > MIN_HEIGHT_FOR_BOX:
                row_boxes.append(curr_row[0])
            else:
                append_prev = False

        groups: Dict[float, List[MyRect]] = defaultdict(list)

        for r in row_boxes:
            groups[r.y1].append(r)

        for y, group in groups.items():
            # skip rows with less then 3 cells
            if len(group) < MIN_CELLS:
                continue

            x0 = min(r.x0 for r in group)
            y0 = min(r.y0 for r in group)
            x1 = max(r.x1 for r in group)
            y1 = max(r.y1 for r in group)

            self.rows.append((MyRect(x0=x0, y0=y0, x1=x1, y1=y1), int(page_num)))

        if len(self.rows) > 0:
            return True
        else:
            return False
