import requests
import json

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

from helper import get_route, get_stop, get_random_stop_id

BOT_TOKEN = 'blablabla' # please replace by yours

updater = Updater(token=BOT_TOKEN, use_context=True)

dispatcher = updater.dispatcher


def get_forecast_by_stop(stopID):
    data_url = "https://transport.orgp.spb.ru/\
Portal/transport/internalapi/forecast/bystop?stopID="+str(stopID)
    d = requests.get(data_url)
    if d.status_code != 200:
        raise ValueError
    forecast_json = d.content
    return json.loads(forecast_json)


def forecast_json_to_text(forecast_json):
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
    forecast_json = get_forecast_by_stop(stop_id)
    msg = '*Остановка: ' + get_stop(stop_id).stop_name + '*\n'
    msg += forecast_json_to_text(forecast_json)
    return msg


def nevskii(update: Update, context: CallbackContext):
    msg = stop_info(15495)
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg,
                             parse_mode='markdown')


nevs_handler = CommandHandler('nevskii', nevskii)
dispatcher.add_handler(nevs_handler)


def random_stop(update: Update, context: CallbackContext):
    msg = stop_info(get_random_stop_id())
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg,
                             parse_mode='markdown')


random_stop_handler = CommandHandler('random_stop', random_stop)
dispatcher.add_handler(random_stop_handler)


updater.start_polling()
