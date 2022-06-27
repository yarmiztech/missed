# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class DatewiseCheque(models.Model):
    _name = "datewise.cheques"
    _description = "DATE Cheques"
    _order = "id desc"

    name = fields.Char("Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)

    user_id = fields.Many2one('res.users', string='Responsible', index=True, track_visibility='onchange',
                              track_sequence=2, default=lambda self: self.env.user)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Done'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")

    payment_date = fields.Date(string='Create Date', default=fields.Date.context_today, required=True, copy=False)
    form_date = fields.Date(string='From Date', copy=False)
    to_date = fields.Date(string='To Date', copy=False)
    today_lines = fields.One2many('today.cheques.line', 'today_id')
    paid_amount = fields.Float(string='Paid Amount', compute='_compute_paid_amount')
    Bal_amount = fields.Float(string='Bal Amount', compute='_compute_paid_amount')
    total_amount = fields.Float(string='Total Amount', compute='_compute_paid_amount')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'datewise.cheques') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('datewise.cheques') or _('New')
        return super(DatewiseCheque, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_confirm(self):
        for line in self.today_lines:
            if line.post_date:
                line.check_line.post_date = line.post_date
                line.check_line.collected_cheque.date = line.post_date
            line.check_line.reason = line.reason
            line.check_line.collected_cheque.reason = line.reason
        self.write({'state': 'validate'})

    # @api.one
    def _compute_paid_amount(self):
        self.Bal_amount = sum(self.today_lines.mapped('balance_amount')) - sum(
            self.today_lines.mapped('amount_total'))
        self.paid_amount = sum(self.today_lines.mapped('amount_total'))
        self.total_amount = sum(self.today_lines.mapped('balance_amount'))

    @api.onchange('payment_date')
    def onchange_payment_date(self):
        today_total_cheques = []
        for each_cheque in self.env['collection.cheque'].search([('state', '!=', 'deposit')]):
            product_line = (0, 0, {
                'check_line': each_cheque.check_line.id,
                'advance_check_line': each_cheque.advance_check_line.id,
                'date': each_cheque.date,
                'collection_cheque_id': each_cheque.id,
                'ref_id': each_cheque.check_line.collection_id.id,
                'partner_id': each_cheque.partner_id.id,
                'balance_amount': each_cheque.balance_amount,
                'amount_total': each_cheque.amount_total,
                'check_no': each_cheque.check_no,
                'check_type': each_cheque.check_type,
                'bank_name': each_cheque.bank_name,
                # 'account_type': each_cheque.account_type,
                'state': each_cheque.state,
                'holder_name': each_cheque.holder_name,
                # 'debited_account': each_cheque.debited_account,
            })
            today_total_cheques.append(product_line)
        self.area_lines = today_total_cheques

    @api.onchange('form_date', 'to_date')
    def onchange_form_date(self):
        today_total_cheques = []
        self.today_lines = False
        for each_cheque in self.env['collection.cheque'].search(
                [('state', '!=', 'deposit'), ('date', '>=', self.form_date), ('date', '<=', self.to_date)]):
            product_line = (0, 0, {
                'check_line': each_cheque.check_line.id,
                'advance_check_line': each_cheque.advance_check_line.id,
                'date': each_cheque.date,
                'collection_cheque_id': each_cheque.id,
                'ref_id': each_cheque.check_line.collection_id.id,
                'partner_id': each_cheque.partner_id.id,
                'balance_amount': each_cheque.balance_amount,
                'amount_total': each_cheque.amount_total,
                'check_no': each_cheque.check_no,
                'check_type': each_cheque.check_type,
                'bank_name': each_cheque.bank_name,
                # 'account_type': each_cheque.account_type,
                'state': each_cheque.state,
                'holder_name': each_cheque.holder_name,
                # 'debited_account': each_cheque.debited_account,
            })
            today_total_cheques.append(product_line)
        self.today_lines = today_total_cheques

    # @api.multi
    def action_cheque_statement(self):

        return self.env.ref('ezp_cash_collection.executive_cheque_collection_id1').report_action(self)


class DatewiseChequesLines(models.Model):
    _name = "datewise.cheques.line"

    today_id = fields.Many2one('datewise.cheques')
    collection_cheque_id = fields.Many2one('collection.cheque')
    check_line = fields.Many2one('executive.cheque.collection.line')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Bal Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    ref_id = fields.Many2one('executive.cheque.collection', string="Source")
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_cheque_relms')
    check_no = fields.Char(string='Cheque No')
    apply = fields.Boolean(default=False, string='Apply')
    check_type = fields.Selection([('cash', 'Cash'), ('pdc', 'PDC'), ], string="Check Type", )
    check_date = fields.Date(string='Check Date', default=fields.Date.today())
    check_manual_date = fields.Date(string='Check Date', )
    new_date = fields.Date(string='Update Date')
    bank_name = fields.Char('Back Name')
    reason = fields.Text('Reason')
    check_post_id = fields.Many2one('post.cheques.line')
    check_bounce_id = fields.Many2one('bounce.cheques.line')
    status = fields.Selection([
        ('none', ''),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('cancel', 'Cancelled')], string='Status',
        default='none')
    post_date = fields.Date(string='Post Date', )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('send', 'Sended'),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='state', readonly=True,
        default='draft')
    # account_type = fields.Selection([
    #     ('current', 'Current'),
    #     ('saving', 'Saving'),
    # ], string="Account Type")
    holder_name = fields.Many2one('res.partner', string='Holder Name')
    debited_account = fields.Many2one('account.journal', string='Debit A/C')
    collected_cheque = fields.Many2one('collection.cheque', )

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))

    @api.onchange('apply')
    def onchange_apply(self):
        if self.apply == True:
            journals = self.env['account.journal'].search(
                [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}


class DatewiseChequeCheck(models.Model):
    _name = "datewise.cheques.test"
    _description = "DATE Cheques"
    _order = "id desc"

    name = fields.Char("Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)

    user_id = fields.Many2one('res.users', string='Responsible', index=True, track_visibility='onchange',
                              track_sequence=2, default=lambda self: self.env.user)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Done'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")

    payment_date = fields.Date(string='Create Date', default=fields.Date.context_today, required=True, copy=False)
    form_date = fields.Date(string='From Date', copy=False)
    to_date = fields.Date(string='To Date', copy=False)
    today_lines = fields.One2many('datewise.cheques.test.line', 'today_id')
    paid_amount = fields.Float(string='Paid Amount', compute='_compute_paid_amount')
    Bal_amount = fields.Float(string='Bal Amount', compute='_compute_paid_amount')
    total_amount = fields.Float(string='Total Amount', compute='_compute_paid_amount')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'datewise.cheques.test') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('datewise.cheques.test') or _('New')
        return super(DatewiseChequeCheck, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_confirm(self):
        for line in self.today_lines:
            line.ref_id.action_confirm()

        self.write({'state': 'validate'})

    # @api.one
    def _compute_paid_amount(self):
        self.Bal_amount = sum(self.today_lines.mapped('balance_amount')) - sum(
            self.today_lines.mapped('amount_total'))
        self.paid_amount = sum(self.today_lines.mapped('amount_total'))
        self.total_amount = sum(self.today_lines.mapped('balance_amount'))

    @api.onchange('payment_date')
    def onchange_payment_date(self):
        today_total_cheques = []
        for each_cheque in self.env['collection.cheque'].search([('state', '=', 'deposit')]):
            product_line = (0, 0, {
                'check_line': each_cheque.check_line.id,
                'advance_check_line': each_cheque.advance_check_line.id,
                'date': each_cheque.date,
                'collection_cheque_id': each_cheque.id,
                'ref_id': each_cheque.check_line.collection_id.id,
                'partner_id': each_cheque.partner_id.id,
                'balance_amount': each_cheque.balance_amount,
                'amount_total': each_cheque.amount_total,
                'check_no': each_cheque.check_no,
                'check_type': each_cheque.check_type,
                'bank_name': each_cheque.bank_name,
                # 'account_type': each_cheque.account_type,
                'state': each_cheque.state,
                'holder_name': each_cheque.holder_name,
                'debited_account': each_cheque.debited_account,
            })
            today_total_cheques.append(product_line)
        self.today_lines = today_total_cheques

    @api.onchange('form_date', 'to_date')
    def onchange_form_date(self):
        today_total_cheques = []
        self.today_lines = False
        for each_cheque in self.env['collection.cheque'].search(
                [('state', '!=', 'deposit'), ('date', '>=', self.form_date), ('date', '<=', self.to_date)]):
            product_line = (0, 0, {
                'check_line': each_cheque.check_line.id,
                'advance_check_line': each_cheque.advance_check_line.id,
                'date': each_cheque.date,
                'collection_cheque_id': each_cheque.id,
                'ref_id': each_cheque.check_line.collection_id.id,
                'partner_id': each_cheque.partner_id.id,
                'balance_amount': each_cheque.balance_amount,
                'amount_total': each_cheque.amount_total,
                'check_no': each_cheque.check_no,
                'check_type': each_cheque.check_type,
                'bank_name': each_cheque.bank_name,
                # 'account_type': each_cheque.account_type,
                'state': each_cheque.state,
                'holder_name': each_cheque.holder_name,
                # 'debited_account': each_cheque.debited_account,
            })
            today_total_cheques.append(product_line)
        self.today_lines = today_total_cheques

    # @api.multi
    def action_cheque_statement(self):

        return self.env.ref('ezp_cash_collection.executive_cheque_collection_id1').report_action(self)


class DatewiseChequesCheckLines(models.Model):
    _name = "datewise.cheques.test.line"

    today_id = fields.Many2one('datewise.cheques.test')
    collection_cheque_id = fields.Many2one('collection.cheque')
    check_line = fields.Many2one('executive.cheque.collection.line')
    advance_check_line = fields.Many2one('advance.cheque.collection.line')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Bal Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    ref_id = fields.Many2one('executive.cheque.collection', string="Source")
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_cheque_relns')
    check_no = fields.Char(string='Cheque No')
    apply = fields.Boolean(default=False, string='Apply')
    check_type = fields.Selection([('cash', 'Cash'), ('pdc', 'PDC'), ], string="Check Type", )
    check_date = fields.Date(string='Check Date', default=fields.Date.today())
    check_manual_date = fields.Date(string='Check Date', )
    new_date = fields.Date(string='Update Date')
    bank_name = fields.Char('Back Name')
    reason = fields.Text('Reason')
    check_post_id = fields.Many2one('post.cheques.line')
    check_bounce_id = fields.Many2one('bounce.cheques.line')
    status = fields.Selection([
        ('none', ''),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('cancel', 'Cancelled')], string='Status',
        default='none')
    post_date = fields.Date(string='Post Date', )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('send', 'Sended'),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='state', readonly=True,
        default='draft')
    # account_type = fields.Selection([
    #     ('current', 'Current'),
    #     ('saving', 'Saving'),
    # ], string="Account Type")
    holder_name = fields.Many2one('res.partner', string='Holder Name')
    debited_account = fields.Many2one('account.journal', string='Debit A/C')
    collected_cheque = fields.Many2one('collection.cheque', )

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))

    @api.onchange('apply')
    def onchange_apply(self):
        if self.apply == True:
            journals = self.env['account.journal'].search(
                [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}


class BulkCollections(models.Model):
    _name = "bulk.collections"
    _description = "DATE Collections"
    _order = "id desc"

    name = fields.Char("Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)

    user_id = fields.Many2one('res.users', string='Cashier', index=True, track_visibility='onchange',
                              track_sequence=2, default=lambda self: self.env.user)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Done'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")

    payment_date = fields.Date(string='Create Date', default=fields.Date.context_today, required=True, copy=False)
    from_date = fields.Date(string='From Date', copy=False)
    to_date = fields.Date(string='To Date', copy=False)
    bulk_lines = fields.One2many('bulk.collections.line', 'bulk_id')
    bulk_all_lines = fields.One2many('bulk.all.line', 'bulk_all_id')
    bulk_cheque_lines = fields.One2many('today.cheques.line', 'bulk_cheque')
    # paid_amount = fields.Float(string='Paid Amount', compute='_compute_paid_amount')
    # Bal_amount = fields.Float(string='Bal Amount', compute='_compute_paid_amount')
    # total_amount = fields.Float(string='Total Amount', compute='_compute_paid_amount')
    sales_person = fields.Many2one('res.users', string="Executive")
    collection_type = fields.Selection([('cash', 'Cash Collections'), ('cheque', 'Cheque Collection'), ('both', 'All')],
                                       default='cash', copy=False, string="Status")
    pending_cheque = fields.Boolean('Pending Cheques')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'bulk.collections') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('bulk.collections') or _('New')
        return super(BulkCollections, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # def action_confirm(self):
    #     for line in self.today_lines:
    #         line.ref_id.action_confirm()
    #
    #     self.write({'state': 'validate'})

    def advance_sub_company_payment(self,sub_c_invoice, line, amount):
        j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

        pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                     # 'amount': check_inv.amount_total,
                                                     'amount': amount,
                                                     'partner_type': 'customer',
                                                     'company_id': line.debited_account.company_id.id,
                                                     'payment_type': 'inbound',
                                                     'payment_method_id': j.id,
                                                     # 'journal_id': line.journal_id.id,
                                                     'journal_id': line.debited_account.id,
                                                     'ref': line.check_no + '=>' + 'Advanced',

                                                     })
        pay_id.action_post()
        pay_id.action_cash_book()

    def sub_company_payment(self,invoices,line,amount):
        stmt = self.env['account.bank.statement']
        if self.collection_type == "cheque":
            for each_inv in invoices:
                # if each_inv.state == 'draft':
                #     each_inv.write({'state':'open'})
                # journal = self.env['account.journal'].search([('name','=','Bank'),('company_id','=',each_inv.company_id.id)])
                journal = line.debited_account
                if not stmt:
                    # _get_payment_info_JSON
                    # bal = sum(self.env['account.move.line'].search([('journal_id', '=', line.debited_account.id)]).mapped(
                    #     'debit'))

                    if self.env['account.bank.statement'].search([('company_id', '=', journal.company_id.id),
                                                                  ('journal_id', '=', journal.id)]):
                        bal = self.env['account.bank.statement'].search(
                            [('company_id', '=', journal.company_id.id),
                             ('journal_id', '=', journal.id)])[0].balance_end_real
                    else:
                        bal = 0

                    stmt = self.env['account.bank.statement'].create({'name': each_inv.partner_id.name,
                                                                      'balance_start': bal,
                                                                      # 'journal_id': line.journal_id.id,
                                                                      'journal_id': journal.id,
                                                                      # 'balance_end_real': line.amount_total,
                                                                      'balance_end_real': bal+line.amount_total,
                                                                       'company_id':each_inv.company_id.id
                                                                      })

                payment_list = []
                pay_id_list = []
                amount = amount
                actual =0
                if each_inv:
                        if amount:
                            if each_inv.amount_total >= amount:
                                actual=amount
                                product_line = (0, 0, {
                                    'date': line.date,
                                    'name': each_inv.display_name,
                                    'partner_id': each_inv.partner_id.id,
                                    'ref': each_inv.display_name,
                                    'amount': amount
                                })
                                amount = amount - amount
                                payment_list.append(product_line)
                            else:
                                if each_inv.amount_total != 0:
                                    amount = amount-each_inv.amount_total
                                    actual = each_inv.amount_total
                                    product_line = (0, 0, {
                                        'date': line.date,
                                        'name': each_inv.display_name,
                                        'partner_id': each_inv.partner_id.id,
                                        'ref': each_inv.display_name,
                                        'amount': each_inv.amount_total
                                    })
                                    payment_list.append(product_line)

                            j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

                            pay_id = self.env['account.payment'].create({'partner_id': each_inv.partner_id.id,
                                                                         # 'amount': check_inv.amount_total,
                                                                         'amount': actual,
                                                                         'partner_type': 'customer',
                                                                         'company_id': each_inv.company_id.id,
                                                                         'payment_type': 'inbound',
                                                                         'payment_method_id': j.id,
                                                                         # 'journal_id': line.journal_id.id,
                                                                         'journal_id': journal.id,
                                                                         'ref': line.check_no+'=>'+'Cleared',
                                                                         'invoice_ids': [(6, 0, each_inv.ids)]
                                                                         })
                            # pay_id.action_validate_invoice_payment()
                            pay_id.action_post()
                            invoices = self.env['account.move'].search(
                                [('partner_id', '=', each_inv.partner_id.id),('company_id','=',each_inv.company_id.id), ('state', '!=', 'paid')])
                            if invoices.mapped('amount_residual'):
                                balance_amount = sum(invoices.mapped('amount_residual'))
                            else:
                                balance_amount = sum(invoices.mapped('amount_total'))
                            balance_amount += self.env['partner.ledger.customer'].search(
                                [('partner_id', '=', each_inv.partner_id.id),
                                 ('description', '=', 'Opening Balance')]).balance
                            balance_ref = self.env['partner.ledger.customer'].search([('company_id','=',self.env.user.company_id.id),('partner_id', '=', each_inv.partner_id.id)])
                            if balance_ref:
                                balance_amount = self.env['partner.ledger.customer'].search([('company_id','=',self.env.user.company_id.id),('partner_id', '=', each_inv.partner_id.id)])[-1].balance


                            for m in each_inv:
                                led = self.env['partner.ledger.customer'].search([('partner_id','=',each_inv.partner_id.id),('company_id','=',each_inv.company_id.id),('invoice_id','=',m.id)])
                                leds = self.env['partner.ledgers.customer'].search([('partner_id','=',each_inv.partner_id.id),('company_id','=',each_inv.company_id.id),('invoice_id','=',m.id)])
                                for l in led:
                                    # l.description = line.check_no+'=>'+'Cleared'
                                    # l.credit += actual
                                    # l.balance = balance_amount-actual
                                    # l.account_journal = journal.id
                                    # l.account = journal.default_debit_account_id.id
                                    # l.paid_date = datetime.today().date()
                                    # l.account_move =pay_id.move_line_ids.mapped('move_id')[0].id
                                    self.env['partner.ledger.customer'].sudo().create({
                                        'date': datetime.today().date(),
                                        'partner_id': line.partner_id.id,
                                        'company_id': m.company_id.id,
                                        'credit': actual,
                                        'check_only': True,
                                        # 'account_move': pay_id.move_line_ids.mapped('move_id')[0].id,
                                        'account_move': pay_id.move_id.id,
                                        'balance': balance_amount-actual,
                                        'description': 'Cheque No' + '=>' + line.check_no,
                                        'account_journal': journal.id,
                                        'account': journal.payment_debit_account_id.id,
                                        'paid_date': datetime.today().date()

                                    })

                                for ls in leds:
                                    ls.description = line.check_no+'=>'+'Cleared'
                                    ls.credit += actual
                                    ls.account_journal = journal.id
                                    ls.account = journal.payment_debit_account_id.id
                                    ls.paid_date = datetime.today().date()

                            # self.action_partner_ledger(each_inv,actual)
                            # for k in pay_id.move_line_ids:
                            for k in pay_id.line_ids:
                                pay_id_list.append(k.id)
                            # line.payments += pay_id
                            # executive_rec = self.env['collection.cheque'].search([('check_line','=',line.check_line.id)])
                            # # executive_rec.amount_total += line.amount_total
                            # executive_rec.al_state =True
                else:
                    j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

                    pay_id = self.env['account.payment'].create({'partner_id': each_inv.partner_id.id,
                                                                 # 'amount': check_inv.amount_total,
                                                                 'amount': actual,
                                                                 'partner_type': 'customer',
                                                                 'company_id': each_inv.company_id.id,
                                                                 'payment_type': 'inbound',
                                                                 'payment_method_id': j.id,
                                                                 # 'journal_id': line.journal_id.id,
                                                                 'journal_id': journal.id,
                                                                 'ref': line.check_no+'=>'+'Cleared',

                                                                 })
                    pay_id.action_post()
                    pay_id.action_cash_book()
                    invoices = self.env['account.move'].search(
                        [('partner_id', '=', each_inv.partner_id.id),
                         ('company_id', '=', each_inv.company_id.id),('state', '!=', 'paid')])
                    if invoices.mapped('amount_residual'):
                        balance_amount = sum(invoices.mapped('amount_residual'))
                    else:
                        balance_amount = sum(invoices.mapped('amount_total'))
                    balance_amount += self.env['partner.ledger.customer'].search(
                        [('partner_id', '=', each_inv.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                    balance_amount = self.env['partner.ledger.customer'].search(
                        [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', each_inv.partner_id.id)])[-1].balance

                    for m in each_inv:
                        led = self.env['partner.ledger.customer'].search(
                            [('partner_id', '=', m.partner_id.id), ('company_id', '=', m.company_id.id)])
                        leds = self.env['partner.ledgers.customer'].search(
                            [('partner_id', '=', m.partner_id.id), ('company_id', '=', m.company_id.id)])

                        for l in led:
                            # l.description = line.check_no + '=>' + 'Cleared',
                            # l.credit += actual
                            # l.balance = balance_amount-actual
                            # l.account_journal = journal.id
                            # l.account = journal.default_debit_account_id.id
                            # l.paid_date = datetime.today().date()
                            self.env['partner.ledger.customer'].sudo().create({
                                'date': datetime.today().date(),
                                'partner_id': line.partner_id.id,
                                'company_id': m.company_id.id,
                                'credit': actual,
                                'check_only': True,
                                # 'account_move': pay_id.move_line_ids.mapped('move_id')[0].id,
                                'account_move': pay_id.move_id.id,
                                'balance': balance_amount-actual,
                                'description': line.check_no + '=>' + 'Cleared Amount',
                                'account_journal': journal.id,
                                'account': journal.payment_debit_account_id.id,
                                'paid_date': datetime.today().date()

                            })

                        for ls in leds:
                            ls.description = line.check_no + '=>' + 'Cleared',
                            ls.credit += actual
                            ls.account_journal = journal.id
                            ls.account = journal.payment_debit_account_id.id
                            ls.paid_date = datetime.today().date()


                if stmt:
                    if amount:

                        j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
                        pay_id = self.env['account.payment'].create({'partner_id': each_inv.partner_id.id,
                                                                     # 'amount': check_inv.amount_total,
                                                                     'amount': amount,
                                                                     'partner_type': 'customer',
                                                                     'company_id': each_inv.company_id.id,
                                                                     'payment_type': 'inbound',
                                                                     'payment_method_id': j.id,
                                                                     # 'journal_id': line.journal_id.id,
                                                                     'journal_id': journal.id,
                                                                     'ref': line.check_no,

                                                                     })
                        pay_id.action_post()
                        pay_id.action_cash_book()
                        for m in each_inv:
                            bal = sum(
                                self.env['account.move.line'].search(
                                    [('journal_id', '=', journal.id)]).mapped('debit'))
                            bal_ref = self.env['partner.ledger.customer'].search([('company_id','=', m.company_id.id),('partner_id', '=', m.partner_id.id)])
                            if bal_ref:
                                bal = self.env['partner.ledger.customer'].search([('company_id','=', m.company_id.id),('partner_id', '=', m.partner_id.id)])[-1].balance

                            self.env['partner.ledger.customer'].sudo().create({
                                'date': datetime.today().date(),
                                # 'invoice_id': m.id,
                                'check_only': True,
                                'partner_id': m.partner_id.id,
                                # 'product_id': m.invoice_line_ids[0].product_id.id,
                                'company_id': m.company_id.id,
                                # 'price_units': m.inv_mc_qty,
                                # 'uom': m.invoice_line_ids[0].uom_id.id,
                                # 'rate': m.invoice_line_ids[0].price_unit,
                                # 'credit': amount,
                                'credit':amount,
                                'balance':bal,
                                'description': 'Cheque No'+ '=>' +line.check_no,
                                'account_journal':journal.id,
                                # 'account_move' : pay_id.move_line_ids.mapped('move_id')[0].id,
                                'account_move' : pay_id.move_id.id,
                                 'account':journal.payment_debit_account_id.id,
                                'paid_date':datetime.today().date()

                            })
                            self.env['partner.ledgers.customer'].create({
                                'date': datetime.today().date(),
                                # 'invoice_id': m.id,
                                'partner_id': m.partner_id.id,
                                # 'product_id': m.invoice_line_ids[0].product_id.id,
                                'company_id': m.company_id.id,
                                # 'price_units': m.inv_mc_qty,
                                # 'uom': m.invoice_line_ids[0].uom_id.id,
                                # 'rate': m.invoice_line_ids[0].price_unit,
                                'credit': amount,
                                'month':str(datetime.today().date().month),
                                'debit':amount,
                                'description':line.check_no + '=>' +'Advance Amount',
                                'account_journal':journal.id,
                                'account':journal.payment_debit_account_id.id,
                                'paid_date':datetime.today().date()

                            })

                            # led = self.env['partner.ledger.customer'].search(
                            #     [('partner_id', '=', m.partner_id.id),
                            #      ('company_id', '=', m.company_id.id),('invoice_id','=',m.id)])
                            # if led:
                            #     led.description = line.check_no + '=>' +'Advance Amount',
                            #     led.debit += amount
                            #     led.account_journal = journal.id
                            #     led.account = journal.default_debit_account_id.id
                            #     led.paid_date = datetime.today().date()

                    stmt.line_ids = payment_list
                    # stmt.move_line_ids = pay_id_list
                    # stmt.write({'state': 'confirm'})
                    self.write({'state': 'validate'})



    def action_confirm(self):
        if self.collection_type == "cash":
            for line in self.bulk_lines:
                if line.amount_total == 0.0:
                    raise UserError(_("Please mention paid amount for this partner %s ")%(line.partner_id.name))
                cv = 0
                # if line.check_type == 'cheque':
                #     journal = self.env['account.journal'].search(
                #         [('name', '=', 'Bank'), ('company_id', '=', self.env.user.company_id.id)])
                # else:
                journal = line.journal_id.id
                stmt = self.env['account.bank.statement']
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
                                                                      # 'balance_end_real': line.amount_total
                                                                      'balance_end_real': bal+line.amount_total

                                                                      })

                payment_list = []
                pay_id_list = []
                account = self.env['account.move'].search([('partner_id','=',line.partner_id.id),('state','=','posted')])
                amount = line.amount_total
                actual =0
                for check_inv in account:
                    if amount:
                        if check_inv.amount_total >= amount:
                            actual=amount
                            product_line = (0, 0, {
                                'date': line.payment_date,
                                'name': check_inv.display_name,
                                'partner_id': line.partner_id.id,
                                'ref': check_inv.display_name,
                                'amount': amount
                            })
                            amount = amount - amount
                            payment_list.append(product_line)
                        else:
                            if check_inv.amount_total != 0:
                                amount = amount-check_inv.amount_total
                                actual =check_inv.amount_total
                                product_line = (0, 0, {
                                    'date': self.payment_date,
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
                                                                     'partner_type': 'customer',
                                                                     'company_id': self.env.user.company_id.id,
                                                                     'payment_type': 'inbound',
                                                                     'payment_method_id': j.id,
                                                                     # 'journal_id': line.journal_id.id,
                                                                     'journal_id': line.journal_id.id,
                                                                     'ref': 'Cash Collection',
                                                                     'invoice_ids': [(6, 0, check_inv.ids)]
                                                                     })
                        # pay_id.action_validate_invoice_payment()
                        pay_id.action_post()
                        # for k in pay_id.move_line_ids:
                        for k in pay_id.line_ids:
                            pay_id_list.append(k.id)
                        # line.payments += pay_id
                        executive_rec = self.env['executive.collection.record'].search(
                            [('collection_line_id', '=', line.collection_line.id)])
                        # executive_rec.amount_total += line.amount_total
                        executive_rec.status =True


            if stmt:
                stmt.line_ids = payment_list
                stmt.move_line_ids = pay_id_list
                # stmt.write({'state': 'confirm'})
                self.write({'state': 'validate'})

        if self.collection_type == "cheque":
            for line in self.bulk_cheque_lines:
                stmt = self.env['account.bank.statement']
                if self.env['account.move'].search([('company_id','=',self.env.user.company_id.id),('partner_id','=',line.partner_id.id)]):
                    if line.amount_total == 0.0:
                        raise UserError(_("Please mention paid amount for this partner %s ")%(line.partner_id.name))
                    cv = 0
                    # if line.check_type == 'cheque':
                    #     journal = self.env['account.journal'].search(
                    #         [('name', '=', 'Bank'), ('company_id', '=', self.env.user.company_id.id)])
                    # else:
                    # journal = line.journal_id.id
                    journal = self.env['account.journal'].search([('name','=','Bank'),('company_id','=',1)])
                    if not stmt:
                        # _get_payment_info_JSON
                        # bal = sum(self.env['account.move.line'].search([('journal_id', '=', line.debited_account.id)]).mapped(
                        #     'debit'))

                        if self.env['account.bank.statement'].search([('company_id', '=', journal.company_id.id),
                                                                      ('journal_id', '=', journal.id)]):
                            bal = self.env['account.bank.statement'].search(
                                [('company_id', '=', journal.company_id.id),
                                 ('journal_id', '=', journal.id)])[0].balance_end_real
                        else:
                            bal = 0


                        stmt = self.env['account.bank.statement'].create({'name': line.partner_id.name,
                                                                          'balance_start': bal,
                                                                          # 'journal_id': line.journal_id.id,
                                                                          'journal_id': journal.id,
                                                                          'balance_end_real': bal+line.amount_total

                                                                          })

                    payment_list = []
                    pay_id_list = []
                    account = self.env['account.move']
                    check_inv = self.env['account.move']
                    account = self.env['account.move'].search([('company_id','=',self.env.user.company_id.id),('partner_id','=',line.partner_id.id),('state','=','posted')])
                    amount = line.amount_total
                    actual =0
                    if account:
                        for check_inv in account:
                            if amount:
                                if check_inv.amount_total >= amount:
                                    # sub_c_invoice = check_inv.estimate_id.invoice_ids.filtered(lambda a: a.company_id.id != 1)
                                    sub_c_invoice = check_inv.estimate_id.invoice_ids.filtered(lambda a: a.company_id.id == line.debited_account.company_id.id)
                                    if not sub_c_invoice:
                                        continue
                                    actual=amount
                                    if sub_c_invoice:
                                        self.sub_company_payment(sub_c_invoice,line,amount)
                                    else:
                                        self.advance_sub_company_payment(sub_c_invoice, line, amount)
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
                                        sub_c_invoice = check_inv.estimate_id.invoice_ids.filtered(
                                            lambda a: a.company_id.id == line.debited_account.company_id.id)
                                        if not sub_c_invoice:
                                            continue
                                        self.sub_company_payment(sub_c_invoice, line,amount)
                                        amount = amount-check_inv.amount_total
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
                                                                             'partner_type': 'customer',
                                                                             'company_id': self.env.user.company_id.id,
                                                                             'payment_type': 'inbound',
                                                                             'payment_method_id': j.id,
                                                                             # 'journal_id': line.journal_id.id,
                                                                             'journal_id': journal.id,
                                                                             'ref': line.check_no+'=>'+'Cleared',
                                                                             'invoice_ids': [(6, 0, check_inv.ids)]
                                                                             })
                                # pay_id.action_validate_invoice_payment()
                                pay_id.action_post()
                                invoices = self.env['account.move'].search(
                                    [('partner_id', '=', line.partner_id.id),
                                     ('company_id', '=', self.env.user.company_id.id),('state', '!=', 'paid')])
                                if invoices.mapped('amount_residual'):
                                    balance_amount = sum(invoices.mapped('amount_residual'))
                                else:
                                    balance_amount = sum(invoices.mapped('amount_total'))
                                balance_amount += self.env['partner.ledger.customer'].search(
                                    [('partner_id', '=', line.partner_id.id),
                                     ('description', '=', 'Opening Balance')]).balance
                                balance_amount_ref = self.env['partner.ledger.customer'].search([('company_id','=',self.env.user.company_id.id),('partner_id', '=', line.partner_id.id)])
                                if balance_amount_ref:
                                   balance_amount = self.env['partner.ledger.customer'].search([('company_id','=',self.env.user.company_id.id),('partner_id', '=', line.partner_id.id)])[-1].balance


                                for m in check_inv:
                                    led = self.env['partner.ledger.customer'].search(
                                        [('partner_id', '=', m.partner_id.id),
                                         ('company_id', '=', m.company_id.id),('invoice_id','=',m.id)])
                                    leds = self.env['partner.ledgers.customer'].search(
                                        [('partner_id', '=', m.partner_id.id),
                                         ('company_id', '=', m.company_id.id),('invoice_id','=',m.id)])

                                    for l in led:
                                        # l.description = line.check_no + '=>' + 'Cleared',
                                        # l.credit += actual
                                        # l.balance = balance_amount-actual
                                        # l.account_journal = journal.id
                                        # l.account = journal.default_debit_account_id.id
                                        # l.paid_date = datetime.today().date()
                                        # l.account_move = pay_id.move_line_ids.mapped('move_id')[0].id
                                        self.env['partner.ledger.customer'].sudo().create({
                                            'date': datetime.today().date(),
                                            'partner_id': line.partner_id.id,
                                            'company_id': m.company_id.id,
                                            'credit': actual,
                                            'check_only': True,
                                            # 'account_move': pay_id.move_line_ids.mapped('move_id')[0].id,
                                            'account_move': pay_id.move_id.id,
                                            'balance': balance_amount - actual,
                                            'description': line.check_no + '=>' + 'Cleared Amount',
                                            'account_journal': journal.id,
                                            'account': journal.payment_debit_account_id.id,
                                            'paid_date': datetime.today().date()

                                        })

                                    for ls in leds:
                                        ls.description = line.check_no + '=>' + 'Cleared',
                                        ls.credit += actual
                                        ls.account_journal = journal.id
                                        ls.account = journal.payment_debit_account_id.id
                                        ls.paid_date = datetime.today().date()

                                # for k in pay_id.move_line_ids:
                                for k in pay_id.line_ids:
                                    pay_id_list.append(k.id)
                                # line.payments += pay_id
                                executive_rec = self.env['collection.cheque'].search([('check_line','=',line.check_line.id)])
                                # executive_rec.amount_total += line.amount_total
                                executive_rec.al_state =True
                    else:
                        j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
                        if actual:
                            pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                                         # 'amount': check_inv.amount_total,
                                                                         'amount': actual,
                                                                         'partner_type': 'customer',
                                                                         'company_id': self.env.user.company_id.id,
                                                                         'payment_type': 'inbound',
                                                                         'payment_method_id': j.id,
                                                                         # 'journal_id': line.journal_id.id,
                                                                         'journal_id': journal.id,
                                                                         'ref': line.check_no,

                                                                         })
                            pay_id.action_post()
                            pay_id.action_cash_book()
                            invoices = self.env['account.move'].search(
                                [('partner_id', '=', line.partner_id.id),
                                 ('company_id', '=', self.env.user.company_id.id),('state', '!=', 'paid')])
                            if invoices.mapped('amount_residual'):
                                balance_amount = sum(invoices.mapped('amount_residual'))
                            else:
                                balance_amount = sum(invoices.mapped('amount_total'))
                            balance_amount += self.env['partner.ledger.customer'].search(
                                [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                            balance_amount = self.env['partner.ledger.customer'].search(
                                [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', line.partner_id.id)])[-1].balance
                            if check_inv:
                                for m in check_inv:
                                    led = self.env['partner.ledger.customer'].search(
                                        [('partner_id', '=', m.partner_id.id),
                                         ('company_id', '=', m.company_id.id)])
                                    leds = self.env['partner.ledgers.customer'].search(
                                        [('partner_id', '=', m.partner_id.id),
                                         ('company_id', '=', m.company_id.id)])
                                    for l in led:
                                        # l.description = line.check_no + '=>' + 'Cleared',
                                        # l.credit += actual
                                        # l.balance = balance_amount-actual
                                        # l.account_journal = journal.id
                                        # l.account = journal.default_debit_account_id.id
                                        # l.paid_date = datetime.today().date()
                                        self.env['partner.ledger.customer'].sudo().create({
                                            'date': datetime.today().date(),
                                            'partner_id': line.partner_id.id,
                                            'company_id': m.company_id.id,
                                            'credit': actual,
                                            'check_only': True,
                                            # 'account_move': pay_id.move_line_ids.mapped('move_id')[0].id,
                                            'account_move': pay_id.move_id.id,
                                            'balance': balance_amount-actual,
                                            'description': line.check_no + '=>' + 'Cleared Amount',
                                            'account_journal': journal.id,
                                            'account': journal.payment_debit_account_id.id,
                                            'paid_date': datetime.today().date()

                                        })


                                    for ls in leds:
                                        ls.description = line.check_no + '=>' + 'Cleared',
                                        ls.credit += actual
                                        ls.account_journal = journal.id
                                        ls.account = journal.payment_debit_account_id.id
                                        ls.paid_date = datetime.today().date()
                        else:
                            # for m in check_inv:
                                balance_amount = 0
                                balance_amount += self.env['partner.ledger.customer'].search(
                                    [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                                if self.env['partner.ledger.customer'].search(
                                    [('company_id', '=', self.env.user.company_id.id),
                                     ('partner_id', '=', line.partner_id.id)]):
                                        balance_amount = self.env['partner.ledger.customer'].search(
                                                        [('company_id', '=', self.env.user.company_id.id),
                                                         ('partner_id', '=', line.partner_id.id)])[-1].balance
                                led = self.env['partner.ledger.customer'].search(
                                    [('partner_id', '=', line.partner_id.id),
                                     ('company_id', '=', line.debited_account.company_id.id)])
                                leds = self.env['partner.ledgers.customer'].search(
                                    [('partner_id', '=', line.partner_id.id),
                                     ('company_id', '=', line.debited_account.company_id.id)])
                                for l in led:
                                    # l.description = line.check_no + '=>' + 'Cleared',
                                    # l.credit += actual
                                    # l.balance = balance_amount-actual
                                    # l.account_journal = journal.id
                                    # l.account = journal.default_debit_account_id.id
                                    # l.paid_date = datetime.today().date()
                                    self.env['partner.ledger.customer'].sudo().create({
                                        'date': datetime.today().date(),
                                        'partner_id': line.partner_id.id,
                                        'company_id': line.debited_account.company_id.id,
                                        'credit': actual,
                                        'check_only': True,
                                        # 'account_move': pay_id.move_line_ids.mapped('move_id')[0].id,
                                        'account_move': pay_id.move_id.id,
                                        'balance': balance_amount-actual,
                                        'description': line.check_no + '=>' + 'Cleared Amount',
                                        'account_journal': journal.id,
                                        'account': journal.payment_debit_account_id.id,
                                        'paid_date': datetime.today().date()

                                    })


                                for ls in leds:
                                    ls.description = line.check_no + '=>' + 'Cleared',
                                    ls.credit += actual
                                    ls.account_journal = journal.id
                                    ls.account = journal.payment_debit_account_id.id
                                    ls.paid_date = datetime.today().date()

                                led = self.env['partner.ledger.customer'].search(
                                    [('partner_id', '=', line.partner_id.id),
                                     ('company_id', '=', 1)])
                                leds = self.env['partner.ledgers.customer'].search(
                                    [('partner_id', '=', line.partner_id.id),
                                     ('company_id', '=', 1)])
                                for l in led:
                                    # l.description = line.check_no + '=>' + 'Cleared',
                                    # l.credit += actual
                                    # l.balance = balance_amount-actual
                                    # l.account_journal = journal.id
                                    # l.account = journal.default_debit_account_id.id
                                    # l.paid_date = datetime.today().date()
                                    self.env['partner.ledger.customer'].sudo().create({
                                        'date': datetime.today().date(),
                                        'partner_id': line.partner_id.id,
                                        'company_id': 1,
                                        'credit': actual,
                                        'check_only': True,
                                        # 'account_move': pay_id.move_line_ids.mapped('move_id')[0].id,
                                        'balance': balance_amount - actual,
                                        'description': line.check_no + '=>' + 'Cleared Amount',
                                        'account_journal': journal.id,
                                        'account': journal.payment_debit_account_id.id,
                                        'paid_date': datetime.today().date()

                                    })

                                for ls in leds:
                                    ls.description = line.check_no + '=>' + 'Cleared',
                                    ls.credit += actual
                                    ls.account_journal = journal.id
                                    ls.account = journal.payment_debit_account_id.id
                                    ls.paid_date = datetime.today().date()

                    if stmt:
                        if amount:
                            if not self.env['account.move'].search([('partner_id','=',line.partner_id.id)]):
                                j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
                                journal_sub = self.env['account.journal'].search([('name','=',journal.name),('company_id','=',line.debited_account.company_id.id)])
                                if line.holder_name:
                                    partner = line.holder_name
                                else:
                                    partner = line.partner_id

                                pay_id = self.env['account.payment'].create({'partner_id': partner.id,
                                                                             # 'amount': check_inv.amount_total,
                                                                             'amount': amount,
                                                                             'partner_type': 'customer',
                                                                             'company_id': line.debited_account.company_id.id,
                                                                             'payment_type': 'inbound',
                                                                             'payment_method_id': j.id,
                                                                             # 'journal_id': line.journal_id.id,
                                                                             'journal_id': journal_sub.id,
                                                                             'ref': line.check_no,

                                                                             })
                                pay_id_main = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                                             # 'amount': check_inv.amount_total,
                                                                             'amount': amount,
                                                                             'partner_type': 'customer',
                                                                             'company_id': self.env.user.company_id.id,
                                                                             'payment_type': 'inbound',
                                                                             'payment_method_id': j.id,
                                                                             # 'journal_id': line.journal_id.id,
                                                                             'journal_id': journal.id,
                                                                             'ref': line.check_no,

                                                                             })
                                pay_id.action_post()
                                pay_id_main.post()
                                pay_id.action_cash_book()
                                pay_id_main.action_cash_book()
                                invoices = self.env['account.move'].search(
                                    [('partner_id', '=', line.partner_id.id),
                                     ('company_id', '=', self.env.user.company_id.id), ('state', '!=', 'paid')])
                                if invoices.mapped('amount_residual'):
                                    balance_amount = sum(invoices.mapped('amount_residual'))
                                else:
                                    balance_amount = sum(invoices.mapped('amount_total'))
                                balance_amount += self.env['partner.ledger.customer'].search(
                                    [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                                if self.env['partner.ledger.customer'].search(
                                    [('company_id', '=', self.env.user.company_id.id),
                                     ('partner_id', '=', line.partner_id.id)]):
                                    balance_amount = self.env['partner.ledger.customer'].search(
                                        [('company_id', '=', self.env.user.company_id.id),
                                         ('partner_id', '=', line.partner_id.id)])[-1].balance

                                self.env['partner.ledger.customer'].sudo().create({
                                    'date': datetime.today().date(),
                                    # 'invoice_id': m.id,
                                    'check_only': True,
                                    'partner_id': line.partner_id.id,
                                    # 'product_id': m.invoice_line_ids[0].product_id.id,
                                    'company_id': self.env.user.company_id.id,
                                    # 'price_units': m.inv_mc_qty,
                                    # 'uom': m.invoice_line_ids[0].uom_id.id,
                                    # 'rate': m.invoice_line_ids[0].price_unit,
                                    # 'credit': amount,
                                    'credit': amount,
                                    # 'account_move': pay_id.move_line_ids.mapped('move_id')[0].id,
                                    'balance': balance_amount - amount,
                                    'description':  'Cheque No'+ '=>' + line.check_no,
                                    'account_journal': journal.id,
                                    'account': journal.payment_debit_account_id.id,
                                    'paid_date': datetime.today().date()

                                })
                                if partner:
                                        invoices = self.env['account.move'].search(
                                            [('partner_id', '=', partner.id),
                                             ('company_id', '=', journal_sub.company_id.id), ('state', '!=', 'paid')])
                                        if invoices.mapped('amount_residual'):
                                            balance_amount = sum(invoices.mapped('amount_residual'))
                                        else:
                                            balance_amount = sum(invoices.mapped('amount_total'))
                                        balance_amount += self.env['partner.ledger.customer'].search(
                                            [('partner_id', '=', partner.id),
                                             ('description', '=', 'Opening Balance')]).balance
                                        if self.env['partner.ledger.customer'].search(
                                                [('company_id', '=', journal_sub.company_id.id),
                                                 ('partner_id', '=',partner.id)]):
                                            balance_amount = self.env['partner.ledger.customer'].search(
                                                [('company_id', '=', journal_sub.company_id.id),
                                                 ('partner_id', '=', partner.id)])[-1].balance
                                        self.env['partner.ledger.customer'].sudo().create({
                                            'date': datetime.today().date(),
                                            # 'invoice_id': m.id,
                                            'check_only': True,
                                            'partner_id': partner.id,
                                            # 'product_id': m.invoice_line_ids[0].product_id.id,
                                            'company_id': line.debited_account.company_id.id,
                                            # 'price_units': m.inv_mc_qty,
                                            # 'uom': m.invoice_line_ids[0].uom_id.id,
                                            # 'rate': m.invoice_line_ids[0].price_unit,
                                            # 'credit': amount,
                                            'credit': amount,
                                            # 'account_move': pay_id.move_line_ids.mapped('move_id')[0].id,
                                            'balance': balance_amount - amount,
                                            'description':  'Cheque No'+ '=>' + line.check_no,
                                            'account_journal': journal.id,
                                            'account': journal.payment_debit_account_id.id,
                                            'paid_date': datetime.today().date()

                                        })
                                self.env['partner.ledgers.customer'].create({
                                    'date': datetime.today().date(),
                                    # 'invoice_id': m.id,
                                    'month': str(datetime.today().date().month),
                                    'partner_id': line.partner_id.id,
                                    # 'product_id': m.invoice_line_ids[0].product_id.id,
                                    'company_id': self.env.user.company_id.id,
                                    # 'price_units': m.inv_mc_qty,
                                    # 'uom': m.invoice_line_ids[0].uom_id.id,
                                    # 'rate': m.invoice_line_ids[0].price_unit,
                                    'credit': amount,
                                    'debit': amount,
                                    'description': line.check_no + '=>' + 'Advance Amount',
                                    'account_journal': journal.id,
                                    'account': journal.payment_debit_account_id.id,
                                    'paid_date': datetime.today().date()

                                })
                                invoices = self.env['account.move'].search(
                                    [('partner_id', '=', line.partner_id.id),
                                     ('company_id', '=', journal_sub.company_id.id), ('state', '!=', 'paid')])
                                if invoices.mapped('amount_residual'):
                                    balance_amount = sum(invoices.mapped('amount_residual'))
                                else:
                                    balance_amount = sum(invoices.mapped('amount_total'))
                                balance_amount += self.env['partner.ledger.customer'].search(
                                    [('partner_id', '=', line.partner_id.id),('company_id','=',journal_sub.company_id.id),('description', '=', 'Opening Balance')]).balance
                                if self.env['partner.ledger.customer'].search(
                                    [('company_id', '=', journal_sub.company_id.id),
                                     ('partner_id', '=', line.partner_id.id)]):
                                    balance_amount = self.env['partner.ledger.customer'].search(
                                                                [('company_id', '=', journal_sub.company_id.id),
                                                                 ('partner_id', '=', line.partner_id.id)])[-1].balance

                                self.env['partner.ledger.customer'].sudo().create({
                                                            'date': datetime.today().date(),
                                                            # 'invoice_id': m.id,
                                                            'check_only': True,
                                                            'partner_id': line.partner_id.id,
                                                            # 'product_id': m.invoice_line_ids[0].product_id.id,
                                                            'company_id': journal_sub.company_id.id,
                                                            # 'price_units': m.inv_mc_qty,
                                                            # 'uom': m.invoice_line_ids[0].uom_id.id,
                                                            # 'rate': m.invoice_line_ids[0].price_unit,
                                                            # 'credit': amount,
                                                            'credit': amount,
                                                            # 'account_move': pay_id.move_line_ids.mapped('move_id')[0].id,
                                                            'balance': balance_amount - amount,
                                                            'description':  'Cheque No'+ '=>' + line.check_no,
                                                            'account_journal': journal_sub.id,
                                                            'account': journal.payment_debit_account_id.id,
                                                            'paid_date': datetime.today().date()

                                                        })
                                self.env['partner.ledgers.customer'].create({
                                    'date': datetime.today().date(),
                                    # 'invoice_id': m.id,
                                    'month': str(datetime.today().date().month),
                                    'partner_id': line.partner_id.id,
                                    # 'product_id': m.invoice_line_ids[0].product_id.id,
                                    'company_id': journal_sub.company_id.id,
                                    # 'price_units': m.inv_mc_qty,
                                    # 'uom': m.invoice_line_ids[0].uom_id.id,
                                    # 'rate': m.invoice_line_ids[0].price_unit,
                                    'credit': amount,
                                    'debit': amount,
                                    'description': line.check_no + '=>' + 'Advance Amount',
                                    'account_journal': journal_sub.id,
                                    'account': journal.payment_debit_account_id.id,
                                    'paid_date': datetime.today().date()

                                })

                            else:

                                j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
                                pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                                             # 'amount': check_inv.amount_total,
                                                                             'amount': amount,
                                                                             'partner_type': 'customer',
                                                                             'company_id': self.env.user.company_id.id,
                                                                             'payment_type': 'inbound',
                                                                             'payment_method_id': j.id,
                                                                             # 'journal_id': line.journal_id.id,
                                                                             'journal_id': journal.id,
                                                                             'ref': line.check_no,

                                                                             })
                                pay_id.action_post()
                                pay_id.action_cash_book()
                                invoices = self.env['account.move'].search(
                                    [('partner_id', '=', line.partner_id.id),
                                     ('company_id', '=', self.env.user.company_id.id),('state', '!=', 'paid')])
                                if invoices.mapped('amount_residual'):
                                    balance_amount = sum(invoices.mapped('amount_residual'))
                                else:
                                    balance_amount = sum(invoices.mapped('amount_total'))
                                balance_amount += self.env['partner.ledger.customer'].search(
                                    [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                                balance_amount = self.env['partner.ledger.customer'].search(
                                    [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', line.partner_id.id)])[-1].balance

                                self.env['partner.ledger.customer'].sudo().create({
                                    'date': datetime.today().date(),
                                    # 'invoice_id': m.id,
                                    'check_only': True,
                                    'partner_id': line.partner_id.id,
                                    # 'product_id': m.invoice_line_ids[0].product_id.id,
                                    'company_id': self.env.user.company_id.id,
                                    # 'price_units': m.inv_mc_qty,
                                    # 'uom': m.invoice_line_ids[0].uom_id.id,
                                    # 'rate': m.invoice_line_ids[0].price_unit,
                                    # 'credit': amount,
                                    'credit': amount,
                                    'account_move': pay_id.move_id.id,
                                    'balance':balance_amount-amount,
                                    'description':  'Cheque No'+ '=>' + line.check_no,
                                    'account_journal': journal.id,
                                    'account': journal.payment_debit_account_id.id,
                                    'paid_date': datetime.today().date()

                                })
                                self.env['partner.ledgers.customer'].create({
                                    'date': datetime.today().date(),
                                    # 'invoice_id': m.id,
                                    'month':str(datetime.today().date().month),
                                    'partner_id': line.partner_id.id,
                                    # 'product_id': m.invoice_line_ids[0].product_id.id,
                                    'company_id': self.env.user.company_id.id,
                                    # 'price_units': m.inv_mc_qty,
                                    # 'uom': m.invoice_line_ids[0].uom_id.id,
                                    # 'rate': m.invoice_line_ids[0].price_unit,
                                    'credit': amount,
                                    'debit': amount,
                                    'description': line.check_no + '=>' + 'Advance Amount',
                                    'account_journal': journal.id,
                                    'account': journal.payment_debit_account_id.id,
                                    'paid_date': datetime.today().date()

                                })

                        stmt.line_ids = payment_list
                        stmt.move_line_ids = pay_id_list
                        # stmt.write({'state': 'confirm'})
                        self.write({'state': 'validate'})
                else:
                    journal = self.env['account.journal'].search([('name', '=', 'Bank'), ('company_id', '=', 1)])
                    stmt1 = self.env['account.bank.statement']
                    j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
                    if not stmt:
                        # _get_payment_info_JSON
                        # bal = sum(self.env['account.move.line'].search([('journal_id', '=', line.debited_account.id)]).mapped(
                        #     'debit'))

                        if self.env['account.bank.statement'].search([('company_id', '=', journal.company_id.id),
                                                                      ('journal_id', '=', journal.id)]):
                            bal = self.env['account.bank.statement'].search(
                                [('company_id', '=', journal.company_id.id),
                                 ('journal_id', '=', journal.id)])[0].balance_end_real
                        else:
                            bal = 0

                        stmt = self.env['account.bank.statement'].create({'name': line.partner_id.name,
                                                                          'balance_start': bal,
                                                                          # 'journal_id': line.journal_id.id,
                                                                          'journal_id': journal.id,
                                                                          'balance_end_real': bal + line.amount_total

                                                                          })
                        pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                                     # 'amount': check_inv.amount_total,
                                                                     'amount': line.amount_total,
                                                                     'partner_type': 'customer',
                                                                     'company_id': self.env.user.company_id.id,
                                                                     'payment_type': 'inbound',
                                                                     'payment_method_id': j.id,
                                                                     # 'journal_id': line.journal_id.id,
                                                                     'journal_id': journal.id,
                                                                     'ref': line.check_no + '=>' + 'Cleared',

                                                                     })
                        pay_id.action_post()
                        pay_id_list = []
                        # for k in pay_id.move_line_ids:
                        for k in pay_id.line_ids:
                            pay_id_list.append(k.id)
                    if not stmt1:
                        # _get_payment_info_JSON
                        # bal = sum(self.env['account.move.line'].search([('journal_id', '=', line.debited_account.id)]).mapped(
                        #     'debit'))

                        if self.env['account.bank.statement'].search([('company_id', '=', line.debited_account.company_id.id),
                                                                      ('journal_id', '=', line.debited_account.id)]):
                            bal = self.env['account.bank.statement'].search(
                                [('company_id', '=', line.debited_account.company_id.id),
                                 ('journal_id', '=', line.debited_account.id)])[0].balance_end_real
                        else:
                            bal = 0

                        stmt1 = self.env['account.bank.statement'].create({'name': line.partner_id.name,
                                                                          'balance_start': bal,
                                                                          # 'journal_id': line.journal_id.id,
                                                                          'journal_id': line.debited_account.id,
                                                                          'balance_end_real': bal + line.amount_total

                                                                          })
                        pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                                     # 'amount': check_inv.amount_total,
                                                                     'amount': line.amount_total,
                                                                     'partner_type': 'customer',
                                                                     'company_id': self.env.user.company_id.id,
                                                                     'payment_type': 'inbound',
                                                                     'payment_method_id': j.id,
                                                                     # 'journal_id': line.journal_id.id,
                                                                     'journal_id': journal.id,
                                                                     'ref': line.check_no + '=>' + 'Cleared',

                                                                     })
                        pay_id_1 = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                                     # 'amount': check_inv.amount_total,
                                                                     'amount': line.amount_total,
                                                                     'partner_type': 'customer',
                                                                     'company_id': line.debited_account.company_id.id,
                                                                     'payment_type': 'inbound',
                                                                     'payment_method_id': j.id,
                                                                     # 'journal_id': line.journal_id.id,
                                                                     'journal_id': line.debited_account.id,
                                                                     'ref': line.check_no + '=>' + 'Cleared',

                                                                     })
                        # pay_id.action_post()
                        # pay_id_1.post()
                        pay_id_1.action_post()
                        pay_id_list_1 = []
                        # for k in pay_id.move_line_ids:
                        #     pay_id_list.append(k.id)
                        for k in pay_id_1.move_line_ids:
                            pay_id_list_1.append(k.id)

                    payment_list = []
                    product_line = (0, 0, {
                        'date': line.date,
                        'name': line.check_no,
                        'partner_id': line.partner_id.id,
                        'ref': line.check_no,
                        'amount': line.amount_total
                    })
                    payment_list.append(product_line)
                    if stmt:
                        stmt.line_ids = payment_list
                        stmt.move_line_ids = pay_id_list
                        # stmt.write({'state': 'confirm'})
                    if stmt1:
                        stmt1.line_ids = payment_list
                        stmt1.move_line_ids = pay_id_list_1
                        # stmt1.write({'state': 'confirm'})
                    invoices = self.env['account.move'].search(
                        [('partner_id', '=', line.partner_id.id), ('company_id', '=', journal.company_id.id),
                         ('state', '!=', 'paid')])
                    if invoices.mapped('amount_residual'):
                        balance_amount = sum(invoices.mapped('amount_residual'))
                    else:
                        balance_amount = sum(invoices.mapped('amount_total'))
                    balance_amount += self.env['partner.ledger.customer'].search(
                        [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                    preview = self.env['partner.ledger.customer'].search(
                        [('company_id', '=', journal.company_id.id), ('partner_id', '=', line.partner_id.id)])
                    if preview:
                        balance_amount = self.env['partner.ledger.customer'].search(
                            [('company_id', '=', journal.company_id.id), ('partner_id', '=', line.partner_id.id)])[
                            -1].balance
                    self.env['partner.ledger.customer'].sudo().create({
                        'date': datetime.today().date(),
                        'partner_id': line.partner_id.id,
                        'company_id': journal.company_id.id,
                        # 'account_move': pay_id.move_line_ids.mapped('move_id').id,
                        'account_move': pay_id.move_id.id,
                        'credit': line.amount_total,
                        'description': 'Cheque No' + '=>' + line.check_no,
                        'account_journal': journal.id,
                        'account': journal.payment_debit_account_id.id,
                        'paid_date': datetime.today().date(),
                        'balance': balance_amount - line.amount_total,
                    })

        if self.collection_type == "both":
            for line in self.bulk_all_lines:
                if line.amount_total == 0.0:
                    raise UserError(_("Please mention paid amount for this partner %s ")%(line.partner_id.name))
                journal = line.debited_account
                if not stmt:
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
                                                                      'journal_id': journal.id,
                                                                      # 'balance_end_real': line.amount_total
                                                                      'balance_end_real': bal+line.amount_total

                                                                      })

                payment_list = []
                pay_id_list = []
                account = self.env['account.move'].search([('company_id','=',self.env.user.company_id.id),('partner_id','=',line.partner_id.id),('state','=','posted')])
                amount = line.amount_total
                actual =0
                for check_inv in account:
                    if amount:
                        if check_inv.amount_total >= amount:
                            actual=amount
                            product_line = (0, 0, {
                                'date': line.payment_date,
                                'name': check_inv.display_name,
                                'partner_id': line.partner_id.id,
                                'ref': check_inv.display_name,
                                'amount': amount
                            })
                            amount = amount - amount
                            payment_list.append(product_line)
                        else:
                            if check_inv.amount_total != 0:
                                amount = amount-check_inv.amount_total
                                actual =check_inv.amount_total
                                product_line = (0, 0, {
                                    'date': line.payment_date,
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
                                                                     'partner_type': 'customer',
                                                                     'company_id': self.env.user.company_id.id,
                                                                     'payment_type': 'inbound',
                                                                     'payment_method_id': j.id,
                                                                     # 'journal_id': line.journal_id.id,
                                                                     'journal_id': journal.id,
                                                                     'ref': 'All Collection',
                                                                     'invoice_ids': [(6, 0, check_inv.ids)]
                                                                     })
                        # pay_id.action_validate_invoice_payment()
                        pay_id.action_post()
                        # for k in pay_id.move_line_ids:
                        for k in pay_id.line_ids:
                            pay_id_list.append(k.id)
                        # line.payments += pay_id
                        executive_rec = self.env['collection.cheque'].search([('check_line','=',line.check_line.id)])
                        # executive_rec.amount_total += line.amount_total
                        if executive_rec:
                            executive_rec.al_state =True
                        executive_coll_rec = self.env['executive.collection.record'].search(
                            [('collection_line_id', '=', line.collection_line.id)])
                        if executive_coll_rec:
                            executive_coll_rec.al_state = True
            if stmt:
                stmt.line_ids = payment_list
                stmt.move_line_ids = pay_id_list
                # stmt.write({'state': 'confirm'})
                self.write({'state': 'validate'})

    # @api.one
    # def _compute_paid_amount(self):
    #     self.Bal_amount = sum(self.today_lines.mapped('balance_amount')) - sum(
    #         self.today_lines.mapped('amount_total'))
    #     self.paid_amount = sum(self.today_lines.mapped('amount_total'))
    #     self.total_amount = sum(self.today_lines.mapped('balance_amount'))

    @api.onchange('payment_date')
    def onchange_payment_date(self):
        today_total_cheques = []
        for each_cheque in self.env['collection.cheque'].search([('state', '=', 'deposit')]):
            product_line = (0, 0, {
                'check_line': each_cheque.check_line.id,
                'advance_check_line': each_cheque.advance_check_line.id,
                'date': each_cheque.date,
                'collection_cheque_id': each_cheque.id,
                'ref_id': each_cheque.check_line.collection_id.id,
                'partner_id': each_cheque.partner_id.id,
                'balance_amount': each_cheque.balance_amount,
                'amount_total': each_cheque.amount_total,
                'check_no': each_cheque.check_no,
                'check_type': each_cheque.check_type,
                'bank_name': each_cheque.bank_name,
                # 'account_type': each_cheque.account_type,
                'state': each_cheque.state,
                'holder_name': each_cheque.holder_name,
                'debited_account': each_cheque.debited_account,
            })
            today_total_cheques.append(product_line)
        self.today_lines = today_total_cheques

    @api.onchange('from_date', 'to_date', 'sales_person', 'collection_type')
    def onchange_form_date(self):
        today_total_cheques = []
        self.bulk_lines = False
        if self.collection_type == "cash":
            self.bulk_cheque_lines = False
            self.bulk_lines = False
            self.bulk_all_lines = False
            if self.sales_person:
                for each_coll in self.env['executive.collection.record'].search(
                        [('sales_person', '=', self.sales_person.id), ('date', '>=', self.from_date),
                         ('date', '<=', self.to_date),('status','=',False)]):
                    product_line = (0, 0, {
                        'collection_id': each_coll.collection_id.id,
                        'payment_date': each_coll.date,
                        'collection_line': each_coll.collection_line_id.id,
                        'partner_id': each_coll.partner_id.id,
                        'balance_amount': each_coll.balance_amount,
                        'amount_total': each_coll.amount_total,
                        'journal_id': each_coll.journal_id.id,
                        'payment_type': each_coll.payment_type,
                        'payments': [(6, 0, each_coll.payments.ids)],
                        'sales_person': each_coll.sales_person.id,
                        'cashier_id': each_coll.cashier_id.id,
                        'pending_amount': each_coll.pending_amount

                    })
                    today_total_cheques.append(product_line)
            else:
                self.bulk_cheque_lines = False
                self.bulk_lines = False
                self.bulk_all_lines = False
                for each_coll in self.env['executive.collection.record'].search(
                        [('date', '>=', self.from_date), ('status','=',False),('date', '<=', self.to_date)]):
                    product_line = (0, 0, {
                        'collection_id': each_coll.collection_id.id,
                        'payment_date': each_coll.date,
                        'collection_line': each_coll.collection_line_id.id,
                        'partner_id': each_coll.partner_id.id,
                        'balance_amount': each_coll.balance_amount,
                        'amount_total': each_coll.amount_total,
                        'journal_id': each_coll.journal_id.id,
                        'payment_type': each_coll.payment_type,
                        'payments': [(6, 0, each_coll.payments.ids)],
                        'sales_person': each_coll.sales_person.id,
                        'cashier_id': each_coll.cashier_id.id,
                        'pending_amount': each_coll.pending_amount

                    })
                    today_total_cheques.append(product_line)
            self.bulk_lines = today_total_cheques
        if self.collection_type == "cheque":
            if self.sales_person:
                self.bulk_cheque_lines = False
                self.bulk_lines = False
                self.bulk_all_lines = False
                for each_cheque in self.env['collection.cheque'].search([('al_state','=',False),('sales_person', '=', self.sales_person.id),('date', '>=', self.from_date),('date', '<=', self.to_date),('state', '=', 'deposit')]):
                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        'collection_cheque_id': each_cheque.id,
                        'ref_id': each_cheque.check_line.collection_id.id,
                        'partner_id': each_cheque.partner_id.id,
                        'balance_amount': each_cheque.balance_amount,
                        'amount_total': each_cheque.amount_total,
                        'check_no': each_cheque.check_no,
                        'check_type': each_cheque.check_type,
                        'bank_name': each_cheque.bank_name,
                        'state': each_cheque.state,
                        'holder_name': each_cheque.holder_name,
                        'debited_account': each_cheque.debited_account,
                    })
                    today_total_cheques.append(product_line)
                self.bulk_cheque_lines = today_total_cheques
            else:
                self.bulk_cheque_lines = False
                self.bulk_lines = False
                self.bulk_all_lines = False
                for each_cheque in self.env['collection.cheque'].search(
                        [('al_state','=',False),('date', '>=', self.from_date), ('date', '<=', self.to_date), ('state', '=', 'deposit')]):
                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        'collection_cheque_id': each_cheque.id,
                        'ref_id': each_cheque.check_line.collection_id.id,
                        'partner_id': each_cheque.partner_id.id,
                        'balance_amount': each_cheque.balance_amount,
                        'amount_total': each_cheque.amount_total,
                        'check_no': each_cheque.check_no,
                        'check_type': each_cheque.check_type,
                        'bank_name': each_cheque.bank_name,
                        'state': each_cheque.state,
                        'holder_name': each_cheque.holder_name,
                        'debited_account': each_cheque.debited_account,
                    })
                    today_total_cheques.append(product_line)
                self.bulk_cheque_lines = today_total_cheques

        if self.collection_type == "both":
            if self.sales_person:
                self.bulk_cheque_lines = False
                self.bulk_lines = False
                self.bulk_all_lines = False
                for each_coll in self.env['executive.collection.record'].search(
                        [('sales_person', '=', self.sales_person.id), ('date', '>=', self.from_date),
                         ('date', '<=', self.to_date), ('status', '=', False)]):
                    product_line = (0, 0, {
                        'collection_id': each_coll.collection_id.id,
                        'payment_date': each_coll.date,
                        'collection_line': each_coll.collection_line_id.id,
                        'partner_id': each_coll.partner_id.id,
                        'balance_amount': each_coll.balance_amount,
                        'amount_total': each_coll.amount_total,
                        'journal_id': each_coll.journal_id.id,
                        'payment_type': each_coll.payment_type,
                        'payments': [(6, 0, each_coll.payments.ids)],
                        'sales_person': each_coll.sales_person.id,
                        'cashier_id': each_coll.cashier_id.id,
                        'pending_amount': each_coll.pending_amount,
                        'debited_account': each_coll.journal_id.id,

                    })
                    today_total_cheques.append(product_line)
            else:
                self.bulk_cheque_lines = False
                self.bulk_lines = False
                self.bulk_all_lines = False
                for each_coll in self.env['executive.collection.record'].search(
                        [('date', '>=', self.from_date), ('status', '=', False), ('date', '<=', self.to_date)]):
                    product_line = (0, 0, {
                        'collection_id': each_coll.collection_id.id,
                        'payment_date': each_coll.date,
                        'collection_line': each_coll.collection_line_id.id,
                        'partner_id': each_coll.partner_id.id,
                        'balance_amount': each_coll.balance_amount,
                        'amount_total': each_coll.amount_total,
                        'journal_id': each_coll.journal_id.id,
                        'payment_type': each_coll.payment_type,
                        'payments': [(6, 0, each_coll.payments.ids)],
                        'sales_person': each_coll.sales_person.id,
                        'cashier_id': each_coll.cashier_id.id,
                        'pending_amount': each_coll.pending_amount,
                        'debited_account': each_coll.journal_id.id,

                    })
                    today_total_cheques.append(product_line)
            if self.sales_person:
                for each_cheque in self.env['collection.cheque'].search(
                        [('al_state', '=', False), ('sales_person', '=', self.sales_person.id),
                         ('date', '>=', self.from_date), ('date', '<=', self.to_date), ('state', '=', 'deposit')]):
                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref =each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref =each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'payment_date': each_cheque.date,
                        # 'collection_cheque': each_cheque.collection_cheque.id,
                        'sales_person': each_cheque.sales_person.id,
                        # 'ref_id': each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        'partner_id': each_cheque.partner_id.id,
                        'balance_amount': each_cheque.balance_amount,
                        'amount_total': each_cheque.amount_total,
                        'check_no': each_cheque.check_no,
                        'journal_id':each_cheque.debited_account.id,
                        'check_type': each_cheque.check_type,
                        'bank_name': each_cheque.bank_name,
                        'state': each_cheque.state,
                        'holder_name': each_cheque.holder_name,
                        'debited_account': each_cheque.debited_account,
                    })
                    today_total_cheques.append(product_line)
            else:

                for each_cheque in self.env['collection.cheque'].search(
                        [('al_state', '=', False), ('date', '>=', self.from_date), ('date', '<=', self.to_date),
                         ('state', '=', 'deposit')]):
                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref =each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref =each_cheque.check_line.collection_id.id
                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'payment_date': each_cheque.date,
                        # 'collection_cheque':each_cheque.collection_cheque_id.id,
                        'sales_person':each_cheque.sales_person.id,
                        # 'ref_id': each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        'partner_id': each_cheque.partner_id.id,
                        'balance_amount': each_cheque.balance_amount,
                        'amount_total': each_cheque.amount_total,
                        'check_no': each_cheque.check_no,
                        'journal_id':each_cheque.debited_account.id,
                        'check_type': each_cheque.check_type,
                        'bank_name': each_cheque.bank_name,
                        'state': each_cheque.state,
                        'holder_name': each_cheque.holder_name,
                        'debited_account': each_cheque.debited_account,
                    })
                    today_total_cheques.append(product_line)
            self.bulk_all_lines = today_total_cheques

    # @api.multi
    def action_cheque_statement(self):

        return self.env.ref('ezp_cash_collection.executive_cheque_collection_id1').report_action(self)


