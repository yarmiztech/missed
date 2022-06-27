# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time
from datetime import datetime, timedelta
from odoo.tools.translate import _
import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dt
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class FreightDiscountConfig(models.Model):
    _name = 'freight.disc.config'

    name = fields.Char('Name')

    # charge = fields.Float('Amount')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'freight.disc.config') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('freight.disc.config') or _('New')
        return super(FreightDiscountConfig, self).create(vals)


class FreightDiscount(models.Model):
    _name = 'freight.disc'
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    freight_lines = fields.One2many('freight.disc.lines', 'freight_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    creates_date = fields.Date(string='Create Date',  required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'freight.disc') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('freight.disc') or _('New')
        return super(FreightDiscount, self).create(vals)

    # def action_post(self):
    #         self.write({'state': 'done'})
    #         for line in self.freight_lines:
    #             j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0].id
    #
    #             pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
    #                                                          'amount': line.amount,
    #                                                          'partner_type': 'customer',
    #                                                          'payment_type': 'inbound',
    #                                                          'payment_method_id': j,
    #                                                          'journal_id': line.journal_id.id,
    #                                                          'ref': line.freight.name,
    #                                                          # 'invoice_ids': [(6, 0, line.invoice_id.ids)]
    #                                                          })
    #             pay_id.action_post()
    #             pay_id.action_cash_book()
    #             invoices = self.env['account.move'].search(
    #                 [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.company_id.id),
    #                  ('state', '!=', 'paid')])
    #             if invoices.mapped('residual'):
    #                 balance_amount = sum(invoices.mapped('residual'))
    #             else:
    #                 balance_amount = sum(invoices.mapped('amount_total'))
    #             balance_amount += self.env['partner.ledger.customer'].search(
    #                 [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
    #             balance_amount = self.env['partner.ledger.customer'].search(
    #                 [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)])[
    #                 -1].balance
    #             self.env['partner.ledger.customer'].sudo().create({
    #                 'date': datetime.today().date(),
    #                 'description': line.freight.name,
    #                 'partner_id': line.partner_id.id,
    #                 'company_id': self.company_id.id,
    #                 'account_journal': line.journal_id.id,
    #                 'account_move': pay_id.move_line_ids.mapped('move_id').id,
    #                 'credit': line.amount,
    #                 # 'debit': line.op_amount,
    #                 # 'balance': 0,
    #                 # 'executive_area': self.executive_areas.id or False,
    #                 # 'area': self.area.id or False,
    #                 # 'vehicle_id': self.estimate_ids[0].vahicle.id,
    #                 'balance':balance_amount-line.amount,
    #             })
    #
    #             # vals = {
    #             #     'journal_id': line.journal_id.id,
    #             #     'state': 'draft',
    #             #     'ref': line.freight.name
    #             # }
    #             # pay_id_list = []
    #             # move_id = self.env['account.move'].create(vals)
    #             # temp = (0, 0, {
    #             #     'account_id': line.journal_id.default_debit_account_id.id,
    #             #     'name': line.freight.name,
    #             #     'move_id': move_id.id,
    #             #     'date': self.create_date,
    #             #     'partner_id': line.partner_id.id,
    #             #     'debit': line.amount,
    #             #     'credit': 0,
    #             # })
    #             # pay_id_list.append(temp)
    #             #
    #             # temp = (0, 0, {
    #             #     'account_id': line.journal_id.payment_credit_account_id.id,
    #             #     'name': line.freight.name,
    #             #     'move_id': move_id.id,
    #             #     'date': self.create_date,
    #             #     # 'partner_id': self.partner_id.id,
    #             #     'debit': 0,
    #             #     'credit': line.amount,
    #             # })
    #             # pay_id_list.append(temp)
    #             # move_id.line_ids = pay_id_list
    #             # move_id.action_post()
    #             # if line.journal_id.type == 'cash':
    #             #     # complete = sum(self.env['account.move.line'].search([('journal_id', '=', acc.id)]).mapped('debit'))
    #             #     complete = sum(self.env['account.move.line'].search(
    #             #         [('company_id', '=', self.env.user.company_id.id), ('account_id', '=', line.journal_id.payment_credit_account_id.id)]).mapped(
    #             #         'debit'))
    #             #     debit = 0
    #             #     credit = line.amount
    #             #     complete_new = complete - credit
    #             #     acc = acc
    #             #     self.env['cash.book.info'].create({
    #             #         'date': self.create_date,
    #             #         'account_journal': line.journal_id.id,
    #             #         'account': acc.id,
    #             #         'partner_id': self.partner_id.id,
    #             #         'company_id': 1,
    #             #         'description': line.freight.name + ' ' + line.partner_id.name,
    #             #         'debit': debit,
    #             #         'credit': credit,
    #             #         'balance': complete_new
    #             #
    #             #     })
    #             #
    def action_post(self):
        self.write({'state': 'done'})
        for line in self.freight_lines:
            j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0].id

            # pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
            #                                              'amount': line.amount,
            #                                              'partner_type': 'customer',
            #                                              'payment_type': 'inbound',
            #                                              'payment_method_id': j,
            #                                              'journal_id': line.journal_id.id,
            #                                              'ref': line.freight.name,
            #                                              # 'invoice_ids': [(6, 0, line.invoice_id.ids)]
            #                                              })

            vals = {
                'journal_id': line.journal_id.id,
                'state': 'draft',
                'ref': line.partner_id.name + 'Freight/Charges'
            }
            pay_id_list = []
            move_id = self.env['account.move'].create(vals)
            partner_id = line.partner_id.id
            label = 'Freight/Charges' + '/' + line.partner_id.name

            # if self.type_of_partner == 'partner':
            #     if self.type_of_credit == False:

            acc = line.account_id
            temp = (0, 0, {
                'account_id': acc.id,
                'name': label,
                'move_id': move_id.id,
                'date': datetime.today().date(),
                'partner_id': line.partner_id.id,
                'debit': 0,
                'credit': line.amount,
            })
            pay_id_list.append(temp)
            temp = (0, 0, {
                'account_id': self.env['account.account'].search(
                    [('name', '=', 'Debtors'), ('company_id', '=', 1)]).id,
                'name': label,
                'move_id': move_id.id,
                'date': datetime.today().date(),
                'partner_id': line.partner_id.id,
                'debit': line.amount,
                'credit': 0,
            })
            pay_id_list.append(temp)

            move_id.line_ids = pay_id_list
            move_id.action_post()
            if line.journal_id.type == 'cash':
                if not self.env['cash.book.info'].search([]):
                    complete = sum(
                        self.env['account.move.line'].search([('journal_id', '=', line.journal_id.id)]).mapped(
                            'debit'))
                else:
                    complete = self.env['cash.book.info'].search([])[-1].balance

                debit = 0
                credit = 0
                complete_new = 0
                acc = self.env['account.account']
                # if self.payment_type == 'outbound':
                credit = line.amount
                complete_new = complete - credit
                acc = line.journal_id.payment_credit_account_id.id
                # if self.payment_type == 'inbound':
                #     debit = self.amount
                #     complete_new = complete + debit
                #     acc = self.journal_id.default_debit_account_id.id

                self.env['cash.book.info'].create({
                    'date': datetime.today().date(),
                    'account_journal': line.journal_id.id,
                    'partner_id': line.partner_id.id,
                    'company_id': 1,
                    # 'description': self.communication,
                    'description': line.partner_id.name,
                    'payment_type': 'outbound',
                    'partner_type': 'customer',
                    'debit': debit,
                    'credit': credit,
                    'account': acc,
                    # 'payment_id': self.id,
                    'balance': complete_new

                })

            # pay_id.action_post()
            # pay_id.action_cash_book()
            invoices = self.env['account.move'].search(
                [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.company_id.id),
                 ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                balance_amount = sum(invoices.mapped('amount_total'))
            balance_amount += self.env['partner.ledger.customer'].search(
                [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
            balance_amount = self.env['partner.ledger.customer'].search(
                [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)])[
                -1].balance
            self.env['partner.ledger.customer'].sudo().create({
                'date': datetime.today().date(),
                'description': line.freight.name,
                'partner_id': line.partner_id.id,
                'company_id': self.company_id.id,
                'account_journal': line.journal_id.id,
                'account_move': move_id.id,
                'credit': line.amount,
                # 'debit': line.op_amount,
                # 'balance': 0,
                # 'executive_area': self.executive_areas.id or False,
                # 'area': self.area.id or False,
                # 'vehicle_id': self.estimate_ids[0].vahicle.id,
                'balance': balance_amount - line.amount,
            })

            # vals = {
            #     'journal_id': line.journal_id.id,
            #     'state': 'draft',
            #     'ref': line.freight.name
            # }
            # pay_id_list = []
            # move_id = self.env['account.move'].create(vals)
            # temp = (0, 0, {
            #     'account_id': line.journal_id.default_debit_account_id.id,
            #     'name': line.freight.name,
            #     'move_id': move_id.id,
            #     'date': self.create_date,
            #     'partner_id': line.partner_id.id,
            #     'debit': line.amount,
            #     'credit': 0,
            # })
            # pay_id_list.append(temp)
            #
            # temp = (0, 0, {
            #     'account_id': line.journal_id.payment_credit_account_id.id,
            #     'name': line.freight.name,
            #     'move_id': move_id.id,
            #     'date': self.create_date,
            #     # 'partner_id': self.partner_id.id,
            #     'debit': 0,
            #     'credit': line.amount,
            # })
            # pay_id_list.append(temp)
            # move_id.line_ids = pay_id_list
            # move_id.action_post()
            # if line.journal_id.type == 'cash':
            #     # complete = sum(self.env['account.move.line'].search([('journal_id', '=', acc.id)]).mapped('debit'))
            #     complete = sum(self.env['account.move.line'].search(
            #         [('company_id', '=', self.env.user.company_id.id), ('account_id', '=', line.journal_id.payment_credit_account_id.id)]).mapped(
            #         'debit'))
            #     debit = 0
            #     credit = line.amount
            #     complete_new = complete - credit
            #     acc = acc
            #     self.env['cash.book.info'].create({
            #         'date': self.create_date,
            #         'account_journal': line.journal_id.id,
            #         'account': acc.id,
            #         'partner_id': self.partner_id.id,
            #         'company_id': 1,
            #         'description': line.freight.name + ' ' + line.partner_id.name,
            #         'debit': debit,
            #         'credit': credit,
            #         'balance': complete_new
            #
            #     })
            #


class FreightDiscountLines(models.Model):
    _name = 'freight.disc.lines'

    @api.model
    def _default_journal_id(self):
        return self.env['account.journal'].search(
            [('name', '=', 'Miscellaneous Operations'), ('company_id', '=', self.env.user.company_id.id)])

    freight_id = fields.Many2one('freight.disc')
    partner_id = fields.Many2one('res.partner', string='Partner', domain=[('estimator', '=', True)])
    freight = fields.Many2one('freight.disc.config', string='Discount/Charge', )
    amount = fields.Float('Amount')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade', default=_default_journal_id,
                                 help="This field is ignored in a bank statement reconciliation.")
    account_id = fields.Many2one('account.account', string='Account')

    @api.onchange('journal_id')
    def onchange_reason(self):
        if self.journal_id:
            expenses_accs = self.env['account.account'].search([('user_type_id.name', '=', 'Expenses')])
            return {'domain': {'account_id': [('id', 'in', expenses_accs.ids)]}}


class ExpensesDiscount(models.Model):
    _name = 'expenses.disc'
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    freight_lines = fields.One2many('expense.disc.lines', 'freight_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    creates_date = fields.Date(string='Create Date', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'expenses.disc') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('expenses.disc') or _('New')
        return super(ExpensesDiscount, self).create(vals)

    def action_post(self):
        self.write({'state': 'done'})
        for line in self.freight_lines:
            j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0].id

            # pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
            #                                              'amount': line.amount,
            #                                              'partner_type': 'customer',
            #                                              'payment_type': 'inbound',
            #                                              'payment_method_id': j,
            #                                              'journal_id': line.journal_id.id,
            #                                              'ref': line.freight.name,
            #                                              # 'invoice_ids': [(6, 0, line.invoice_id.ids)]
            #                                              })

            vals = {
                'journal_id': line.journal_id.id,
                'state': 'draft',
                'ref': line.reason
            }
            pay_id_list = []
            move_id = self.env['account.move'].create(vals)
            # partner_id = line.partner_id.id
            label = line.reason

            # if self.type_of_partner == 'partner':
            #     if self.type_of_credit == False:

            # acc = line.account_id
            temp = (0, 0, {
                # 'account_id': acc.id,
                'account_id': line.journal_id.payment_credit_account_id.id,
                'name': label,
                'move_id': move_id.id,
                'date': datetime.today().date(),
                # 'partner_id': line.partner_id.id,
                'debit': 0,
                'credit': line.amount,
            })
            pay_id_list.append(temp)
            temp = (0, 0, {
                'account_id': line.account_id.id,
                # 'account_id': self.env['account.account'].search(
                #     [('name', '=', 'Purchase Expense'), ('company_id', '=', 1)]).id,
                'name': label,
                'move_id': move_id.id,
                'date': datetime.today().date(),
                # 'partner_id': line.partner_id.id,
                'debit': line.amount,
                'credit': 0,
            })
            pay_id_list.append(temp)

            move_id.line_ids = pay_id_list
            move_id.action_post()
            if line.journal_id.type == 'cash':
                if not self.env['cash.book.info'].search([]):
                    complete = sum(
                        self.env['account.move.line'].search([('journal_id', '=', line.journal_id.id)]).mapped(
                            'debit'))
                else:
                    complete = self.env['cash.book.info'].search([])[-1].balance

                debit = 0
                credit = 0
                complete_new = 0
                acc = self.env['account.account']
                # if self.payment_type == 'outbound':
                credit = line.amount
                complete_new = complete - credit
                acc = line.journal_id.payment_credit_account_id.id
                # if self.payment_type == 'inbound':
                #     debit = self.amount
                #     complete_new = complete + debit
                #     acc = self.journal_id.default_debit_account_id.id

                self.env['cash.book.info'].create({
                    'date': datetime.today().date(),
                    'account_journal': line.journal_id.id,
                    # 'partner_id': line.partner_id.id,
                    'company_id': 1,
                    # 'description': self.communication,
                    'description': line.reason,
                    'payment_type': 'outbound',
                    'partner_type': 'customer',
                    'debit': debit,
                    'credit': credit,
                    'account': acc,
                    # 'payment_id': self.id,
                    'balance': complete_new

                })

            # pay_id.action_post()
            # pay_id.action_cash_book()
            # invoices = self.env['account.move'].search(
            #     [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.company_id.id),
            #      ('state', '!=', 'paid')])
            # if invoices.mapped('residual'):
            #     balance_amount = sum(invoices.mapped('residual'))
            # else:
            #     balance_amount = sum(invoices.mapped('amount_total'))
            # balance_amount += self.env['partner.ledger.customer'].search(
            #     [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
            # balance_amount = self.env['partner.ledger.customer'].search(
            #     [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)])[
            #     -1].balance
            # self.env['partner.ledger.customer'].sudo().create({
            #     'date': datetime.today().date(),
            #     'description': line.freight.name,
            #     'partner_id': line.partner_id.id,
            #     'company_id': self.company_id.id,
            #     'account_journal': line.journal_id.id,
            #     'account_move': move_id.id,
            #     'credit': line.amount,
            #     # 'debit': line.op_amount,
            #     # 'balance': 0,
            #     # 'executive_area': self.executive_areas.id or False,
            #     # 'area': self.area.id or False,
            #     # 'vehicle_id': self.estimate_ids[0].vahicle.id,
            #     'balance': balance_amount - line.amount,
            # })

            # vals = {
            #     'journal_id': line.journal_id.id,
            #     'state': 'draft',
            #     'ref': line.freight.name
            # }
            # pay_id_list = []
            # move_id = self.env['account.move'].create(vals)
            # temp = (0, 0, {
            #     'account_id': line.journal_id.default_debit_account_id.id,
            #     'name': line.freight.name,
            #     'move_id': move_id.id,
            #     'date': self.create_date,
            #     'partner_id': line.partner_id.id,
            #     'debit': line.amount,
            #     'credit': 0,
            # })
            # pay_id_list.append(temp)
            #
            # temp = (0, 0, {
            #     'account_id': line.journal_id.payment_credit_account_id.id,
            #     'name': line.freight.name,
            #     'move_id': move_id.id,
            #     'date': self.create_date,
            #     # 'partner_id': self.partner_id.id,
            #     'debit': 0,
            #     'credit': line.amount,
            # })
            # pay_id_list.append(temp)
            # move_id.line_ids = pay_id_list
            # move_id.action_post()
            # if line.journal_id.type == 'cash':
            #     # complete = sum(self.env['account.move.line'].search([('journal_id', '=', acc.id)]).mapped('debit'))
            #     complete = sum(self.env['account.move.line'].search(
            #         [('company_id', '=', self.env.user.company_id.id), ('account_id', '=', line.journal_id.payment_credit_account_id.id)]).mapped(
            #         'debit'))
            #     debit = 0
            #     credit = line.amount
            #     complete_new = complete - credit
            #     acc = acc
            #     self.env['cash.book.info'].create({
            #         'date': self.create_date,
            #         'account_journal': line.journal_id.id,
            #         'account': acc.id,
            #         'partner_id': self.partner_id.id,
            #         'company_id': 1,
            #         'description': line.freight.name + ' ' + line.partner_id.name,
            #         'debit': debit,
            #         'credit': credit,
            #         'balance': complete_new
            #
            #     })
            #


class ExpensesDiscounttLines(models.Model):
    _name = 'expense.disc.lines'

    freight_id = fields.Many2one('expenses.disc')
    reason = fields.Text('Reason')
    # partner_id = fields.Many2one('res.partner', string='Partner', domain=[('estimator', '=', True)])
    # freight = fields.Many2one('freight.disc.config', string='Discount/Charge', )
    amount = fields.Float('Amount')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade',
                                 help="This field is ignored in a bank statement reconciliation.")
    account_id = fields.Many2one('account.account', string='Account')

    @api.onchange('reason')
    def onchange_reason(self):
        if self.reason:
            expenses_accs = self.env['account.account'].search(
                [('user_type_id.name', '=', 'Expenses'), ('company_id', '=', self.env.user.company_id.id)])
            journal_filt = self.env['account.journal'].search(
                [('type', 'in', ('bank', 'cash')), ('company_id', '=', self.env.user.company_id.id)])
            return {'domain': {'account_id': [('id', 'in', expenses_accs.ids)]
                , 'journal_id': [('id', 'in', journal_filt.ids)]}}


