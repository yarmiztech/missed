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


class ResCompany(models.Model):
    _inherit = "res.company"

    tcs = fields.Boolean(default=False)


class AccountMove(models.Model):
    _inherit = 'account.move'

    invoiced_number = fields.Char('Invoice No')
    vehicle_no = fields.Char(string='Vehicle Number')
    invoiced_date = fields.Date('Invoice Date')
    purchase_date = fields.Date()
    # amount_tcs = fields.Monetary(string='TCS Amount', store=True, readonly=True, compute='_compute_m_amount')
    # grand_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_compute_m_amount')
    amount_tcs = fields.Monetary(string='TCS Amount', store=True, compute='_compute_amount')
    grand_total = fields.Monetary(string='Total', store=True, readonly=True, )
    transport_receipt = fields.Char(string='Transport Receipt no')
    gate_pass = fields.Char(string='Gate Pass No')

    # amount_total = fields.Monetary(string='Total',
    #                                store=True, readonly=True, compute='_compute_amount')
    #

    # @api.one
    # @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
    #              'currency_id', 'company_id', 'date_invoice', 'type', 'date')
    # @api.depends(
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.debit',
    #     'line_ids.credit',
    #     'line_ids.currency_id',
    #     'line_ids.amount_currency',
    #     'line_ids.amount_residual',
    #     'line_ids.amount_residual_currency',
    #     'line_ids.payment_id.state',
    #     'line_ids.full_reconcile_id')
    # def _compute_amount(self):
    #     if self.move_type == 'in_invoice':
    #         round_curr = self.currency_id.round
    #         self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
    #         self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
    #         # self.amount_tax = sum(round_curr(line.amount_total) for line in self.invoice_line_ids)
    #         self.amount_total = self.amount_untaxed + self.amount_tax
    #         self.grand_total = self.amount_untaxed + self.amount_tax
    #         if self.company_id.id != 1:
    #             if self.partner_id.tcs == True:
    #                 self.amount_tcs = self.amount_total * 0.10 / 100
    #         self.amount_total = self.amount_untaxed + self.amount_tax + self.amount_tcs
    #
    #         amount_total_company_signed = self.amount_total
    #         amount_untaxed_signed = self.amount_untaxed
    #         if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
    #             currency_id = self.currency_id
    #             rate_date = self._get_currency_rate_date() or fields.Date.today()
    #             amount_total_company_signed = currency_id._convert(self.amount_total, self.company_id.currency_id,
    #                                                                self.company_id, rate_date)
    #             amount_untaxed_signed = currency_id._convert(self.amount_untaxed, self.company_id.currency_id,
    #                                                          self.company_id, rate_date)
    #         sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
    #         self.amount_total_company_signed = amount_total_company_signed * sign
    #         self.amount_total_signed = self.amount_total * sign
    #         self.amount_untaxed_signed = amount_untaxed_signed * sign
    #     else:
    #         round_curr = self.currency_id.round
    #         self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
    #         self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
    #         self.amount_total = self.amount_untaxed + self.amount_tax
    #         amount_total_company_signed = self.amount_total
    #         amount_untaxed_signed = self.amount_untaxed
    #         if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
    #             currency_id = self.currency_id
    #             rate_date = self._get_currency_rate_date() or fields.Date.today()
    #             amount_total_company_signed = currency_id._convert(self.amount_total, self.company_id.currency_id,
    #                                                                self.company_id, rate_date)
    #             amount_untaxed_signed = currency_id._convert(self.amount_untaxed, self.company_id.currency_id,
    #                                                          self.company_id, rate_date)
    #         sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
    #         self.amount_total_company_signed = amount_total_company_signed * sign
    #         self.amount_total_signed = self.amount_total * sign
    #         self.amount_untaxed_signed = amount_untaxed_signed * sign

    # @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line_ids.price_subtotal',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.currency_id')
    def _compute_residual(self):
        residual = 0.0
        residual_company_signed = 0.0
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        for line in self._get_aml_for_amount_residual():
            residual_company_signed += line.amount_residual
            if line.currency_id == self.currency_id:
                residual += line.amount_residual_currency if line.currency_id else line.amount_residual
            else:
                if line.currency_id:
                    residual += line.currency_id._convert(line.amount_residual_currency, self.currency_id,
                                                          line.company_id, line.date or fields.Date.today())
                else:
                    residual += line.company_id.currency_id._convert(line.amount_residual, self.currency_id,
                                                                     line.company_id, line.date or fields.Date.today())
        self.residual_company_signed = abs(residual_company_signed) * sign
        self.residual_signed = abs(residual) * sign
        if self.company_id.id != 1:
            if self.amount_tcs:
                self.residual = abs(residual) + self.amount_tcs
            else:
                self.residual = abs(residual)
        else:
            self.residual = abs(residual)
        digits_rounding_precision = self.currency_id.rounding
        if float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
            self.reconciled = True
        else:
            self.reconciled = False

    # @api.one
    # @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding', )
    @api.depends('invoice_line_ids.price_subtotal')
    def _compute_m_amount(self):
        self._compute_amount()
        if self.move_type == 'in_invoice':
            if self.purchase_id:
                self.amount_tcs = self.purchase_id.amount_tcs
                self.grand_total = self.purchase_id.grand_total
                self.amount_total = self.purchase_id.amount_total
        return

    @api.constrains('vehicle')
    def onchange_vehicle(self):
        report = self.env['partner.ledger.customer'].search([('invoice_id', '=', self.id)])
        reports = self.env['partner.ledgers.customer'].search([('invoice_id', '=', self.id)])
        if report:
            for each_report in report:
                each_report.in_vehicle_id = self.vehicle
        if reports:
            for each_reports in reports:
                each_reports.in_vehicle_id = self.vehicle

    @api.constrains('transport_receipt')
    def constraint_transport_receipt(self):
        report = self.env['partner.ledger.customer'].search([('invoice_id', '=', self.id)])
        reports = self.env['partner.ledgers.customer'].search([('invoice_id', '=', self.id)])
        if report:
            for each_report in report:
                each_report.transport_receipt = self.transport_receipt

        if reports:
            for each_reports in reports:
                each_reports.transport_receipt = self.transport_receipt

    # @api.onchange('vehicle','transport_receipt','gate_pass','complete_address')
    # @api.constrains('vehicle')
    # def onchange_vehicle(self):
    #     report = self.env['partner.ledger.customer'].search([('invoice_id','=',self._origin.id)])
    #     reports = self.env['partner.ledgers.customer'].search([('invoice_id','=',self._origin.id)])
    #     if report:
    #         for each_report in report:
    #             each_report.in_vehicle_id = self.vehicle
    #             each_report.transport_receipt = self.transport_receipt
    #             each_report.gate_pass = self.gate_pass
    #             each_report.address = self.complete_address
    #     if reports:
    #         for each_reports in reports:
    #             each_reports.in_vehicle_id = self.vehicle
    #             each_reports.transport_receipt = self.transport_receipt
    #             each_reports.gate_pass = self.gate_pass
    #             each_reports.address = self.complete_address

    @api.constrains('gate_pass')
    def complete_gate_pass(self):
        report = self.env['partner.ledger.customer'].search([('invoice_id', '=', self.id)])
        reports = self.env['partner.ledgers.customer'].search([('invoice_id', '=', self.id)])
        if report:
            for each_report in report:
                each_report.gate_pass = self.gate_pass
        if reports:
            for each_reports in reports:
                each_reports.gate_pass = self.gate_pass

    @api.constrains('complete_address')
    def constraint_complete_address(self):
        report = self.env['partner.ledger.customer'].search([('invoice_id', '=', self.id)])
        reports = self.env['partner.ledgers.customer'].search([('invoice_id', '=', self.id)])
        if report:
            for each_report in report:
                each_report.address = self.complete_address
        if reports:
            for each_reports in reports:
                each_reports.address = self.complete_address

    def constraint_complete_address_1(self):
        print('dfdfgerf')
        return self.env['sale.order'].search([('name','=',self.ref)]).eway_bill_no


