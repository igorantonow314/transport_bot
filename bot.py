import requests
import json

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext


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
        msg += ('автобус/троллейбус № ' + str(p['orderNumber'])
                + ' прибудет в ' + p['arrivingTime'].split()[1]
                + '\n')
    return msg


def nevskii(update: Update, context: CallbackContext):
    forecast_json = get_forecast_by_stop(15495)
    msg = forecast_json_to_text(forecast_json)
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


nevs_handler = CommandHandler('nevskii', nevskii)
dispatcher.add_handler(nevs_handler)


updater.start_polling()
