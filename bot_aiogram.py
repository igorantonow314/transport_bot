import math
import logging
from typing import (
    List,
    Tuple,
    Any,
    Optional,
)

from aiogram import Bot, Dispatcher, executor, types, filters

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from data import (
    get_route,
    get_stop,
    get_forecast_by_stop,
    get_routes_by_stop,
)
from bot_conf import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


TRANSPORT_TYPE_EMOJI = {"bus": "🚌", "trolley": "🚎", "tram": "🚊", "ship": "🚢"}
EMOJI_MINIMAL_THEME = {
    "back": "◁",
    "forward": "▷",
    "close": "✖️",
    "change_direction": "⇵",
}

EMOJI_BLUE_THEME = {"back": "◀", "forward": "▶", "close": "✖️", "change_direction": "🔄"}

EMOJI = EMOJI_BLUE_THEME


@dp.message_handler(commands=["start", "help"])
async def start_message(message: types.Message):
    text = """Привет!
Этот бот покажет тебе время прибытия транспорта на любую остановку.

🚩 отправь *местоположение*, чтобы найти ближайшие остановки

🔎 чтобы *найти остановку по названию*, просто напиши название

🚌 можно посмотреть маршрут транспорта, который подходит к остановке

🎲 можно посмотреть случайную остановку: 👉 /random\\_stop

_Данные о транспорте получены благодаря:_
[Экосистеме городских сервисов «Цифровой Петербург»](https://petersburg.ru)
[Порталу общественного транспорта\
 Санкт-Петербурга](https://transport.orgp.spb.ru)

**Контакты:**
@igorantonow
Сообщайте обо всех багах, пишите любые предложения по изменению\
 дизайна, функционала и т.п.
"""
    kbd = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    'Остановка "метро Невский проспект"',
                    callback_data="BusStopMsgBlock newmsg 15495",
                )
            ]
        ]
    )
    await message.answer(text, reply_markup=kbd, parse_mode="markdown")


def make_keyboard(
    items: List[Tuple[str, Any]], columns: int = 5
) -> InlineKeyboardMarkup:
    if not columns > 0:
        raise ValueError("number of columns must be > 0")
    keyboard = []
    row = []
    for it in items:
        row.append(InlineKeyboardButton(it[0], callback_data=it[1]))
        if len(row) >= columns:
            keyboard.append(row)
            row = []
    if len(row) > 0:
        if len(keyboard) > 0:
            for i in range(columns - len(row)):
                row.append(InlineKeyboardButton(" ", callback_data="common pass"))
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def make_paginator(
    items: List[Tuple[str, str]],
    previous_page_cmd: str,
    next_page_cmd: str,
    title: Optional[str] = None,
    cur_page=0,
    page_size=10,
    show_buttons=False,
) -> Tuple[str, InlineKeyboardMarkup]:
    """
    :param items: Truple of option name and callback_data
    :param show_buttons: show arrow buttons if all items is in one page
    """
    max_page_num = math.ceil(len(items) / page_size) - 1
    assert 0 <= cur_page
    assert cur_page <= max_page_num
    msg = ""
    if title:
        msg += title + "\n"
    s = cur_page * page_size
    e = min(len(items), (cur_page + 1) * page_size)
    for i in range(s, e):
        msg += f"*{i+1}.* {items[i][0]} \n"
    msg += f"_{s+1} - {e} из {len(items)}_\n"

    kbd = make_keyboard(
        [(str(i + 1), items[i][1]) for i in range(s, e)]
    ).inline_keyboard
    ctrls = []
    if cur_page == 0:
        ctrls.append(InlineKeyboardButton(" ", callback_data="common pass"))
    else:
        ctrls.append(
            InlineKeyboardButton(EMOJI["back"], callback_data=previous_page_cmd)
        )
    ctrls.append(InlineKeyboardButton(EMOJI["close"], callback_data="common delete_me"))
    if cur_page == max_page_num:
        ctrls.append(InlineKeyboardButton(" ", callback_data="common pass"))
    else:
        ctrls.append(
            InlineKeyboardButton(EMOJI["forward"], callback_data=next_page_cmd)
        )
    if max_page_num > 1 or show_buttons:
        kbd.append(ctrls)
    return msg, InlineKeyboardMarkup(inline_keyboard=kbd)


