import pandas as pd
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