class BulkCollectionsLines(models.Model):
    _name = "bulk.collections.line"

    bulk_id = fields.Many2one('bulk.collections')
    collection_id = fields.Many2one('executive.collection')
    collection_line = fields.Many2one('executive.collection.line')
    payment_date = fields.Date('Payment Date')
    sales_person = fields.Many2one('res.users', string="Executive")
    partner_id = fields.Many2one('res.partner', string="Partner")
    journal_id = fields.Many2one('account.journal', string="Journal")
    amount_total = fields.Float(string="Paid Amount")
    balance_amount = fields.Float(string="Inv Amount")
    executive_collection_line = fields.Many2one('executive.collection.line', string="line id")

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))

    @api.onchange('apply')
    def onchange_apply(self):
        if self.apply == True:
            journals = self.env['account.journal'].search(
                [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}


class BulkAllLines(models.Model):
    _name = "bulk.all.line"

    bulk_all_id = fields.Many2one('bulk.collections')
    collection_id = fields.Many2one('executive.collection')
    collection_line = fields.Many2one('executive.collection.line')
    payment_date = fields.Date('Payment Date')
    sales_person = fields.Many2one('res.users', string="Executive")
    partner_id = fields.Many2one('res.partner', string="Partner")
    journal_id = fields.Many2one('account.journal', string="Journal")
    amount_total = fields.Float(string="Paid Amount")
    balance_amount = fields.Float(string="Inv Amount")
    executive_collection_line = fields.Many2one('executive.collection.line', string="line id")
    ref_id = fields.Many2one('executive.cheque.collection', string="Source")
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_all_rels')
    check_no = fields.Char(string='Cheque No')
    check_type = fields.Selection([('cash', 'Cash'), ('pdc', 'PDC'), ], string="Check Type", )
    check_date = fields.Date(string='Check Date', default=fields.Date.today())
    check_manual_date = fields.Date(string='Check Date', )
    new_date = fields.Date(string='New Date')
    bank_name = fields.Char('Back Name')
    reason = fields.Text('Reason')
    check_post_id = fields.Many2one('post.cheques.line')
    check_bounce_id = fields.Many2one('bounce.cheques.line')
    check_line = fields.Many2one('executive.cheque.collection.line')
    advance_check_line = fields.Many2one('advance.cheque.collection.line')
    status = fields.Selection([
        ('none', ''),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('cancel', 'Cancelled')], string='Status',
        default='none')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('send', 'Sended'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='state',
        default='draft')
    holder_name = fields.Many2one('res.partner', string='Holder Name')
    debited_account = fields.Many2one('account.journal', string='Debit A/C')
    collected_cheque = fields.Many2one('collection.cheque')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))

    @api.onchange('apply')
    def onchange_apply(self):
        if self.apply == True:
            journals = self.env['account.journal'].search(
                [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
