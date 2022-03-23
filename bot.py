from telegram.ext.updater import Updater
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters
from telegram.ext import CallbackQueryHandler
from database import (
    get_route,
    get_stop,
    get_random_stop_id,
    get_stops_by_route,
)
from message_blocks import (
    stop_msgblock,
    test_block,
    nearest_stops_msgblock,
    route_msgblock,
    start_msg_msgblock,
)

from bot_conf import BOT_TOKEN

# BOT_TOKEN = 'blablabla' # please replace by yours
TRANSPORT_TYPE_EMOJI = {'bus': '🚌', 'trolley': '🚎',
                        'tram': '🚊', 'ship': '🚢'}


def send_stop_info(update: Update, context: CallbackContext, stop_id: int):
    msg, kbd = stop_msgblock.form_message(stop_id)
    update.message.reply_text(msg, parse_mode='markdown', reply_markup=kbd)


def nevskii_command_handler(update: Update, context: CallbackContext):
    '''
    Forecast for Nevskii prospect stop
    '''
    send_stop_info(update, context, stop_id=15495)


def random_stop(update: Update, context: CallbackContext):
    send_stop_info(update, context, get_random_stop_id())


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
            context.bot.send_message(text='ok',
                                     chat_id=update.effective_chat.id)
    if query_text.startswith('btn'):
        test_block.callback_handler(update, context)
    if query_text.startswith('BusStopMsgBlock'):
        stop_msgblock.callback_handler(update, context)
    query.answer()


updater = Updater(token=BOT_TOKEN, use_context=True)


def start_bot():
    handlers = [
        CommandHandler('start', start_msg_msgblock.send_new_message),
        CommandHandler('nevskii', nevskii_command_handler),
        CommandHandler('random_stop', random_stop),
        MessageHandler(Filters.location,
                       nearest_stops_msgblock.send_new_message),
        MessageHandler(Filters.regex('/stop_([0-9])+'),
                       stop_msgblock.send_new_message),
        MessageHandler(Filters.regex('/route_([0-9])+_[0-1]'),
                       route_msgblock.send_new_message),
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
