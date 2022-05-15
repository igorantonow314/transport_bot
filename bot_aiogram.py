import logging

from aiogram import (
    Bot,
    Dispatcher,
    executor,
    types,
)
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from bot_conf import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def start_message(message: types.Message):
    text = '''Привет!
Этот бот покажет тебе время прибытия транспорта на любую остановку.

🚩 отправь *местоположение*, чтобы найти ближайшие остановки

🔎 чтобы *найти остановку по названию*, просто напиши название

🚌 можно посмотреть маршрут транспорта, который подходит к остановке

🎲 можно посмотреть случайную остановку: 👉 /random\\_stop

_Данные о транспорте получены благодаря:_
[Экосистеме городских сервисов «Цифровой Петербург»](https://petersburg.ru)
[Порталу общественного транспорта\
 Санкт-Петербурга](https://transport.orgp.spb.ru)

**Контакты:**
@igorantonow
Сообщайте обо всех багах, пишите любые предложения по изменению\
 дизайна, функционала и т.п.
'''
    kbd = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton('Остановка "метро Невский проспект"',
                             callback_data='BusStopMsgBlock newmsg 15495')
    ]])
    await message.answer(
        text,
        reply_markup=kbd,
        parse_mode='markdown')


def start_bot():
    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    start_bot()
