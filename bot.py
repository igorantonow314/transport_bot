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
    # msg += '_Посмотреть маршруты:_\n'
    # for i in routes:
    #     msg += TRANSPORT_TYPE_EMOJI[get_route(i).transport_type]
    #     msg += get_route(i).route_short_name.ljust(3) + '    '
    #     msg += '/route\\_' + str(route_id) + '\\_'
    #     msg += str(get_direction_by_stop(stop_id, route_id)) + '\n'
    return msg


def stop_info(stop_id):
    '''
    :result: human-readable arrival time forecast for the stop
    in markdown format
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
    reply_markup = make_buttons_with_routes(forecast_json, stop_id)
    return msg, reply_markup


def make_buttons_with_routes(forecast_json, stop_id):
    routes = [int(p['routeId']) for p in forecast_json['result']]
    routes = set(routes)
    keyboard = []
    l5 = []
    for route_id in routes:
        l5.append(InlineKeyboardButton(
            TRANSPORT_TYPE_EMOJI[get_route(route_id).transport_type]
            + get_route(route_id).route_short_name,
            callback_data='/route_' + str(route_id) + '_'
                          +str(get_direction_by_stop(stop_id, route_id))
            ))
        if len(l5) >= 5:
            keyboard.append(l5)
            l5 = []
    if len(l5) > 0:
        for i in range(5 - len(l5)):
            l5.append(InlineKeyboardButton(' ', callback_data='/test'))
    keyboard.append(l5)
    return InlineKeyboardMarkup(keyboard)


def send_stop_info(update: Update, context: CallbackContext, stop_id=None):
    if not stop_id:
        stop_id = int(update.message.text.replace('/stop_', ''))
    msg, reply_markup = stop_info(stop_id)
    update.message.reply_text(msg, parse_mode='markdown',
                              reply_markup=reply_markup)


def nevskii(update: Update, context: CallbackContext):
    '''
    Forecast for Nevskii prospect stop
    '''
    msg = stop_info(15495)
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg,
                             parse_mode='markdown')


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


def send_route_info(update: Update, context: CallbackContext):
    route_id, direction = map(int, update.message.text
                                   .replace('/route_', '')
                                   .split('_'))
    update.message.reply_text(route_info(route_id, direction),
                              parse_mode='markdown')


def send_routes_buttons(update: Update, context: CallbackContext): # routes: list[int], chat_id):
    keyboard = [
        [
            InlineKeyboardButton("Option 1", callback_data='1'),
            InlineKeyboardButton("Option 2", callback_data='2'),
        ],
        [InlineKeyboardButton("Option 3", callback_data='3')],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Please choose:', reply_markup=reply_markup)


def button(update: Update, context: CallbackContext) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    query_text = str(query.data)
    print(query_text)
    if query_text.startswith('/'):
        if query_text.startswith('/route_'):
            route_id, direction = map(int, query_text
                                           .replace('/route_', '')
                                           .split('_'))
            context.bot.send_message(text=route_info(route_id, direction),
                              chat_id=update.effective_chat.id,
                              parse_mode='markdown')
        if query_text == '/test':
            context.bot.send_message(text='ok', chat_id=update.effective_chat.id)
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()

    # context.bot.send_message(chat_id=update.effective_chat.id, text=f"Selected option: {query.data}")


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
        CommandHandler('nevskii', nevskii),
        CommandHandler('random_stop', random_stop),
        MessageHandler(Filters.location, nearest_stops),
        MessageHandler(Filters.regex('/stop_([0-9])+'), send_stop_info),
        MessageHandler(Filters.regex('/route_([0-9])+_[0-1]'),
                       send_route_info),
        CommandHandler('test', send_routes_buttons),
        CallbackQueryHandler(button),
    ]
    for h in handlers:
        updater.dispatcher.add_handler(h)

    updater.start_polling()


def stop_bot():
    updater.stop()


if __name__ == '__main__':
    start_bot()
