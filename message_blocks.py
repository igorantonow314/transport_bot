from typing import Tuple, Callable, List, Optional
from math import ceil
import functools

from telegram import Message
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext

from data import (
    get_route,
    get_direction_by_stop,
    get_nearest_stops,
    get_stop,
    get_stops_by_route,
    get_forecast_by_stop,
)


TRANSPORT_TYPE_EMOJI = {'bus': '🚌', 'trolley': '🚎',
                        'tram': '🚊', 'ship': '🚢'}


def forecast_json_to_text(forecast_json, stop_id):
    '''
    Converts result of get_forecast_by_stop into human-readable form.
    '''
    # TRANSLATION = {'bus': 'автобус', 'trolley': 'троллейбус',
    #                'tram': 'трамвай', 'ship': 'аквабус'}
    assert forecast_json['success']
    msg = ''
    routes = set()
    for p in forecast_json['result']:
        route_id = int(p['routeId'])
        route = get_route(route_id)
        msg += ('_' + p['arrivingTime'].split()[1][:-3] + '_.................'
                + TRANSPORT_TYPE_EMOJI[route.transport_type]
                + '*' + route.route_short_name.ljust(3) + '*\n')
        routes.add(route_id)
    return msg


def stop_info(stop_id):
    '''
    :result: human-readable arrival time forecast for the stop
    in markdown format
    and forecast_json (так надо)
    '''
    forecast_json = get_forecast_by_stop(stop_id)
    stop = get_stop(stop_id)
    msg = '*Остановка: ' + stop.stop_name
    msg += TRANSPORT_TYPE_EMOJI[stop.transport_type] + '*\n'
    msg += forecast_json_to_text(forecast_json, stop_id)
    if len(forecast_json_to_text(forecast_json, stop_id)) == 0:
        msg += '_не найдено ни одного автобуса, '
        msg += 'посмотрите другие остановки._\n'
    msg += '\n'
    msg += 'Обновить: /stop\\_' + str(stop_id)
    return msg, forecast_json


class MsgBlock:
    """Class for managing messages with inline buttons"""
    def __init__(self):
        self.message = 'This is message for testing'
        self.kbd = InlineKeyboardMarkup([
                 [InlineKeyboardButton('Button 1', callback_data='btn1')],
                 [
                     InlineKeyboardButton('Button 2', callback_data='btn2'),
                     InlineKeyboardButton('Button 3', callback_data='btn3'),
                 ]
            ])

    def callback_handler(self,
                         update: Update,
                         context: CallbackContext) -> None:
        assert update.callback_query is not None
        assert update.callback_query.message is not None
        button = str(update.callback_query.data)
        update.callback_query.message.edit_text('Choosed button: ' + button)
        update.callback_query.answer()

    def send_new_message(self,
                         update: Update,
                         context: CallbackContext) -> Message:
        assert update.effective_chat is not None
        return context.bot.send_message(text=self.message,
                                        parse_mode='markdown',
                                        chat_id=update.effective_chat.id,
                                        reply_markup=self.kbd)


class StartMsgBlock(MsgBlock):
    """Welcome message"""
    def __init__(self):
        super().__init__()
        self.message = '''Привет!
Это альфа версия бота. Чтобы посмотреть расписание транспорта\
 на ближайшей остановке, пришли мне своё местоположение (или не своё).\
 Также можно посмотреть расписание для случайной остановки: \
/random\\_stop

**Все команды:**
/nevskii -- расписание транспорта на остановке "Невский проспект"
/random\\_stop -- расписание транспорта на случайной остановке
/stop\\_15495 -- расписание транспорта на остановке с соответствующим id
/route\\_306\\_0 -- остановки маршрута с id 306 и направлением 0 (прямым)

**Контакты:**
@igorantonow
'''
        self.kbd = InlineKeyboardMarkup([[]])


