from typing import Tuple

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext


class MsgBlock:
    """Class for managing messages with inline buttons"""
    def __init__(self):
        self.message = 'This is message for testing'

    def form_message(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        :result: tuple of:
        - message in markdown format
        - InlineKeyboardMarkup
        """
        kbd = InlineKeyboardMarkup([
                 [InlineKeyboardButton('Button 1', callback_data='btn1')],
                 [
                     InlineKeyboardButton('Button 2', callback_data='btn2'),
                     InlineKeyboardButton('Button 3', callback_data='btn3'),
                 ]
            ])
        return (self.message, kbd)

    def callback_handler(self, update: Update) -> None:
        assert update.callback_query is not None
        assert update.callback_query.message is not None
        button = str(update.callback_query.data)
        update.callback_query.message.edit_text('Choosed button: ' + button)
        update.callback_query.answer()

    def send_new_message(self,
                         update: Update,
                         context: CallbackContext) -> None:
        assert update.effective_chat is not None
        msg, kbd = self.form_message()
        context.bot.send_message(text=msg,
                                 parse_mode='markdown',
                                 chat_id=update.effective_chat.id,
                                 reply_markup=kbd)


test_block = MsgBlock()
