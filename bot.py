import requests
import json

from telegram.ext.updater import Updater
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters
from database import get_route, get_stop, get_random_stop_id, get_nearest_stops

from bot_conf import BOT_TOKEN

# BOT_TOKEN = 'blablabla' # please replace by yours


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


def forecast_json_to_text(forecast_json):
    '''
    Converts result of get_forecast_by_stop into human-readable form.
    '''
    assert forecast_json['success']
    msg = ''
    for p in forecast_json['result']:
        route_id = int(p['routeId'])
        route = get_route(route_id)
        TRANSLATION = {'bus': 'автобус', 'trolley': 'троллейбус',
                       'tram': 'трамвай', 'ship': 'аквабус'}
        msg += (TRANSLATION[route.transport_type] + ' № '
                + route.route_short_name
                + ' прибудет в ' + p['arrivingTime'].split()[1]
                + '\n')
    return msg


def stop_info(stop_id):
    '''
    :result: human-readable arrival time forecast for the stop
    in markdown format
    '''
    forecast_json = get_forecast_by_stop(stop_id)
    msg = '*Остановка: ' + get_stop(stop_id).stop_name + '*\n'
    msg += forecast_json_to_text(forecast_json)
    msg += 'Обновить: /stop\\_' + str(stop_id)
    return msg


def send_stop_info(update: Update, context: CallbackContext):
    stop_id = int(update.message.text.replace('/stop_', ''))
    update.message.reply_text(stop_info(stop_id), parse_mode='markdown')


def nevskii(update: Update, context: CallbackContext):
    '''
    Forecast for Nevskii prospect stop
    '''
    msg = stop_info(15495)
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg,
                             parse_mode='markdown')


def random_stop(update: Update, context: CallbackContext):
    msg = stop_info(get_random_stop_id())
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg,
                             parse_mode='markdown')


def nearest_stops(update: Update, context: CallbackContext):
    stops = get_nearest_stops(update.message.location.latitude,
                              update.message.location.longitude, n=10)
    msg = '\n'.join(['/stop\\_'+str(i) + ": " + get_stop(i).stop_name for i in stops])
    update.message.reply_text(msg, parse_mode='markdown')



if __name__ == '__main__':
    updater = Updater(token=BOT_TOKEN, use_context=True)

    updater.dispatcher.add_handler(CommandHandler('nevskii', nevskii))
    updater.dispatcher.add_handler(CommandHandler('random_stop', random_stop))
    updater.dispatcher.add_handler(MessageHandler(Filters.location, nearest_stops))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex('/stop_([0-9])+'), send_stop_info))

    updater.start_polling()
