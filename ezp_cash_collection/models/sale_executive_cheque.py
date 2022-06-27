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


class SalesExecutiveCheque(models.Model):
    _name = "executive.cheque.collection"
    _description = "Exe Cheque Collection"
    _order = "id desc"

    def default_payment_method_id(self):
        return self.env['account.payment.method'].search([])[0]
    def default_user_id(self):
        return self.env['res.users'].search([('id','=',self.env.user.id)])


    name = fields.Char("Collection Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )

    user_id = fields.Many2one('res.users', string='Sales Executive', index=True, track_visibility='onchange',
                              track_sequence=2,default=default_user_id)
    another_area = fields.Boolean(string='Another Area')
    state = fields.Selection(
        [('draft', 'Draft'), ('collected', 'Collected'), ('deposited', 'Deposited'), ('pending', 'Pending'),
         ('validate', 'Done'), ('cancelled', 'Cancelled')], readonly=True, default='draft', copy=False,
        string="Status")
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method Type', required=True,
                                        oldname="payment_method", default=default_payment_method_id,
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
    partner_invoices = fields.One2many('executive.cheque.collection.line', 'collection_id')
    sub_partner_invoices = fields.One2many('sub.cheque.collection.line', 'collection_sub_id')
    a_partner_invoices = fields.One2many('advance.cheque.collection.line', 'a_collection_id')
    cashier_id = fields.Many2one('res.users', string='Cashier')
    status_compute = fields.Boolean(compute='_compute_status_compute')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'executive.cheque.collection') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('executive.cheque.collection') or _('New')
        return super(SalesExecutiveCheque, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # @api.multi
    def _compute_status_compute(self):
        if len(self.partner_invoices.filtered(lambda a: a.state == 'deposit')) > 0:
            self.status_compute = True
        else:
            self.status_compute = False

    # @api.multi
    def action_cheque_statement(self):

        return self.env.ref('ezp_cash_collection.executive_cheque_collection_id').report_action(self)

    # @api.multi
    def action_cheque_statement_cashier(self):

        return self.env.ref('ezp_cash_collection.casheir_cheque_collection_id').report_action(self)
    def create_pdc_record(self):
        pdc_c = self.env['pdc.cheque.collection']
        for line in self.partner_invoices.filtered(lambda a:a.check_type == 'pdc' and a.state =='draft'):
            if not pdc_c:
                pdc_id = self.env['pdc.cheque.collection'].create({
                        'payment_type':self.payment_type,
                        'partner_type':self.partner_type,
                        'user_id':self.user_id.id,
                        'cashier_id':self.cashier_id.id,
                        'payment_method_id':self.payment_method_id.id
                     })
            if line:
                pdc_line = self.env['pdc.cheque.collection.line'].create({
                    'collection_id':pdc_id.id,
                    'partner_id':line.partner_id.id,
                    'balance_amount':line.balance_amount,
                    'amount_total':line.amount_total,
                    'journal_id':line.journal_id.id,
                    'check_no':line.check_no,
                    'check_type':line.check_type,
                    'check_date':line.check_date,
                    'check_manual_date':line.check_manual_date,
                    'bank_name':line.bank_name,
                    'cheque_ref_id':line.id,
                    # 'account_type':line.account_type,
                    'holder_name':line.holder_name.id,
                    'debited_account':line.debited_account.id,
                    'collected_cheque':line.collected_cheque.id
                })
                line.check_ref_id = pdc_line.id
    # def create_post_record(self):
    #     pdc_c = self.env['post.cheques']
    #     for line in self.partner_invoices.filtered(lambda a:a.status == 'postpone' and a.state =='draft'):
    #         if not pdc_c:
    #             pdc_id = self.env['post.cheques'].create({
    #                     'payment_type':self.payment_type,
    #                     'partner_type':self.partner_type,
    #                     'user_id':self.user_id.id,
    #                     'cashier_id':self.cashier_id.id,
    #                     'payment_method_id':self.payment_method_id.id
    #                  })
    #         if line:
    #             pdc_line = self.env['post.cheques.line'].create({
    #                 'today_id':pdc_id.id,
    #                 'partner_id':line.partner_id.id,
    #                 'balance_amount':line.balance_amount,
    #                 'amount_total':line.amount_total,
    #                 'journal_id':line.journal_id.id,
    #                 'check_no':line.check_no,
    #                 'check_type':line.check_type,
    #                 'check_date':line.check_date,
    #                 'check_manual_date':line.check_manual_date,
    #                 'bank_name':line.bank_name,
    #                 'post_date':line.post_date,
    #                 'status':line.status,
    #                 'cheque_ref_id':line.id,
    #                 'account_type':line.account_type,
    #                 'holder_name':line.holder_name.id,
    #                 'debited_account':line.debited_account.id or False,
    #                 'collected_cheque':line.collected_cheque.id
    #             })
    #             line.check_post_id = pdc_line.id
    # def create_bounce_record(self):
    #     pdc_c = self.env['bounce.cheques']
    #     for line in self.partner_invoices.filtered(lambda a:a.status == 'bounce' and a.state =='draft'):
    #         if not pdc_c:
    #             pdc_id = self.env['bounce.cheques'].create({
    #                     'payment_type':self.payment_type,
    #                     'partner_type':self.partner_type,
    #                     'user_id':self.user_id.id,
    #                     'cashier_id':self.cashier_id.id,
    #                     'payment_method_id':self.payment_method_id.id
    #                  })
    #         if line:
    #             pdc_line = self.env['bounce.cheques.line'].create({
    #                 'today_id':pdc_id.id,
    #                 'partner_id':line.partner_id.id,
    #                 'balance_amount':line.balance_amount,
    #                 'amount_total':line.amount_total,
    #                 'journal_id':line.journal_id.id,
    #                 'check_no':line.check_no,
    #                 'check_type':line.check_type,
    #                 'check_date':line.check_date,
    #                 'check_manual_date':line.check_manual_date,
    #                 'bank_name':line.bank_name,
    #                 'reason':line.reason,
    #                 'status':line.status,
    #                 'cheque_ref_id':line.id,
    #                 'account_type':line.account_type,
    #                 'holder_name':line.holder_name.id,
    #                 'debited_account':line.debited_account.id or False,
    #                 'collected_cheque':line.collected_cheque.id
    #             })
    #             line.check_bounce_id = pdc_line.id
    #

    def create_advance_payment(self):
        for line in self.a_partner_invoices:
            collected = self.env['collection.cheque'].create({
                'advance_check_line': line.id,
                'date': line.check_manual_date,
                'ref_id': self.id,
                'partner_id': line.partner_id.id,
                'sales_person': self.user_id.id,
                'balance_amount': 0,
                'amount_total': line.amount_total,
                'check_no': line.check_no,
                'check_type': line.check_type,
                'bank_name': line.bank_name,
                'state': line.state,
                'reason': line.reason,
                'post_date': line.post_date,
                'holder_name': line.holder_name.id,
            })
            line.collected_cheque = collected



            # j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
            # journal = self.env['account.journal'].search(
            #     [('name', '=', 'Cash'), ('company_id', '=', self.env.user.company_id.id)])
            # pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
            #                                              'amount': line.amount_total,
            #                                              'partner_type': 'customer',
            #                                              'payment_type': 'inbound',
            #                                              'payment_method_id': j.id,
            #                                              'journal_id': journal.id,
            #                                              'ref': 'Advance Payments',
            #                                              # 'invoice_ids': [(6, 0, inv.ids)]
            #                                              })
            # pay_id.action_validate_invoice_payment()

    def action_confirm(self):
        stmt = self.env['account.bank.statement']
        any_draft = False

        # self.create_pdc_record()
        for line in self.partner_invoices:

            if line.state == 'deposit':
                line.write({'state': 'done'})
                line.write({'status': 'deposit'})
                line.collected_cheque.write({'state': 'done'})
                if not stmt:
                    # _get_payment_info_JSON
                    bal = sum(
                        self.env['account.move.line'].search([('journal_id', '=', line.debited_account.id)]).mapped(
                            'debit'))
                    stmt = self.env['account.bank.statement'].create({'name': line.check_no,
                                                                      'balance_start': bal,
                                                                      'journal_id': line.debited_account.id,
                                                                      'balance_end_real': line.amount_total

                                                                      })

                payment_list = []
                pay_id_list = []
                account = self.env['account.move'].search(
                    [('partner_id', '=', line.partner_id.id), ('state', '=', 'open')])
                amount = line.amount_total
                actual = 0
                for check_inv in account:
                    if amount:
                        if check_inv.amount_total >= amount:
                            actual = amount

                            product_line = (0, 0, {
                                'date': self.payment_date,
                                'name': check_inv.display_name,
                                'partner_id': check_inv.partner_id.id,
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
                        journal = line.debited_account
                        pay_id = self.env['account.payment'].create({'partner_id': check_inv.partner_id.id,
                                                                     'amount': actual,
                                                                     'partner_type': 'customer',
                                                                     'payment_type': 'inbound',
                                                                     'payment_method_id': j.id,
                                                                     'journal_id': journal.id,
                                                                     'ref': 'Cheque Collection',
                                                                     'invoice_ids': [(6, 0, check_inv.ids)]
                                                                     })
                        # pay_id.action_validate_invoice_payment()
                        pay_id.action_post()
                        # for k in pay_id.move_line_ids:
                        for k in pay_id.line_ids:
                            pay_id_list.append(k.id)
                        line.payments += pay_id
                        if line.check_ref_id:
                           line.check_ref_id.write({'state': 'done'})
                           line.check_ref_id.payments = pay_id
                        if line.check_bounce_id:
                           line.check_bounce_id.write({'state': 'done'})
                           line.check_bounce_id.write({'status': 'deposit'})
                           line.check_bounce_id.payments = pay_id
                        if line.check_post_id:
                           line.check_post_id.write({'state': 'done'})
                           line.check_post_id.write({'status': 'deposit'})
                           line.check_post_id.payments = pay_id
            else:
                any_draft = True

        if stmt:
            stmt.line_ids = payment_list
            stmt.mapped('line_ids')
            stmt.move_line_ids = pay_id_list
            # stmt.write({'state': 'confirm'})
        if not self.partner_invoices.filtered(lambda a: a.state == 'draft'):
            self.write({'state': 'validate'})
        else:
            if self.partner_invoices.filtered(lambda a: a.state == 'draft'):
                self.write({'state': 'pending'})

        accountant = self.env['accountant.record'].create({
            'payment_type': self.payment_type,
            'user_id': self.user_id.id,
            'payment_method_id': self.payment_method_id.id,
            'partner_type': self.partner_type,
            'payment_date': self.payment_date,
            'cashier_id': self.cashier_id.id,
            'source':self.name
        })
        if accountant:
            for each in self.partner_invoices.filtered(lambda a: a.state != 'draft'):
                self.env['accountant.record.line'].create({
                    'date': each.date,
                    'partner_id': each.partner_id.id,
                    'balance_amount': each.balance_amount,
                    'amount_total': each.amount_total,
                    'journal_id': each.journal_id.id,
                    'collection_id': accountant.id,
                    'payments': [(6, 0, each.payments.ids)]
                })


    def action_deposit(self):
        self.create_advance_payment()
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




        self.write({'state': 'collected'})
        for line in self.partner_invoices:
            if not line.amount_total:
                raise UserError(_('''You are Not allowed to Process the Zero Amount Cheques
                                           '''))
            # if line.partner_id != line.holder_name:
            #     raise UserError(_('''Both the partner name and the holder name must match
            #                                                '''))

            if line.check_type == 'cash':
                date = line.check_date
            else:
                date = line.check_manual_date
            collected = self.env['collection.cheque'].create({
                'check_line': line.id,
                'date': date,
                'ref_id': self.id,
                'partner_id': line.partner_id.id,
                'sales_person': self.user_id.id,
                'balance_amount': line.balance_amount,
                'amount_total': line.amount_total,
                'check_no': line.check_no,
                'check_type': line.check_type,
                'bank_name': line.bank_name,
                # 'account_type': line.account_type,
                'state': line.state,
                'reason':line.reason,
                'post_date':line.post_date,
                'holder_name': line.holder_name.id,
                # 'debited_account':line.debited_account.id,
            })
            line.collected_cheque = collected
        self.create_pdc_record()
        # self.create_post_record()
        # self.create_bounce_record()

        for line in self.partner_invoices:
            self.env['check.repo'].create({
                'date':line.check_manual_date,
                'partner_id':line.partner_id.id,
                'amount_total':line.amount_total,
                'check_no':line.check_no,
                'bank_name':line.bank_name,
                'line_id':line.id,



            })


class ExecutiveChequeCollectionLines(models.Model):
    _name = "executive.cheque.collection.line"

    collection_id = fields.Many2one('executive.cheque.collection')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Bal Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_chequess_rel')
    check_no = fields.Char(string='Cheque No')
    sub_balance_amount = fields.Float(string='Sub Amount', )

    check_type = fields.Selection([('pdc', 'PDC'), ], string="Check Type",default='pdc')
    check_date = fields.Date(string='Check Date', default=fields.Date.today())
    check_manual_date = fields.Date(string='Check Date', )
    bank_name = fields.Char('Bank Name')
    check_ref_id = fields.Many2one('pdc.cheque.collection.line')
    check_post_id = fields.Many2one('post.cheques.line')
    check_bounce_id = fields.Many2one('bounce.cheques.line')
    reason = fields.Text('Reason')
    new_date = fields.Date(string='New Date')
    status = fields.Selection([
        ('none', ''),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('cancel', 'Cancelled')], string='Status',
        default='none')
    post_date = fields.Date(string='Post Date', )
    bounce = fields.Char(string='Reason')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('send', 'Sended'),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='state',
        default='draft', readonly=True)
    # account_type = fields.Selection([
    #     ('current', 'Current'),
    #     ('saving', 'Saving'),
    # ], string="Account Type")
    holder_name = fields.Many2one('res.partner', string='Holder Name')
    debited_account = fields.Many2one('account.journal', string='Debit A/C')
    collected_cheque = fields.Many2one('collection.cheque', )

    # @api.onchange('check_manual_date')
    # def onchange_check_manual_date(self):
    #     if self.check_manual_date:
    #         print('check_manual_date')
    #         self.check_manual_date=self.check_manual_date.strftime("%d-%m-%y")

    @api.onchange('check_manual_date')
    def onchange_check_manual_date(self):
        if self.check_manual_date:

            for l in self.env['pdc.configuration'].search([('active', '=', True)]):
                if l.days:
                    from dateutil import relativedelta
                    if self.check_manual_date > datetime.today().date() + relativedelta.relativedelta(days=l.days):
                        raise UserError(_("You are not allowed to take after this %s date Cheques") % (
                                    datetime.today().date() + relativedelta.relativedelta(days=l.days)))

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id),('company_id','=',1), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))
            if self.env['partner.ledger.customer'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', self.partner_id.id)]):
                self.balance_amount = self.env['partner.ledger.customer'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', self.partner_id.id)])[
                    -1].balance

            sub_customers = self.partner_id.sub_customers
            if sub_customers:
                return {'domain': {'holder_name': [('id', '=', sub_customers.mapped('partner').ids)]}}
            else:
                return {'domain': {'holder_name': [('id', '=',False)]}}

            # self.holder_name = self.partner_id

    @api.onchange('holder_name')
    def onchange_holder_name(self):
        if self.holder_name:
            invoices = self.env['account.move'].sudo().search(
                [('partner_id', '=', self.holder_name.id), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                self.sub_balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.sub_balance_amount = sum(invoices.mapped('amount_total'))
            if self.env['partner.ledger.customer'].sudo().search(
                    [('company_id','!=',1),('partner_id', '=', self.holder_name.id)]):
                self.sub_balance_amount = self.env['partner.ledger.customer'].sudo().search(
                    [('company_id','!=',1),('partner_id', '=', self.holder_name.id)])[
                    -1].balance


class ChequeEXRecord(models.Model):
    _name = "collection.cheque"

    check_line = fields.Many2one('executive.cheque.collection.line')
    advance_check_line = fields.Many2one('advance.cheque.collection.line')
    date = fields.Date(string='Cheque Date')
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Amount', )
    sales_person = fields.Many2one('res.users',string="Sales Person")
    amount_total = fields.Float(string='Check Amount', )
    check_no = fields.Char(string='Cheque No')
    check_type = fields.Selection([('cash', 'Cash'), ('pdc', 'PDC'), ], string="Check Type", )
    bank_name = fields.Char('Back Name')
    status = fields.Selection([
        ('none', ''),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('cancel', 'Cancelled')], string='Status',
        default='none')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('send', 'Sended'),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='state',
        default='draft')
    # account_type = fields.Selection([
    #     ('current', 'Current'),
    #     ('saving', 'Saving'),
    # ], string="Account Type")
    holder_name = fields.Many2one('res.partner', string='Holder Name')
    debited_account = fields.Many2one('account.journal', string='Debit A/C')
    ref_id = fields.Many2one('executive.cheque.collection', string="Source")
    new_date = fields.Date('bounce new Date')
    reason = fields.Text('Reason')
    postpone_date = fields.Date('Postpone Date')
    post_date = fields.Date('Postpone Date')
    al_state = fields.Boolean()
    comm_state = fields.Boolean()

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))