class InternalAmountTransfer(models.Model):
    _name = 'internal.amount.transfer'
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    freight_lines = fields.One2many('internal.transfer.lines', 'freight_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    create_date = fields.Date(string='Create Date', default=fields.Date.context_today, required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'internal.amount.transfer') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('internal.amount.transfer') or _('New')
        return super(InternalAmountTransfer, self).create(vals)

    def action_post(self):
        self.write({'state': 'done'})
        for line in self.freight_lines:
            self.env['bank.transfer.lines'].create({
                'date':datetime.today().date(),
                'freight_ids':self.id,
                'reason':line.reason,
                'amount':line.amount,
                'from_acc_company':line.from_acc_company.id,
                'to_acc_company':line.to_acc_company.id,
                'journal_id':line.journal_id.id,
                'account_id':line.account_id.id,
                'to_account':line.to_account.id,
                'balance':line.balance,
                'to_balance':line.to_balance
            })



            j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0].id
            vals = {
                'journal_id': line.journal_id.id,
                'state': 'draft',
                'ref': self.name
            }
            pay_id_list = []
            move_id = self.env['account.move'].create(vals)
            label = self.name
            temp = (0, 0, {
                # 'account_id': acc.id,
                'account_id': line.account_id.id,
                'name': label,
                'move_id': move_id.id,
                'date': datetime.today().date(),
                # 'partner_id': line.partner_id.id,
                'debit': 0,
                'credit': line.amount,
            })
            pay_id_list.append(temp)
            temp = (0, 0, {
                'account_id': line.to_account.id,
                'name': label,
                'move_id': move_id.id,
                'date': datetime.today().date(),
                'debit': line.amount,
                'credit': 0,
            })
            pay_id_list.append(temp)

            move_id.line_ids = pay_id_list
            move_id.action_post()

            if line.journal_id.type == 'cash':
                if not self.env['cash.book.info'].search([('account', '=', line.account_id.id)]):
                    acc = self.env['account.move.line'].sudo().search([('account_id', '=', line.account_id.id)])
                    complete = sum(acc.mapped('debit')) - sum(acc.mapped('credit'))
                    acc_sub = self.env['account.move.line'].sudo().search([('account_id', '=', line.to_account.id)])
                    complete_sub = sum(acc.mapped('debit')) - sum(acc.mapped('credit'))

                else:
                    complete = self.env['cash.book.info'].search([('account', '=', line.account_id.id)])[-1].balance
                    complete_sub = self.env['cash.book.info'].search([('account', '=', line.to_account.id)])[-1].balance

                debit = 0
                credit = 0
                complete_new = 0
                # acc = self.env['account.account']
                # if self.payment_type == 'outbound':
                # credit = self.amount
                # complete_new = complete - credit
                # acc = line.journal_id.payment_credit_account_id.id
                # if self.payment_type == 'inbound':
                #     debit = self.amount
                #     complete_new = complete + debit
                #     acc = self.journal_id.default_debit_account_id.id
                complete_new = complete
                self.env['cash.book.info'].create({
                    'date': datetime.today().date(),
                    'account_journal': line.journal_id.id,
                    # 'partner_id': line.partner_id.id,
                    'company_id': 1,
                    # 'description': self.communication,
                    'description': self.name,
                    'payment_type': 'outbound',
                    'partner_type': 'customer',
                    'debit': 0,
                    'credit': line.amount,
                    'account': line.account_id.id,
                    # 'payment_id': self.id,
                    'balance': complete_new

                })
                # if line.to_account.
                # self.env['cash.book.info'].create({
                #     'date': datetime.today().date(),
                #     'account_journal': line.journal_id.id,
                #     'partner_id': line.partner_id.id,
                #     'company_id': 1,
                #     # 'description': self.communication,
                #     'description': self.name,
                #     'payment_type': 'outbound',
                #     'partner_type': 'customer',
                #     'debit': line.amount,
                #     'credit': 0,
                #     'account': line.to_account.id,
                #     # 'payment_id': self.id,
                #     'balance': complete_sub
                #
                # })


