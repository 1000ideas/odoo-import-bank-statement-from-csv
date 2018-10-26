# -*- coding: utf-8 -*-
# vim: sw=4:ts=4:expandtab
# pylint: disable=invalid-name
"""

"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from operator import itemgetter


def date_func(trxn):
    tag = trxn[1]
    return '{}/{}/{}'.format(tag[3:5], tag[:2], tag[-4:])


mapping = {
    'is_split': False,
    'has_header': False,
    'currency': 'PLN',
    'language': 'PL',
    'delimiter': ',',
    'account': 'Bank',
    'date': date_func,
    'type': 'Bank',
    'amount': lambda r: r[5].replace('.', '').replace(',', '.'),
    'desc': itemgetter(3),
    'payee': itemgetter(2),
}
