import pandas as pd
from random import choice
import zipfile
import requests
import os


def update_feed():
    URL = 'http://transport.orgp.spb.ru/Portal/transport/internalapi/gtfs/feed.zip'
    with open('feed.zip', 'wb') as f:
        r = requests.get(URL)
        f.write(r.content)
        f.close()
    with zipfile.ZipFile('feed.zip') as z:
        z.extractall('feed')
    os.remove('feed.zip')


if not (os.path.exists('feed/routes.txt')
        and os.path.exists('feed/stops.txt')):
    print('downloading files...')
    update_feed()
route_df = pd.read_csv('feed/routes.txt')
stop_df = pd.read_csv('feed/stops.txt')


def get_route(route_id: int):
    r = route_df[route_df.route_id == route_id]
    if len(r) == 0:
        return None
    return r.iloc[0]


def get_random_stop_id():
    return choice(stop_df.stop_id)


def get_stop(stop_id: int):
    r = stop_df[stop_df.stop_id == stop_id]
    if len(r) == 0:
        return None
    return r.iloc[0]