class InternalTransferLines(models.Model):
    _name = 'internal.transfer.lines'

    freight_id = fields.Many2one('internal.amount.transfer')
    reason = fields.Text('Reason')
    amount = fields.Float('Amount')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    from_acc_company = fields.Many2one('res.company', string='From A/c Company')
    to_acc_company = fields.Many2one('res.company', string='To A/c Company')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade',
                                 domain=[('type', 'in', ('bank', 'cash'))],
                                 help="This field is ignored in a bank statement reconciliation.")
    account_id = fields.Many2one('account.account', string='from Account')
    to_account = fields.Many2one('account.account', string='To Account')
    balance = fields.Float(string='from Balance')
    to_balance = fields.Float(string='to Balance')

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        if self.journal_id:
            expenses_accs = self.env['account.account'].search(
                [('user_type_id.name', '=', 'Bank and Cash')])
            return {'domain': {'account_id': [('id', 'in', expenses_accs.ids)],
                               'to_account': [('id', 'in', expenses_accs.ids)]}}

    @api.onchange('account_id')
    def onchange_account_id(self):
        if self.account_id:
            acc = self.env['account.move.line'].sudo().search([('account_id', '=', self.account_id.id)])
            bal = sum(acc.mapped('debit')) - sum(acc.mapped('credit'))
            self.balance = bal
            self.from_acc_company = self.account_id.company_id

    @api.onchange('to_account')
    def onchange_to_account(self):
        if self.to_account:
            acc = self.env['account.move.line'].sudo().search([('account_id', '=', self.to_account.id)])
            self.to_balance = sum(acc.mapped('debit')) - sum(acc.mapped('credit'))
            self.to_acc_company = self.to_account.company_id


class BankTransferLines(models.Model):
    _name = 'bank.transfer.lines'

    freight_ids = fields.Many2one('internal.amount.transfer')
    date = fields.Date(string='Date')
    reason = fields.Text('Reason')
    amount = fields.Float('Amount')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    from_acc_company = fields.Many2one('res.company', string='From A/c Company')
    to_acc_company = fields.Many2one('res.company', string='To A/c Company')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade',
                                 domain=[('type', 'in', ('bank', 'cash'))],
                                 help="This field is ignored in a bank statement reconciliation.")
    account_id = fields.Many2one('account.account', string='from Account')
    to_account = fields.Many2one('account.account', string='To Account')
    balance = fields.Float(string='from Balance')
    to_balance = fields.Float(string='to Balance')
