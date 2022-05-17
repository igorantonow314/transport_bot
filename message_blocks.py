import math
import logging
from typing import (
    Tuple,
    List,
    Optional,
    Any,
)

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext

from data import (
    get_route,
    get_nearest_stops,
    get_stop,
    get_stops_by_route,
    get_forecast_by_stop,
    search_stop_groups_by_name,
    get_stops_in_group,
    get_routes_by_stop,
)


TRANSPORT_TYPE_EMOJI = {"bus": "🚌", "trolley": "🚎", "tram": "🚊", "ship": "🚢"}
EMOJI_MINIMAL_THEME = {
    "back": "◁",
    "forward": "▷",
    "close": "✖️",
    "change_direction": "⇵",
}

EMOJI_BLUE_THEME = {"back": "◀", "forward": "▶", "close": "✖️", "change_direction": "🔄"}

EMOJI = EMOJI_BLUE_THEME

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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


class MsgBlock:
    """Class for managing messages with inline buttons"""

    def __init__(self):
        self.message = "This is message for testing"
        self.kbd = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Button 1", callback_data="btn1")],
                [
                    InlineKeyboardButton("Button 2", callback_data="btn2"),
                    InlineKeyboardButton("Button 3", callback_data="btn3"),
                ],
            ]
        )

    def callback_handler(self, update: Update, context: CallbackContext) -> None:
        logger.info(f"callback processing by {self}")
        assert update.callback_query is not None
        assert update.callback_query.message is not None
        button = str(update.callback_query.data)
        update.callback_query.message.edit_text("Choosed button: " + button)
        update.callback_query.answer()

    def send_new_message(self, update: Update, context: CallbackContext) -> None:
        logger.info(f"send new message by {self}")
        assert update.effective_chat is not None
        context.bot.send_message(
            text=self.message,
            parse_mode="markdown",
            chat_id=update.effective_chat.id,
            reply_markup=self.kbd,
        )