def make_keyboard(items: List[Tuple[str, str]], columns=5):
    """:param items: list of (button name, button callback)"""
    keyboard = []
    row = []
    for it in items:
        row.append(InlineKeyboardButton(it[0], callback_data=it[1]))
        if len(row) >= 5:
            keyboard.append(row)
            row = []
    if len(row) > 0:
        if len(keyboard) > 0:
            for i in range(5 - len(row)):
                row.append(InlineKeyboardButton(' ', callback_data='/test'))
    keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


class BusStopMsgBlock(MsgBlock):
    """Message with forecast for the stop"""
    def send_new_message(self,
                         update: Update,
                         context: CallbackContext) -> Message:
        assert update.message is not None
        assert update.message.text is not None
        assert update.message.text.startswith('/stop_')
        stop_id = int(update.message.text.replace('/stop_', ''))
        self.message, self.kbd = self.form_message(stop_id)
        return super().send_new_message(update, context)

    def form_message(self, stop_id) -> Tuple[str, InlineKeyboardMarkup]:
        self.message, forecast_json = stop_info(stop_id)
        rl = [int(p['routeId']) for p in forecast_json['result']]
        routes = set(rl)
        s = []
        for route_id in routes:
            s.append((
                TRANSPORT_TYPE_EMOJI[get_route(route_id).transport_type]
                + get_route(route_id).route_short_name,

                'BusStopMsgBlock get_route ' + str(route_id) + ' '
                + str(get_direction_by_stop(stop_id, route_id))
                ))
        return self.message, make_keyboard(s)

    def callback_handler(self,
                         update: Update,
                         context: CallbackContext) -> None:
        assert update.callback_query is not None
        assert update.callback_query.data is not None
        assert update.callback_query.message is not None
        params = update.callback_query.data.split()
        assert params[0] == 'BusStopMsgBlock'
        if params[1] == 'get_route':
            some_route_msgblock = RouteMsgBlock()
            msg, kbd = some_route_msgblock.form_message(int(params[2]),
                                                        int(params[3]))
            update.callback_query.message.edit_text(
                msg, parse_mode='markdown', reply_markup=kbd)
            update.callback_query.answer()


class NearestStopsMsgBlock(MsgBlock):
    """Stops behind sended location"""
    def form_message(self,
                     latitude: float,
                     longitude: float) -> Tuple[str, InlineKeyboardMarkup]:
        stops = get_nearest_stops(latitude, longitude, n=10)
        msg = '*Ближайшие остановки:*\n'
        for i in stops:
            msg += (('/stop\\_'+str(i) + ": ").ljust(13)
                    + TRANSPORT_TYPE_EMOJI[get_stop(i).transport_type]
                    + get_stop(i).stop_name
                    )
            msg += '\n'
        return msg, InlineKeyboardMarkup([[]])

    def send_new_message(self,
                         update: Update,
                         context: CallbackContext) -> Message:
        assert update.message is not None
        assert update.message.location is not None

        self.message, self.kbd = self.form_message(
            update.message.location.latitude,
            update.message.location.longitude
            )
        return super().send_new_message(update, context)


