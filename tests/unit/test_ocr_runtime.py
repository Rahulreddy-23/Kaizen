"""Offline engine recovery must not turn installation failures into missing components."""

import subprocess

import pymupdf
import pytest
from typer.testing import CliRunner

from kaizen.cli.main import app
from kaizen.ingest import ocr


@pytest.fixture
def page():
    ocr._CACHE.clear()
    with pymupdf.open() as pdf:
        yield pdf.new_page(width=200, height=100)
    ocr._CACHE.clear()


@pytest.mark.parametrize("first_result", [[], subprocess.CalledProcessError(1, "tesseract", stderr=b"private subprocess output")])
def test_recognition_uses_the_next_engine_after_failure_or_empty_output(page, monkeypatch, first_result):
    monkeypatch.setattr(ocr, "available_engines", lambda: ["tesseract", "rapidocr-onnxruntime"])
    calls = []

    def recognize(png, engine, single_line):
        calls.append(engine)
        if engine == "tesseract":
            if isinstance(first_result, Exception):
                raise first_result
            return first_result
        return [(10, 20, 60, 40, "MASK", .9)]

    monkeypatch.setattr(ocr, "_recognize", recognize)
    result = ocr.ocr_page(page, dpi=144)
    assert calls == ["tesseract", "rapidocr-onnxruntime"]
    assert result.engine == "rapidocr-onnxruntime"
    assert result.words == [(5, 10, 30, 20, "MASK", .9)]
    assert "private subprocess output" not in str(result)
    cached = ocr.ocr_page(page, dpi=144)
    assert cached == result and len(calls) == 2
    cached.words.clear()
    assert ocr.ocr_page(page, dpi=144).words


def test_all_engine_failures_are_safe_actionable_and_retryable(page, monkeypatch):
    monkeypatch.setattr(ocr, "available_engines", lambda: ["tesseract", "rapidocr-onnxruntime"])

    def fail(*args):
        raise RuntimeError("private file contents")

    monkeypatch.setattr(ocr, "_recognize", fail)
    with pytest.raises(ocr.OcrError) as caught:
        ocr.ocr_page(page)
    assert "kaizen doctor" in str(caught.value) and "private file contents" not in str(caught.value)
    monkeypatch.setattr(ocr, "_recognize", lambda *args: [(10, 10, 30, 20, "MASK", .9)])
    assert ocr.ocr_page(page).words


def test_empty_page_is_not_cached_as_a_success(page, monkeypatch):
    monkeypatch.setattr(ocr, "available_engines", lambda: ["fake"])
    monkeypatch.setattr(ocr, "_recognize", lambda *args: [])
    assert ocr.ocr_page(page).words == []
    monkeypatch.setattr(ocr, "_recognize", lambda *args: [(10, 10, 30, 20, "MASK", .9)])
    assert ocr.ocr_page(page).words


@pytest.mark.parametrize("ready,exit_code", [(True, 0), (False, 1)])
def test_doctor_checks_recognition_and_exits_nonzero_when_no_engine_works(monkeypatch, ready, exit_code):
    monkeypatch.setattr(ocr, "ocr_diagnostics", lambda: [{"engine": "portable", "ready": ready, "detail": "synthetic check"}])
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == exit_code
    assert ("Offline OCR is ready" if ready else "pip install") in result.output


def test_bundled_engine_is_preferred_even_when_tesseract_exists(monkeypatch):
    monkeypatch.setattr(ocr, '_rapid_module', lambda: object())
    monkeypatch.setattr(ocr.shutil, 'which', lambda name: '/optional/tesseract')
    assert ocr.available_engines() == ['rapidocr-onnxruntime', 'tesseract']


def test_cache_distinguishes_a_flattened_scan_from_vector_recovery_geometry(monkeypatch):
    monkeypatch.setattr(ocr, 'available_engines', lambda: ['rapidocr-onnxruntime'])
    monkeypatch.setattr(ocr, 'outline_regions', lambda page: [pymupdf.Rect(10, 10, 60, 20)] if page.number else [])
    calls = []
    monkeypatch.setattr(ocr, '_recognize', lambda *args: calls.append(True) or [(10, 10, 60, 20, 'MASK', .9)])
    monkeypatch.setattr(ocr, '_recover_outline_lines', lambda page, words, *, regions: (words, 0, [tuple(r) for r in regions]))
    ocr._CACHE.clear()
    with pymupdf.open() as pdf:
        pdf.new_page(width=200, height=100)
        pdf.new_page(width=200, height=100)
        scan = ocr.ocr_page(pdf[0])
        vector = ocr.ocr_page(pdf[1])
    assert len(calls) == 2 and not scan.outlined and vector.outlined
    ocr._CACHE.clear()
