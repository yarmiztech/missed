# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TodayChequeFirst(models.Model):
    _name = "today.cheques.sub"
    _description = "Today Cheques"
    _order = "id desc"

    name = fields.Char("Collection Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)

    user_id = fields.Many2one('res.users', string='Responsible', index=True, track_visibility='onchange',
                              track_sequence=2, default=lambda self: self.env.user)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Validate'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")

    payment_date = fields.Date(string='Date', default=fields.Date.context_today, required=True, copy=False)
    today_lines = fields.One2many('today.cheques.sub.line', 'today_id')
    from_date = fields.Date('From Date', default=fields.Date.context_today, )
    to_date = fields.Date('To Date', default=fields.Date.context_today, )
    sales_person = fields.Many2one('res.users', string="Sales Person")
    partner_id = fields.Many2one('res.partner')
    paid_amount = fields.Float(string='Paid Amount', compute='_compute_paid_amount')
    Bal_amount = fields.Float(string='Bal Amount', compute='_compute_paid_amount')
    total_amount = fields.Float(string='Total Amount', compute='_compute_paid_amount')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'today.cheques.sub') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('today.cheques.sub') or _('New')
        return super(TodayChequeFirst, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # @api.one
    def _compute_paid_amount(self):
        self.Bal_amount = sum(self.today_lines.mapped('balance_amount')) - sum(
            self.today_lines.mapped('amount_total'))
        self.paid_amount = sum(self.today_lines.mapped('amount_total'))
        self.total_amount = sum(self.today_lines.mapped('balance_amount'))

    # def create_post_record(self):
    #     pdc_c = self.env['post.cheques']
    #     for line in self.today_lines.filtered(lambda a:a.status == 'postpone' and a.state =='draft'):
    #         if not pdc_c:
    #             pdc_id = self.env['post.cheques'].create({
    #                     'payment_type':line.ref_id.payment_type,
    #                     'partner_type':line.ref_id.partner_type,
    #                     'user_id':self.user_id.id,
    #                     # 'cashier_id':self.cashier_id.id,
    #                     'payment_method_id':line.ref_id.payment_method_id.id
    #                  })
    #         if line:
    #             if line.check_line.collected_cheque:
    #                 line.check_line.collected_cheque.postpone_date = line.post_date
    #                 line.check_line.collected_cheque.date = line.post_date
    #                 line.check_line.collected_cheque.reason = line.reason
    #                 line.check_line.collected_cheque.debited_account = line.debited_account.id
    #                 line.check_line.collected_cheque.status = line.status
    #                 line.check_line.post_date = line.post_date
    #                 line.check_line.reason = line.reason
    #                 line.check_line.debited_account = line.debited_account.id
    #                 line.check_line.status = line.status
    #
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
    #                 'new_date':line.new_date,
    #                 'ref_today_id':line.id,
    #                 # 'account_type':line.account_type,
    #                 'holder_name':line.holder_name.id,
    #                 'debited_account':line.debited_account.id or False,
    #                 'collected_cheque':line.collected_cheque.id
    #             })
    #             line.check_post_id = pdc_line.id
    # def create_bounce_record(self):
    #     pdc_c = self.env['bounce.cheques']
    #     for line in self.today_lines.filtered(lambda a:a.status == 'bounce' and a.state =='draft'):
    #         if not pdc_c:
    #             pdc_id = self.env['bounce.cheques'].create({
    #                      'payment_type':line.ref_id.payment_type,
    #                     'partner_type':line.ref_id.partner_type,
    #                     'user_id':self.user_id.id,
    #                     # 'cashier_id':self.cashier_id.id,
    #                     'payment_method_id':line.ref_id.payment_method_id.id
    #                  })
    #         if line:
    #             if line.check_line.collected_cheque:
    #                 line.check_line.collected_cheque.reason = line.reason
    #                 line.check_line.collected_cheque.status = line.status
    #                 line.check_line.collected_cheque.new_date = line.new_date
    #                 line.check_line.collected_cheque.debited_account = line.debited_account.id
    #                 line.check_line.reason = line.reason
    #                 line.check_line.status = line.status
    #                 line.check_line.new_date = line.new_date
    #                 line.check_line.debited_account = line.debited_account.id
    #
    #
    #
    #                 # line.check_line.collected_cheque.new_date = line.new_date
    #
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
    #                 'ref_today_id':line.id,
    #                 # 'account_type':line.account_type,
    #                 'holder_name':line.holder_name.id,
    #                 'debited_account':line.debited_account.id or False,
    #                 'collected_cheque':line.collected_cheque.id
    #             })
    #             line.check_bounce_id = pdc_line.id
    #

    def complete_submission_rec(self):
        for line in self.today_lines.filtered(lambda a: a.select == True):
            sales_person = self.env['res.users']
            check_line = self.env['executive.cheque.collection.line']
            advance_check_line = self.env['advance.cheque.collection.line']
            if self.sales_person:
                sales_person = self.sales_person.id
            if line.check_line:
                check_line = line.check_line.id
            if line.advance_check_line:
                advance_check_line = line.advance_check_line.id
            self.env['cheque.submission'].create({
                'type_state': 'submit',
                'from_date': self.from_date,
                'to_date': self.to_date,
                'date': line.date,
                'sales_person': sales_person,
                'partner_id': line.partner_id.id,
                'check_line': check_line,
                'advance_check_line': advance_check_line,
                'balance_amount': line.balance_amount,
                'amount_total': line.amount_total,
                'ref_id': line.ref_id.id,
                # 'journal_id':line.journal_id.id,
                'check_no': line.check_no,
                'check_type': line.check_type,
                'check_manual_date': line.check_manual_date,
                'bank_name': line.bank_name,
                'status': line.status,
                'state': line.state,
                'holder_name': line.holder_name.id,
                'debited_account': line.debited_account.id,
                # 'collected_cheque':line.collected_cheque.id,
            })

    def action_confirm(self):
        today_total_cheques = []
        self.complete_submission_rec()
        today_rec = self.env['today.cheques']
        for each in self.today_lines:
            if not today_rec:
                today_rec = self.env['today.cheques'].create({
                    'user_id': self.user_id.id,
                    'payment_date': self.payment_date
                })
            coll_cheque = self.env['collection.cheque'].search([('check_line', '=', each.check_line.id)])
            for l in coll_cheque:
                l.comm_state = True
            product_line = (0, 0, {
                'today_id': today_rec.id,
                'date': each.date,
                'bulk_cheque': each.bulk_cheque.id,
                'check_line': each.check_line.id,
                'advance_check_line': each.advance_check_line.id,
                'partner_id': each.partner_id.id,
                'balance_amount': each.balance_amount,
                'amount_total': each.amount_total,
                'check_type': each.check_type,
                'ref_id': each.ref_id.id,
                'journal_id': each.journal_id.id,
                'bank_name': each.bank_name,
                'payment_type': each.payment_type,
                'check_manual_date': each.check_manual_date,
                'bank_name': each.bank_name,
                'collected_cheque': each.collected_cheque.id,
                # 'account_type': each_cheque.account_type,
                'state': each.state,
                'holder_name': each.holder_name.id,
                'debited_account': each.debited_account.id,
                'account_id': each.account_id.id,
            })
            today_total_cheques.append(product_line)
        if today_rec:
            today_rec.today_lines = today_total_cheques

            # if each.
            # if each.status == 'deposit':
            #     each.check_line.write({'state':'deposit'})
            #     each.check_line.debited_account = each.debited_account
            #     # if each.check_line.check_bounce_id:
            #     #     each.check_line.check_bounce_id.debited_account = each.debited_account
            #     #     each.check_line.check_bounce_id.write({'state':'deposit'})
            #     # if each.check_line.check_post_id:
            #     #     each.check_line.check_post_id.debited_account = each.debited_account
            #     #     each.check_line.check_post_id.write({'state':'deposit'})
            #     each.check_line.collected_cheque.write({'state':'deposit'})
            #     each.check_line.collected_cheque.debited_account=each.debited_account
            #     # each.check_line.collection_id.write({'state':'deposited'})
            #     if each.check_line.check_ref_id:
            #         each.check_line.check_ref_id.debited_account = each.debited_account
            #         each.check_line.check_ref_id.write({'state': 'deposit'})
            #         # each.check_line.check_ref_id.collected_cheque.write({'state': 'deposit'})
            #
            #     each.write({'state':'deposit'})

        # self.create_post_record()
        # self.create_bounce_record()
        self.write({'state': 'validate'})

    # @api.onchange('payment_date')
    # def onchange_payment_date(self):
    #     today_total_cheques = []
    #     for each_cheque in self.env['collection.cheque'].search([('comm_state','=',False),('date','=',self.payment_date),('state','not in',('deposit','done'))]):
    #
    #         ref = self.env['executive.cheque.collection']
    #         if each_cheque.advance_check_line:
    #             ref = each_cheque.advance_check_line.a_collection_id.id
    #         if each_cheque.check_line:
    #             ref = each_cheque.check_line.collection_id.id
    #
    #         product_line = (0, 0, {
    #                 'check_line': each_cheque.check_line.id,
    #                 'advance_check_line': each_cheque.advance_check_line.id,
    #                 'date': each_cheque.date,
    #                 # 'ref_id':each_cheque.check_line.collection_id.id,
    #                 'ref_id':ref,
    #                 'partner_id': each_cheque.partner_id.id,
    #                 'balance_amount': each_cheque.balance_amount,
    #                 'amount_total': each_cheque.amount_total,
    #                 'check_no': each_cheque.check_no,
    #                 'check_type': each_cheque.check_type,
    #                 'bank_name': each_cheque.bank_name,
    #                 # 'account_type': each_cheque.account_type,
    #                 'state': each_cheque.state,
    #                 'holder_name': each_cheque.holder_name,
    #                 # 'debited_account': each_cheque.debited_account,
    #             })
    #         today_total_cheques.append(product_line)
    #     # for each_cheque in self.env['collection.cheque'].search([('new_date','=',self.payment_date),('state','!=','deposit')]):
    #     #
    #     #    product_line = (0, 0, {
    #     #         'check_line': each_cheque.check_line.id,
    #     #         'date': each_cheque.date,
    #     #         'ref_id':each_cheque.check_line.collection_id.id,
    #     #         'partner_id': each_cheque.partner_id.id,
    #     #         'balance_amount': each_cheque.balance_amount,
    #     #         'amount_total': each_cheque.amount_total,
    #     #         'check_no': each_cheque.check_no,
    #     #         'check_type': each_cheque.check_type,
    #     #         'bank_name': each_cheque.bank_name,
    #     #         'account_type': each_cheque.account_type,
    #     #         'state': each_cheque.state,
    #     #         'holder_name': each_cheque.holder_name,
    #     #         # 'debited_account': each_cheque.debited_account,
    #     #     })
    #     #    today_total_cheques.append(product_line)
    #     # for each_cheque in self.env['collection.cheque'].search([('new_date','=',self.payment_date),('state','!=','deposit')]):
    #     #
    #     #    product_line = (0, 0, {
    #     #         'check_line': each_cheque.check_line.id,
    #     #         'date': each_cheque.date,
    #     #         'ref_id':each_cheque.check_line.collection_id.id,
    #     #         'partner_id': each_cheque.partner_id.id,
    #     #         'balance_amount': each_cheque.balance_amount,
    #     #         'amount_total': each_cheque.amount_total,
    #     #         'check_no': each_cheque.check_no,
    #     #         'check_type': each_cheque.check_type,
    #     #         'bank_name': each_cheque.bank_name,
    #     #         'account_type': each_cheque.account_type,
    #     #         'state': each_cheque.state,
    #     #         'holder_name': each_cheque.holder_name,
    #     #         # 'debited_account': each_cheque.debited_account,
    #     #     })
    #     #    today_total_cheques.append(product_line)
    #     self.today_lines = today_total_cheques
    #     # journals = self.env['account.journal'].search([('id', '=', self.env.user.company_id.id)])
    #     # if journals:
    #     #     return {'domain': {'flat_id': [('id', 'in', journals.ids)]}}
    #     # else:
    #     #     return {'domain': {'flat_id': [('id', '=', False)]}}
    #     journals = self.env['account.journal'].search(
    #         [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
    #     if journals:
    #         return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}

    @api.onchange('from_date', 'to_date', 'sales_person', 'partner_id')
    def onchange_payment_date(self):
        today_total_cheques = []
        self.today_lines = False
        if not self.sales_person and not self.partner_id:
            for each_cheque in self.env['collection.cheque'].search(
                    [('comm_state', '=', False), ('date', '>=', self.from_date), ('date', '<=', self.to_date),
                     ('state', 'not in', ('deposit', 'done'))]):

                ref = self.env['executive.cheque.collection']
                if each_cheque.advance_check_line:
                    ref = each_cheque.advance_check_line.a_collection_id.id
                if each_cheque.check_line:
                    ref = each_cheque.check_line.collection_id.id

                product_line = (0, 0, {
                    'check_line': each_cheque.check_line.id,
                    'advance_check_line': each_cheque.advance_check_line.id,
                    'date': each_cheque.date,
                    # 'ref_id':each_cheque.check_line.collection_id.id,
                    'ref_id': ref,
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
            journals = self.env['account.journal'].search(
                [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
        if self.sales_person:
            self.today_lines = False
            for each_cheque in self.env['collection.cheque'].search(
                    [('comm_state', '=', False), ('date', '>=', self.from_date), ('date', '<=', self.to_date),
                     ('sales_person', '=', self.sales_person.id),
                     ('state', 'not in', ('deposit', 'done'))]):

                ref = self.env['executive.cheque.collection']
                if each_cheque.advance_check_line:
                    ref = each_cheque.advance_check_line.a_collection_id.id
                if each_cheque.check_line:
                    ref = each_cheque.check_line.collection_id.id

                product_line = (0, 0, {
                    'check_line': each_cheque.check_line.id,
                    'advance_check_line': each_cheque.advance_check_line.id,
                    'date': each_cheque.date,
                    # 'ref_id':each_cheque.check_line.collection_id.id,
                    'ref_id': ref,
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
            journals = self.env['account.journal'].search(
                [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
        if self.partner_id:
            self.today_lines = False
            for each_cheque in self.env['collection.cheque'].search(
                    [('comm_state', '=', False), ('date', '>=', self.from_date), ('date', '<=', self.to_date),
                     ('partner_id', '=', self.partner_id.id),
                     ('state', 'not in', ('deposit', 'done'))]):

                ref = self.env['executive.cheque.collection']
                if each_cheque.advance_check_line:
                    ref = each_cheque.advance_check_line.a_collection_id.id
                if each_cheque.check_line:
                    ref = each_cheque.check_line.collection_id.id

                product_line = (0, 0, {
                    'check_line': each_cheque.check_line.id,
                    'advance_check_line': each_cheque.advance_check_line.id,
                    'date': each_cheque.date,
                    # 'ref_id':each_cheque.check_line.collection_id.id,
                    'ref_id': ref,
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
            journals = self.env['account.journal'].search(
                [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}

    # @api.multi
    def action_cheque_statement(self):

        return self.env.ref('ezp_cash_collection.executive_cheque_collection_id1').report_action(self)


class TodayChequeSubLines(models.Model):
    _name = "today.cheques.sub.line"

    today_id = fields.Many2one('today.cheques.sub')
    bulk_cheque = fields.Many2one('bulk.collections')
    check_line = fields.Many2one('executive.cheque.collection.line')
    advance_check_line = fields.Many2one('advance.cheque.collection.line')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Bal Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    ref_id = fields.Many2one('executive.cheque.collection', string="Source")
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_chequde_rels')
    check_no = fields.Char(string='Cheque No')
    apply = fields.Boolean(default=False, string='Apply')
    check_type = fields.Selection([('cash', 'Cash'), ('pdc', 'PDC'), ], string="Check Type", )
    check_date = fields.Date(string='Check Date', default=fields.Date.today())
    check_manual_date = fields.Date(string='Check Date', )
    new_date = fields.Date(string='New Date')
    bank_name = fields.Char('Back Name')
    reason = fields.Text('Reason')
    check_post_id = fields.Many2one('post.cheques.line')
    check_bounce_id = fields.Many2one('bounce.cheques.line')
    select = fields.Boolean('select')
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
            invoices = self.env['account.invoice'].search(
                [('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))

    @api.onchange('apply')
    def onchange_apply(self):
        if self.apply == True:
            journals = self.env['account.journal'].search(
                [('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}


class TodayCheques(models.Model):
    _name = "today.cheques"
    _description = "Today Cheques"
    _order = "id desc"

    name = fields.Char("Collection Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)

    user_id = fields.Many2one('res.users', string='Responsible', index=True, track_visibility='onchange',
                              track_sequence=2, default=lambda self: self.env.user)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Validate'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")
    check_count = fields.Selection(
        [('pending', 'Pending Submission'), ('submit', 'Submitted Cheques'), ('clear', 'Cleared Cheques'),
         ('bounce', 'Bounced Cheques')], copy=False, string="Cheque Status", default='pending')

    payment_date = fields.Date(string='Date', default=fields.Date.context_today, required=True, copy=False)
    today_lines = fields.One2many('today.cheques.line', 'today_id')
    from_date = fields.Date('From Date', default=fields.Date.context_today, )
    to_date = fields.Date('To Date', default=fields.Date.context_today, )
    sales_person = fields.Many2one('res.users', string="Sales Person")
    partner_id = fields.Many2one('res.partner', domain=[('estimator', '=', True)])
    paid_amount = fields.Float(string='Paid Amount', compute='_compute_paid_amount')
    Bal_amount = fields.Float(string='Bal Amount', compute='_compute_paid_amount')
    total_amount = fields.Float(string='Total Amount', compute='_compute_paid_amount')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'today.cheques') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('today.cheques') or _('New')
        return super(TodayCheques, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def complete_submission_rec(self):
        for line in self.today_lines:
            before_rec = self.env['cheque.submission'].search(
                [('partner_id', '=', line.partner_id.id), ('check_no', '=', line.check_no)])
            if before_rec:
                if line.status == "deposit":
                    before_rec[0].clearing_date = line[0].clearing_date
                before_rec[0].status = line.status
                before_rec[0].type_state = line.status
            sales_person = self.env['res.users']
            check_line = self.env['executive.cheque.collection.line']
            advance_check_line = self.env['advance.cheque.collection.line']
            if self.sales_person:
                sales_person = self.sales_person.id
            if line.check_line:
                check_line = line.check_line.id
            if line.advance_check_line:
                advance_check_line = line.advance_check_line.id
            if not before_rec:
                self.env['cheque.submission'].create({
                    'type_state': line.status,
                    'submitted_date': line.submitted_date,
                    'from_date': self.from_date,
                    'to_date': self.to_date,
                    'date': line.clearing_date,
                    'sales_person': sales_person,
                    'partner_id': line.partner_id.id,
                    'check_line': check_line,
                    'advance_check_line': advance_check_line,
                    'balance_amount': line.balance_amount,
                    'amount_total': line.amount_total,
                    'ref_id': line.ref_id.id,
                    # 'journal_id':line.journal_id.id,
                    'check_no': line.check_no,
                    'check_type': line.check_type,
                    'check_manual_date': line.check_manual_date,
                    'bank_name': line.bank_name,
                    'status': line.status,
                    'state': line.state,
                    'holder_name': line.holder_name.id,
                    'debited_account': line.debited_account.id,
                    'account_id': line.account_id.id,
                    # 'collected_cheque':line.collected_cheque.id,
                })

    # @api.one
    def _compute_paid_amount(self):
        self.Bal_amount = sum(self.today_lines.mapped('balance_amount')) - sum(
            self.today_lines.mapped('amount_total'))
        self.paid_amount = sum(self.today_lines.mapped('amount_total'))
        self.total_amount = sum(self.today_lines.mapped('balance_amount'))

    def create_post_record(self):
        pdc_c = self.env['post.cheques']
        for line in self.today_lines.filtered(lambda a: a.status == 'postpone' and a.state == 'draft'):
            if not pdc_c:
                pdc_id = self.env['post.cheques'].create({
                    'payment_type': line.ref_id.payment_type,
                    'partner_type': line.ref_id.partner_type,
                    'user_id': self.user_id.id,
                    # 'cashier_id':self.cashier_id.id,
                    'payment_method_id': line.ref_id.payment_method_id.id
                })
            if line:
                submit = self.env['cheque.submission'].search([('check_line', '=', line.check_line.id)])
                if submit:
                    submit.write({'type_state': 'postponed'})
                    submit.write({'state': 'postpone'})
                if line.check_line.collected_cheque:
                    line.check_line.collected_cheque.postpone_date = line.post_date
                    line.check_line.collected_cheque.date = line.post_date
                    line.check_line.collected_cheque.reason = line.reason
                    line.check_line.collected_cheque.debited_account = line.debited_account.id
                    line.check_line.collected_cheque.status = line.status
                    line.check_line.post_date = line.post_date
                    line.check_line.reason = line.reason
                    line.check_line.debited_account = line.debited_account.id
                    # line.check_line.account_id = line.account_id.id
                    line.check_line.status = line.status

                pdc_line = self.env['post.cheques.line'].create({
                    'today_id': pdc_id.id,
                    'partner_id': line.partner_id.id,
                    'balance_amount': line.balance_amount,
                    'amount_total': line.amount_total,
                    'journal_id': line.journal_id.id,
                    'check_no': line.check_no,
                    'check_type': line.check_type,
                    'check_date': line.check_date,
                    'check_manual_date': line.check_manual_date,
                    'bank_name': line.bank_name,
                    'post_date': line.post_date,
                    'status': line.status,
                    'new_date': line.new_date,
                    'ref_today_id': line.id,
                    # 'account_type':line.account_type,
                    'holder_name': line.holder_name.id,
                    'debited_account': line.debited_account.id or False,
                    # 'account_id': line.account_id.id or False,
                    'collected_cheque': line.collected_cheque.id
                })
                line.check_post_id = pdc_line.id

    def create_bounce_record(self):
        pdc_c = self.env['bounce.cheques']
        for line in self.today_lines.filtered(lambda a: a.status == 'bounce' and a.state == 'draft'):
            if not pdc_c:
                pdc_id = self.env['bounce.cheques'].create({
                    # 'payment_type': line.ref_id.payment_type,
                    'partner_type': line.ref_id.partner_type,
                    'user_id': self.user_id.id,
                    # 'cashier_id':self.cashier_id.id,
                    'payment_method_id': line.ref_id.payment_method_id.id
                })
            if line:
                submit = self.env['cheque.submission'].search([('check_line', '=', line.check_line.id)])
                if submit:
                    submit.write({'type_state': 'bounce'})
                    submit.write({'state': 'bounce'})
                if line.check_line.collected_cheque:
                    line.check_line.collected_cheque.reason = line.reason
                    line.check_line.collected_cheque.status = line.status
                    line.check_line.collected_cheque.new_date = line.new_date
                    line.check_line.collected_cheque.debited_account = line.debited_account.id
                    # line.check_line.collected_cheque.account_id = line.account_id.id
                    line.check_line.reason = line.reason
                    line.check_line.status = line.status
                    line.check_line.new_date = line.new_date
                    line.check_line.debited_account = line.debited_account.id
                    # line.check_line.account_id = line.account_id.id

                    # line.check_line.collected_cheque.new_date = line.new_date

                pdc_line = self.env['bounce.cheques.line'].create({
                    'today_id': pdc_id.id,
                    'partner_id': line.partner_id.id,
                    'balance_amount': line.balance_amount,
                    'amount_total': line.amount_total,
                    'journal_id': line.journal_id.id,
                    'check_no': line.check_no,
                    'check_type': line.check_type,
                    'check_date': line.check_date,
                    'check_manual_date': line.check_manual_date,
                    'bank_name': line.bank_name,
                    'bounce_date': line.bounce_date,
                    'reason': line.reason,
                    'status': line.status,
                    'ref_today_id': line.id,
                    # 'account_type':line.account_type,
                    'holder_name': line.holder_name.id,
                    'debited_account': line.debited_account.id or False,
                    # 'account_id': line.account_id.id or False,
                    'collected_cheque': line.collected_cheque.id
                })
                line.check_bounce_id = pdc_line.id

    def action_confirm(self):
        self.complete_submission_rec()
        today_total_cheques = []
        for each in self.today_lines:
            # if each.
            line = self.env['check.repo'].search([('line_id', '=', each.check_line.id)])
            line.debited_account = each.debited_account
            line.account_id = each.account_id
            if each.status == 'deposit':
                submit = self.env['cheque.submission'].search([('check_line', '=', each.check_line.id)])
                if submit:
                    submit.write({'type_state': 'deposit'})
                    submit.write({'state': 'deposit'})
                    # submit.clearing_date = each.clearing_date

                if each.check_line:
                    each.check_line.write({'state': 'deposit'})
                    each.check_line.debited_account = each.debited_account
                    each.check_line.account_id = each.account_id
                if each.advance_check_line:
                    each.advance_check_line.write({'state': 'deposit'})
                    each.advance_check_line.debited_account = each.debited_account
                    each.advance_check_line.account_id = each.account_id
                # if each.check_line.check_bounce_id:
                #     each.check_line.check_bounce_id.debited_account = each.debited_account
                #     each.check_line.check_bounce_id.write({'state':'deposit'})
                # if each.check_line.check_post_id:
                #     each.check_line.check_post_id.debited_account = each.debited_account
                #     each.check_line.check_post_id.write({'state':'deposit'})
                if each.check_line:
                    each.check_line.collected_cheque.write({'state': 'deposit'})
                    each.check_line.collected_cheque.debited_account = each.debited_account
                    each.check_line.collected_cheque.account_id = each.account_id
                    # each.check_line.collection_id.write({'state':'deposited'})
                    if each.check_line.check_ref_id:
                        each.check_line.check_ref_id.debited_account = each.debited_account
                        each.check_line.check_ref_id.account_id = each.account_id
                        each.check_line.check_ref_id.write({'state': 'deposit'})
                        # each.check_line.check_ref_id.collected_cheque.write({'state': 'deposit'})
                if each.advance_check_line:
                    each.advance_check_line.collected_cheque.write({'state': 'deposit'})
                    each.advance_check_line.collected_cheque.debited_account = each.debited_account
                    each.advance_check_line.collected_cheque.account_id = each.account_id
                    # each.check_line.collection_id.write({'state':'deposited'})
                    if each.advance_check_line.check_ref_id:
                        each.advance_check_line.check_ref_id.debited_account = each.debited_account
                        each.advance_check_line.check_ref_id.account_id = each.account_id
                        each.advance_check_line.check_ref_id.write({'state': 'deposit'})
                        # each.check_line.check_ref_id.collected_cheque.write({'state': 'deposit'})

                each.write({'state': 'deposit'})
                bulk_id = self.env['bulk.collections'].create({
                    'from_date': datetime.today().date(),
                    'to_date': datetime.today().date(),
                    'collection_type': "cheque"
                })
                # bulk_cheque_lines
                product_line = self.env['today.cheques.line'].create({
                    'check_line': each.check_line.id,
                    # 'advance_check_line': each.advance_check_line.id,
                    'date': each.clearing_date,
                    'collection_cheque_id': each.id,
                    'ref_id': each.check_line.collection_id.id,
                    'partner_id': each.partner_id.id,
                    'balance_amount': each.balance_amount,
                    'amount_total': each.amount_total,
                    'check_no': each.check_no,
                    'check_type': each.check_type,
                    'bank_name': each.bank_name,
                    'state': each.state,
                    'holder_name': each.holder_name.id,
                    'account_id': each.account_id.id,
                    'debited_account': each.debited_account.id,
                    'bulk_cheque': bulk_id.id
                })
                bulk_id.action_confirm()
                # today_total_cheques.append(product_line)
            # self.bulk_cheque_lines = today_total_cheques

            # if self.collection_type == "cheque":
            # stmt = self.env['account.bank.statement']
            # for line in bulk_id.bulk_cheque_lines:
            #     journal = each.debited_account
            #     if not stmt:
            #         # _get_payment_info_JSON
            #         bal = sum(
            #             self.env['account.move.line'].search([('journal_id', '=', line.journal_id.id)]).mapped(
            #                 'debit'))
            #
            #         # stmt = self.env['account.bank.statement'].create({'name': line.partner_id.name,
            #         #                                                   'balance_start': bal,
            #         #                                                   # 'journal_id': line.journal_id.id,
            #         #                                                   'journal_id': journal.id,
            #         #                                                   'balance_end_real': line.amount_total
            #         #
            #         #                                                   })
            #
            #     payment_list = []
            #     pay_id_list = []
            #     account = self.env['account.invoice'].search(
            #         [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', line.partner_id.id),
            #          ('state', '=', 'open')])
            #     amount = line.amount_total
            #     actual = 0
            #     if account:
            #         for check_inv in account:
            #             if amount:
            #                 if check_inv.amount_total >= amount:
            #                     sub_c_invoice = check_inv.estimate_id.invoice_ids.filtered(
            #                         lambda a: a.company_id.id != 1)
            #                     actual = amount
            #                     # self.sub_company_payment(sub_c_invoice, line, amount)
            #                     product_line = (0, 0, {
            #                         'date': each.clearing_date,
            #                         'name': check_inv.display_name,
            #                         'partner_id': line.partner_id.id,
            #                         'ref': check_inv.display_name,
            #                         'amount': amount
            #                     })
            #                     amount = amount - amount
            #                     payment_list.append(product_line)
            #                 else:
            #                     if check_inv.amount_total != 0:
            #                         amount = amount - check_inv.amount_total
            #                         sub_c_invoice = check_inv.estimate_id.invoice_ids.filtered(
            #                             lambda a: a.company_id.id != 1)
            #                         # self.sub_company_payment(sub_c_invoice, line, amount)
            #                         actual = check_inv.amount_total
            #                         product_line = (0, 0, {
            #                             'date': each.clearing_date,
            #                             'name': check_inv.display_name,
            #                             'partner_id': line.partner_id.id,
            #                             'ref': check_inv.display_name,
            #                             'amount': check_inv.amount_total
            #                         })
            #                         payment_list.append(product_line)
            #
            #                 j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
            #                 narration = each.check_no + '/' + each.debited_account.bank_acc_number + '/' + 'Cleared'
            #                 pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
            #                                                              # 'amount': check_inv.amount_total,
            #                                                              'amount': actual,
            #                                                              'partner_type': 'customer',
            #                                                              'company_id': self.env.user.company_id.id,
            #                                                              'payment_type': 'inbound',
            #                                                              'payment_method_id': j.id,
            #                                                              # 'journal_id': line.journal_id.id,
            #                                                              'journal_id': journal.id,
            #                                                              'ref': narration,
            #                                                              'invoice_ids': [(6, 0, check_inv.ids)]
            #                                                              })
            #                 pay_id.action_validate_invoice_payment()
            #                 for k in pay_id.move_line_ids:
            #                     pay_id_list.append(k.id)
            #                 # line.payments += pay_id
            #                 executive_rec = self.env['collection.cheque'].search(
            #                     [('check_line', '=', line.check_line.id)])
            #                 # executive_rec.amount_total += line.amount_total
            #                 executive_rec.al_state = True
            #     else:
            #         j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
            #
            #         pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
            #                                                      # 'amount': check_inv.amount_total,
            #                                                      'amount': actual,
            #                                                      'partner_type': 'customer',
            #                                                      'company_id': self.env.user.company_id.id,
            #                                                      'payment_type': 'inbound',
            #                                                      'payment_method_id': j.id,
            #                                                      # 'journal_id': line.journal_id.id,
            #                                                      'journal_id': journal.id,
            #                                                      'ref': 'Advance Cheque Collection',
            #
            #                                                      })
            #         pay_id.action_post()
            #
            # if stmt:
            #         if amount:
            #             j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
            #             pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
            #                                                          # 'amount': check_inv.amount_total,
            #                                                          'amount': amount,
            #                                                          'partner_type': 'customer',
            #                                                          'company_id': self.env.user.company_id.id,
            #                                                          'payment_type': 'inbound',
            #                                                          'payment_method_id': j.id,
            #                                                          # 'journal_id': line.journal_id.id,
            #                                                          'journal_id': journal.id,
            #                                                          'communication': 'Advance Cheque Collection',
            #
            #                                                          })
            #             pay_id.action_post()
            #
            #         stmt.line_ids = payment_list
            #         stmt.move_line_ids = pay_id_list
            #         self.write({'state': 'validate'})

            # self.today_lines = today_total_cheques

            if each.status == "bounce":
                journal_id = self.env['account.journal'].search(
                    [('name', '=', 'Tax Invoices'), ('type', '=', 'sale'), ('company_id', '=', 1)])[0].id,

                j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0].id

                pay_id = self.env['account.payment'].create({'partner_id': each.partner_id.id,
                                                             'amount': 600,
                                                             'partner_type': 'customer',
                                                             'payment_type': 'outbound',
                                                             'payment_method_id': j,
                                                             'journal_id': journal_id,
                                                             'ref': each.partner_id.name + '/' + each.check_no + '/' + 'Bounced',
                                                             # 'invoice_ids': [(6, 0, line.invoice_id.ids)]
                                                             })
                pay_id.action_post()
                pay_id.action_cash_book()
                invoices = self.env['account.invoice'].search(
                    [('partner_id', '=', each.partner_id.id), ('company_id', '=', 1),
                     ('state', '!=', 'paid')])
                if invoices.mapped('amount_residual'):
                    balance_amount = sum(invoices.mapped('amount_residual'))
                else:
                    balance_amount = sum(invoices.mapped('amount_total'))
                balance_amount += self.env['partner.ledger.customer'].search(
                    [('partner_id', '=', each.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                balance_amount = self.env['partner.ledger.customer'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', each.partner_id.id)])[
                    -1].balance
                self.env['partner.ledger.customer'].sudo().create({
                    'date': datetime.today().date(),
                    # 'invoice_id': inv.id,
                    'partner_id': each.partner_id.id,
                    # 'product_id': line.product_id.id,
                    'company_id': 1,
                    # 'price_units': inv.inv_mc_qty,
                    # 'uom': line.uom_id.id,
                    # 'rate': line.price_unit,
                    # 'estimate_id': self.id,
                    # 'account_journal': inv.journal_id.id,
                    # 'account_move': inv.move_id.id,
                    # 'credit': inv.amount_total_signed,
                    'debit': 600,
                    'balance': balance_amount + 600,
                })

                # vals = {
                #     'journal_id': self.env['account.journal'].search([('name','=','Tax Invoices'),('type','=','sale'),('company_id','=',1)])[0].id,
                #     'state': 'draft',
                #     'ref': each.partner_id.name +'/' +each.check_no
                # }
                # pay_id_list = []
                # move_id = self.env['account.move'].create(vals)
                # if each.partner_id:
                #     partner_id = each.partner_id.id
                # else:
                #     partner_id = False
                #
                # label = 'Bounce Check'+'/'+ each.check_no
                #
                # temp = (0, 0, {
                #     'account_id': self.env['account.account'].search([('name','=','Administration Expenses-bounce')]).id,
                #     'name': label,
                #     'move_id': move_id.id,
                #     'date': datetime.today().date(),
                #     'partner_id': partner_id,
                #     'debit': 600,
                #     'credit': 0,
                # })
                # pay_id_list.append(temp)
                #
                # acc = self.env['account.account'].search(
                #     [('name', '=', 'Local Sales'), ('company_id', '=', 1)])
                #
                # temp = (0, 0, {
                #     'account_id': acc.id,
                #     'name': 'Bounce Amount',
                #     'move_id': move_id.id,
                #     'date': datetime.today().date(),
                #     # 'partner_id': self.partner_id.id,
                #     'debit': 0,
                #     'credit':600,
                # })
                # pay_id_list.append(temp)
                # move_id.line_ids = pay_id_list
                # move_id.action_post()
                # invoices = self.env['account.invoice'].search(
                #     [('partner_id', '=', each.partner_id.id), ('company_id', '=', 1),
                #      ('state', '!=', 'paid')])
                # if invoices.mapped('residual'):
                #     balance_amount = sum(invoices.mapped('residual'))
                # else:
                #     balance_amount = sum(invoices.mapped('amount_total'))
                #
                # self.env['partner.ledger.customer'].create({
                #     'date': datetime.today().date(),
                #     # 'invoice_id': inv.id,
                #     'partner_id': each.partner_id.id,
                #     # 'product_id': line.product_id.id,
                #     'company_id': 1,
                #     # 'price_units': inv.inv_mc_qty,
                #     # 'uom': line.uom_id.id,
                #     # 'rate': line.price_unit,
                #     # 'estimate_id': self.id,
                #     # 'account_journal': inv.journal_id.id,
                #     # 'account_move': inv.move_id.id,
                #     # 'credit': inv.amount_total_signed,
                #     'debit': 600,
                #     'balance': balance_amount,
                # })

                # pay_id.action_cash_book()

                # j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
                # narration = each.check_no + '=>' + 'Bounced'
                # pay_id = self.env['account.payment'].create({'partner_id': each.partner_id.id,
                #                                              'amount': 600,
                #                                              'partner_type': 'customer',
                #                                              'company_id': self.env.user.company_id.id,
                #                                              'payment_type': 'inbound',
                #                                              'payment_method_id': j.id,
                #                                              # 'journal_id': line.journal_id.id,
                #                                              'journal_id': each.debited_account.id,
                #                                              'ref': narration,
                #                                              'invoice_ids': []
                #                                              })
                # pay_id.action_post()
                # pay_id.action_cash_book()
        self.create_post_record()
        self.create_bounce_record()
        self.write({'state': 'validate'})

    # @api.onchange('payment_date')
    # def onchange_payment_date(self):
    #     today_total_cheques = []
    #     for each_cheque in self.env['collection.cheque'].search([('date','=',self.payment_date),('state','not in',('deposit','done'))]):
    #
    #        product_line = (0, 0, {
    #             'check_line': each_cheque.check_line.id,
    #             'date': each_cheque.date,
    #             'ref_id':each_cheque.check_line.collection_id.id,
    #             'partner_id': each_cheque.partner_id.id,
    #             'balance_amount': each_cheque.balance_amount,
    #             'amount_total': each_cheque.amount_total,
    #             'check_no': each_cheque.check_no,
    #             'check_type': each_cheque.check_type,
    #             'bank_name': each_cheque.bank_name,
    #             # 'account_type': each_cheque.account_type,
    #             'state': each_cheque.state,
    #             'holder_name': each_cheque.holder_name,
    #             # 'debited_account': each_cheque.debited_account,
    #         })
    #        today_total_cheques.append(product_line)
    #     # for each_cheque in self.env['collection.cheque'].search([('new_date','=',self.payment_date),('state','!=','deposit')]):
    #     #
    #     #    product_line = (0, 0, {
    #     #         'check_line': each_cheque.check_line.id,
    #     #         'date': each_cheque.date,
    #     #         'ref_id':each_cheque.check_line.collection_id.id,
    #     #         'partner_id': each_cheque.partner_id.id,
    #     #         'balance_amount': each_cheque.balance_amount,
    #     #         'amount_total': each_cheque.amount_total,
    #     #         'check_no': each_cheque.check_no,
    #     #         'check_type': each_cheque.check_type,
    #     #         'bank_name': each_cheque.bank_name,
    #     #         'account_type': each_cheque.account_type,
    #     #         'state': each_cheque.state,
    #     #         'holder_name': each_cheque.holder_name,
    #     #         # 'debited_account': each_cheque.debited_account,
    #     #     })
    #     #    today_total_cheques.append(product_line)
    #     # for each_cheque in self.env['collection.cheque'].search([('new_date','=',self.payment_date),('state','!=','deposit')]):
    #     #
    #     #    product_line = (0, 0, {
    #     #         'check_line': each_cheque.check_line.id,
    #     #         'date': each_cheque.date,
    #     #         'ref_id':each_cheque.check_line.collection_id.id,
    #     #         'partner_id': each_cheque.partner_id.id,
    #     #         'balance_amount': each_cheque.balance_amount,
    #     #         'amount_total': each_cheque.amount_total,
    #     #         'check_no': each_cheque.check_no,
    #     #         'check_type': each_cheque.check_type,
    #     #         'bank_name': each_cheque.bank_name,
    #     #         'account_type': each_cheque.account_type,
    #     #         'state': each_cheque.state,
    #     #         'holder_name': each_cheque.holder_name,
    #     #         # 'debited_account': each_cheque.debited_account,
    #     #     })
    #     #    today_total_cheques.append(product_line)
    #     self.today_lines = today_total_cheques
    #     # journals = self.env['account.journal'].search([('id', '=', self.env.user.company_id.id)])
    #     # if journals:
    #     #     return {'domain': {'flat_id': [('id', 'in', journals.ids)]}}
    #     # else:
    #     #     return {'domain': {'flat_id': [('id', '=', False)]}}
    #     journals = self.env['account.journal'].search(
    #         [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
    #     if journals:
    #         return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}

    # @api.onchange('from_date', 'to_date', 'sales_person', 'partner_id','check_count')
    # def onchange_payment_date(self):
    #     today_total_cheques = []
    #     self.today_lines = False
    #     if not self.sales_person and not self.partner_id:
    #         for each_cheque in self.env['collection.cheque'].search(
    #                 [('comm_state', '=', False), ('date', '>=', self.from_date), ('date', '<=', self.to_date),
    #                  ('state', 'not in', ('deposit', 'done'))]):
    #
    #             ref = self.env['executive.cheque.collection']
    #             if each_cheque.advance_check_line:
    #                 ref = each_cheque.advance_check_line.a_collection_id.id
    #             if each_cheque.check_line:
    #                 ref = each_cheque.check_line.collection_id.id
    #
    #             product_line = (0, 0, {
    #                 'check_line': each_cheque.check_line.id,
    #                 'advance_check_line': each_cheque.advance_check_line.id,
    #                 'date': each_cheque.date,
    #                 # 'ref_id':each_cheque.check_line.collection_id.id,
    #                 'ref_id': ref,
    #                 'partner_id': each_cheque.partner_id.id,
    #                 'balance_amount': each_cheque.balance_amount,
    #                 'amount_total': each_cheque.amount_total,
    #                 'check_no': each_cheque.check_no,
    #                 'check_type': each_cheque.check_type,
    #                 'bank_name': each_cheque.bank_name,
    #                 # 'account_type': each_cheque.account_type,
    #                 'state': each_cheque.state,
    #                 'holder_name': each_cheque.holder_name,
    #                 # 'debited_account': each_cheque.debited_account,
    #             })
    #             today_total_cheques.append(product_line)
    #         self.today_lines = today_total_cheques
    #         journals = self.env['account.journal'].search(
    #             [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
    #         if journals:
    #             return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
    #     if self.sales_person:
    #         self.today_lines = False
    #         for each_cheque in self.env['collection.cheque'].search(
    #                 [('comm_state', '=', False), ('date', '>=', self.from_date), ('date', '<=', self.to_date),
    #                  ('sales_person', '=', self.sales_person.id),
    #                  ('state', 'not in', ('deposit', 'done'))]):
    #
    #             ref = self.env['executive.cheque.collection']
    #             if each_cheque.advance_check_line:
    #                 ref = each_cheque.advance_check_line.a_collection_id.id
    #             if each_cheque.check_line:
    #                 ref = each_cheque.check_line.collection_id.id
    #
    #             product_line = (0, 0, {
    #                 'check_line': each_cheque.check_line.id,
    #                 'advance_check_line': each_cheque.advance_check_line.id,
    #                 'date': each_cheque.date,
    #                 # 'ref_id':each_cheque.check_line.collection_id.id,
    #                 'ref_id': ref,
    #                 'partner_id': each_cheque.partner_id.id,
    #                 'balance_amount': each_cheque.balance_amount,
    #                 'amount_total': each_cheque.amount_total,
    #                 'check_no': each_cheque.check_no,
    #                 'check_type': each_cheque.check_type,
    #                 'bank_name': each_cheque.bank_name,
    #                 # 'account_type': each_cheque.account_type,
    #                 'state': each_cheque.state,
    #                 'holder_name': each_cheque.holder_name,
    #                 # 'debited_account': each_cheque.debited_account,
    #             })
    #             today_total_cheques.append(product_line)
    #         self.today_lines = today_total_cheques
    #         journals = self.env['account.journal'].search(
    #             [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
    #         if journals:
    #             return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
    #     if self.partner_id:
    #         self.today_lines = False
    #         for each_cheque in self.env['collection.cheque'].search(
    #                 [('comm_state', '=', False), ('date', '>=', self.from_date), ('date', '<=', self.to_date),
    #                  ('partner_id', '=', self.partner_id.id),
    #                  ('state', 'not in', ('deposit', 'done'))]):
    #
    #             ref = self.env['executive.cheque.collection']
    #             if each_cheque.advance_check_line:
    #                 ref = each_cheque.advance_check_line.a_collection_id.id
    #             if each_cheque.check_line:
    #                 ref = each_cheque.check_line.collection_id.id
    #
    #             product_line = (0, 0, {
    #                 'check_line': each_cheque.check_line.id,
    #                 'advance_check_line': each_cheque.advance_check_line.id,
    #                 'date': each_cheque.date,
    #                 # 'ref_id':each_cheque.check_line.collection_id.id,
    #                 'ref_id': ref,
    #                 'partner_id': each_cheque.partner_id.id,
    #                 'balance_amount': each_cheque.balance_amount,
    #                 'amount_total': each_cheque.amount_total,
    #                 'check_no': each_cheque.check_no,
    #                 'check_type': each_cheque.check_type,
    #                 'bank_name': each_cheque.bank_name,
    #                 # 'account_type': each_cheque.account_type,
    #                 'state': each_cheque.state,
    #                 'holder_name': each_cheque.holder_name,
    #                 # 'debited_account': each_cheque.debited_account,
    #             })
    #             today_total_cheques.append(product_line)
    #         self.today_lines = today_total_cheques
    #         journals = self.env['account.journal'].search(
    #             [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
    #         if journals:
    #             return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
    def action_view_journal(self):
        mod_obj = self.env["ir.model.data"]
        if self._context is None:
            self._context = {}
        model_data_ids = mod_obj.search(
            [
                ("model", "=", "ir.ui.view"),
                ("name", "=", "bulk_colle_test_form"),
            ]
        )
        resource_id = model_data_ids.read(fields=["res_id"])[0]["res_id"]
        return {
            "name": _("Create journals"),
            # "context": self._context,
            "view_type": "form",
            "view_mode": "form",
            "res_model": "bulk.collections",
            "views": [(resource_id, "form")],
            "type": "ir.actions.act_window",
            "target": "self",
            "context": {
                "default_from_date": datetime.today().date(),
                "default_to_date": datetime.today().date(),
                "default_collection_type": "cheque",
            }
        }

    @api.onchange('from_date', 'to_date', 'sales_person', 'partner_id', 'check_count')
    def onchange_payment_date(self):
        today_total_cheques = []
        self.today_lines = False
        if self.check_count == "submit":
            if not self.sales_person and not self.partner_id:
                for each_cheque in self.env['cheque.submission'].search(
                        [('type_state', '=', 'submit'), ('submitted_date', '>=', self.from_date),
                         ('submitted_date', '<=', self.to_date)
                         ]):

                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref = each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref = each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        # 'ref_id':each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        'partner_id': each_cheque.partner_id.id,
                        'balance_amount': each_cheque.balance_amount,
                        'amount_total': each_cheque.amount_total,
                        'check_no': each_cheque.check_no,
                        'check_type': each_cheque.check_type,
                        'bank_name': each_cheque.bank_name,
                        # 'account_type': each_cheque.account_type,
                        'state': each_cheque.state,
                        'submitted_date': each_cheque.submitted_date,
                        'holder_name': each_cheque.holder_name,
                        'debited_account': each_cheque.debited_account,
                        'account_id': each_cheque.account_id.id
                        # 'status': each_cheque.type_state,
                    })
                    today_total_cheques.append(product_line)
                self.today_lines = today_total_cheques
                journals = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
                if journals:
                    return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
            if self.sales_person:
                self.today_lines = False
                for each_cheque in self.env['cheque.submission'].search(
                        [('type_state', '=', 'submit'), ('sales_person', '=', self.sales_person.id),
                         ('submitted_date', '>=', self.from_date), (
                                 'submitted_date', '<=', self.to_date)]):

                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref = each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref = each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        # 'ref_id':each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        'partner_id': each_cheque.partner_id.id,
                        'balance_amount': each_cheque.balance_amount,
                        'amount_total': each_cheque.amount_total,
                        'check_no': each_cheque.check_no,
                        'check_type': each_cheque.check_type,
                        'bank_name': each_cheque.bank_name,
                        'submitted_date': each_cheque.submitted_date,
                        # 'account_type': each_cheque.account_type,
                        'state': each_cheque.state,
                        'holder_name': each_cheque.holder_name,
                        # 'account_id': each_cheque.account_id.id,
                        'debited_account': each_cheque.debited_account,
                    })
                    today_total_cheques.append(product_line)
                self.today_lines = today_total_cheques
                journals = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
                if journals:
                    return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
            if self.partner_id:
                self.today_lines = False
                for each_cheque in self.env['cheque.submission'].search(
                        [('type_state', '=', 'submit'), ('partner_id', '=', self.partner_id.id),
                         ('submitted_date', '>=', self.from_date), (
                                 'submitted_date', '<=', self.to_date)]):

                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref = each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref = each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        'submitted_date': each_cheque.submitted_date,
                        # 'ref_id':each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        # 'account_id': each_cheque.account_id.id,
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
                journals = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
                if journals:
                    return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}

        if self.check_count == "bounce":
            if not self.sales_person and not self.partner_id:
                self.today_lines = False
                for each_cheque in self.env['cheque.submission'].search(
                        [('type_state', '=', 'bounce'), ('submitted_date', '>=', self.from_date),
                         ('submitted_date', '<=', self.to_date)
                         ]):

                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref = each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref = each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        'submitted_date': each_cheque.submitted_date,
                        # 'ref_id':each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        # 'account_id': each_cheque.account_id.id,
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
                        'status': each_cheque.type_state,
                    })
                    today_total_cheques.append(product_line)
                self.today_lines = today_total_cheques
                journals = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
                if journals:
                    return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
            if self.sales_person:
                self.today_lines = False
                for each_cheque in self.env['cheque.submission'].search(
                        [('type_state', '=', 'bounce'), ('sales_person', '=', self.sales_person.id),
                         ('submitted_date', '>=', self.from_date), (
                                 'submitted_date', '<=', self.to_date)]):

                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref = each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref = each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        # 'ref_id':each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        'submitted_date': each_cheque.submitted_date,
                        'partner_id': each_cheque.partner_id.id,
                        'balance_amount': each_cheque.balance_amount,
                        'amount_total': each_cheque.amount_total,
                        # 'account_id': each_cheque.account_id.id,
                        'check_no': each_cheque.check_no,
                        'check_type': each_cheque.check_type,
                        'bank_name': each_cheque.bank_name,
                        # 'account_type': each_cheque.account_type,
                        'state': each_cheque.state,
                        'holder_name': each_cheque.holder_name,
                        'debited_account': each_cheque.debited_account,
                        'status': each_cheque.type_state,
                    })
                    today_total_cheques.append(product_line)
                self.today_lines = today_total_cheques
                journals = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
                if journals:
                    return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
            if self.partner_id:
                self.today_lines = False
                for each_cheque in self.env['cheque.submission'].search(
                        [('type_state', '=', 'bounce'), ('partner_id', '=', self.partner_id.id),
                         ('submitted_date', '>=', self.from_date), (
                                 'submitted_date', '<=', self.to_date)]):

                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref = each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref = each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        'submitted_date': each_cheque.submitted_date,
                        # 'ref_id':each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
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
                        'status': each_cheque.type_state,
                    })
                    today_total_cheques.append(product_line)
                self.today_lines = today_total_cheques
                journals = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
                if journals:
                    return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
        if self.check_count == "clear":
            if not self.sales_person and not self.partner_id:
                for each_cheque in self.env['cheque.submission'].search(
                        [('type_state', '=', 'deposit'), ('clearing_date', '>=', self.from_date),
                         ('clearing_date', '<=', self.to_date)
                         ]):

                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref = each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref = each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        # 'ref_id':each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        # 'account_id': each_cheque.account_id.id,
                        'submitted_date': each_cheque.submitted_date,
                        'clearing_date': each_cheque.clearing_date,
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
                        'status': each_cheque.type_state,
                    })
                    today_total_cheques.append(product_line)
                self.today_lines = today_total_cheques
                journals = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
                if journals:
                    return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
            if self.sales_person:
                self.today_lines = False
                for each_cheque in self.env['cheque.submission'].search(
                        [('type_state', '=', 'deposit'), ('sales_person', '=', self.sales_person.id),
                         ('submitted_date', '>=', self.from_date), (
                                 'submitted_date', '<=', self.to_date)]):

                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref = each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref = each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        'submitted_date': each_cheque.submitted_date,
                        # 'ref_id':each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        # 'account_id': each_cheque.account_id.id,
                        'clearing_date': each_cheque.clearing_date,
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
                        'status': each_cheque.type_state,
                    })
                    today_total_cheques.append(product_line)
                self.today_lines = today_total_cheques
                journals = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
                if journals:
                    return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
            if self.partner_id:
                self.today_lines = False
                for each_cheque in self.env['cheque.submission'].search(
                        [('type_state', '=', 'deposit'), ('partner_id', '=', self.partner_id.id),
                         ('submitted_date', '>=', self.from_date), (
                                 'submitted_date', '<=', self.to_date)]):

                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref = each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref = each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        # 'ref_id':each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        # 'account_id': each_cheque.account_id.id,
                        'submitted_date': each_cheque.submitted_date,
                        'partner_id': each_cheque.partner_id.id,
                        'balance_amount': each_cheque.balance_amount,
                        'amount_total': each_cheque.amount_total,
                        'check_no': each_cheque.check_no,
                        'check_type': each_cheque.check_type,
                        'bank_name': each_cheque.bank_name,
                        # 'account_type': each_cheque.account_type,
                        'state': each_cheque.state,
                        'clearing_date': each_cheque.clearing_date,
                        'holder_name': each_cheque.holder_name,
                        'debited_account': each_cheque.debited_account,
                        'status': each_cheque.type_state,
                    })
                    today_total_cheques.append(product_line)
                self.today_lines = today_total_cheques
                journals = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
                if journals:
                    return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}



        else:
            if not self.sales_person and not self.partner_id:
                for each_cheque in self.env['collection.cheque'].search(
                        [('comm_state', '=', False), ('date', '>=', self.from_date), ('date', '<=', self.to_date),
                         ('state', '=', 'draft')]):
                    sub_rec = self.env['cheque.submission'].search(
                        [('partner_id', '=', each_cheque.partner_id.id), ('check_no', '=', each_cheque.check_no)
                         ])
                    if sub_rec:
                        continue
                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref = each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref = each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        # 'ref_id':each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        # 'account_id': each_cheque.account_id.id,
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
                journals = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
                if journals:
                    return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
            if self.sales_person:
                self.today_lines = False
                for each_cheque in self.env['collection.cheque'].search(
                        [('comm_state', '=', False), ('date', '>=', self.from_date), ('date', '<=', self.to_date),
                         ('sales_person', '=', self.sales_person.id),
                         ('state', 'not in', ('deposit', 'done'))]):
                    sub_rec = self.env['cheque.submission'].search(
                        [('partner_id', '=', each_cheque.partner_id.id), ('check_no', '=', each_cheque.check_no)
                         ])
                    if sub_rec:
                        continue

                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref = each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref = each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        # 'ref_id':each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        # 'account_id': each_cheque.account_id.id,
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
                journals = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
                if journals:
                    return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}
            if self.partner_id:
                self.today_lines = False
                for each_cheque in self.env['collection.cheque'].search(
                        [('comm_state', '=', False), ('date', '>=', self.from_date), ('date', '<=', self.to_date),
                         ('partner_id', '=', self.partner_id.id),
                         ('state', 'not in', ('deposit', 'done'))]):
                    sub_rec = self.env['cheque.submission'].search(
                        [('partner_id', '=', each_cheque.partner_id.id), ('check_no', '=', each_cheque.check_no)
                         ])
                    if sub_rec:
                        continue

                    ref = self.env['executive.cheque.collection']
                    if each_cheque.advance_check_line:
                        ref = each_cheque.advance_check_line.a_collection_id.id
                    if each_cheque.check_line:
                        ref = each_cheque.check_line.collection_id.id

                    product_line = (0, 0, {
                        'check_line': each_cheque.check_line.id,
                        'advance_check_line': each_cheque.advance_check_line.id,
                        'date': each_cheque.date,
                        # 'ref_id':each_cheque.check_line.collection_id.id,
                        'ref_id': ref,
                        # 'account_id': each_cheque.account_id.id,
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
                journals = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
                if journals:
                    return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}

    # self.ref_id =
    # @api.multi
    def action_cheque_statement(self):

        return self.env.ref('ezp_cash_collection.executive_cheque_collection_id1').report_action(self)


class TodayChequeLines(models.Model):
    _name = "today.cheques.line"

    today_id = fields.Many2one('today.cheques')
    bulk_cheque = fields.Many2one('bulk.collections')
    check_line = fields.Many2one('executive.cheque.collection.line')
    advance_check_line = fields.Many2one('advance.cheque.collection.line')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Bal Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    ref_id = fields.Many2one('executive.cheque.collection', string="Source")
    account_id = fields.Many2one('account.account', string='Debit Acc')
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_cheque_relks')
    check_no = fields.Char(string='Cheque No')
    apply = fields.Boolean(default=False, string='Apply')
    check_type = fields.Selection([('cash', 'Cash'), ('pdc', 'PDC'), ], string="Check Type", )
    check_date = fields.Date(string='Check Date', default=fields.Date.today())
    check_manual_date = fields.Date(string='Check Date', )
    new_date = fields.Date(string='New Date')
    clearing_date = fields.Date(string='Clear Date')
    submitted_date = fields.Date(string='Submitted Date')
    bounce_date = fields.Date(string='Bounce Date')
    bank_name = fields.Char('Back Name')
    reason = fields.Text('Reason')
    check_post_id = fields.Many2one('post.cheques.line')
    check_bounce_id = fields.Many2one('bounce.cheques.line')
    collection_cheque_id = fields.Many2one('today.cheques.line')
    status = fields.Selection([
        ('none', ''),
        ('submit', 'submitted'),
        # ('postpone', 'Postpone'),
        ('deposit', 'Cleared'),
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

    @api.onchange('status')
    def onchange_status(self):
        if self.status == "deposit":
            self.clearing_date = datetime.today().date()
        if self.status == "submit":
            self.submitted_date = datetime.today().date()

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.invoice'].search(
                [('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                self.balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))

    @api.onchange('apply')
    def onchange_apply(self):
        if self.apply == True:
            journals = self.env['account.journal'].search(
                [('company_id', '!=', 1), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'debited_account': [('id', 'in', journals.ids)]}}


class PostCheques(models.Model):
    _name = "post.cheques"
    _description = "Post Cheques"
    _order = "id desc"

    name = fields.Char("Collection Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)

    user_id = fields.Many2one('res.users', string='Responsible', index=True, track_visibility='onchange',
                              track_sequence=2, default=lambda self: self.env.user)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Done'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status", )

    payment_date = fields.Date(string='Date', default=fields.Date.context_today, required=True, copy=False)
    today_lines = fields.One2many('post.cheques.line', 'today_id')
    paid_amount = fields.Float(string='Paid Amount', compute='_compute_paid_amount')
    Bal_amount = fields.Float(string='Bal Amount', compute='_compute_paid_amount')
    total_amount = fields.Float(string='Total Amount', compute='_compute_paid_amount')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'post.cheques') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('post.cheques') or _('New')
        return super(PostCheques, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # @api.one
    def _compute_paid_amount(self):
        self.Bal_amount = sum(self.today_lines.mapped('balance_amount')) - sum(
            self.today_lines.mapped('amount_total'))
        self.paid_amount = sum(self.today_lines.mapped('amount_total'))
        self.total_amount = sum(self.today_lines.mapped('balance_amount'))

    # def action_confirm(self):
    #     for each in self.today_lines:
    #         each.check_line.write({'state':'deposit'})
    #         each.check_line.debited_account = each.debited_account
    #         each.check_line.collected_cheque.write({'state':'deposit'})
    #         each.check_line.collected_cheque.debited_account=each.debited_account
    #         # each.check_line.collection_id.write({'state':'deposited'})
    #         if each.check_line.check_ref_id:
    #             each.check_line.check_ref_id.debited_account = each.debited_account
    #             each.check_line.check_ref_id.write({'state': 'deposit'})
    #             # each.check_line.check_ref_id.collected_cheque.write({'state': 'deposit'})
    #
    #         each.write({'state':'deposit'})
    #     self.write({'state': 'validate'})

    # @api.multi
    def action_cheque_statement(self):

        return self.env.ref('ezp_cash_collection.executive_cheque_collection_id1').report_action(self)


class PostChequesLines(models.Model):
    _name = "post.cheques.line"

    today_id = fields.Many2one('post.cheques')
    check_line = fields.Many2one('executive.cheque.collection.line')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Bal Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    ref_id = fields.Many2one('executive.cheque.collection', string="Source")
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_cheque_post')
    post_date = fields.Date('Postpone Date')
    cheque_ref_id = fields.Many2one('executive.cheque.collection.line')
    collected_cheque = fields.Many2one('collection.cheque', )
    debited_account = fields.Many2one('account.journal', string='Debit A/C')
    ref_today_id = fields.Many2one('today.cheques.line', string='Debit A/C')

    status = fields.Selection([
        ('none', ''),
        ('deposit', 'Deposit'),
        ('postpone', 'Postpone'),
        ('bounce', 'Bounce'),
        ('cancel', 'Cancelled')], string='Status',
        default='none')
    check_no = fields.Char(string='Cheque No')
    apply = fields.Boolean(default=False, string='Apply')
    check_type = fields.Selection([('cash', 'Cash'), ('pdc', 'PDC'), ], string="Check Type", )
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
        ('cancel', 'Cancelled')], string='state', readonly=True,
        default='draft')
    # account_type = fields.Selection([
    #     ('current', 'Current'),
    #     ('saving', 'Saving'),
    # ], string="Account Type")
    holder_name = fields.Many2one('res.partner', string='Holder Name')
    debited_account = fields.Many2one('account.journal', string='Debit A/C', required=True)
    collected_cheque = fields.Many2one('collection.cheque', )

    @api.onchange('state', 'status')
    def onchange_state(self):
        if len(self.today_id.mapped('today_lines')) == len(
                self.today_id.mapped('today_lines').search([('state', '=', 'done')])):
            self.today_id.write({'state': 'validate'})

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


class BounceCheques(models.Model):
    _name = "bounce.cheques"
    _description = "Bounce Cheques"
    _order = "id desc"

    name = fields.Char("Collection Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)

    user_id = fields.Many2one('res.users', string='Responsible', index=True, track_visibility='onchange',
                              track_sequence=2, default=lambda self: self.env.user)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Done'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")

    payment_date = fields.Date(string='Date', default=fields.Date.context_today, required=True, copy=False)
    today_lines = fields.One2many('bounce.cheques.line', 'today_id')
    paid_amount = fields.Float(string='Paid Amount', compute='_compute_paid_amount')
    Bal_amount = fields.Float(string='Bal Amount', compute='_compute_paid_amount')
    total_amount = fields.Float(string='Total Amount', compute='_compute_paid_amount')
    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')])
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method Type',
                                        oldname="payment_method",
                                        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n" \
                                             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n" \
                                             "Check: Pay bill by check and print it from Odoo.\n" \
                                             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n" \
                                             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'bounce.cheques') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('bounce.cheques') or _('New')
        return super(BounceCheques, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # @api.one
    def _compute_paid_amount(self):
        self.Bal_amount = sum(self.today_lines.mapped('balance_amount')) - sum(
            self.today_lines.mapped('amount_total'))
        self.paid_amount = sum(self.today_lines.mapped('amount_total'))
        self.total_amount = sum(self.today_lines.mapped('balance_amount'))

    def action_confirm(self):
        for each in self.today_lines:
            # each.collected_cheque.new_date = each.new_date
            each.ref_today_id.check_line.new_date = each.new_date
            self.env['collection.cheque'].search(
                [('check_line', '=', each.ref_today_id.check_line.id)]).date = each.new_date
        self.write({'state': 'validate'})

    # @api.multi
    def action_cheque_statement(self):

        return self.env.ref('ezp_cash_collection.executive_cheque_collection_id1').report_action(self)


class BounceChequesLines(models.Model):
    _name = "bounce.cheques.line"

    today_id = fields.Many2one('bounce.cheques')
    check_line = fields.Many2one('executive.cheque.collection.line')
    date = fields.Date('Date', default=fields.Date.context_today, )
    new_date = fields.Date('New Date', )
    bounce_date = fields.Date('Bounced Date', )
    partner_id = fields.Many2one('res.partner', 'Partner')
    balance_amount = fields.Float(string='Bal Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    ref_id = fields.Many2one('executive.cheque.collection', string="Source")
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_cheque_bounce')
    cheque_ref_id = fields.Many2one('executive.cheque.collection.line')
    collected_cheque = fields.Many2one('collection.cheque', )
    debited_account = fields.Many2one('account.journal', string='Debit A/C')
    status = fields.Selection([
        ('none', ''),
        ('deposit', 'Deposit'),
        ('postpone', 'Postpone'),
        ('bounce', 'Bounce'),
        ('cancel', 'Cancelled')], string='Status',
        default='none')
    check_no = fields.Char(string='Cheque No')
    apply = fields.Boolean(default=False, string='Apply')
    check_type = fields.Selection([('cash', 'Cash'), ('pdc', 'PDC'), ], string="Check Type", )
    check_date = fields.Date(string='Check Date', default=fields.Date.today())
    check_manual_date = fields.Date(string='Check Date', )
    bank_name = fields.Char('Back Name')
    reason = fields.Text('Reason')
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
    debited_account = fields.Many2one('account.journal', string='Debit A/C', )
    collected_cheque = fields.Many2one('collection.cheque', )
    ref_today_id = fields.Many2one('today.cheques.line', string='Debit A/C')

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