class AccountAccount(models.Model):
    _inherit = "account.account"

    def _compute_opening_debit_credit(self):
        super(AccountAccount, self)._compute_opening_debit_credit()
        for each in self:
            if each.opening_credit or each.opening_debit:
                bal = sum(self.env['account.move.line'].search([('journal_id', '=', each.id)]).mapped(
                    'debit'))

                journal = self.env['account.journal'].search(
                    [('type', '=', 'general'), ('name', '=', 'Miscellaneous Operations'),
                     ('company_id', '=', each.company_id.id)])
                account = self.env['partner.ledger.customer'].search(
                    [('partner_id', '=', False), ('company_id', '=', each.company_id.id), ('account', '=', each.id)])
                cash_book = self.env['cash.book.info'].search(
                    [('partner_id', '=', False), ('company_id', '=', each.company_id.id), ('account', '=', each.id)])
                if each.name == "Cash":
                    if not cash_book:
                        self.env['cash.book.info'].create({
                            'date': datetime.today().date(),
                            'account_journal': journal.id,
                            # 'partner_id': self.partner_id.id,
                            'company_id': each.company_id.id,
                            'description': 'Opening Balance',
                            # 'payment_type': each.payment_type,
                            # 'partner_type': each.partner_type,
                            'debit': each.opening_debit,
                            'credit': each.opening_credit,
                            'account': each.id,
                            # 'payment_id': self.id,
                            'balance': 0

                        })
                    else:
                        cash_book[0].credit = each.opening_credit
                        cash_book[0].debit = each.opening_debit
                        cash_book[0].balance = 0

                if not account:
                    self.env['partner.ledger.customer'].sudo().create({
                        'date': datetime.today().date(),
                        'company_id': each.company_id.id,
                        'credit': each.opening_credit,
                        'debit': each.opening_debit,
                        'balance': 0,
                        'description': 'Opening Balance',
                        'account_journal': journal.id,
                        'account': each.id,

                    })
                else:
                    account[0].credit = each.opening_credit
                    account[0].debit = each.opening_debit
                    account[0].balance = 0

            # record.opening_debit = opening_debit
        # record.opening_credit = opening_credit


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    compute_invoice_amount = fields.Float('Balance Amount', compute='_compute_invoice_amount')
    bool = fields.Boolean('Balance Amount', compute='_compute_invoice_amount')
    test_hide = fields.Boolean(default=False)

    # @api.multi
    @api.depends('partner_id')
    def _compute_invoice_amount(self):
        self.compute_invoice_amount=0
        if self.partner_id:
            if self.env['account.move'].search(
                    [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.env.user.company_id.id),
                     ('state', '!=', 'paid')]).mapped('amount_residual'):
                self.compute_invoice_amount = sum(self.env['account.move'].search(
                    [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.env.user.company_id.id),
                     ('state', '!=', 'paid')]).mapped('amount_residual'))
                # balance_amount += self.env['partner.ledger.customer'].search(
                #     [('partner_id', '=', self.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                Previous_led = self.env['partner.ledger.customer'].search(
                    [('company_id', '=', self.company_id.id), ('partner_id', '=', self.partner_id.id)])
                if Previous_led:
                    self.compute_invoice_amount = Previous_led[-1].balance


            else:
                self.compute_invoice_amount = sum(self.env['account.move'].search(
                    [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.env.user.company_id.id),
                     ('state', '!=', 'paid')]).mapped('amount_total'))
                Previous_led = self.env['partner.ledger.customer'].search(
                    [('company_id', '=', self.company_id.id), ('partner_id', '=', self.partner_id.id)])
                if Previous_led:
                    self.compute_invoice_amount = Previous_led[-1].balance

            self.bool = True
        else:
            self.compute_invoice_amount =0

    def action_validate_invoice_payment_est(self):
        self.action_validate_invoice_payment()
        # super(AccountPayment, self).action_validate_invoice_payment()
        invoices = self.env['account.move'].search(
            [('partner_id', '=', self.partner_id.id),
             ('company_id', '=', self.env.user.company_id.id), ('state', '!=', 'paid')])
        if invoices.mapped('amount_residual'):
            balance_amount = sum(invoices.mapped('amount_residual'))
        else:
            balance_amount = sum(invoices.mapped('amount_total'))
        Previous_led = self.env['supplier.ledger.customer'].search(
            [('company_id', '=', self.company_id.id), ('partner_id', '=', self.partner_id.id)])
        if Previous_led:
            balance_amount = Previous_led[-1].balance

        self.env['supplier.ledger.customer'].sudo().create({
            'date': datetime.today().date(),
            'partner_id': self.partner_id.id,
            'month': str(datetime.today().date().month),
            # 'purchase_id': self.id,
            # 'invoice_id':self.invoice_id.id or False,
            'company_id': self.company_id.id,
            # 'product_id': line.product_id.id,
            # 'price_units': line.price_unit,
            # 'uom': line.product_uom.id,
            # 'rate': line.price_unit,
            'debit': self.amount,
            'balance': balance_amount - self.amount
        })
        for po_id in self.env['purchase.payment.remainder'].search([('state', '=', 'draft')]):
            if po_id.purchase_id == self.invoice_ids.purchase_id:
                po_id.write({'state': 'paid'})
        for each in self.env['cash.discount'].search([('state', '=', 'not')]):
            if each.purchase_id == self.invoice_ids.purchase_id:
                if each.purchase_id.purchase_payment_term:
                    if each.purchase_id.date_approve + timedelta(
                            days=each.purchase_id.purchase_payment_term.days) >= datetime.today().date():
                        each.write({'state': 'draft'})
        if self.journal_id.type == 'cash':
            if not self.env['cash.book.info'].search([]):
                complete = sum(
                    self.env['account.move.line'].search([('journal_id', '=', self.journal_id.id)]).mapped('debit'))
            else:
                complete = self.env['cash.book.info'].search([])[-1].balance

            debit = 0
            credit = 0
            complete_new = 0
            acc = self.env['account.account']
            if self.payment_type == 'outbound':
                credit = self.amount
                complete_new = complete - credit
                acc = self.journal_id.payment_credit_account_id.id
            # if self.payment_type == 'inbound':
            #     debit = self.amount
            #     complete_new = complete + debit
            #     acc = self.journal_id.default_debit_account_id.id
            #
            self.env['cash.book.info'].create({
                'date': self.date,
                'account_journal': self.journal_id.id,
                'partner_id': self.partner_id.id,
                'company_id': self.company_id.id,
                # 'description': self.communication,
                'description': self.partner_id.name,
                'payment_type': self.payment_type,
                'partner_type': self.partner_type,
                'debit': debit,
                'credit': credit,
                'account': acc,
                'payment_id': self.id,
                'balance': complete_new

            })

        return

    # @api.multi
    # def post(self):
    #     if self.journal_id.name == 'Cash':
    #         complete = sum(self.env['account.move.line'].search([('journal_id', '=', self.journal_id.id)]).mapped('debit'))
    #         debit = 0
    #         credit = 0
    #         complete_new = 0
    #         acc = self.env['account.account']
    #         if self.payment_type == 'outbound':
    #             debit = self.amount
    #             complete_new = complete+debit
    #             acc = self.journal_id.default_debit_account_id.id
    #         if self.payment_type == 'inbound':
    #             credit = self.amount
    #             complete_new = complete-credit
    #             acc = self.journal_id.payment_credit_account_id.id
    #
    #         self.env['cash.book.info'].create({
    #             'date': self.payment_   #             'account_journal': self.journal_    #             'company_id': self.   #             'payment_type': self.payment_type,
    #             'partner_type': self.partner_type,
    #             'debit': debit,
    #             'credit': credit,
    #             'account':acc,
    #             'payment_id':self.id,
    #             'balance':complete_new
    #
    #         })
    #
    #     return super(AccountPayment, self).post()

    def action_cash_book(self):
        if self.journal_id.type == 'cash':
            if not self.env['cash.book.info'].search([]):
                # complete = sum(self.env['account.move.line'].search([('journal_id', '=', self.journal_id.id)]).mapped('debit'))
                complete = sum(self.env['account.move.line'].search(
                    [('account_id', '=', self.journal_id.payment_credit_account_id.id)]).mapped('debit'))
            else:
                complete = self.env['cash.book.info'].search([])[-1].balance

            debit = 0
            credit = 0
            complete_new = 0
            acc = self.env['account.account']
            if self.payment_type == 'outbound':
                credit = self.amount
                complete_new = complete - credit
                acc = self.journal_id.payment_credit_account_id.id
            if self.payment_type == 'inbound':
                debit = self.amount
                complete_new = complete + debit
                acc = self.journal_id.payment_debit_account_id.id

            self.env['cash.book.info'].create({
                'date': self.date,
                'account_journal': self.journal_id.id,
                'partner_id': self.partner_id.id,
                'company_id': self.company_id.id,
                # 'description': self.communication,
                'description': self.partner_id.name,
                'payment_type': self.payment_type,
                'partner_type': self.partner_type,
                'debit': debit,
                'credit': credit,
                'account': acc,
                'payment_id': self.id,
                'balance': complete_new

            })

    # @api.multi
    def account_record(self):
        # super(AccountPayment, self).post()
        accountant = self.env['accountant.record'].create({
            'payment_type': self.payment_type,
            'user_id': self.env.user.id,
            'payment_method_id': self.payment_method_id.id,
            'partner_type': self.partner_type,
            'payment_date': self.payment_date,
            'expense_direct': self.id,
            'source': self.name,
        })
        if accountant:
            # for each in self.partner_invoices:
            self.env['accountant.record.line'].create({
                'date': self.date,
                'partner_id': self.partner_id.id,
                'balance_amount': self.compute_invoice_amount,
                'amount_total': self.amount,
                'journal_id': self.journal_id.id,
                'collection_id': accountant.id
            })
        self.action_cash_book()
        if self.partner_type == 'customer':
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.company_id.id),
                 ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                balance_amount = sum(invoices.mapped('amount_total'))
            balance_amount += self.env['partner.ledger.customer'].search(
                [('partner_id', '=', self.partner_id.id), ('description', '=', 'Opening Balance')]).balance

            preveious = self.env['partner.ledger.customer'].search(
                [('company_id', '=', self.company_id.id), ('partner_id', '=', self.partner_id.id)])
            if preveious:
                balance_amount = self.env['partner.ledger.customer'].search(
                    [('company_id', '=', self.company_id.id), ('partner_id', '=', self.partner_id.id)])[
                    -1].balance

            self.env['partner.ledger.customer'].sudo().create({
                'date': datetime.today().date(),
                'description': self.ref,
                'partner_id': self.partner_id.id,
                'company_id': self.company_id.id,
                'account_journal': self.journal_id.id,
                # 'account_move': pay_id.move_line_ids.mapped('move_id').id,
                # 'account_move': move_id.id,
                'credit': self.amount,
                # 'debit': line.op_amount,
                # 'balance': 0,
                # 'executive_area': self.executive_areas.id or False,
                # 'area': self.area.id or False,
                # 'vehicle_id': self.estimate_ids[0].vahicle.id,
                'balance': balance_amount - self.amount,
            })


        self.test_hide = True

    # accountant = self.env['accountant.record'].create({
    #     'payment_type': self.payment_type,
    #     'user_id': self.user_id.id,
    #     'payment_method_id': self.payment_method_id.id,
    #     'partner_type': self.partner_type,
    #     'payment_date': self.payment_date,
    #     'expense_direct':self.id
    # })
    # if accountant:
    #     # for each in self.partner_invoices:
    #         self.env['accountant.record.line'].create({
    #             'date': self.payment_date,
    #             'partner_id': self.partner_id.id,
    #             'balance_amount': self.compute_invoice_amount,
    #             'amount_total': self.amount,
    #             'journal_id': self.journal_id.id,
    #         })
    # # self.write({'state': 'validate'})