class PaginatedChoosingMsgBlock(MsgBlock):
    def __init__(self):
        super().__init__()
        self.title = "Выберите:"
        # _type: list[Tuple[str, Callable[[Update, CallbackContext], None]]]
        self.option_list: List[Tuple[str, Callable[[Update, CallbackContext],
                                                   None]]] = []

        self.page_size = 10    # recommendation: size = 5 * n
        self.message_id: Optional[int] = None

    def set_title(self, title: str):
        self.title = title

    def add_option(self, annotation: str, action: Callable):
        if type(annotation) is not str:
            raise TypeError('annotation must be str')
        if not callable(action):
            raise TypeError('action must be callable')
        self.option_list.append((annotation, action))

    def form_page(self, page_num=0):
        msg = self.title + '\n'
        s = page_num * self.page_size
        e = min(len(self.option_list), (page_num + 1) * self.page_size)
        for i in range(s, e):
            msg += f'*{i}.* {self.option_list[i][0]} \n'
        kbd = make_keyboard([
            (str(i), f'PaginatedChoosingMsgBlock sel {i}')
            for i in range(s, e)
        ]).inline_keyboard
        # TODO: hide inactive buttons
        kbd.append([
            InlineKeyboardButton(
                '<',
                callback_data=f'PaginatedChoosingMsgBlock page {page_num - 1}'
            ),
            InlineKeyboardButton(
                'x',
                callback_data='PaginatedChoosingMsgBlock del'
            ),
            InlineKeyboardButton(
                '>',
                callback_data=f'PaginatedChoosingMsgBlock page {page_num + 1}'
            )
        ])
        return msg, InlineKeyboardMarkup(kbd)

    def form_message(self):
        return self.form_page(0)

    def callback_handler(self,
                         update: Update,
                         context: CallbackContext) -> None:
        assert update.callback_query is not None
        assert update.callback_query.data is not None
        assert update.effective_chat is not None
        params = update.callback_query.data.split()
        assert params[0] == 'PaginatedChoosingMsgBlock'
        if params[1] == 'page':
            assert update.callback_query.message is not None
            if not update.callback_query.message.message_id == self.message_id:
                return
            assert (0 <= int(params[2])
                    <= ceil(len(self.option_list) / self.page_size))
            msg, kbd = self.form_page(int(params[2]))
            update.callback_query.message.edit_text(msg,
                                                    parse_mode='markdown',
                                                    reply_markup=kbd)
        elif params[1] == 'sel':
            self.option_list[int(params[2])][1](update, context)
        elif params[1] == 'del':
            pass   # TODO
        else:
            raise ValueError(f'Unknown option: {params[1]}')

    def send_new_message(self,
                         update: Update,
                         context: CallbackContext) -> Message:
        self.message, self.kbd = self.form_message()
        m = super().send_new_message(update, context)
        self.message_id = m.message_id
        return m


class RouteMsgBlock(MsgBlock):
    """Route stops list"""
    def form_message(self,
                     route_id: int,
                     direction: int) -> Tuple[str, InlineKeyboardMarkup]:
        """Do not forget to set up pager.message_id!"""
        pager = PaginatedChoosingMsgBlock()
        title = '_Остановки маршрута:_\n'
        title += '*' + get_route(route_id).route_long_name + '*\n'
        title += ('_Обратное' if direction else '_Прямое') + ' направление_\n'
        title += '\n'
        title += ('_Прямое' if direction else '_Обратное') + ' направление_: '
        title += f'/route\\_{route_id}\\_{1-direction}\n'
        pager.set_title(title)

        stops = get_stops_by_route(route_id, direction)

        def it_action_t(s: int,
                        update: Update,
                        context: CallbackContext) -> None:
            # TODO
            assert update.callback_query is not None
            assert update.callback_query.message is not None
            bus_stop_msgblock = BusStopMsgBlock()
            msg, kbd = bus_stop_msgblock.form_message(s)
            update.callback_query.message.edit_text(
                msg,
                parse_mode='markdown',
                reply_markup=kbd
            )
            update.callback_query.answer()

        for s in stops:
            it_name = get_stop(s).stop_name
            pager.add_option(it_name, functools.partial(it_action_t, s))
        msg, kbd = pager.form_message()
        self.pager = pager
        return msg, kbd

    def send_new_message(self,
                         update: Update,
                         context: CallbackContext) -> Message:
        assert update.message is not None
        assert update.message.text is not None

        route_id, direction = map(
            int,
            update.message.text.replace('/route_', '').split('_')
            )
        self.form_message(route_id, direction)
        return self.pager.send_new_message(update, context)


stop_msgblock = BusStopMsgBlock()
test_block = MsgBlock()
nearest_stops_msgblock = NearestStopsMsgBlock()
route_msgblock = RouteMsgBlock()
start_msg_msgblock = StartMsgBlock()
