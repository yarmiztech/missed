# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class AmountWithdraw(models.Model):

    _name = "amount.withdraw"
    _description = "Withdraw"
    _order = "id desc"
    @api.model
    def _default_journal_id(self):
        return self.env['account.journal'].search([('name', '=', 'Miscellaneous Operations'),('company_id','=',self.env.user.company_id.id)])

    name = fields.Char("Collection Name", index=True,default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True, domain=[('type', 'in', ('bank', 'cash'))],default=_default_journal_id)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'), ('cancelled', 'Cancelled')], readonly=True, default='draft', copy=False, string="Status")
    type = fields.Selection([('cash', 'Cash'), ('bank', 'Bank'), ('cheque', 'Cheque')], default='cash', copy=False, string="Type Of Withdraw")
    type_of_draw = fields.Selection([('deposit', 'Deposit'), ('withdraw', 'Withdraw')], default='withdraw', copy=False, string="Type Of Draw")
    partner_id = fields.Many2one('res.partner', string='Partner')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    payment_date = fields.Date(string='Payment Date',  required=True, copy=False)
    reference = fields.Char('Reason',required=True)
    account_id = fields.Many2one('account.account',string='Deposit Account')
    credit_account = fields.Many2one('account.account',string='Credit Bank')
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, index=True)
    amount = fields.Float(default=0.0,required=True)
    # check_number =fields.Char('Check Number')
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'amount.withdraw') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('amount.withdraw') or _('New')
        return super(AmountWithdraw, self).create(vals)

    @api.onchange('account_id')
    def onchange_account_id(self):
        if self.account_id:
            self.partner_id = self.env['account.account'].search([('company_id','=',self.env.user.company_id.id),('name','=',self.account_id.name)]).company_id.partner_id


    # @api.onchange('journal_id')
    # def onchange_journal(self):
    #
    #     all_equitys = self.env['account.account'].search([('user_type_id','=','equity')])
    #     if all_equitys:
    #             return {'domain': {'account_id': [('id', 'in', all_equitys.ids)]}}
    #     else:
    #             return {'domain': {'account_id': [('id', '=', [])]}}
    @api.onchange('type_of_draw')
    def onchange_type_of_draw(self):
        if self.type_of_draw == 'withdraw':
            all_equitys = self.env['account.account'].search([('user_type_id','=','equity')])
            if all_equitys:
                    return {'domain': {'account_id': [('id', 'in', all_equitys.ids)]}}
        else:
                return {'domain': {'account_id': []}}

    def action_confirm(self):
        self.write({'state':'done'})

        vals = {
            'journal_id': self.journal_id.id,
            'state': 'draft',
            'ref':self.reference
        }
        pay_id_list = []
        move_id = self.env['account.move'].create(vals)
        if self.partner_id:
            partner_id = self.partner_id.id
        else:
            partner_id = False
        if self.account_id.user_type_id.display_name == 'equity':
            label = 'Withdraw Amount'
        else:
            label = 'Deposit Amount'


        temp = (0, 0, {
            'account_id': self.account_id.id,
            'name': label,
            'move_id': move_id.id,
            'date': self.payment_date,
            'partner_id': partner_id,
            'debit': self.amount,
            'credit': 0,
        })
        pay_id_list.append(temp)
        if self.type == 'cash' or self.type == 'cheque':
            acc = self.env['account.account'].search(
                [('name', '=', 'Cash'), ('company_id', '=', self.env.user.company_id.id)])
        else:
            acc = self.credit_account
        temp = (0, 0, {
            'account_id': acc.id,
            'name': 'Credit Amount',
            'move_id': move_id.id,
            'date': self.payment_date,
            # 'partner_id': self.partner_id.id,
            'debit': 0,
            'credit': self.amount,
        })
        pay_id_list.append(temp)
        move_id.line_ids = pay_id_list
        move_id.action_post()
        # move_id.action_cash_book()
        if self.type == 'cash' and self.journal_id.type == 'cash':
            # complete = sum(self.env['account.move.line'].search([('journal_id', '=', acc.id)]).mapped('debit'))
            complete = sum(self.env['account.move.line'].search([('company_id','=',self.env.user.company_id.id),('account_id','=',acc.id)]).mapped('debit'))
            if not self.env['cash.book.info'].search([]):
                complete = sum(
                    self.env['account.move.line'].search([('journal_id', '=', self.journal_id.id)]).mapped('debit'))
            else:
                complete = self.env['cash.book.info'].search([])[-1].balance

            debit = 0
            credit = 0
            complete_new = 0
            if self.type_of_draw == 'withdraw':
                credit = self.amount
                complete_new = complete - credit
                acc = acc
            else:
                debit = self.amount
                complete_new = complete + debit
                acc =acc
            type_m = ''
            if self.type_of_draw == 'withdraw':
                type_m = 'outbound'
            if self.type_of_draw == 'deposit':
                type_m = 'inbound'

            self.env['cash.book.info'].create({
                'date': self.payment_date,
                'account_journal': self.journal_id.id,
                'account': acc.id,
                'partner_id': self.partner_id.id,
                'company_id': 1,
                'description': label +' ' + self.reference,
                'payment_type': type_m,

                # 'partner_type': self.partner_type,
                'debit': debit,
                'credit': credit,
                # 'payment_id': self.id,
                'balance': complete_new

            })