class AccountantRecorded(models.Model):
    _name = "accountant.record"
    _description = "Account Record"
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
    partner_invoices = fields.One2many('accountant.record.line', 'collection_id')
    cashier_id = fields.Many2one('res.users', string='Cashier')
    bal_amount = fields.Integer(string='Bal Amount', compute='compute_bal_amount')
    paid_amount = fields.Integer(string='Paid Amount', compute='compute_bal_amount')
    expense_direct = fields.Many2one('account.payment', string='Expense')
    source = fields.Char('Source')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'accountant.record') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('accountant.record') or _('New')
        return super(AccountantRecorded, self).create(vals)

    # @api.one
    def compute_bal_amount(self):
        self.bal_amount = sum(self.partner_invoices.mapped('balance_amount')) - sum(
            self.partner_invoices.mapped('amount_total'))
        self.paid_amount = sum(self.partner_invoices.mapped('amount_total'))

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_payment_confirm(self):
        self.ensure_one()
        return {
            'name': _('Payment'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'view_id': self.env.ref('ezp_estimate.view_account_payment_form_cu').id,
            'type': 'ir.actions.act_window',
            'context': {
                'default_payment_type': 'inbound',
                'default_amount_given': sum(self.partner_invoices.mapped('amount_total')),
                'default_amount_bal': self.bal_amount,
                #     'default_period_type': self.period_type,
                #     'default_date_of_rent': self.end_of_rent,
                #     # 'default_end_of_rent': self.end_of_rent,
                #     'default_amount': self.amount,
            },
            # 'target': 'new',
        }


class AccountantRecordLines(models.Model):
    _name = "accountant.record.line"

    collection_id = fields.Many2one('accountant.record')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    bal_total = fields.Float(string='Bal Amount', compute='compute_bal_total')
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_manya_rel')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    v_company = fields.Many2one('res.company', 'Vehicle Company')
    ex_company = fields.Many2one('res.company', 'Expense Company')

    # @api.one
    def compute_bal_total(self):
        self.bal_total = sum(self.mapped('balance_amount')) - sum(
            self.mapped('amount_total'))


class AccountPayment(models.Model):
    _inherit = "account.payment"

    amount_given = fields.Float(string='Amount Given As')
    amount_bal = fields.Float(string='Amount Bal As')


class StockRule(models.Model):
    _inherit = 'stock.rule'

    # @api.multi
    def _run_buy(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        cache = {}
        if product_id.seller_ids:
            suppliers = product_id.seller_ids[0]
        if not suppliers:
            msg = _('There is no vendor associated to the product %s. Please define a vendor for this product.') % (
            product_id.display_name,)
            raise UserError(msg)
        supplier = self._make_po_select_supplier(values, suppliers)
        partner = supplier.name
        # we put `supplier_info` in values for extensibility purposes
        values['supplier'] = supplier

        domain = self._make_po_get_domain(values, partner)
        if domain in cache:
            po = cache[domain]
        else:
            po = self.env['purchase.order'].sudo().search([dom for dom in domain])
            po = po[0] if po else False
            cache[domain] = po
        if not po:
            vals = self._prepare_purchase_order(product_id, product_qty, product_uom, origin, values, partner)
            company_id = values.get('company_id') and values['company_id'].id or self.env.user.company_id.id
            po = self.env['purchase.order'].with_context(force_company=company_id).sudo().create(vals)
            cache[domain] = po
        elif not po.origin or origin not in po.origin.split(', '):
            if po.origin:
                if origin:
                    po.write({'origin': po.origin + ', ' + origin})
                else:
                    po.write({'origin': po.origin})
            else:
                po.write({'origin': origin})

        # Create Line
        po_line = False
        for line in po.order_line:
            if line.product_id == product_id and line.product_uom == product_id.uom_po_id:
                if line._merge_in_existing_line(product_id, product_qty, product_uom, location_id, name, origin,
                                                values):
                    vals = self._update_purchase_order_line(product_id, product_qty, product_uom, values, line, partner)
                    po_line = line.write(vals)
                    break
        if not po_line:
            vals = self._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, partner)
            self.env['purchase.order.line'].sudo().create(vals)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def awb_qr(self):
        return self.eway_bill_no + '\n' + self.company_id.vat + '\n' + str(self.eway_bill_date)
    #
    # @api.model
    # def build_qr_code_url(self, amount, comment):
    #     communication = ""
    #     if comment:
    #         communication = (comment[:137] + '...') if len(comment) > 140 else comment
    #     qr_code_string = 'BCD\n001\n1\nSCT\n%s\n%s\n%s\nEUR%s\n\n\n%s' % (
    #         self.partner_id.name, self.company_id.name, self.partner_id.name, amount, communication)
    #     qr_code_url = ('QR', werkzeug.url_quote_plus(qr_code_string), 128, 128)
    #     return qr_code_url
