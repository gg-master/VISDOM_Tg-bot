import argparse
import base64
import logging
import os

from dotenv import load_dotenv


def create_token(token):
    return str(base64.b64encode(token.encode("utf-8")))[2:-1]


def get_from_env(item):
    try:
        path = os.path.join(os.getcwd(), '.env')
        if os.path.exists(path):
            load_dotenv(path)
        return base64.b64decode(os.environ.get(item)).decode('utf-8')
    except Exception as ex:
        logging.error(f'Probably not found .env file\nEXCEPTION: {ex}')
        exit(0)


def convert_tz(coords=None, tz_offset=None) -> str:
    from datetime import datetime, timedelta

    import pytz
    import timezonefinder

    now = datetime.now(pytz.utc)
    if coords and not tz_offset:
        lat, lon = coords
        tf = timezonefinder.TimezoneFinder()
        timezone = pytz.timezone(tf.certain_timezone_at(lat=lat, lng=lon))
        all_tz = list(
            {tz.zone for tz in map(pytz.timezone, pytz.all_timezones_set)
             if now.astimezone(tz).utcoffset() == now.astimezone(
                timezone).utcoffset() and tz.zone.startswith('Etc/')})
        return all_tz[0]
    else:
        utc_offset = timedelta(hours=int(tz_offset))
        all_tz = list(
            {tz.zone for tz in map(pytz.timezone, pytz.all_timezones_set)
             if now.astimezone(tz).utcoffset() == utc_offset
             and tz.zone.startswith('Etc/')})
        return all_tz[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-T', '--token',
                        help='convert a token into an encrypted token')

    args = parser.parse_args()
    if args.token:
        print(create_token(args.token))
