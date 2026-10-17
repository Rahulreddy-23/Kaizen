"""Guard local installer version/platform checks and downloaded-archive integrity."""

import hashlib

import pytest

from scripts import setup_local


@pytest.mark.parametrize('version,ready', [((3, 11, 9), False), ((3, 12, 0), True), ((3, 13, 7), True), ((3, 14, 0), False)])
def test_python_version_selects_an_ocr_tested_runtime(version, ready):
    assert setup_local.supported_python(version) is ready


@pytest.mark.parametrize('system,machine,target', [('Windows', 'AMD64', 'win-x64.zip'), ('Darwin', 'arm64', 'darwin-arm64.tar.gz'), ('Linux', 'x86_64', 'linux-x64.tar.gz')])
def test_node_archive_matches_the_machine(system, machine, target):
    assert setup_local.node_target(system, machine) == target


def test_unsupported_architecture_is_actionable():
    with pytest.raises(RuntimeError, match='install Node 22 manually'):
        setup_local.node_target('Linux', 'unknown')


def test_corrupted_download_is_rejected_before_extraction(tmp_path):
    archive = tmp_path / 'node.zip'
    archive.write_bytes(b'trusted archive')
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    setup_local.verify_sha256(archive, checksum)
    archive.write_bytes(b'corrupted archive')
    with pytest.raises(RuntimeError, match='checksum failed'):
        setup_local.verify_sha256(archive, checksum)
