from argparse import ArgumentParser
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG

lg = getLogger('wonambi')


def main():
    parser = ArgumentParser(prog='won_convert',
                            description='Convert data from one known format to another format')
    parser.add_argument('-v', '--version', action='store_true',
                        help='Return version')
    parser.add_argument('-l', '--log', default='info',
                        help='Logging level: info (default), debug')

    args = parser.parse_args()

    DATE_FORMAT = '%H:%M:%S'
    if args.log[:1].lower() == 'i':
        lg.setLevel(INFO)
        FORMAT = '{asctime:<10}{message}'

    elif args.log[:1].lower() == 'd':
        lg.setLevel(DEBUG)
        FORMAT = '{asctime:<10}{levelname:<10}{filename:<40}(l. {lineno: 6d})/ {funcName:<40}: {message}'

    formatter = Formatter(fmt=FORMAT, datefmt=DATE_FORMAT, style='{')
    handler = StreamHandler()
    handler.setFormatter(formatter)

    lg.handlers = []
    lg.addHandler(handler)
