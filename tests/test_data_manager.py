from src.data.data_manager import DataManager


def test_add_data():
    manager = DataManager()

    manager.add_data("BTC")

    assert manager.get_data() == ["BTC"]


def test_multiple_data():
    manager = DataManager()

    manager.add_data("BTC")
    manager.add_data("ETH")

    assert manager.get_data() == ["BTC", "ETH"]