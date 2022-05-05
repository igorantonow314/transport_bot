# [@PiterBusBot](https://t.me/PiterBusBot)

Телеграм бот, позволяющий смотреть прогноз прибытия транспорта в Питере в режиме реального времени.

Попробовать: [@PiterBusBot](https://t.me/PiterBusBot)


## Установка
Должен быть установлен `python 3.7+`.

```bash
$ git clone https://github.com/igorantonow314/transport_bot
$ cd transport_bot
$ make install
```
Опционально:
установить libspatialindex-dev для ускорения поиска ближайших остановок (для rtree, см. https://github.com/Toblerity/rtree/issues/64)
```bash
$ sudo apt install libspatialindex-dev python-rtree
```

## Запуск
```bash
$ cd transport_bot
$ python __main__.py
```

Логи по-умолчанию записываются в `bot.log`.

## Источники

_Данные о транспорте получены благодаря:_
 [Экосистеме городских сервисов «Цифровой Петербург»](https://petersburg.ru),
 [Порталу общественного транспорта
Санкт-Петербурга](https://transport.orgp.spb.ru)