class Pdccheque(models.Model):
    _name = "pdc.cheque.collection"
    _description = "PDC Cheque Collection"
    _order = "id desc"

    name = fields.Char("Collection Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )

    user_id = fields.Many2one('res.users', string='Sales Executive', index=True, track_visibility='onchange',
                              track_sequence=2)
    state = fields.Selection(
        [('draft', 'Draft'), ('collected', 'Collected'), ('deposited', 'Deposited'), ('pending', 'Pending'),
         ('validate', 'Validate'), ('cancelled', 'Cancelled')], readonly=True, default='draft', copy=False,
        string="Status")
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

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], default='customer')
    partner_id = fields.Many2one('res.partner', string='Partner')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False)
    partner_invoices = fields.One2many('pdc.cheque.collection.line', 'collection_id')
    cashier_id = fields.Many2one('res.users', string='Cashier')
    status_compute = fields.Boolean(compute='_compute_status_compute')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'pdc.cheque.collection') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('pdc.cheque.collection') or _('New')
        return super(Pdccheque, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # @api.multi
    def _compute_status_compute(self):
        if len(self.partner_invoices.filtered(lambda a: a.state == 'deposit')) > 0:
            self.status_compute = True

    # @api.multi
    def action_cheque_statement(self):

        return self.env.ref('ezp_cash_collection.executive_cheque_collection_id').report_action(self)

    # @api.multi
    def action_cheque_statement_cashier(self):

        return self.env.ref('ezp_cash_collection.casheir_cheque_collection_id').report_action(self)

    def action_confirm(self):
        stmt = self.env['account.bank.statement']
        any_draft = False
        for line in self.partner_invoices:
            if line.state == 'deposit':
                line.write({'state': 'done'})
                line.collected_cheque.write({'state': 'done'})
                if not stmt:
                    # _get_payment_info_JSON
                    bal = sum(
                        self.env['account.move.line'].search([('journal_id', '=', line.debited_account.id)]).mapped(
                            'debit'))
                    stmt = self.env['account.bank.statement'].create({'name': line.check_no,
                                                                      'balance_start': bal,
                                                                      'journal_id': line.debited_account.id,
                                                                      'balance_end_real': line.amount_total

                                                                      })

                payment_list = []
                pay_id_list = []
                account = self.env['account.move'].search(
                    [('partner_id', '=', line.partner_id.id), ('state', '=', 'open')])
                for check_inv in account:

                    product_line = (0, 0, {
                        'date': self.payment_date,
                        'name': check_inv.display_name,
                        'partner_id': check_inv.partner_id.id,
                        'ref': check_inv.display_name,
                        'amount': line.amount_total
                    })

                    payment_list.append(product_line)
                    j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
                    journal = line.debited_account
                    pay_id = self.env['account.payment'].create({'partner_id': check_inv.partner_id.id,
                                                                 'amount': line.amount_total,
                                                                 'partner_type': 'customer',
                                                                 'payment_type': 'inbound',
                                                                 'payment_method_id': j.id,
                                                                 'journal_id': journal.id,
                                                                 'ref': 'Cheque Collection',
                                                                 'invoice_ids': [(6, 0, check_inv.ids)]
                                                                 })
                    # pay_id.action_validate_invoice_payment()
                    pay_id.action_post()
                    # for k in pay_id.move_line_ids:
                    for k in pay_id.line_ids:
                        pay_id_list.append(k.id)
                    line.payments = pay_id
                    if line.cheque_ref_id:
                        line.cheque_ref_id.write({'state': 'done'})
                        line.cheque_ref_id.payments = pay_id

            else:
                any_draft = True

        if stmt:
            stmt.line_ids = payment_list
            stmt.mapped('line_ids')
            stmt.move_line_ids = pay_id_list
            # stmt.write({'state': 'confirm'})
        if not self.partner_invoices.filtered(lambda a: a.state == 'draft'):
            self.write({'state': 'validate'})
        else:
            if self.partner_invoices.filtered(lambda a: a.state == 'draft'):
                self.write({'state': 'pending'})

        accountant = self.env['accountant.record'].create({
            'payment_type': self.payment_type,
            'user_id': self.user_id.id,
            'payment_method_id': self.payment_method_id.id,
            'partner_type': self.partner_type,
            'payment_date': self.payment_date,
            'cashier_id': self.cashier_id.id,
            'source':self.name
        })
        if accountant:
            for each in self.partner_invoices.filtered(lambda a: a.state != 'draft'):
                self.env['accountant.record.line'].create({
                    'date': each.date,
                    'partner_id': each.partner_id.id,
                    'balance_amount': each.balance_amount,
                    'amount_total': each.amount_total,
                    'journal_id': each.journal_id.id,
                    'collection_id': accountant.id,
                    'payments': [(6, 0, each.payments.ids)]
                })

    def action_deposit(self):
        self.write({'state': 'collected'})

        for line in self.partner_invoices:
            if not line.amount_total:
                raise UserError(_('''You are Not allowed to Process the Zero Amount Cheques
                                           '''))
            # if line.partner_id != line.holder_name:
            #     raise UserError(_('''Both the partner name and the holder name must match
            #                                                '''))

            if line.check_type == 'cash':
                date = line.check_date
            else:
                date = line.check_manual_date
            collected = self.env['collection.cheque'].create({
                'check_line': line.id,
                'date': date,
                'ref_id': self.id,
                'partner_id': line.partner_id.id,
                'balance_amount': line.balance_amount,
                'amount_total': line.amount_total,
                'check_no': line.check_no,
                'check_type': line.check_type,
                'bank_name': line.bank_name,
                # 'account_type': line.account_type,
                'state': line.state,
                'holder_name': line.holder_name.id,
                # 'debited_account':line.debited_account.id,
            })
            line.collected_cheque = collected

class PdcChequeLines(models.Model):
    _name = "pdc.cheque.collection.line"

    collection_id = fields.Many2one('pdc.cheque.collection')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Bal Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_pdc_rel')
    apply = fields.Boolean(default=False,string='Apply')
    check_no = fields.Char(string='Cheque No')
    check_type = fields.Selection([('cash', 'Cash'), ('pdc', 'PDC'), ], string="Check Type", default='pdc')
    check_date = fields.Date(string='Check Date', default=fields.Date.today())
    check_manual_date = fields.Date(string='Check Date', )
    bank_name = fields.Char('Back Name')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('send', 'Sended'),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='state',
        default='draft', readonly=True)
    # account_type = fields.Selection([
    #     ('current', 'Current'),
    #     ('saving', 'Saving'),
    # ], string="Account Type")
    holder_name = fields.Many2one('res.partner', string='Holder Name')
    debited_account = fields.Many2one('account.journal', string='Debit A/C')
    collected_cheque = fields.Many2one('collection.cheque', )
    cheque_ref_id = fields.Many2one('executive.cheque.collection.line')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid'),('company_id','=',self.env.user.company_id.id)])
            if invoices.mapped('amount_residual'):
                self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))
    @api.onchange('apply')
    def onchange_apply(self):
        if self.apply == True :
            journals = self.env['account.journal'].search(
                [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'journal_id': [('id', 'in', journals.ids)]}}
