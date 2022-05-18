import math
import logging
from typing import (
    List,
    Tuple,
    Any,
    Optional,
    Dict,
    Union,
)

from aiogram import Bot, Dispatcher, executor, types, filters

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ContentTypes

from data import (
    get_route,
    get_stop,
    get_forecast_by_stop,
    get_routes_by_stop,
    get_nearest_stops,
    get_stops_by_route,
    get_stops_in_group,
    search_stop_groups_by_name,
    get_random_stop_id,
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
            ],
            [
                InlineKeyboardButton(
                    'Пример ближайших остановок',
                    callback_data="NearestStops example 59.928048 30.348679",
                )
            ],
            [
                InlineKeyboardButton(
                "🎲Случайная остановка",
                callback_data="random_stop"
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
    always_show_buttons=False,
) -> Tuple[str, InlineKeyboardMarkup]:
    """
    :param items: Truple of option name and callback_data
    :param always_show_buttons: show arrow buttons even if all items is in one page
    """
    assert len(items) > 0
    max_page_num = math.ceil(len(items) / page_size) - 1
    # num of pages must be >= len(items) / page_size
    # numeration starts from 0
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
    if max_page_num > 1 or always_show_buttons:
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


def stop_info_message(stop_id) -> Dict[str, Any]:
    """Forms message to send about stop forecast.

    Example:
        my_message.answer(**stop_info_message(2080))

    :return: kwargs to bot.send_message() or types.Message().answer(), etc"""
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
    return {"text": message, "reply_markup": kbd, "parse_mode": "markdown"}


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
        if params[1] == "appear_here":
            await callback.message.edit_text(**stop_info_message(int(params[2])))
        else:
            await callback.message.reply(**stop_info_message(int(params[2])))
        await callback.answer()


@dp.message_handler(filters.RegexpCommandsFilter(regexp_commands=["stop_([0-9]+)"]))
async def stop_command_handler(message: types.Message):
    """Handles commands like /stop_12345, where 12345 is stop_id."""
    assert message.text.startswith("/stop_")
    stop_id = int(message.text.replace("/stop_", ""))
    await message.reply(**stop_info_message(stop_id))


@dp.message_handler(commands=["nevskii"])
async def nevskii_command_handler(message: types.Message):
    """
    Forecast for stop "metro Nevskii prospect"
    """
    logger.info("/nevskii command handler")
    await message.reply(**stop_info_message(15495))


@dp.message_handler(commands=["random_stop"])
@dp.callback_query_handler(lambda x: x.data == "random_stop")
async def random_stop_command_handler(x: Union[types.Message, types.CallbackQuery]):
    """
    Forecast for random stop
    """
    logger.info("/nevskii command handler")
    m = stop_info_message(get_random_stop_id())
    m['reply_markup'].inline_keyboard[-1].append(
        types.InlineKeyboardButton(
            "🎲Случайная",
            callback_data="random_stop"
            )
        )
    if isinstance(x, types.CallbackQuery):
        await x.message.answer(**m)
        await x.answer()
    else:
        await x.reply(**m)


def nearest_stops_message(latitude: float, longitude: float, n=10) -> Dict[str, Any]:
    """Forms message to send about nearest stops.

    Example:
        my_message.answer(**nearest_stops_message(60.0, 30.0))

    :arg n: number of shown stops (not tested)
    :return: kwargs to bot.send_message() or types.Message().answer(), etc"""
    logger.info(f"form nearest_stops message")
    stops = get_nearest_stops(latitude, longitude, n=n)
    title = "*Ближайшие остановки:*"
    items = []  # type: List[Tuple[str, str]]
    for i in stops:
        items.append(
            (
                TRANSPORT_TYPE_EMOJI[get_stop(i).transport_type]
                + get_stop(i).stop_name,
                f"BusStopMsgBlock newmsg {i}",
            )
        )
    msg, kbd = make_paginator(items, "", "", title=title, always_show_buttons=False)
    return {"text": msg, 'reply_markup': kbd, 'parse_mode': 'markdown'}


@dp.message_handler(commands=["test_location"])
async def nearest_stops_test_message_handler(message: types.Message):
    m = nearest_stops_message(60, 30)
    await message.reply(**m)


@dp.message_handler(content_types=ContentTypes.LOCATION)
async def nearest_stops_message_handler(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    await message.reply(**nearest_stops_message(lat, lon))


@dp.callback_query_handler(lambda x: x.data.startswith('NearestStops'))
async def nearest_stops_callback_handler(callback: types.CallbackQuery):
    params = callback.data.split()
    assert params[0] == "NearestStops"
    if params[1] == "example":
        lat = float(params[2])
        lon = float(params[3])
        await callback.message.answer_location(lat, lon)
        params[1] = "msg"
    if params[1] == "msg":
        lat = float(params[2])
        lon = float(params[3])
        await callback.message.answer(**nearest_stops_message(lat, lon))
        await callback.answer()


def route_message(route_id: int, direction: int, page_num: Optional[int] = None
) -> Dict[str, Any]:
    logger.info(f"form route message")
    if not page_num:
        page_num = 0
    route = get_route(route_id)
    msg = ""
    msg += "*" + TRANSPORT_TYPE_EMOJI[route.transport_type]
    msg += route.route_short_name
    msg += "*\n"
    msg += "*" + get_route(route_id).route_long_name + "*\n"
    msg += ("_Обратное" if direction else "_Прямое") + " направление_\n"
    msg += "\n"
    stops = get_stops_by_route(route_id, direction)
    options = []
    for s in stops:
        options.append(
            (get_stop(s).stop_name, "BusStopMsgBlock appear_here " + str(s))
        )
    m, kbd = make_paginator(
        options,
        cur_page=page_num,
        previous_page_cmd="RouteMsgBlock appear_here "
        + f"{route_id} {direction} {page_num-1}",
        next_page_cmd="RouteMsgBlock appear_here "
        + f"{route_id} {direction} {page_num+1}",
        always_show_buttons=True,
    )
    msg += m
    msg += "_Сменить направление_: " + EMOJI["change_direction"]
    kbd.inline_keyboard[-1].insert(
        -1,
        InlineKeyboardButton(
            EMOJI["change_direction"],
            callback_data="RouteMsgBlock appear_here "
            + f"{route_id} {1-direction} 0",
        ),
    )
    return {"text": msg, "reply_markup": kbd, "parse_mode": "markdown"}


@dp.callback_query_handler(lambda x: x.data.startswith('RouteMsgBlock'))
async def route_callback_handler(callback: types.CallbackQuery):
    params = callback.data.split()
    assert params[0] == "RouteMsgBlock"
    if params[1] in ["appear_here", "newmsg"]:
        r = int(params[2])
        d = int(params[3])
        if len(params) >= 5:
            page_num = int(params[4])
        else:
            page_num = None
        if params[1] == "appear_here":
            await callback.message.edit_text(**route_message(r, d, page_num))
        else:
            await callback.message.answer(**route_message(r, d, page_num))
        await callback.answer()


def search_stop_by_name_message(query: str) -> Dict[str, Any]:
    stop_groups = search_stop_groups_by_name(query)
    # formatting query into markdown
    # (see https://core.telegram.org/bots/api#formatting-options)
    fq = query
    for c in "*_[`":
        fq = fq.replace(c, "\\" + c)

    if len(stop_groups) == 0:
        return {"text": f"**Остановок по запросу** '{fq}' **не найдено** :-(",
                "parse_mode": "markdown"}
    title = 'Остановки по запросу "' + fq + '":'
    items = []
    for stop_group_name in stop_groups:
        stop_ex_id = get_stops_in_group(stop_group_name)[0]
        items.append(
            (stop_group_name, f"SearchStopsMsgBlock stop_group_newmsg {stop_ex_id}")
        )
    message, kbd = make_paginator(
        items, " ", " ", title=title, page_size=10
    )
    return {"text": message, "reply_markup": kbd, "parse_mode": "markdown"}


def stop_group_message(
        stop_ex_id: int, page_num: int = 0
    ) -> Dict[str, Any]:
    stop_group_name = get_stop(stop_ex_id).stop_name.lower()
    stops = get_stops_in_group(stop_group_name)
    options = []
    for i in stops:
        s = get_stop(i)
        n = TRANSPORT_TYPE_EMOJI[s.transport_type]
        n += "*" + s.stop_name + "*\n"
        n += ", ".join(
            [get_route(r).route_short_name for r, d in get_routes_by_stop(i)]
        )
        options.append((n, f"BusStopMsgBlock appear_here {i}"))

    pt = "Какая остановка Вам нужна?"
    ppc = f"SearchStopsMsgBlock stop_group {stop_ex_id} {page_num-1}"
    npc = f"SearchStopsMsgBlock stop_group {stop_ex_id} {page_num+1}"
    m, k =  make_paginator(
        options,
        title=pt,
        previous_page_cmd=ppc,
        next_page_cmd=npc,
        cur_page=page_num,
    )
    return {"text": m, "reply_markup": k, "parse_mode": "markdown"}


@dp.message_handler()
async def search_stop_message_handler(message: types.Message):
    query = message.text
    await message.reply(**search_stop_by_name_message(query))


@dp.callback_query_handler(lambda x: x.data.startswith("SearchStopsMsgBlock"))
async def search_stop_callback_handler(callback: types.CallbackQuery):
    params = callback.data.split()
    assert params[0] == "SearchStopsMsgBlock"
    if params[1] == "stop_group" or params[1] == "stop_group_newmsg":
        logger.info("callback: Search stop: stop group block sending")
        logger.debug(f"stop group stop_id: {params[2]}")
        if len(params) == 3:
            msg = stop_group_message(int(params[2]))
        else:
            # there is page num
            pn = int(params[3])
            stop_ex_id = int(params[2])
            msg = stop_group_message(stop_ex_id, pn)

        if params[1] == "stop_group":
            await callback.message.edit_text(**msg)
        else:  # stop_group_newmsg
            await callback.message.reply(**msg)
        await callback.answer()


@dp.callback_query_handler()
async def callback_handler(callback: types.CallbackQuery) -> None:
    logger.info("callback recieved")
    
    if callback.data.startswith("common"):
        if callback.data == "common delete_me":
            logger.info("callback: common delete_me")
            assert callback.message is not None
            await callback.message.delete()
            await callback.answer()
        elif callback.data == "common pass":
            logger.info("callback: pass")
            await callback.answer()
        else:
            raise ValueError(f"Unknown callback: {callback.data}")
    else:
        raise ValueError(f"Unknown callback: {callback.data}")


def start_bot():
    executor.start_polling(dp, skip_updates=True)


if __name__ == "__main__":
    start_bot()
