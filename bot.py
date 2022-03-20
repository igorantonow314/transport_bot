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



def nearest_stops(update: Update, context: CallbackContext):
    stops = get_nearest_stops(update.message.location.latitude,
                              update.message.location.longitude)
    msg = '\n'.join([str(i) + ": " + get_stop(i).stop_name for i in stops])
    update.message.reply_text(msg)

updater.dispatcher.add_handler(MessageHandler(Filters.location, nearest_stops))


updater.start_polling()
