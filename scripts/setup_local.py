"""Check/repair a checkout using local tools; compatible with bootstrap Python 3.9+.

Default: install missing runtimes, sync the app dependencies, build the UI, test OCR.
--check-only: report and test without installing or changing dependencies.
No customer documents, credentials, account settings or workspace data are read.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / '.kaizen-tools'
REPORT = ROOT / 'out' / 'setup-report.json'


def run(args, **kwargs):
    print('+ ' + ' '.join(str(a) for a in args), flush=True)
    return subprocess.run([str(a) for a in args], cwd=ROOT, check=True, **kwargs)


def output(args):
    return run(args, capture_output=True, text=True).stdout.strip()


def python_version(executable):
    try:
        return tuple(json.loads(output([executable, '-c', 'import json,sys; print(json.dumps(list(sys.version_info[:3])))'])))
    except (OSError, subprocess.CalledProcessError, ValueError):
        return ()


def supported_python(version):
    return version[:2] in ((3, 12), (3, 13))


def venv_python(folder):
    return folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def ensure_python(check_only):
    candidates = [sys.executable, venv_python(ROOT / '.venv')]
    candidates += [shutil.which(name) for name in ('python3.13', 'python3.12')]
    candidates += list((TOOLS / 'python').glob('**/python.exe' if os.name == 'nt' else '**/python3.13'))
    if os.name == 'nt' and shutil.which('py'):
        for version in ('-3.13', '-3.12'):
            try:
                candidates.append(output(['py', version, '-c', 'import sys; print(sys.executable)']))
            except (OSError, subprocess.CalledProcessError):
                pass
    for candidate in candidates:
        if candidate and supported_python(python_version(candidate)):
            return str(candidate)
    if check_only:
        raise RuntimeError('Python 3.12 or 3.13 is required; run setup without --check-only to install a local Python.')
    # Bootstrap uv in an isolated environment, never with system pip. Its managed
    # Python stays in this ignored checkout folder, with no global PATH changes.
    TOOLS.mkdir(exist_ok=True)
    bootstrap = TOOLS / 'bootstrap'
    run([sys.executable, '-m', 'venv', bootstrap])
    py = venv_python(bootstrap)
    run([py, '-m', 'pip', 'install', 'uv'])
    env = dict(os.environ, UV_PYTHON_INSTALL_DIR=str(TOOLS / 'python'), UV_CACHE_DIR=str(TOOLS / 'cache'))
    uv = bootstrap / ('Scripts/uv.exe' if os.name == 'nt' else 'bin/uv')
    run([uv, 'python', 'install', '3.13'], env=env)
    return run(
        [uv, 'python', 'find', '--managed-python', '3.13'], env=env, capture_output=True, text=True
    ).stdout.strip()


def node_target(system, machine):
    operating_system = {'Darwin': 'darwin', 'Linux': 'linux', 'Windows': 'win'}.get(system)
    arch = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'x64', 'amd64': 'x64'}.get(machine.lower())
    if not operating_system or not arch:
        raise RuntimeError('Automatic Node install supports macOS/Linux/Windows on x64/arm64; install Node 22 manually on this platform.')
    extension = 'zip' if operating_system == 'win' else 'tar.gz'
    return operating_system + '-' + arch + '.' + extension


def verify_sha256(archive, expected):
    digest = hashlib.sha256()
    with archive.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise RuntimeError('Node download checksum failed; the archive will not be installed.')


def install_node():
    suffix = node_target(platform.system(), platform.machine())
    base = 'https://nodejs.org/dist/latest-v22.x/'
    with urllib.request.urlopen(base + 'SHASUMS256.txt', timeout=60) as response:
        manifest = response.read().decode('utf-8')
    matches = [line.split() for line in manifest.splitlines() if line.endswith('-' + suffix)]
    if len(matches) != 1:
        raise RuntimeError('No matching official Node 22 download was found.')
    checksum, filename = matches[0]
    if not re.fullmatch(r'node-v22\.\d+\.\d+-[a-z0-9.-]+', filename):
        raise RuntimeError('Unexpected Node archive name.')
    destination = TOOLS / 'node'
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='kaizen-node-') as directory:
        archive = Path(directory) / filename
        print('Downloading verified Node 22 from nodejs.org...', flush=True)
        with urllib.request.urlopen(base + filename, timeout=120) as response, archive.open('wb') as stream:
            shutil.copyfileobj(response, stream)
        verify_sha256(archive, checksum)
        if archive.suffix == '.zip':
            with zipfile.ZipFile(archive) as package:
                for name in package.namelist():
                    if not (destination / name).resolve().is_relative_to(destination.resolve()):
                        raise RuntimeError('Unsafe path in Node archive.')
                package.extractall(destination)
        else:
            with tarfile.open(archive) as package:
                package.extractall(destination, filter='data')
    extracted = destination / filename.removesuffix('.zip').removesuffix('.tar.gz')
    return extracted if os.name == 'nt' else extracted / 'bin'


def ensure_node(check_only):
    managed = sorted((TOOLS / 'node').glob('node-v22.*')) if (TOOLS / 'node').exists() else []
    for directory in managed:
        binary_dir = directory if os.name == 'nt' else directory / 'bin'
        os.environ['PATH'] = str(binary_dir) + os.pathsep + os.environ.get('PATH', '')
    try:
        version = output(['node', '--version'])
        ready = int(version.lstrip('v').split('.')[0]) >= 20 and bool(shutil.which('npm.cmd' if os.name == 'nt' else 'npm'))
    except (OSError, ValueError, subprocess.CalledProcessError):
        ready = False
    if not ready:
        if check_only:
            raise RuntimeError('Node >=20 and npm are required to build the UI; run setup without --check-only to install local Node 22.')
        os.environ['PATH'] = str(install_node()) + os.pathsep + os.environ.get('PATH', '')
    return output(['node', '--version']), shutil.which('npm.cmd' if os.name == 'nt' else 'npm')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', help='Check versions and OCR; do not install anything')
    parser.add_argument('--skip-ui', action='store_true', help='Only check/repair Python, API and OCR')
    parser.add_argument('--venv', type=Path, default=ROOT / '.venv', help='App virtual environment (default .venv)')
    args = parser.parse_args(argv)
    report = {'platform': platform.system(), 'architecture': platform.machine(), 'status': 'FAIL', 'checks': {}}
    print('Kaizen local setup | Python 3.12/3.13 | Node >=20 | bundled offline OCR', flush=True)
    delegated = False
    try:
        python = ensure_python(args.check_only)
        # Archive extraction and app dependencies require the supported interpreter.
        if not supported_python(sys.version_info):
            delegated = True
            return run([python, __file__, *(argv if argv is not None else sys.argv[1:])]).returncode
        py = venv_python(args.venv.resolve())
        if not supported_python(python_version(py)):
            if args.check_only:
                raise RuntimeError('The app virtual environment is missing or uses an unsupported Python. Run setup to repair it.')
            if args.venv.exists():
                backup = args.venv.with_name(args.venv.name + '-backup-' + str(time.time_ns()))
                args.venv.rename(backup)
                print('Kept old virtual environment at ' + str(backup), flush=True)
            run([python, '-m', 'venv', args.venv.resolve()])
        report['checks']['python'] = '.'.join(map(str, python_version(py)))
        try:
            report['commit'] = output(['git', 'rev-parse', '--short', 'HEAD'])
            report['source_modified'] = bool(output(['git', 'status', '--porcelain', '--untracked-files=no']))
        except (OSError, subprocess.CalledProcessError):
            report['commit'] = 'Git revision unavailable (archive checkout)'
        if not args.check_only:
            run([py, '-m', 'pip', 'install', '--upgrade', 'pip'])
            run([py, '-m', 'pip', 'install', '-e', '.[api]'])
        run([py, '-m', 'pip', 'check'])
        packages = 'import json,importlib.metadata as m; print(json.dumps({p:m.version(p) for p in ["kaizen-crosscheck","pydantic","pymupdf","openpyxl","rapidfuzz","typer","rich","rapidocr-onnxruntime","onnxruntime","opencv-python","numpy","Pillow","PyYAML","Shapely","pyclipper","fastapi","uvicorn","python-multipart"]}))'
        report['checks']['packages'] = json.loads(output([py, '-c', packages]))
        assert report['checks']['packages']['rapidocr-onnxruntime'] == '1.2.3', 'Bundled OCR version differs; run setup to sync dependencies'
        report['checks']['ocr'] = output([py, '-m', 'kaizen', 'doctor'])
        print(report['checks']['ocr'], flush=True)
        report['checks']['pdf_workflow'] = output([py, ROOT / 'scripts/smoke_local.py'])
        print(report['checks']['pdf_workflow'], flush=True)
        if not args.skip_ui:
            report['checks']['node'], npm = ensure_node(args.check_only)
            report['checks']['npm'] = output([npm, '--version'])
            if not args.check_only:
                run([npm, '--prefix', 'ui', 'ci'])
                run([npm, '--prefix', 'ui', 'run', 'build'])
            if not (ROOT / 'ui/dist/index.html').is_file():
                raise RuntimeError('The UI has not been built. Run setup without --check-only.')
            report['checks']['ui'] = 'built'
        report['status'] = 'PASS'
    except (OSError, ValueError, RuntimeError, AssertionError, subprocess.CalledProcessError, tarfile.TarError, zipfile.BadZipFile) as exc:
        # No environment dumps, document contents or credentials in the shareable report.
        report['error'] = str(exc)
        print('FAIL: ' + str(exc), flush=True)
    finally:
        if not delegated:
            REPORT.parent.mkdir(exist_ok=True)
            REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            print('Report: ' + str(REPORT), flush=True)
    if report['status'] != 'PASS':
        print('See docs/pdf-ocr.md for OS library/DLL troubleshooting.', flush=True)
        return 1
    print('PASS: dependencies and scanned-PDF workflow work.', flush=True)
    print('Stop any running Kaizen server, restart with the command below, and create a new run to use the fixes.', flush=True)
    print(str(py.parent / ('kaizen.exe' if os.name == 'nt' else 'kaizen')) + ' serve', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
