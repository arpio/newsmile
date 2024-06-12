from pathlib import Path


def pytest_generate_tests(metafunc):
    if 'smile_path' in metafunc.fixturenames:
        paths = Path('tests/data-test/smile').iterdir()
        metafunc.parametrize('smile_path', paths)

    if 'json_path' in metafunc.fixturenames:
        paths = Path('tests/data-test/json').iterdir()
        metafunc.parametrize('json_path', paths)
