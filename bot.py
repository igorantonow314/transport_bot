from telegram.ext.updater import Updater
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters
from telegram.ext import CallbackQueryHandler
import logging

from data import get_random_stop_id
from message_blocks import (
    stop_msgblock,
    test_block,
    nearest_stops_msgblock,
    route_msgblock,
    start_msg_msgblock,
)

from bot_conf import BOT_TOKEN

# BOT_TOKEN = 'blablabla' # please replace by yours

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TRANSPORT_TYPE_EMOJI = {'bus': '🚌', 'trolley': '🚎',
                        'tram': '🚊', 'ship': '🚢'}


def send_stop_info(update: Update, context: CallbackContext, stop_id: int):
    logger.info('send_stop_info usage')
    assert update.message is not None    # It is always correct, isn't it?
    msg, kbd = stop_msgblock.form_message(stop_id)
    update.message.reply_text(msg, parse_mode='markdown', reply_markup=kbd)


def nevskii_command_handler(update: Update, context: CallbackContext):
    '''
    Forecast for Nevskii prospect stop
    '''
    logger.info('/nevskii command handler')
    send_stop_info(update, context, stop_id=15495)


def random_stop(update: Update, context: CallbackContext):
    logger.info('/random_stop command handler')
    send_stop_info(update, context, get_random_stop_id())


def callback_handler(update: Update, context: CallbackContext) -> None:
    logger.info('callback recieved')
    assert update.callback_query is not None
    assert update.effective_chat is not None   # It is always true, isn't it?
    query = update.callback_query
    query_text = str(query.data)

    if query_text.startswith('common'):
        if query_text == 'common delete_me':
            logger.info('callback: common delete_me')
            assert update.callback_query.message is not None
            update.callback_query.message.delete()
            query.answer()
        else:
            raise ValueError(f'Unknown callback: {query_text}')

    elif query_text.startswith('BusStopMsgBlock'):
        logger.info('callback: BusStopMsgBlock')
        stop_msgblock.callback_handler(update, context)
    elif query_text.startswith('RouteMsgBlock'):
        logger.info('callback: RouteMsgBlock')
        route_msgblock.callback_handler(update, context)
    else:
        raise ValueError(f'Unknown callback: {query_text}')


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log')
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
    print('bot started')
    logger.info('Bot started')


def stop_bot():
    updater.stop()


if __name__ == '__main__':
    start_bot()
