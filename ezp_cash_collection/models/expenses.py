# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ExpensePayments(models.Model):
    _name = "expense.payments"
    _description = "Expense Payment"
    _order = "id desc"

    name = fields.Char("Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='outbound', )

    user_id = fields.Many2one('res.users', string='Responsible', index=True, track_visibility='onchange',
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

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], default='supplier')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False)
    partner_invoices = fields.One2many('expense.payments.line', 'expense_pay_id')
    cashier_id = fields.Many2one('res.users', string='Cashier')
    paid_amount = fields.Float(string='Paid Amount', compute='compute_bal_amount')
    bal_amount = fields.Float(string='Bal Amount', compute='compute_bal_amount')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'expense.payments') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('expense.payments') or _('New')
        return super(ExpensePayments, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # @api.multi
    def compute_bal_amount(self):
        for each in self:
            each.bal_amount = sum(each.mapped('partner_invoices').mapped('balance_amount')) - sum(
                each.mapped('partner_invoices').mapped('amount_total'))
            each.paid_amount = sum(each.mapped('partner_invoices').mapped('amount_total'))

    # @api.multi
    def action_statement(self):

        return self.env.ref('ezp_cash_collection.expense_payments_report').report_action(self)

    # @api.multi
    def action_statement_cashier(self):

        return self.env.ref('ezp_cash_collection.expense_payments_report').report_action(self)
        # return self.env.ref('ezp_cash_collection.test_div').report_action(self)

    def action_confirm(self):
        accountant = self.env['accountant.record'].create({
            'payment_type': self.payment_type,
            'user_id': self.user_id.id,
            'payment_method_id': self.payment_method_id.id,
            'partner_type': self.partner_type,
            'payment_date': self.payment_date,
            'cashier_id': self.cashier_id.id,
            'source': self.name
        })
        if accountant:
            for each in self.partner_invoices:
                self.env['accountant.record.line'].create({
                    'date': each.date,
                    'partner_id': each.partner_id.id,
                    'balance_amount': each.balance_amount,
                    'amount_total': each.amount_total,
                    'vehicle_id': each.vehicle_id.id,
                    'v_company': each.v_company.id,
                    'collection_id': accountant.id,
                    'ex_company': each.ex_company.id,
                })
        self.write({'state': 'validate'})

        stmt = self.env['account.bank.statement']
        for line in self.partner_invoices:

            # j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
            #
            # pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
            #                                              'amount': line.amount_total,
            #                                              'partner_type': self.partner_type,
            #                                              'company_id':self.env.user.company_id.id,
            #                                              'payment_type':self.payment_type,
            #                                              'payment_method_id': self.payment_method_id.id,
            #                                              'journal_id': line.journal_id.id,
            #                                              'ref': 'Cash Collection',
            #                                              # 'invoice_ids': [(6, 0, line.invoice_id.ids)]
            #                                              })
            # pay_id.action_post()
            # line.payments = pay_id
            # self.write({'state':'validate'})
            #

            cv = 0
            if not stmt:
                # _get_payment_info_JSON
                bal = sum(self.env['account.move.line'].search([('journal_id', '=', line.journal_id.id)]).mapped(
                    'debit'))
                stmt = self.env['account.bank.statement'].create({'name': line.partner_id.name,
                                                                  'balance_start': bal,
                                                                  'journal_id': line.journal_id.id,
                                                                  'balance_end_real': line.amount_total

                                                                  })

            payment_list = []
            pay_id_list = []
            # account = self.env['account.move'].search([('partner_id','=',line.partner_id.id),('state','=','open')])
            for check_inv in self.partner_invoices:
                product_line = (0, 0, {
                    'date': line.date,
                    'name': check_inv.vehicle_id.name,
                    'partner_id': line.partner_id.id,
                    'ref': check_inv.vehicle_id.name,
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
                                                             'journal_id': line.journal_id.id,
                                                             'ref': 'Expenses Payments',
                                                             # 'invoice_ids': [(6, 0, check_inv.ids)]
                                                             })
                pay_id.action_post()
                pay_id.action_cash_book()
                # for k in pay_id.move_line_ids:
                for k in pay_id.line_ids:
                    pay_id_list.append(k.id)
                line.payments = pay_id

        if stmt:
            stmt.line_ids = payment_list
            stmt.move_line_ids = pay_id_list
            # self.write({'state': 'validate'})

    @api.onchange('payment_date')
    def _onchange_payment_date(self):
        current_estimates = self.env['sale.estimate'].search([('c_date', '=', self.payment_date)])
        rent_lines_list = []
        for each in current_estimates:
            for exp in self.env['expense.balance.payment'].search([('estimate_id', '=', each.id)]):
                line = (0, 0, {
                    'partner_id': exp.partner_id.id,
                    'ex_company': exp.est_from_company.id,
                    'v_company': exp.est_to_company.id,
                    'vehicle_id': exp.vahicle.id,
                    'date': self.payment_date,
                    'balance_amount': exp.vahicle_exp_amount,
                })
                rent_lines_list.append(line)
        self.partner_invoices = rent_lines_list


class ExpensePaymentsLines(models.Model):
    _name = "expense.payments.line"

    @api.model
    def default_journal_id(self):
        journals = self.env['account.journal'].search(
            [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
        if journals:
            return {'domain': {'journal_id': [('id', 'in', journals.ids)]}}
        # return self.journal_id = journals.ids

    expense_pay_id = fields.Many2one('expense.payments')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Company')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    v_company = fields.Many2one('res.company', 'Vehicle Company')
    ex_company = fields.Many2one('res.company', 'Expense Company')
    balance_amount = fields.Float(string='Bal Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    apply = fields.Boolean(default=False, string='Apply')
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='outbound', )
    payments = fields.Many2many('account.payment', 'payments_exp_rel')
    bal_amount = fields.Float(string='Bal Amount', compute='compute_bal_amount')

    # @api.multi
    def compute_bal_amount(self):
        for line in self:
            line.bal_amount = line.balance_amount - line.amount_total

    @api.onchange('partner_id', 'expense_pay_id.user_id', 'expense_pay_id.cashier_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))

    #
    # @api.onchange('expense_pay_id.user_id','expense_pay_id.cashier_id')
    # def onchange_expenses_pay(self):
    #     journals = self.env['account.journal'].search(
    #         [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
    #     if journals:
    #         return {'domain': {'journal_id': [('id', 'in', journals.ids)]}}

    @api.onchange('apply')
    def onchange_apply(self):
        if self.apply == True:
            journals = self.env['account.journal'].search(
                [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'journal_id': [('id', 'in', journals.ids)]}}


# class ExpensesCashier(models.Model):
#     _name = "expenses.cashier"
#
    # def default_payment_method_id(self):
    #     return self.env['account.payment.method'].search([])[0]
    #
    # def default_user_id(self):
    #     return self.env['res.users'].search([('id', '=', self.env.user.id)])
    #
    # name = fields.Char("Collection Name", index=True, default=lambda self: _('New'))
    # sequence = fields.Integer(index=True)
    # payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
    #                                 required=True, default='inbound', )
    #
    # user_id = fields.Many2one('res.users', default=default_user_id, string='Sales Executive', index=True,
    #                           track_visibility='onchange',
    #                           track_sequence=2)
    # state = fields.Selection([('draft', 'Draft'), ('validate', 'Validate'), ('cancelled', 'Cancelled')], readonly=True,
    #                          default='draft', copy=False, string="Status")
    # payment_method_id = fields.Many2one('account.payment.method', default=default_payment_method_id,
    #                                     string='Payment Method Type', required=True,
    #                                     oldname="payment_method",
    #                                     help="Manual: Get paid by cash, check or any other method outside of Odoo.\n" \
    #                                          "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n" \
    #                                          "Check: Pay bill by check and print it from Odoo.\n" \
    #                                          "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n" \
    #                                          "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")
    #
    # payment_method_code = fields.Char(related='payment_method_id.code',
    #                                   help="Technical field used to adapt the interface to the payment type selected.",
    #                                   readonly=True)
    #
    # partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], default='customer')
    # partner_id = fields.Many2one('hr.employee', string='Employee')
    # currency_id = fields.Many2one('res.currency', string='Currency', required=True,
    #                               default=lambda self: self.env.user.company_id.currency_id)
    # payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False)
    # cashier_id = fields.Many2one('res.users', string='Cashier')
    # expense_name = fields.Char('Expense Name')
    # product_id = fields.Many2one('product.product', string='Product')
    # quantity = fields.Float('Quantity')
    # unit_amount = fields.Float('Unit Amount')
    # total_amount = fields.Float('Total Amount')
    # account_id = fields.Float('account.account', string='Account')
    # tax_ids = fields.Many2many('account.tax', string='Taxes')
