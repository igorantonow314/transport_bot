import requests
import json

from telegram.ext.updater import Updater
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters
from telegram.ext import CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import (
    get_route,
    get_stop,
    get_random_stop_id,
    get_nearest_stops,
    get_stops_by_route,
    get_direction_by_stop,
)
from message_blocks import test_block

from bot_conf import BOT_TOKEN

# BOT_TOKEN = 'blablabla' # please replace by yours
TRANSPORT_TYPE_EMOJI = {'bus': '🚌', 'trolley': '🚎',
                        'tram': '🚊', 'ship': '🚢'}


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


def send_routes_buttons(context: CallbackContext, chat_id, forecast_json, stop_id):
    routes = [int(p['routeId']) for p in forecast_json['result']]
    routes = set(routes)
    s = []
    for route_id in routes:
        s.append((
            TRANSPORT_TYPE_EMOJI[get_route(route_id).transport_type]
            + get_route(route_id).route_short_name,

            '/route_' + str(route_id) + '_'
            +str(get_direction_by_stop(stop_id, route_id))
            ))
    context.bot.send_message(text='Маршруты:',
        chat_id = chat_id,
        reply_markup=make_keyboard(s))


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


def send_stop_info(update: Update, context: CallbackContext, stop_id=None):
    if not stop_id:
        stop_id = int(update.message.text.replace('/stop_', ''))
    msg, forecast_json = stop_info(stop_id)
    update.message.reply_text(msg, parse_mode='markdown')
    send_routes_buttons(context, update.effective_chat.id, forecast_json, stop_id)


def nevskii_command_handler(update: Update, context: CallbackContext):
    '''
    Forecast for Nevskii prospect stop
    '''
    send_stop_info(update, context, stop_id=15495)


def random_stop(update: Update, context: CallbackContext):
    send_stop_info(update, context, get_random_stop_id())


def nearest_stops(update: Update, context: CallbackContext):
    stops = get_nearest_stops(update.message.location.latitude,
                              update.message.location.longitude, n=10)
    msg = '*Ближайшие остановки:*\n'
    for i in stops:
        msg += (('/stop\\_'+str(i) + ": ").ljust(13)
                + TRANSPORT_TYPE_EMOJI[get_stop(i).transport_type]
                + get_stop(i).stop_name
                )
        msg += '\n'
    update.message.reply_text(msg, parse_mode='markdown')


def route_info(route_id: int, direction: int):
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
    return msg


def route_command_handler(update: Update, context: CallbackContext):
    route_id, direction = map(int, update.message.text
                                   .replace('/route_', '')
                                   .split('_'))
    send_route_info(update.effective_chat.id, context, route_id, direction)


def send_route_info(chat_id, context: CallbackContext, route_id, direction):
    context.bot.send_message(text=route_info(route_id, direction),
                             chat_id=chat_id,
                             parse_mode='markdown')


def callback_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query_text = str(query.data)
    if query_text.startswith('/'):
        if query_text.startswith('/route_'):
            route_id, direction = map(int, query_text
                                           .replace('/route_', '')
                                           .split('_'))
            send_route_info(update.effective_chat.id, context,
                            route_id, direction)
        if query_text == '/test':
            context.bot.send_message(text='ok', chat_id=update.effective_chat.id)
    if query_text.startswith('btn'):
        test_block.callback_handler(update)
    query.answer()


def start_message(update: Update, context: CallbackContext):
    msg = '''Привет!
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
    update.message.reply_text(msg, parse_mode='markdown')


updater = Updater(token=BOT_TOKEN, use_context=True)


def start_bot():
    handlers = [
        CommandHandler('start', start_message),
        CommandHandler('nevskii', nevskii_command_handler),
        CommandHandler('random_stop', random_stop),
        MessageHandler(Filters.location, nearest_stops),
        MessageHandler(Filters.regex('/stop_([0-9])+'), send_stop_info),
        MessageHandler(Filters.regex('/route_([0-9])+_[0-1]'),
                       route_command_handler),
        CallbackQueryHandler(callback_handler),
        CommandHandler('test', test_block.send_new_message)
    ]
    for h in handlers:
        updater.dispatcher.add_handler(h)

    updater.start_polling()


def stop_bot():
    updater.stop()


if __name__ == '__main__':
    start_bot()
