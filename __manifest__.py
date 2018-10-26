# -*- coding: utf-8 -*-
{
    'name': '1000i Import CSV Bank Statements',
    'category': 'Accounting',

    'author': "1000ideas",
    'website': "https://1000i.pl",

    'version': '0.3',

    # any module necessary for this one to work correctly
    #
    'depends': ['account_bank_statement_import'],

    # always loaded
    'data': [
        'wizards/account_bank_statement_import_csv_view.xml',
    ],
}
