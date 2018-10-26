# Copyright 2015 Odoo S. A.
# Copyright 2015 Laurent Mignon <laurent.mignon@acsone.eu>
# Copyright 2015 Ronald Portier <rportier@therp.nl>
# Copyright 2016-2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import csv
import itertools as it

from odoo.addons.account_bank_statement_import_csv_ideas.libs.mappings.santander import mapping
from csv2ofx import utils
from csv2ofx.qif import QIF
from csv2ofx.ofx import OFX

from tabutils.io import read_csv, IterStringIO

import dateutil.parser

from odoo.tools.translate import _
from odoo import api, models
from odoo.exceptions import UserError


class customQif(QIF):
    def gen_body(self, data):
        """ Generate the QIF body """
        split_account = self.split_account or self.inv_split_account

        for datum in data:
            trxn_data = self.transaction_data(datum['trxn'])
            account = self.account(datum['trxn'])
            grp = datum['group']

            if self.prev_group and self.prev_group != grp and self.is_split:
                yield self.transaction_end()

            if (self.is_split and datum['is_main']) or not self.is_split:
                yield self.transaction(**trxn_data)
                self.prev_account = account

            if (self.is_split and not datum['is_main']) or split_account:
                yield self.split_content(**trxn_data)

            if not self.is_split:
                yield self.transaction_end()

            self.prev_group = grp


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    @api.model
    def _check_csv(self, data_file):
        data = data_file.decode('utf-8')
        records = csv.reader(data.splitlines())
        header_line = next(records, None)
        return len(header_line) == 9

    @api.model
    def _check_qif(self, data_file):
        return data_file.strip().startswith(b'!Type:')

    def _parse_file(self, data_file):
        if not self._check_csv(data_file):
            return super(AccountBankStatementImport, self)._parse_file(data_file)
        # try:
        data = data_file.decode('utf-8')
        records = csv.reader(data.splitlines())
        next(records, None)

        qif = customQif(mapping, def_type='Bank')
        groups = qif.gen_groups(records)
        trxns = qif.gen_trxns(groups)
        cleaned_trxns = qif.clean_trxns(trxns)
        qif_data = utils.gen_data(cleaned_trxns)
        content = it.chain([qif.gen_body(qif_data), qif.footer()])

        for line in IterStringIO(content):
            return self._parse_qif_file(line)

    def _parse_qif_file(self, data_file):
        if not self._check_qif(data_file):
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)
        try:
            file_data = data_file.decode()
            if '\r' in file_data:
                data_list = file_data.split('\r')
            else:
                data_list = file_data.split('\n')
            header = data_list[0].strip()
            header = header.split(":")[1]
        except:
            raise UserError(_('Could not decipher the QIF file.'))
        transactions = []
        vals_line = {}
        total = 0
        if header in ("Bank", "CCard"):
            vals_bank_statement = {}
            for line in data_list:
                line = line.strip()
                if not line:
                    continue
                if line[0] == 'D':  # date of transaction
                    vals_line['date'] = dateutil.parser.parse(
                        line[1:], fuzzy=True).date()
                elif line[0] == 'T':  # Total amount
                    total += float(line[1:].replace(',', ''))
                    vals_line['amount'] = float(line[1:].replace(',', ''))
                elif line[0] == 'N':  # Check number
                    vals_line['ref'] = line[1:]
                elif line[0] == 'P':  # Payee
                    vals_line['name'] = (
                        'name' in vals_line and
                        line[1:] + ': ' + vals_line['name'] or line[1:]
                    )
                elif line[0] == 'M':  # Memo
                    vals_line['name'] = ('name' in vals_line and
                                         vals_line['name'] + ': ' + line[1:] or
                                         line[1:])
                elif line[0] == '^' and vals_line:  # end of item
                    transactions.append(vals_line)
                    vals_line = {}
                elif line[0] == '\n':
                    transactions = []
                else:
                    pass
        else:
            raise UserError(_('This file is either not a bank statement or is '
                              'not correctly formed.'))
        vals_bank_statement.update({
            'balance_end_real': total,
            'transactions': transactions
        })
        return None, None, [vals_bank_statement]

    def _complete_stmts_vals(self, stmt_vals, journal_id, account_number):
        """Match partner_id if hasn't been deducted yet."""
        res = super(AccountBankStatementImport, self)._complete_stmts_vals(
            stmt_vals, journal_id, account_number,
        )
        # Since QIF doesn't provide account numbers (normal behaviour is to
        # provide 'account_number', which the generic module uses to find
        # the partner), we have to find res.partner through the name
        partner_obj = self.env['res.partner']
        for statement in res:
            for line_vals in statement['transactions']:
                if not line_vals.get('partner_id') and line_vals.get('name'):
                    name = line_vals['name']
                    title = None
                    names = line_vals['name'].split(': ')
                    if len(names) > 1:
                        name = names[1]
                        title = names[0]

                    partner = partner_obj.search(
                        [('name', 'ilike', name)], limit=1,
                    )
                    line_vals['partner_id'] = partner.id
        return res
