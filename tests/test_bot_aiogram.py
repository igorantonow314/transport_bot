import pytest
from aiogram.types import InlineKeyboardMarkup

from bot_aiogram import (
    get_forecast_by_stop,
    stop_info,
    make_keyboard,
)


def test_get_forecast_by_stop():
    f = get_forecast_by_stop(15495)
    assert f["success"]
    assert f["result"]


def test_stop_info():
    # TODO: more test cases
    stops = [15495, 2080]
    for i in stops:
        assert stop_info(i)


def test_make_keyboard():
    # TODO: use pytest parametrising
    buttons_lists = [
        [("|>", "play"), ("||", "pause")],
        [("A", "1"), ("B", "2"), ("C", "3"), ("D", "4")],
        [("A", "1"), ("B", "2"), ("C", "3"), ("D", "4"), ("E", "5")],
        [("A", "1"), ("B", "2"), ("C", "3"), ("D", "4"), ("E", "5"), ("F", "6")],
        [
            ("A", "1"),
            ("B", "2"),
            ("C", "3"),
            ("D", "4"),
            ("E", "5"),
            ("F", "6"),
            ("G", "7"),
        ],
        [
            ("A", "1"),
            ("B", "2"),
            ("C", "3"),
            ("C", "4"),
            ("B", "2"),
            ("A", "dkdk"),
            ("G", "7"),
        ],
    ]
    columns_vars = [1, 2, 3, 4, 5, 6, 7]
    for bl in buttons_lists:
        for c in columns_vars:
            k = make_keyboard(bl, columns=c)
            assert type(k) == InlineKeyboardMarkup
            for btn_row in k.inline_keyboard:
                print(f"case: {bl} columns={c}; len(btn_row)={len(btn_row)}")
                assert len(btn_row) <= c
                assert len(btn_row) > 0
    # empty keys set
    for c in columns_vars:
        k = make_keyboard([], columns=c)
        assert type(k) is InlineKeyboardMarkup
        assert k.inline_keyboard == []
    # exceptions
    for c in [-1, 0]:
        with pytest.raises(ValueError):
            make_keyboard([], columns=c)
        with pytest.raises(ValueError):
            make_keyboard(buttons_lists[-1], columns=c)
