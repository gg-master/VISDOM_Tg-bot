import os
import base64
import logging
import argparse

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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-T', '--token',
                        help='convert a token into an encrypted token')

    args = parser.parse_args()
    if args.token:
        print(create_token(args.token))
