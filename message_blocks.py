from typing import Tuple

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext


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

    def form_message(self, update: Update) -> Tuple[str, InlineKeyboardMarkup]:
        """
        :result: tuple of:
        - message in markdown format
        - InlineKeyboardMarkup
        """
        return (self.message, self.kbd)

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
        msg, kbd = self.form_message(update)
        context.bot.send_message(text=msg,
                                 parse_mode='markdown',
                                 chat_id=update.effective_chat.id,
                                 reply_markup=kbd)


class StopMsgBlock(MsgBlock):
    """Message with forecast for the stop"""
    def __init__(self):
        super(StopMsgBlock, self).__init__()

    def form_message(self, update: Update) -> Tuple[str, InlineKeyboardMarkup]:
        from bot import stop_info, TRANSPORT_TYPE_EMOJI, make_keyboard
        from database import get_route, get_direction_by_stop

        assert update.message is not None
        assert update.message.text is not None
        assert update.message.text.startswith('/stop_')
        stop_id = int(update.message.text.replace('/stop_', ''))
        self.message, forecast_json = stop_info(stop_id)
        rl = [int(p['routeId']) for p in forecast_json['result']]
        routes = set(rl)
        s = []
        for route_id in routes:
            s.append((
                TRANSPORT_TYPE_EMOJI[get_route(route_id).transport_type]
                + get_route(route_id).route_short_name,

                'StopMsgBlock get_route ' + str(route_id) + ' '
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
        assert params[0] == 'StopMsgBlock'
        if params[1] == 'get_route':
            from bot import send_route_info
            send_route_info(update.effective_chat.id,
                            context, int(params[2]), int(params[3]))


class NearestStopsMsgBlock(MsgBlock):
    """Stops behind sended location"""
    def form_message(self, update: Update) -> Tuple[str, InlineKeyboardMarkup]:
        assert update.message is not None
        assert update.message.location is not None

        from bot import TRANSPORT_TYPE_EMOJI
        from database import get_nearest_stops, get_stop

        stops = get_nearest_stops(update.message.location.latitude,
                                  update.message.location.longitude, n=10)
        msg = '*Ближайшие остановки:*\n'
        for i in stops:
            msg += (('/stop\\_'+str(i) + ": ").ljust(13)
                    + TRANSPORT_TYPE_EMOJI[get_stop(i).transport_type]
                    + get_stop(i).stop_name
                    )
            msg += '\n'
        return msg, InlineKeyboardMarkup([[]])


stop_msgblock = StopMsgBlock()
test_block = MsgBlock()
nearest_stops_msgblock = NearestStopsMsgBlock()
