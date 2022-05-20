import json
import logging
import argparse

from aiogram import Bot, Dispatcher, executor, types, filters

logging.basicConfig(level=logging.INFO)


BOT_TOKEN = None
with open("../bot_conf.py", "r") as f:
    for line in f:
        if line.find("BOT_TOKEN") >= 0:
            assert line.startswith("BOT_TOKEN")
            assert line.count("'") == 2
            BOT_TOKEN = line.split("'")[1]
            break
    else:
        raise ValueError("Bot token not found")

SAVE_ALL = False
OUT_FILE = "saved_messages.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler()
async def log_message(message: types.Message):
    global SAVE_ALL
    print("Received message:")
    print(message)
    if SAVE_ALL or input("Save? [y]/n:").strip() in ["", "y"]:
        save_message(message)


def save_message(message: types.Message):
    msgs = []
    try:
        f = open(OUT_FILE, "r")
        msgs = json.loads(f.read())
    except FileNotFoundError:
        pass
    msgs.append(json.loads(str(message)))
    with open(OUT_FILE, "w") as f:
        f.write(json.dumps(msgs))


def print_messages():
    with open(OUT_FILE, "r") as f:
        msgs = json.loads(f.read())
        for i in msgs:
            print(types.Message(**i))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Save some messages for testing purposes, etc"
    )
    parser.add_argument("--list", action="store_true", help="print existing messages")
    parser.add_argument(
        "-a", action="store_true", help="save all messages without prompt"
    )
    parser.add_argument("--output", metavar="file", type=str, help="output file")
    args = parser.parse_args()
    if args.list:
        print_messages()
        exit()

    SAVE_ALL = args.a
    OUT_FILE = args.output
    executor.start_polling(dp, skip_updates=True)