def forecast_json_to_text(forecast_json, stop_id):
    """
    Converts result of get_forecast_by_stop into human-readable form.
    """
    # TRANSLATION = {'bus': 'автобус', 'trolley': 'троллейбус',
    #                'tram': 'трамвай', 'ship': 'аквабус'}
    assert forecast_json["success"]
    msg = ""
    routes = set()
    for p in forecast_json["result"]:
        route_id = int(p["routeId"])
        route = get_route(route_id)
        msg += (
            "_"
            + p["arrivingTime"].split()[1][:-3]
            + "_................."
            + TRANSPORT_TYPE_EMOJI[route.transport_type]
            + "*"
            + route.route_short_name.ljust(3)
            + "*\n"
        )
        routes.add(route_id)
    return msg


def stop_info(stop_id):
    """
    :result: human-readable arrival time forecast for the stop
    in markdown format
    and forecast_json (так надо)
    """
    forecast_json = get_forecast_by_stop(stop_id)
    stop = get_stop(stop_id)
    msg = "*" + stop.stop_name
    msg += "*\n"
    msg += forecast_json_to_text(forecast_json, stop_id)
    if len(forecast_json_to_text(forecast_json, stop_id)) == 0:
        msg += "_не найдено ни одного автобуса, "
        msg += "посмотрите другие остановки._\n"
    return msg, forecast_json


def stop_info_message(stop_id) -> Tuple[str, InlineKeyboardMarkup]:
    logger.info("form stop info message")
    message, forecast_json = stop_info(stop_id)
    rl = [int(p["routeId"]) for p in forecast_json["result"]]
    routes = get_routes_by_stop(stop_id)
    if not set(rl).issubset([i[0] for i in routes]):
        logger.exception("Fantom bus!")
        logger.warn(f"stop: {stop_id}")
        logger.warn(f"routes: {routes}")
        logger.warn(f"but here is {set(rl)}")
    s = []
    for route_id, direction in routes:
        s.append(
            (
                TRANSPORT_TYPE_EMOJI[get_route(route_id).transport_type]
                + get_route(route_id).route_short_name,
                f"RouteMsgBlock appear_here {route_id} {direction}",
            )
        )
    kbd = make_keyboard(s)
    kbd.inline_keyboard.append(
        [
            InlineKeyboardButton(
                "Обновить", callback_data=f"BusStopMsgBlock refresh {stop_id}"
            ),
            InlineKeyboardButton(
                "Похожие", callback_data=f"SearchStopsMsgBlock stop_group {stop_id}"
            ),
        ]
    )
    return message, kbd


@dp.callback_query_handler(lambda x: x.data.startswith("BusStopMsgBlock"))
async def bus_stop_cb_handler(callback: types.CallbackQuery):
    params = callback.data.split()
    assert params[0] == "BusStopMsgBlock"
    if params[1] == "refresh":
        assert callback.message is not None
        msg = "Обновление..."
        await callback.message.edit_text(msg)
        params[1] = "appear_here"
    if params[1] in ("appear_here", "newmsg"):
        logger.info("callback: BusStop message")
        assert get_stop(int(params[2])) is not None
        assert callback.message is not None
        msg, kbd = stop_info_message(int(params[2]))
        if params[1] == "appear_here":
            await callback.message.edit_text(
                msg, parse_mode="markdown", reply_markup=kbd
            )
        else:
            await callback.message.reply(msg, parse_mode="markdown", reply_markup=kbd)
        await callback.answer()


@dp.message_handler(filters.RegexpCommandsFilter(regexp_commands=["stop_([0-9]+)"]))
async def stop_command_handler(message: types.Message):
    assert message.text.startswith("/stop_")
    stop_id = int(message.text.replace("/stop_", ""))
    msg, ikm = stop_info_message(stop_id)
    await message.reply(msg, reply_markup=ikm, parse_mode="markdown")


def start_bot():
    executor.start_polling(dp, skip_updates=True)


if __name__ == "__main__":
    start_bot()
