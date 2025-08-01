from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
from venv import logger
from helper_functions import equals_within_boundary

import fitz
import pandas as pd
from traits.trait_types import false

from helper_classes import MyRect, PyMuDataRowElement, PyMuCollapsedRowElement

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
    table_rows: List[Tuple["MyRect", int]] = field(default_factory=list)
    raw_pdf_content_elements: pd.DataFrame = field(default_factory=pd.DataFrame)
    collapsed_pdf_rows: pd.DataFrame = field(default_factory=pd.DataFrame)
    text_blocks: pd.DataFrame = field(default_factory=pd.DataFrame)

    @classmethod
    def from_document(cls, document: fitz.Document) -> "DocumentWrapper":
        return cls(document=document)

    def close_and_save(self, path):
        self.document.save(path)

    def dump_blocks_to_file(self, path, name):
        df_serialize = self.text_blocks.copy()
        df_serialize = df_serialize.sort_values(
            by=['page', 'y1'],
            ascending=[True, True]
        )
        path_final = path / f"{name}.json"
        df_serialize['text_content'].to_json(
            path_final,
            index=False
        )

    def paint_and_write_boxes(self):
        for row in self.text_blocks.iterrows():
            r = row[1]
            page = self.document[r['page'] - 1]
            box = r['box']
            rect = fitz.Rect(box.x0, box.y0, box.x1, box.y1)
            shape = page.new_shape()
            shape.draw_rect(rect)
            shape.finish(
                color=(1, 0, 0),
                width=0.5,
                fill=None
            )
            shape.commit()
        # DEBUG fraw lines
        # for rect, page in self.table_rows:
        #     rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1)
        #     p = self.document[page - 1]
        #     shape = p.new_shape()
        #     shape.draw_rect(rect)
        #     shape.finish(
        #         color=(0, 1, 0),
        #         width=1,
        #         fill=None
        #     )
        #     shape.commit()


    def parse_pdf_entries(self):
        rows = []
        for page_num, page in enumerate(self.document, start=1):
            for block in page.get_text('dict')['blocks']:
                if block['type'] != 0: continue
                for line in block['lines']:
                    for span in line['spans']:
                        x0, y0, x1, y1 = span['bbox']
                        rows.append(
                            PyMuDataRowElement(
                                page=page_num,
                                x0=x0,
                                y0=y0,
                                x1=x1,
                                y1=y1,
                                text_content=span['text'],
                                font=span['font'],
                                size=span['size'],
                                flag=span['flags']
                            )
                        )

        # prevent padnas from saving dicts
        buffer = [row.dict() for row in rows]
        self.raw_pdf_content_elements = pd.DataFrame(buffer)

    def sanitize_parsed_pdf_entries(self):
        # replace empty text entries with NA so they can be dropped easily
        self.raw_pdf_content_elements.replace({'text': ' '}, {'text': pd.NA}, inplace=True)
        self.raw_pdf_content_elements.dropna(inplace=True)

    # Todo: implement alternative approach if there were tables detected in the beginning
    def collapse_parsed_entries_into_rows(self):
        grouped = []
        for (page, y1), group in self.raw_pdf_content_elements.groupby(['page', 'y1'], sort=False):
            group_sorted = group.sort_values(by='x0')  # order from left to right

            # add additional debug file dump write here

            fonts = group_sorted['font'].tolist()
            sizes = group_sorted['size'].to_list()

            grouped.append(
                PyMuCollapsedRowElement(
                    page=page,
                    x0=group_sorted['x0'].min(),
                    y0=group_sorted['y0'].min(),
                    x1=group_sorted['x1'].max(),
                    y1=group_sorted['y1'].max(),
                    text_content=' '.join(group_sorted['text_content']),
                    fonts=list(group_sorted['font']),
                    sizes=list(group_sorted['size']),
                    font_flow_begin=fonts[0] if fonts else None,
                    font_flow_end=fonts[-1] if fonts else None,
                    size_flow_begin=sizes[0] if sizes else None,
                    size_flow_end=sizes[-1] if sizes else None,
                    flags=group_sorted['flag'],
                )
            )

        self.collapsed_pdf_rows = pd.DataFrame([
            {
                **g.dict(),
                "height": g.get_height(),
                "width": g.get_width()
            }
            for g in grouped
        ])

    def detect_connected_blocks_from_rows(self):
        block_ids = []
        # helper variables
        current_block = 0
        prev_font_begin = None
        prev_font_end = None
        prev_size_begin = None
        prev_size_end = None
        prev_bottom = None

        for idx, row in self.collapsed_pdf_rows.iterrows():
            if idx == 0:
                current_block = 1
            else:
                if row['y0'] < prev_bottom:
                    current_block += 1
                elif (row['font_flow_begin'] != prev_font_end and not equals_within_boundary(row['y0'], prev_bottom,
                                                                                             row['height'] + 3)):
                    current_block += 1
                elif (row['font_flow_begin'] == prev_font_end and (
                        abs(row['y0'] - prev_bottom) > row['height'] + 3)):
                    current_block += 1

            block_ids.append(current_block)
            prev_font_begin = row['font_flow_begin']
            prev_font_end = row['font_flow_end']
            prev_size_begin = row['size_flow_begin']
            prev_size_end = row['size_flow_end']
            prev_bottom = row['y0']

        self.collapsed_pdf_rows['block_id'] = block_ids
        self.text_blocks = self.collapsed_pdf_rows.groupby(['page', 'block_id'], as_index=False).agg({
            'text_content': lambda texts: '\n'.join(texts),
            'x0': 'min',
            'y0': 'min',
            'x1': 'max',
            'y1': 'max'
        })

        self.text_blocks['box'] = self.text_blocks.apply(
            lambda _row: MyRect(
                x0=_row['x0'],
                y0=_row['y0'],
                x1=_row['x1'],
                y1=_row['y1']
            ), axis=1
        )


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
                            self.rects.append((my_rect, int(page.number)))
                        except TypeError as e:
                            logger.error(e)

                    # fill horizontal / vertical for now ToDo: change if needed

                    if abs(y1 - y0) >= 0:
                        try:
                            # left
                            self.vertical_lines.append((int(page.number), float(x0), float(y0), float(y1)))
                            # right
                            self.vertical_lines.append((int(page.number), float(x1), float(y0), float(y1)))
                        except TypeError as e:
                            logger.error(e)

                    if abs(x1 - x0) >= 0:
                        try:
                            # top
                            self.horizontal_lines.append((int(page.number), float(y0), float(x0), float(x1)))
                            # bottom
                            self.horizontal_lines.append((int(page.number), float(y1), float(x0), float(x1)))
                        except TypeError as e:
                            logger.error(e)

        # no drawings mean table cant be detected ==> false
        if len(self.rects) == 0:
            return False

        # this flag is used so that the last element in the iteration is also appended
        append_prev = False
        row_boxes: List[MyRect] = []

        for i in range(len(self.rects) - 1):

            current_row = self.rects[i]
            next_row = self.rects[i + 1]

            if (
                current_row[0].y1  - current_row[0].y1 ==  next_row[0].y1  - next_row[0].y1
                and next_row[0].x0 > current_row[0].x0
                and current_row[0].get_height() > 2
            ) :
                row_boxes.append(current_row[0])
                append_prev = True
            elif (
                append_prev
                and current_row[0].y1 -  current_row[0].y1 == next_row[0].y1 - next_row[0].y1
                and current_row[0].get_height() > 2
            ):
                row_boxes.append(current_row[0])

        groups: Dict[float, List[MyRect]] = defaultdict(list)

        for r in row_boxes:
            groups[r.y1].append(r)

        for y, group in groups.items():
            # skip rows with less than MIN_CELLS cells
            if len(group) < MIN_CELLS:
                continue

            x0 = min(r.x0 for r in group)
            y0 = min(r.y0 for r in group)
            x1 = max(r.x1 for r in group)
            y1 = max(r.y1 for r in group)

            self.table_rows.append(
                (MyRect(x0=x0, y0=y0, x1=x1, y1=y1), int(page.number))
            )

        return len(self.table_rows) > 0


    def apply_table_boundaries(self):

        if not self.table_rows or self.raw_pdf_content_elements.empty:
            return

        df = self.raw_pdf_content_elements.copy()
        indices_to_drop: List[int] = []

        for rect, page in self.table_rows:

            # cond_page = df["page"] == page
            # cond_x0 = df["x0"] >= rect.x0
            # cond_y0 = df["y0"] >= rect.y0
            # cond_x1 = df["x1"] >= rect.x1
            # cond_y1 = df["y1"] >= rect.y1

            # subset = df.assign(
            #     cond_page=cond_page,
            #     cond_x0=cond_x0,
            #     cond_y0=cond_y0,
            #     cond_x1=cond_x1,
            #     cond_y1=cond_y1
            # )

            mask = (
                    (df["page"] == page)
                    & (df["x0"] >= rect.x0)
                    & (df["x1"] <= rect.x1)
                    & (df["y0"] >= rect.y0)
                    & (df["y1"] <= rect.y1)
            )

            subset = df[mask]
            if subset.empty:
                continue

            first_index = subset.index[0]

            merged = PyMuDataRowElement(
                page=page,
                x0=subset["x0"].min(),
                y0=subset["y0"].min(),
                x1=subset["x1"].max(),
                y1=subset["y1"].max(),
                text_content=" ".join(subset["text_content"].tolist()),
                font=subset.iloc[0]["font"],
                size=subset.iloc[0]["size"],
                flag=subset.iloc[0]["flag"],
            )

            # replace the first row with the merged one
            df.loc[first_index] = merged.model_dump()

            # mark the remaining rows for removal
            indices_to_drop.extend(idx for idx in subset.index[1:])

        if indices_to_drop:
            df.drop(index=indices_to_drop, inplace=True)

        self.raw_pdf_content_elements = df
