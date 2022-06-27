# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta
from odoo.tools import float_is_zero, float_compare
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
#
# from googletrans import Translator
#
# translator = Translator(service_urls=['translate.googleapis.com'])
# import werkzeug.urls
#
# try:
#     import qrcode
# except ImportError:
#     qrcode = None

class CashierDirectCollection(models.Model):
    _name = "cashier.direct.collection"
    _description = "DIcerect Record"
    _order = "id desc"

    name = fields.Char("Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )

    user_id = fields.Many2one('res.users', string='Sales Executive', index=True, track_visibility='onchange',
                              track_sequence=2)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Validate'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method Type',
                                        oldname="payment_method",
                                        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n" \
                                             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n" \
                                             "Check: Pay bill by check and print it from Odoo.\n" \
                                             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n" \
                                             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")

    payment_method_code = fields.Char(related='payment_method_id.code',
                                      help="Technical field used to adapt the interface to the payment type selected.",
                                      readonly=True)

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], default='customer')
    partner_id = fields.Many2one('res.partner', string='Partner')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False)
    partner_invoices = fields.One2many('cashier.direct.collection.line', 'collection_id')
    cashier_id = fields.Many2one('res.users', string='Cashier')
    source = fields.Char('Source')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'accountant.record') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('accountant.record') or _('New')
        return super(CashierDirectCollection, self).create(vals)

    # @api.one
    def compute_bal_amount(self):
        self.bal_amount = sum(self.partner_invoices.mapped('balance_amount')) - sum(
            self.partner_invoices.mapped('amount_total'))
        self.paid_amount = sum(self.partner_invoices.mapped('amount_total'))

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_confirm(self):
        # stmt = self.env['account.bank.statement']

        for line in self.partner_invoices:

            if line.amount_total == 0.0:
                raise UserError(_("Please mention paid amount for this partner %s ") % (line.partner_id.name))
            cv = 0
          # if line.check_type == 'cheque':
            journal = self.env['account.journal'].search(
                [('name', '=', 'Cash'), ('company_id', '=', self.env.user.company_id.id)])
            j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

            pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                         'amount': line.amount_total,
                                                         'partner_type': 'customer',
                                                        'payment_type': 'inbound',
                                                         'payment_method_id': j.id,
                                                         'journal_id': journal.id,
                                                         'ref': 'Direct Cash Collection',
                                                         })
            pay_id.action_post()

            pay_id.action_cash_book()

            invoices = self.env['account.move'].search(
                [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.env.user.company_id.id),
                 ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                balance_amount = sum(invoices.mapped('amount_total'))
            balance_amount += self.env['partner.ledger.customer'].search(
                [('partner_id', '=', self.env.user.company_id.id), ('description', '=', 'Opening Balance')]).balance

            preveious = self.env['partner.ledger.customer'].search(
                [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', line.partner_id.id)])
            if preveious:
                balance_amount = self.env['partner.ledger.customer'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', line.partner_id.id)])[
                    -1].balance

            self.env['partner.ledger.customer'].sudo().create({
                'date': datetime.today().date(),
                'description': 'Direct Cash Collection',
                'partner_id': line.partner_id.id,
                'company_id': self.env.user.company_id.id,
                'account_journal': journal.id,
                'credit': line.amount_total,
                'balance': balance_amount - line.amount_total,
            })
        self.write({'state':'validate'})

class CashierDirectCollectionLines(models.Model):
    _name = "cashier.direct.collection.line"

    collection_id = fields.Many2one('cashier.direct.collection')
    date = fields.Date('Date')
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    # bal_total = fields.Float(string='Bal Amount', compute='compute_bal_total')
    # journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    # payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
    #                                 required=True, default='inbound', )
    # payments = fields.Many2many('account.payment', 'payments_manya_rel')

    # @api.one
    # def compute_bal_total(self):
    #     self.bal_total = sum(self.mapped('balance_amount')) - sum(
    #         self.mapped('amount_total'))
    #