start_msg_msgblock = MsgBlock()
start_msg_msgblock.message = """Привет!
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
start_msg_msgblock.kbd = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                'Остановка "метро Невский проспект"',
                callback_data="BusStopMsgBlock newmsg 15495",
            )
        ]
    ]
)


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
    return InlineKeyboardMarkup(keyboard)


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
    return msg, InlineKeyboardMarkup(kbd)


class BusStopMsgBlock(MsgBlock):
    """Message with forecast for the stop"""

    def send_new_message(self, update: Update, context: CallbackContext) -> None:
        logger.info(f"send new message by {self}")
        assert update.message is not None
        assert update.message.text is not None
        assert update.message.text.startswith("/stop_")
        stop_id = int(update.message.text.replace("/stop_", ""))
        self.message, self.kbd = self.form_message(stop_id)
        super().send_new_message(update, context)

    def form_message(self, stop_id) -> Tuple[str, InlineKeyboardMarkup]:
        logger.info(f"form message by {self}")
        self.message, forecast_json = stop_info(stop_id)
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
        self.kbd = make_keyboard(s)
        self.kbd.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    "Обновить", callback_data=f"BusStopMsgBlock refresh {stop_id}"
                ),
                InlineKeyboardButton(
                    "Похожие", callback_data=f"SearchStopsMsgBlock stop_group {stop_id}"
                ),
            ]
        )
        return self.message, self.kbd

    def callback_handler(self, update: Update, context: CallbackContext) -> None:
        logger.info(f"callback processing by {self}")
        assert update.callback_query is not None
        assert update.callback_query.data is not None
        assert update.effective_chat is not None
        params = update.callback_query.data.split()
        assert params[0] == "BusStopMsgBlock"
        if params[1] == "get_route":
            raise NotImplementedError("deprecated")
        if params[1] == "refresh":
            assert update.callback_query.message is not None
            msg = "Обновление..."
            update.callback_query.message.edit_text(msg)
            params[1] = "appear_here"
        if params[1] == "appear_here":
            logger.info("callback: appear BusStop message")
            assert get_stop(int(params[2])) is not None
            assert update.callback_query.message is not None
            msg, kbd = self.form_message(int(params[2]))
            update.callback_query.message.edit_text(
                msg, parse_mode="markdown", reply_markup=kbd
            )
            update.callback_query.answer()
        if params[1] == "newmsg":
            logger.info("callback: new BusStop message")
            assert get_stop(int(params[2])) is not None
            assert update.callback_query.message is not None
            msg, kbd = self.form_message(int(params[2]))
            update.callback_query.message.reply_text(
                msg, parse_mode="markdown", reply_markup=kbd
            )
            update.callback_query.answer()


class NearestStopsMsgBlock(MsgBlock):
    """Stops behind sended location"""

    def form_message(
        self, latitude: float, longitude: float
    ) -> Tuple[str, InlineKeyboardMarkup]:
        logger.info(f"form message by {self}")
        stops = get_nearest_stops(latitude, longitude, n=10)
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
        msg, kbd = make_paginator(items, "", "", title=title, show_buttons=False)
        return msg, kbd

    def send_new_message(self, update: Update, context: CallbackContext) -> None:
        logger.info(f"send new message by {self}")
        assert update.message is not None
        assert update.message.location is not None

        self.message, self.kbd = self.form_message(
            update.message.location.latitude, update.message.location.longitude
        )
        super().send_new_message(update, context)


class RouteMsgBlock(MsgBlock):
    """Route stops list"""

    def form_message(
        self, route_id: int, direction: int, page_num: Optional[int] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        logger.info(f"form message by {self}")
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
            show_buttons=True,
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
        return msg, kbd

    def send_new_message(self, update: Update, context: CallbackContext) -> None:
        logger.info(f"send new message by {self}")
        assert update.message is not None
        assert update.message.text is not None

        route_id, direction = map(
            int, update.message.text.replace("/route_", "").split("_")
        )
        self.message, self.kbd = self.form_message(route_id, direction)
        super().send_new_message(update, context)

    def callback_handler(self, update: Update, context: CallbackContext) -> None:
        logger.info(f"callback processing by {self}")
        assert update.callback_query is not None
        assert update.callback_query.data is not None
        params = update.callback_query.data.split()
        if params[0] == "RouteMsgBlock":
            if params[1] == "appear_here":
                logger.info("callback: appear/edited Route message")
                assert update.callback_query.message is not None
                page_num = 0 if (len(params) == 4) else int(params[4])
                msg, kbd = self.form_message(int(params[2]), int(params[3]), page_num)
                update.callback_query.message.edit_text(
                    msg, parse_mode="markdown", reply_markup=kbd
                )
                update.callback_query.answer()
            else:
                raise ValueError(f"Unknown command: {params[1]}")


class SearchStopsMsgBlock(MsgBlock):
    """Searching stops by name"""

    def form_message(self, query: str) -> Tuple[str, InlineKeyboardMarkup]:
        stop_groups = search_stop_groups_by_name(query)
        # formatting query into markdown
        # (see https://core.telegram.org/bots/api#formatting-options)
        fq = query
        for c in "*_[`":
            fq = fq.replace(c, "\\" + c)
        title = 'Остановки по запросу "' + fq + '":'
        items = []
        for stop_group_name in stop_groups:
            stop_ex_id = get_stops_in_group(stop_group_name)[0]
            items.append(
                (stop_group_name, f"SearchStopsMsgBlock stop_group_newmsg {stop_ex_id}")
            )
        self.message, self.kbd = make_paginator(
            items, " ", " ", title=title, page_size=10
        )
        return self.message, self.kbd

    def form_stop_group_message(
        self, stop_ex_id: int, page_num: int = 0
    ) -> Tuple[str, InlineKeyboardMarkup]:
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
        return make_paginator(
            options,
            title=pt,
            previous_page_cmd=ppc,
            next_page_cmd=npc,
            cur_page=page_num,
        )

    def send_new_message(self, update: Update, context: CallbackContext) -> None:
        logger.info(f"send new message by {self}")
        assert update.message is not None
        assert update.message.text is not None
        self.message, self.kbd = self.form_message(update.message.text)
        update.message.reply_text(
            text=self.message, reply_markup=self.kbd, parse_mode="markdown"
        )

    def callback_handler(self, update: Update, context: CallbackContext) -> None:
        logger.info(f"callback processing by {self}")
        assert update.callback_query is not None
        assert update.callback_query.data is not None
        params = update.callback_query.data.split()

        if params[0] == "SearchStopsMsgBlock":
            if params[1] == "stop_group" or params[1] == "stop_group_newmsg":
                logger.info("callback: Search stop: stop group block sending")
                logger.debug(f"stop group stop_id: {params[2]}")
                if len(params) == 3:
                    msg, kbd = self.form_stop_group_message(int(params[2]))
                else:
                    # there is page num
                    pn = int(params[3])
                    stop_ex_id = int(params[2])
                    msg, kbd = self.form_stop_group_message(stop_ex_id, pn)

                # sending new message or editing old
                if params[1] == "stop_group":
                    assert update.callback_query.message is not None
                    update.callback_query.message.edit_text(
                        msg, parse_mode="markdown", reply_markup=kbd
                    )
                else:  # 'stop_group_newmsg'
                    assert update.effective_chat is not None
                    update.effective_chat.send_message(
                        msg, parse_mode="markdown", reply_markup=kbd
                    )
                update.callback_query.answer()

            else:
                raise ValueError(f"Unknown command: {params[1]}")


stop_msgblock = BusStopMsgBlock()
test_block = MsgBlock()
nearest_stops_msgblock = NearestStopsMsgBlock()
route_msgblock = RouteMsgBlock()
search_stop_msgblock = SearchStopsMsgBlock()
