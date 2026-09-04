import re


def test_package_exposes_semver_version():
    import kaizen

    assert re.fullmatch(r"\d+\.\d+\.\d+", kaizen.__version__)