class AdvanceChequeCollectionLines(models.Model):
    _name = "advance.cheque.collection.line"

    a_collection_id = fields.Many2one('executive.cheque.collection')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    amount_total = fields.Float(string='Cheque Amount', )
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_chequead_rel')
    check_no = fields.Char(string='Cheque No')
    check_type = fields.Selection([('pdc', 'PDC'), ], string="Check Type",default='pdc')
    check_date = fields.Date(string='Check Date', default=fields.Date.today())
    check_manual_date = fields.Date(string='Check Date', )
    bank_name = fields.Char('Bank Name')
    check_ref_id = fields.Many2one('pdc.cheque.collection.line')
    check_post_id = fields.Many2one('post.cheques.line')
    check_bounce_id = fields.Many2one('bounce.cheques.line')
    reason = fields.Text('Reason')
    status = fields.Selection([
        ('none', ''),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('cancel', 'Cancelled')], string='Status',
        default='none')
    post_date = fields.Date(string='Post Date', )
    bounce = fields.Char(string='Reason')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('send', 'Sended'),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='state',
        default='draft', readonly=True)
    # account_type = fields.Selection([
    #     ('current', 'Current'),
    #     ('saving', 'Saving'),
    # ], string="Account Type")
    holder_name = fields.Many2one('res.partner', string='Holder Name')
    debited_account = fields.Many2one('account.journal', string='Debit A/C')
    collected_cheque = fields.Many2one('collection.cheque', )

    # @api.onchange('check_manual_date')
    # def onchange_check_manual_date(self):
    #     if self.check_manual_date:
    #         print('check_manual_date')
    #         self.check_manual_date=self.check_manual_date.strftime("%d-%m-%y")
    # @api.onchange('partner_id')
    # def onchange_partner_id(self):
    #     if self.partner_id:
    #         invoices = self.env['account.move'].search(
    #             [('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid')])
    #         if invoices.mapped('residual'):
    #             self.balance_amount = sum(invoices.mapped('residual'))
    #         else:
    #             self.balance_amount = sum(invoices.mapped('amount_total'))
    #         sub_customers = self.partner_id.sub_customers
    #         if sub_customers:
    #             return {'domain': {'holder_name': [('id', 'in', sub_customers.ids)]}}


            # self.holder_name = self.partner_id
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.holder_name = self.partner_id


class SubChequeCollectionLines(models.Model):
    _name = "sub.cheque.collection.line"

    collection_sub_id = fields.Many2one('executive.cheque.collection')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    sub_customer = fields.Many2one('res.partner', 'Sub Estimator')
    amount_total = fields.Float(string='Cheque Amount', )
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])


    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
                sub_customers = self.partner_id.sub_customers
                if sub_customers:
                    return {'domain': {'sub_customer': [('id', '=', sub_customers.mapped('partner').ids)]}}
