import logging

from aiogram import (
    Bot,
    Dispatcher,
    executor,
    types,
)

from bot_conf import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def start_message(message: types.Message):
    button = types.InlineKeyboardButton('test', callback_data='test data')
    b2 = types.InlineKeyboardButton('t2', callback_data='t2')
    ikm = types.InlineKeyboardMarkup(row_width=1,
                                     inline_keyboard=[[button, b2]])
    await message.reply('hi', reply_markup=ikm)


@dp.callback_query_handler(lambda x: x.data.startswith('test'))
async def callback_handler(call: types.CallbackQuery):
    await call.message.edit_text(call.data)
    await start_message(call.message)
    await call.answer()


@dp.callback_query_handler(lambda x: True)
async def log_callback(call: types.CallbackQuery):
    await call.message.reply(f'requested callback with data: {call.data}')


def start_bot():
    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    start_bot()
