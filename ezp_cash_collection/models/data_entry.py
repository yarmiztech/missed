# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class DataEntry(models.Model):

    _name = "data.entry"
    _description = "Exe Collection"
    _order = "id desc"

    name = fields.Char("Collection Name", index=True,default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type', required=True,default='inbound',)

    user_id = fields.Many2one('res.users', string='Sales Executive', index=True, track_visibility='onchange',
                              track_sequence=2)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Validate'), ('cancelled', 'Cancelled')], readonly=True, default='draft', copy=False, string="Status")
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method Type', required=True,
                                        oldname="payment_method",
                                        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n" \
                                             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n" \
                                             "Check: Pay bill by check and print it from Odoo.\n" \
                                             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n" \
                                             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")

    payment_method_code = fields.Char(related='payment_method_id.code',
                                      help="Technical field used to adapt the interface to the payment type selected.",
                                      readonly=True)

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')],default='customer')
    partner_id = fields.Many2one('res.partner', string='Partner')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False)
    partner_invoices = fields.One2many('data.entry.line','collection_id')
    cashier_id = fields.Many2one('res.users',string='Cashier')
    paid_amount = fields.Float(string='Paid Amount' ,compute='_compute_paid_amount')
    Bal_amount = fields.Float(string='Bal Amount',compute='_compute_paid_amount')
    total_amount = fields.Float(string='Total Amount',compute='_compute_paid_amount')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'data.entry') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('data.entry') or _('New')
        return super(DataEntry, self).create(vals)
    def action_cancel(self):
        self.write({'state':'cancelled'})
    # @api.multi
    def _compute_paid_amount(self):
        self.Bal_amount = sum(self.partner_invoices.mapped('balance_amount'))-sum(self.partner_invoices.mapped('amount_total'))
        self.paid_amount =sum(self.partner_invoices.mapped('amount_total'))
        self.total_amount =sum(self.partner_invoices.mapped('balance_amount'))

    # @api.multi
    def action_statement(self):

        return self.env.ref('ezp_cash_collection.direct_collection_id').report_action(self)

    # @api.multi
    def action_statement_cashier(self):

        return self.env.ref('ezp_cash_collection.casheir_dcollection_id').report_action(self)




    def action_confirm(self):
        stmt = self.env['account.bank.statement']
        for line in self.partner_invoices:
            if line.amount_total == 0.0:
                raise UserError(_("Please mention paid amount for this partner %s ")%(line.partner_id.name))

            # j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
            #
            # pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
            #                                              'amount': line.amount_total,
            #                                              'partner_type': self.partner_type,
            #                                              'company_id':self.env.user.company_id.id,
            #                                              'payment_type':self.payment_type,
            #                                              'payment_method_id': self.payment_method_id.id,
            #                                              'journal_id': line.journal_id.id,
            #                                              'communication': 'Cash Collection',
            #                                              # 'invoice_ids': [(6, 0, line.invoice_id.ids)]
            #                                              })
            # pay_id.action_post()
            # line.payments = pay_id
            # self.write({'state':'validate'})
            #

            cv = 0
            # if line.check_type == 'cheque':
            #     journal = self.env['account.journal'].search(
            #         [('name', '=', 'Bank'), ('company_id', '=', self.env.user.company_id.id)])
            # else:
            journal = line.journal_id
            if not stmt:
                # _get_payment_info_JSON
                bal = sum(self.env['account.move.line'].search([('journal_id', '=', line.journal_id.id)]).mapped(
                    'debit'))

                stmt = self.env['account.bank.statement'].create({'name': line.partner_id.name,
                                                                  'balance_start': bal,
                                                                  # 'journal_id': line.journal_id.id,
                                                                  'journal_id': journal.id,
                                                                  'balance_end_real': line.amount_total

                                                                  })

            payment_list = []
            pay_id_list = []
            account = self.env['account.move'].search([('partner_id','=',line.partner_id.id),('state','=','posted')])
            for check_inv in account:
                product_line = (0, 0, {
                    'date': line.date,
                    'name': check_inv.display_name,
                    'partner_id': line.partner_id.id,
                    'ref': check_inv.display_name,
                    'amount': line.amount_total
                })

                payment_list.append(product_line)
                j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

                pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                             'amount': line.amount_total,
                                                             'partner_type': self.partner_type,
                                                             'company_id': self.env.user.company_id.id,
                                                             'payment_type': self.payment_type,
                                                             'payment_method_id': self.payment_method_id.id,
                                                             # 'journal_id': line.journal_id.id,
                                                             'journal_id': journal.id,
                                                             'ref': 'Cash Collection',
                                                             'invoice_ids': [(6, 0, check_inv.ids)]
                                                             })
                # pay_id.action_validate_invoice_payment()
                pay_id.action_post()
                # for k in pay_id.move_line_ids:
                for k in pay_id.line_ids:
                    pay_id_list.append(k.id)
                line.payments = pay_id

        if stmt:
            stmt.line_ids = payment_list
            stmt.move_line_ids = pay_id_list
            self.write({'state': 'validate'})
        # accountant = self.env['accountant.record'].create({
        #     'payment_type': self.payment_type,
        #     'user_id': self.user_id.id,
        #     'payment_method_id': self.payment_method_id.id,
        #     'partner_type': self.partner_type,
        #     'payment_date': self.payment_date,
        #     'cashier_id': self.cashier_id.id
        # })
        # if accountant:
        #     for each in self.partner_invoices:
        #         self.env['accountant.record.line'].create({
        #             'date': each.date,
        #             'partner_id': each.partner_id.id,
        #             'balance_amount': each.balance_amount,
        #             'amount_total': each.amount_total,
        #             'journal_id': each.journal_id.id,
        #             'collection_id': accountant.id,
        #             'payments': [(6, 0, each.payments.ids)]
        #         })
        #


class DataEntryLine(models.Model):
    _name = "data.entry.line"

    collection_id = fields.Many2one('data.entry')
    date = fields.Date('Date', default=fields.Date.context_today,)
    partner_id = fields.Many2one('res.partner','Partner')
    invoice_id = fields.Many2one('account.move','Invoice')
    balance_amount = fields.Float(string='Bal Amount',)
    amount_total = fields.Float(string='Paid Amount',)
    journal_id = fields.Many2one('account.journal', string='Payment Journal',  domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type', required=True,default='inbound',)
    payments = fields.Many2many('account.payment','payments_m_rel')
    estimate_id = fields.Many2one('sale.estimate')


    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id),('state','!=','paid')])
            if invoices.mapped('amount_residual'):
               self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))
            journals = self.env['account.journal'].search([('company_id', '=', self.env.user.company_id.id),('type','in',('cash','bank'))])
            if journals:
                return {'domain': {'journal_id': [('id', 'in', journals.ids)]}}







