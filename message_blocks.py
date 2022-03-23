from typing import Tuple
import json
import requests

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext

from database import (
    get_route,
    get_direction_by_stop,
    get_nearest_stops,
    get_stop,
    get_stops_by_route,
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


def get_forecast_by_stop(stopID):
    '''
    Requests arrival time forecast for a particular stop.

    See also forecast_json_to_text() for human-readable result.
    Data from site: transport.orgp.spb.ru
    '''
    assert get_stop(int(stopID)) is not None
    data_url = "https://transport.orgp.spb.ru/\
Portal/transport/internalapi/forecast/bystop?stopID="+str(stopID)
    d = requests.get(data_url)
    if d.status_code != 200:
        raise ValueError
    forecast_json = d.content
    return json.loads(forecast_json)


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
                         context: CallbackContext) -> None:
        assert update.effective_chat is not None
        context.bot.send_message(text=self.message,
                                 parse_mode='markdown',
                                 chat_id=update.effective_chat.id,
                                 reply_markup=self.kbd)


class StartMsgBlock(MsgBlock):
    """Welcome message"""
    def __init__(self):
        super(MsgBlock, self).__init__()
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


def make_keyboard(items, columns=5):
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
                         context: CallbackContext) -> None:
        assert update.message is not None
        assert update.message.text is not None
        assert update.message.text.startswith('/stop_')
        stop_id = int(update.message.text.replace('/stop_', ''))
        self.message, self.kbd = self.form_message(stop_id)
        super().send_new_message(update, context)

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
        assert update.effective_chat is not None
        params = update.callback_query.data.split()
        assert params[0] == 'BusStopMsgBlock'
        if params[1] == 'get_route':
            from bot import send_route_info
            send_route_info(update.effective_chat.id,
                            context, int(params[2]), int(params[3]))


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
                         context: CallbackContext) -> None:
        assert update.message is not None
        assert update.message.location is not None

        self.message, self.kbd = self.form_message(
            update.message.location.latitude,
            update.message.location.longitude
            )
        super().send_new_message(update, context)


class RouteMsgBlock(MsgBlock):
    """Route stops list"""
    def form_message(self,
                     route_id: int,
                     direction: int) -> Tuple[str, InlineKeyboardMarkup]:
        msg = '_Остановки маршрута:_\n'
        msg += '*' + get_route(route_id).route_long_name + '*\n'
        msg += ('_Обратное' if direction else '_Прямое') + ' направление_\n'
        msg += '\n'
        stops = get_stops_by_route(route_id, direction)
        for s in stops:
            msg += '/stop\\_' + str(s) + ': '
            msg += get_stop(s).stop_name + '\n'
        msg += '\n'
        msg += ('_Прямое' if direction else '_Обратное') + ' направление_: '
        msg += f'/route\\_{route_id}\\_{1-direction}\n'
        return msg, InlineKeyboardMarkup([[]])

    def send_new_message(self,
                         update: Update,
                         context: CallbackContext) -> None:
        assert update.message is not None
        assert update.message.text is not None

        route_id, direction = map(
            int,
            update.message.text.replace('/route_', '').split('_')
            )
        self.message, self.kbd = self.form_message(route_id, direction)
        super().send_new_message(update, context)


stop_msgblock = BusStopMsgBlock()
test_block = MsgBlock()
nearest_stops_msgblock = NearestStopsMsgBlock()
route_msgblock = RouteMsgBlock()
start_msg_msgblock = StartMsgBlock()
