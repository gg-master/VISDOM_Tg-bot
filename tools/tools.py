import argparse
import base64


def create_token(token):
    return str(base64.b64encode(token.encode("utf-8")))[2:-1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-T', '--token',
                        help='convert a token into an encrypted token')

    args = parser.parse_args()
    if args.token:
        print(create_token(args.token))
