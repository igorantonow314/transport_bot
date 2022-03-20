from bot import get_forecast_by_stop, stop_info


def test_get_forecast_by_stop():
    f = get_forecast_by_stop(15495)
    assert f['success']
    assert f['result']


def test_stop_info():
    # TODO: more test cases
    stops = [15495, 2080]
    for i in stops:
        assert stop_info(i)
