"""Find text-sized vector rows for OCR recovery when letters are PDF paths.

This supplements page OCR: it does not interpret glyph shapes as characters or
use product names, document identifiers, fixed page regions or a language list.
"""

import statistics

import pymupdf


def outline_regions(page: pymupdf.Page) -> list[pymupdf.Rect]:
    pieces = []
    for drawing in page.get_drawings():
        rect = drawing['rect'] * page.rotation_matrix
        fill = drawing.get('fill')
        if 'f' in drawing['type'] and fill and max(fill) < .5 and .15 < rect.width < 24 and .15 < rect.height < 24:
            pieces.append(rect)
    # A few symbols or a border do not establish an outlined text layer.
    if len(pieces) < 80:
        return []
    stems = [r for r in pieces if 3.5 < r.height < 18 and r.width > .3]
    bands: list[list[pymupdf.Rect]] = []
    for rect in sorted(stems, key=lambda r: r.y1):
        if bands and abs(rect.y1 - statistics.median(r.y1 for r in bands[-1])) < .9:
            bands[-1].append(rect)
        else:
            bands.append([rect])
    regions = []
    for band in bands:
        if len(band) < 4:
            continue
        height = statistics.median(r.height for r in band)
        if height < 4:
            continue
        fragments: list[pymupdf.Rect] = []
        for rect in sorted(band, key=lambda r: r.x0):
            if fragments and rect.x0 - fragments[-1].x1 < 2 * height:
                fragments[-1] |= rect
            else:
                fragments.append(pymupdf.Rect(rect))
        for fragment in fragments:
            if fragment.width <= 10:
                continue
            # Include punctuation, descenders and smaller digits sharing the row.
            # Those may have a different baseline from the main capital letters.
            for _ in range(2):
                for piece in pieces:
                    vertical = min(piece.y1, fragment.y1) - max(piece.y0, fragment.y0)
                    gap = max(piece.x0 - fragment.x1, fragment.x0 - piece.x1, 0)
                    if vertical > .6 * min(piece.height, fragment.height) and gap < height * 2:
                        fragment |= piece
            regions.append((fragment + (-1, -1, 1, 1)) & page.rect)
    # One glyph can be made of several overlapping paths. Read each row once.
    unique: list[pymupdf.Rect] = []
    for rect in sorted(regions, key=lambda r: r.get_area(), reverse=True):
        if not any((rect & previous).get_area() >= .8 * rect.get_area() for previous in unique):
            unique.append(rect)
    return sorted(unique, key=lambda r: (r.y0, r.x0))
