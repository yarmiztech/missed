# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}
# Since invoice amounts are unsigned, this is how we know if money comes in or goes out
MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': -1,
    'in_invoice': -1,
    'out_refund': 1,
}


class SalesExecutiveCollections(models.Model):
    _name = "executive.collection"
    _description = "Exe Collection"
    _order = "id desc"

    def default_payment_method_id(self):
        return self.env['account.payment.method'].search([])[0]

    def default_user_id(self):
        return self.env['res.users'].search([('id', '=', self.env.user.id)])

    def default_journal_id_id(self):
        return self.env['account.journal'].search([('type', '=', 'cash'),('company_id','=',self.env.user.company_id.id)])

    name = fields.Char("Collection Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )

    user_id = fields.Many2one('res.users', default=default_user_id, string='Sales Executive', index=True,
                              track_visibility='onchange',readonly=True,
                              track_sequence=2)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Validate'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")
    payment_method_id = fields.Many2one('account.payment.method', default=default_payment_method_id,
                                        string='Payment Method Type', required=True,
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
    partner_invoices = fields.One2many('executive.collection.line', 'collection_id')
    cashier_id = fields.Many2one('res.users', string='Cashier')
    collected = fields.Boolean('Collected')
    another_area = fields.Boolean(string='Another Area')
    sum_amount = fields.Float(compute='compute_sum_amount',string='Amount Total')
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))],default=default_journal_id_id)


    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'executive.collection') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('executive.collection') or _('New')
        return super(SalesExecutiveCollections, self).create(vals)
    # @api.multi
    def compute_sum_amount(self):
        for e in self:
            e.sum_amount = sum(e.partner_invoices.mapped('amount_total'))
    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # @api.multi
    def action_statement(self):

        return self.env.ref('ezp_cash_collection.executive_collection_id').report_action(self)

    # @api.multi
    def action_statement_cashier(self):

        return self.env.ref('ezp_cash_collection.casheir_collection_id').report_action(self)

    def collection_record_coll(self):
        for line in self.partner_invoices:
            self.env['executive.collection.record'].create({
                'collection_id': self.id,
                'collection_line_id': line.id,
                'date': self.payment_date,
                'partner_id': line.partner_id.id,
                'balance_amount': line.balance_amount,
                'amount_total': line.amount_total,
                'journal_id': line.journal_id.id,
                'payment_type': self.payment_type,
                'payments': [(6, 0, line.payments.ids)],
                'sales_person': self.user_id.id,
                'cashier_id': self.cashier_id.id,
                'pending_amount': line.balance_amount - line.amount_total
            })

    def action_exe_confirm(self):
        self.collection_record_coll()
        if self.another_area == True:
            old = self.env['executive.areas.assign'].search(
                [('date', '=', self.payment_date), ('sales_person', '=', self.user_id.partner_id.id)])
            for line in self.partner_invoices:
                if old:
                    balance = 0
                    if self.env['partner.ledger.customer'].search(
                            [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.env.user.company_id.id)]):
                        outstand = self.env['partner.ledger.customer'].search(
                            [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.env.user.company_id.id)])[-1].balance
                        balance = outstand
                    line_id = self.env['areas.customers.other'].sudo().create({
                        'assign_other_id': old.id,
                        'partner_id': line.partner_id.id,
                        'partner_area': line.partner_id.area.id,
                        'out_standing_balance': balance,
                        'state': 'visit',
                        'collected_amount': line.amount_total
                    })
                    old.partner_other_lines += line_id
                else:
                    balance = 0
                    list = []
                    if self.env['partner.ledger.customer'].search(
                            [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.env.user.company_id.id)]):
                        outstand = self.env['partner.ledger.customer'].search(
                            [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.env.user.company_id.id)])[-1].balance
                        balance = outstand
                    call_list = (0, 0, {'partner_id': line.partner_id.id,
                                        'partner_area': line.partner_id.area.id,
                                        'out_standing_balance': balance,
                                        'state': 'visit',
                                        'collected_amount': line.amount_total
                                        })
                    list.append(call_list)

                    ass = self.env['areas.executive.config'].search(
                        [('sales_person', '=', self.user_id.partner_id.id)])
                    today_area = self.env['executive.area.wise']
                    if ass:
                        today_area = ass.days_line.filtered(
                            lambda a: a.week_list == str(datetime.today().weekday())).executive_area.id
                    if not today_area:
                        today_area = self.user_id.partner_id.executive_area[0].id

                    self.env['executive.areas.assign'].sudo().create({
                        'sales_person': self.user_id.partner_id.id,
                        'executive_area': today_area,
                        'partner_other_lines': list

                    })





        self.collected = True

    def action_confirm(self):
        stmt = self.env['account.bank.statement']
        for line in self.partner_invoices:

            if line.amount_total == 0.0:
                raise UserError(_("Please mention paid amount for this partner %s ") % (line.partner_id.name))
            cv = 0
            if line.check_type == 'cheque':
                journal = self.env['account.journal'].search(
                    [('name', '=', 'Bank'), ('company_id', '=', self.env.user.company_id.id)])
            else:
                journal = line.journal_id.id
            if not stmt:
                # _get_payment_info_JSON
                # bal = sum(self.env['account.move.line'].search([('journal_id', '=', line.journal_id.id)]).mapped(
                #     'debit'))

                if self.env['account.bank.statement'].search([('company_id', '=', line.journal_id.company_id.id),
                                                              ('journal_id', '=', line.journal_id.id)]):
                    bal = self.env['account.bank.statement'].search(
                        [('company_id', '=', line.journal_id.company_id.id),
                         ('journal_id', '=', line.journal_id.id)])[0].balance_end_real
                else:
                    bal = 0

                stmt = self.env['account.bank.statement'].create({'name': line.partner_id.name,
                                                                  'balance_start': bal,
                                                                  # 'journal_id': line.journal_id.id,
                                                                  'journal_id': line.journal_id.id,
                                                                  'balance_end_real': bal+line.amount_total

                                                                  })

            payment_list = []
            pay_id_list = []
            account = self.env['account.move'].search(
                [('partner_id', '=', line.partner_id.id),('company_id','=',line.journal_id.company_id.id),('state', '=', 'open')])
            amount = line.amount_total
            actual = 0
            if account:
               for check_inv in account:
                if amount:
                    if check_inv.amount_total >= amount:
                        actual = amount

                        product_line = (0, 0, {
                            'date': line.date,
                            'name': check_inv.display_name,
                            'partner_id': line.partner_id.id,
                            'ref': check_inv.display_name,
                            'amount': amount
                        })
                        amount = amount - amount
                        payment_list.append(product_line)
                    else:
                        if check_inv.amount_total != 0:
                            amount = amount - check_inv.amount_total
                            actual = check_inv.amount_total
                            product_line = (0, 0, {
                                'date': line.date,
                                'name': check_inv.display_name,
                                'partner_id': line.partner_id.id,
                                'ref': check_inv.display_name,
                                'amount': check_inv.amount_total
                            })
                            payment_list.append(product_line)

                    j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
                    pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                                 # 'amount': check_inv.amount_total,
                                                                 'amount': actual,
                                                                 'partner_type': self.partner_type,
                                                                 'company_id': self.env.user.company_id.id,
                                                                 'payment_type': self.payment_type,
                                                                 'payment_method_id': self.payment_method_id.id,
                                                                 # 'journal_id': line.journal_id.id,
                                                                 'journal_id': line.journal_id.id,
                                                                 'ref': 'Cash Collection',
                                                                 'invoice_ids': [(6, 0, check_inv.ids)]
                                                                 })
                    # pay_id.action_validate_invoice_payment()
                    pay_id.action_post()
                    pay_id.action_cash_book()
                    # for k in pay_id.move_line_ids:
                    for k in pay_id.line_ids:
                        pay_id_list.append(k.id)
                    line.payments += pay_id
                    invoices = self.env['account.move'].search(
                        [('partner_id', '=', line.partner_id.id),
                         ('company_id', '=', self.env.user.company_id.id), ('state', '!=', 'paid')])
                    if invoices.mapped('amount_residual'):
                        bal = sum(invoices.mapped('amount_residual'))
                    else:
                        bal = sum(invoices.mapped('amount_total'))
                    bal += self.env['partner.ledger.customer'].search(
                        [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                    bal_ref = self.env['partner.ledger.customer'].search(
                        [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', line.partner_id.id)])

                    if bal_ref:
                        bal = self.env['partner.ledger.customer'].search(
                        [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', line.partner_id.id)])[
                        -1].balance

                    self.env['partner.ledger.customer'].sudo().create({
                        'date': datetime.today().date(),
                        # 'invoice_id': inv.id,
                        'description': 'Cash',
                        'partner_id': line.partner_id.id,
                        'company_id': 1,
                        'account_journal': line.journal_id.id,
                        'account_move': line.payments.move_id.id,
                        'credit': line.amount_total,
                        'balance': bal - line.amount_total,
                    })
            else:
                if not account:
                    actual = amount

                j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

                pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                             # 'amount': check_inv.amount_total,
                                                             'amount': actual,
                                                             'partner_type': self.partner_type,
                                                             'company_id': self.env.user.company_id.id,
                                                             'payment_type': self.payment_type,
                                                             'payment_method_id': self.payment_method_id.id,
                                                             # 'journal_id': line.journal_id.id,
                                                             'journal_id': line.journal_id.id,
                                                             'ref': 'Cash Collection',
                                                             # 'invoice_ids': [(6, 0, check_inv.ids)]
                                                             })
                pay_id.action_post()
                pay_id.action_cash_book()
                product_line = (0, 0, {
                    'date': self.payment_date,
                    'name': self.display_name,
                    'partner_id': line.partner_id.id,
                    'ref': self.name,
                    'amount': actual
                })
                payment_list.append(product_line)

                # for k in pay_id.move_line_ids:
                for k in pay_id.line_ids:
                    pay_id_list.append(k.id)
                line.payments += pay_id
                invoices = self.env['account.move'].search(
                    [('partner_id', '=', line.partner_id.id),
                     ('company_id', '=', self.env.user.company_id.id), ('state', '!=', 'paid')])
                if invoices:
                    if invoices.mapped('amount_residual'):
                        bal = sum(invoices.mapped('amount_residual'))
                    else:
                        bal = sum(invoices.mapped('amount_total'))
                bal += self.env['partner.ledger.customer'].search(
                    [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                bal_ref = self.env['partner.ledger.customer'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', line.partner_id.id)])

                if bal_ref:
                    bal = self.env['partner.ledger.customer'].search(
                        [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', line.partner_id.id)])[
                        -1].balance

                self.env['partner.ledger.customer'].sudo().create({
                    'date': datetime.today().date(),
                    # 'invoice_id': inv.id,
                    'description': 'Cash',
                    'partner_id': line.partner_id.id,
                    'company_id': 1,
                    'account_journal': line.journal_id.id,
                    'account_move': line.payments.move_id.id,
                    'credit': line.amount_total,
                    'balance': bal - line.amount_total,
                })

        if stmt:
            stmt.line_ids = payment_list
            stmt.move_line_ids = pay_id_list
            # stmt.write({'state': 'confirm'})
            self.write({'state': 'validate'})

        self.action_accountant_record()

    def action_accountant_record(self):
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
                    'journal_id': each.journal_id.id,
                    'collection_id': accountant.id,
                    'payments': [(6, 0, each.payments.ids)]
                })


class ExecutiveCollectionLines(models.Model):
    _name = "executive.collection.line"

    collection_id = fields.Many2one('executive.collection')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Bal Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_manys_rel')
    check_date = fields.Date(string='Check Date', copy=False)
    new_date = fields.Date('New Date')
    check_boolean = fields.Boolean(string='Check Type', default=False, copy=False)
    check_type = fields.Selection([('none', ''), ('cheque', 'Cheque')], default='none')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.move'].search(
                [('company_id','=',self.env.user.company_id.id),('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))
            if self.env['partner.ledger.customer'].search(
                    [('company_id', '=',self.env.user.company_id.id), ('partner_id', '=', self.partner_id.id)]):

                self.balance_amount = self.env['partner.ledger.customer'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', self.partner_id.id)])[-1].balance

            journals = self.env['account.journal'].search(
                [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'journal_id': [('id', 'in', journals.ids)]}}


class ExRecord(models.Model):
    _name = "executive.collection.record"

    collection_id = fields.Many2one('executive.collection')
    collection_line_id = fields.Many2one('executive.collection.line')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Bal Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_rec_rel')
    sales_person = fields.Many2one('res.users', string="Sales Person")
    cashier_id = fields.Many2one('res.users', string='Cashier')
    pending_amount = fields.Float(string='Pending Amount')
    status = fields.Boolean(string="Status")

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))
