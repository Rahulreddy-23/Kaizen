"""Run inside the built image; use only synthetic pixels and a temporary workspace."""
import tempfile
from pathlib import Path

import pymupdf

from kaizen.ai.providers import NullProvider, get_provider
from kaizen.api.app import create_app
from kaizen.ingest.ocr import _recognize, available_engines
from kaizen.review.access import AccessStore
from kaizen.security import confidential_mode
from kaizen.workspace import Workspace


def main():
    assert confidential_mode(), 'The image must enforce confidential mode'
    assert isinstance(get_provider(), NullProvider)
    engines = available_engines()
    assert {'tesseract', 'rapidocr-onnxruntime'} <= set(engines), engines
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=600, height=140)
        page.insert_text((30, 85), 'KAIZEN TEST 123', fontsize=36)
        png = page.get_pixmap(dpi=150).tobytes('png')
        for engine in engines:
            words = _recognize(png, engine, False)
            text = ' '.join(str(word[4]) for word in words).upper()
            assert 'KAIZEN' in text and '123' in text, f'{engine} could not read synthetic pixels'
    assert Path('/app/ui/dist/index.html').is_file()
    assert not Path('/app/kaizen-workspace').exists()
    with tempfile.TemporaryDirectory() as directory:
        ws = Workspace(directory)
        try:
            AccessStore(ws.db).bootstrap('container-smoke@bd.com', 'synthetic-container-password')
            app = create_app(ws, ui_dir=Path('/app/ui/dist'))
            paths = {getattr(route, 'path', '') for route in app.routes}
            assert {'/api/auth/signup', '/api/terminology/selections', '/api/health'} <= paths
        finally:
            ws.db.close()
    print('Container checks passed: both OCR engines, confidential mode, UI and workspace bootstrap.')


if __name__ == '__main__':
    main()
