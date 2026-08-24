from src.config import PROJECT_NAME, VERSION


def test_project_name():
    assert PROJECT_NAME == "AL TRADING AGENT"


def test_version():
    assert VERSION == "0.1.0"