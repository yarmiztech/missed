# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class CashCollection(models.Model):

    _name = "cash.collection"
    _description = "Cash Collection"
    _order = "payment_date desc"

    def default_payment_method_id(self):
        return self.env['account.payment.method'].search([])[0]
    def default_user_id(self):
        return self.env['res.users'].search([('id','=',self.env.user.id)])





    name = fields.Char("Collection Name", index=True,default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Validate'), ('cancelled', 'Cancelled')], readonly=True, default='draft', copy=False, string="Status")
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type', required=True,default='inbound',)
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method Type', required=True,
                                        oldname="payment_method",default=default_payment_method_id,
                                        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n" \
                                             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n" \
                                             "Check: Pay bill by check and print it from Odoo.\n" \
                                             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n" \
                                             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")

    payment_method_code = fields.Char(related='payment_method_id.code',
                                      help="Technical field used to adapt the interface to the payment type selected.",
                                      readonly=True)
    another_area = fields.Boolean(string='Another Area')
    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')],default='customer')
    partner_id = fields.Many2one('res.partner', string='Partner')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False)
    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True, domain=[('type', 'in', ('bank', 'cash'))])
    partner_invoices = fields.One2many('cash.collection.lines','collection_id')
    total_amount = fields.Float('Total Amount',compute='_compute_total_amount')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'cash.collection') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('cash.collection') or _('New')
        return super(CashCollection, self).create(vals)
    # @api.multi
    @api.depends('partner_id')
    def _compute_total_amount(self):
        for each in self:
            if each.partner_id:
                invoices = self.env['account.move'].search([('partner_id', '=', each.partner_id.id), ('state', '=', 'open'),('company_id','=',self.env.user.company_id.id)])
                each.total_amount = sum(invoices.mapped('amount_total'))
            else:
                each.total_amount = 0
    @api.onchange('payment_type')
    def onchange_payment_type(self):
        self.partner_invoices =False
        if self.payment_type == 'inbound':
            est = self.env['res.partner'].search([('estimator','=',True)])
            if est:
              return {'domain': {'partner_id': [('id', 'in', est.ids)]}}

        if self.payment_type == 'outbound':
            vendors = self.env['res.partner'].search([('supplier','=',True)])
            if vendors:
                return {'domain': {'partner_id': [('id', 'in', vendors.ids)]}}


    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.partner_invoices = False
            # total_amount = self.en

            invoices = self.env['account.move'].search([('company_id','=',self.env.user.company_id.id),('partner_id','=',self.partner_id.id),('state','=','posted')])
            self.total_amount = sum(invoices.mapped('amount_total'))
            invoice_list = []
            for each_invoice in invoices:
                product_line = (0, 0, {
                    'invoice_id':each_invoice.id,
                    'partner_id':self.partner_id.id,
                    'invoice_date':each_invoice.date_invoice,
                    'invoice_due_date':each_invoice.date_due,
                    'state':each_invoice.state,
                    'amount_total':each_invoice.amount_total,
                    'residual':each_invoice.residual,
                    'total':each_invoice.amount_total-each_invoice.residual,
                    'collection_id':self.id,
                })
                invoice_list.append(product_line)
            self.partner_invoices= invoice_list
            journals = self.env['account.journal'].search(
                [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'journal_id': [('id', 'in', journals.ids)]}}

    def action_confirm(self):
        for line in self.partner_invoices:
            j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

            pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                         'amount': line.total_paid,
                                                         'partner_type': self.partner_type,
                                                         'payment_type':self.payment_type,
                                                         'payment_method_id': self.payment_method_id.id,
                                                         'journal_id': self.journal_id.id,
                                                         'ref': 'Cash Collection',
                                                         'invoice_ids': [(6, 0, line.invoice_id.ids)]
                                                         })
            pay_id.action_post()
            pay_id.action_cash_book()
            line.payments = pay_id
            line.residual = line.residual-line.total_paid
            line.total += line.total_paid
            self.write({'state':'validate'})
            line.write({'state':'paid'})

    # @api.multi
    def action_statement(self):

        return self.env.ref('ezp_cash_collection.cash_payments_print').report_action(self)


class CashCollectionLines(models.Model):
    _name = "cash.collection.lines"

    collection_id = fields.Many2one('cash.collection')
    invoice_id = fields.Many2one('account.move','Invoice')
    partner_id = fields.Many2one('res.partner','Partner')
    invoice_date = fields.Date('Invoice Date')
    invoice_due_date = fields.Date('Due Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'In Payment' status is used when payments have been registered for the entirety of the invoice in a journal configured to post entries at bank reconciliation only, and some of them haven't been reconciled with a bank statement line yet.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")

    amount_total = fields.Monetary(string='Total Amount',)
    residual = fields.Monetary(string='Amount Due',
                               help="Remaining amount due.")
    total = fields.Monetary('Paid Amount')
    total_paid = fields.Float('Pay Amount')
    payments = fields.Many2many('account.payment','payments_many_rel')
    total_payments = fields.Monetary(string='Total Payments',
                                   readonly=True, )
    currency_id = fields.Many2one('res.currency', string='Account Currency',
                                  help="Forces all moves for this account to have this account currency.")



