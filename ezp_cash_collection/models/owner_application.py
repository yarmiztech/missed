# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time
from datetime import datetime, timedelta
from odoo.tools.translate import _
import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dt
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class OwnerApplication(models.Model):
    _name = 'owner.application'
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))

    type = fields.Selection([
        ('data', 'Data Entry'),
        ('executive', 'Sales Executive'),
        ('direct', 'Direct'),
        ('owner', 'Owner'),
    ], string='Type Of Order', copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='data')
    sales_executive = fields.Many2one('res.partner',string='Sales Executive',domain=[('user_id','!=',False)])
    area = fields.Many2one('area.wise', string='Area')
    partner_id = fields.Many2one('res.partner', string='Estimate')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float('Quantity')
    outstanding_amount = fields.Float('Outstanding Amount', compute='_compute_outstanding_amount')
    create_date = fields.Date('Date')
    company_id = fields.Many2one('res.company', string='Company')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'owner.application') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('owner.application') or _('New')
        return super(OwnerApplication, self).create(vals)

    # @api.multi
    def _compute_outstanding_amount(self):
        for line in self:
            record_ref = self.env['partner.ledger.customer'].search(
                [('product_id', '=', line.product_id.id), ('partner_id', '=', line.partner_id.id)])
            if record_ref:
                if len(record_ref) > 1:
                    line.outstanding_amount = record_ref[-1].balance
                else:
                    line.outstanding_amount = record_ref[0].balance
            else:
                line.outstanding_amount =0

    def action_post(self):
        self.write({'state': 'done'})
        for line in self.freight_lines:
            j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0].id

            # pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
            #                                              'amount': line.amount,
            #                                              'partner_type': 'customer',
            #                                              'payment_type': 'inbound',
            #                                              'payment_method_id': j,
            #                                              'journal_id': line.journal_id.id,
            #                                              'communication': line.freight.name,
            #                                              # 'invoice_ids': [(6, 0, line.invoice_id.ids)]
            #                                              })

            vals = {
                'journal_id':line.journal_id.id,
                'state': 'draft',
                'ref': line.partner_id.name + 'Freight/Charges'
            }
            pay_id_list = []
            move_id = self.env['account.move'].create(vals)
            partner_id = line.partner_id.id
            label = 'Freight/Charges' + '/' + line.partner_id.name

            if self.type_of_partner == 'partner':
                if self.type_of_credit == False:

                    acc = line.account_id
                    temp = (0, 0, {
                        'account_id': acc.id,
                        'name': label,
                        'move_id': move_id.id,
                        'date': datetime.today().date(),
                        'partner_id': line.partner_id.id,
                        'debit': 0,
                        'credit': line.amount,
                    })
                    pay_id_list.append(temp)
                    temp = (0, 0, {
                        'account_id': self.env['account.account'].search(
                            [('name', '=', 'Creditors'), ('company_id', '=', 1)]).id,
                        'name': label,
                        'move_id': move_id.id,
                        'date': datetime.today().date(),
                        'partner_id': line.partner_id.id,
                        'debit': line.amount,
                        'credit': 0,
                    })
                    pay_id_list.append(temp)

                    move_id.line_ids = pay_id_list
                    move_id.action_post()
                    if self.journal_id.type == 'cash':
                        if not self.env['cash.book.info'].search([]):
                            complete = sum(
                                self.env['account.move.line'].search([('journal_id', '=', line.journal_id.id)]).mapped(
                                    'debit'))
                        else:
                            complete = self.env['cash.book.info'].search([])[-1].balance

                        debit = 0
                        credit = 0
                        complete_new = 0
                        acc = self.env['account.account']
                        # if self.payment_type == 'outbound':
                        credit = self.amount
                        complete_new = complete - credit
                        acc = line.journal_id.payment_credit_account_id.id
                        # if self.payment_type == 'inbound':
                        #     debit = self.amount
                        #     complete_new = complete + debit
                        #     acc = self.journal_id.default_debit_account_id.id

                        self.env['cash.book.info'].create({
                            'date': datetime.today().date(),
                            'account_journal': line.journal_id.id,
                            'partner_id': line.partner_id.id,
                            'company_id': 1,
                            # 'description': self.communication,
                            'description': line.partner_id.name,
                            'payment_type': 'outbound',
                            'partner_type':'customer',
                            'debit': debit,
                            'credit': credit,
                            'account': acc,
                            # 'payment_id': self.id,
                            'balance': complete_new

                        })

            # pay_id.action_post()
            # pay_id.action_cash_book()
            invoices = self.env['account.move'].search(
                [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.company_id.id),
                 ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                balance_amount = sum(invoices.mapped('amount_total'))
            balance_amount += self.env['partner.ledger.customer'].search(
                [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
            balance_amount = self.env['partner.ledger.customer'].search(
                [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)])[
                -1].balance
            self.env['partner.ledger.customer'].sudo().create({
                'date': datetime.today().date(),
                'description': line.freight.name,
                'partner_id': line.partner_id.id,
                'company_id': self.company_id.id,
                'account_journal': line.journal_id.id,
                # 'account_move': pay_id.move_line_ids.mapped('move_id').id,
                'account_move': move_id.id,
                'credit': line.amount,
                # 'debit': line.op_amount,
                # 'balance': 0,
                # 'executive_area': self.executive_areas.id or False,
                # 'area': self.area.id or False,
                # 'vehicle_id': self.estimate_ids[0].vahicle.id,
                'balance': balance_amount - line.amount,
            })

            # vals = {
            #     'journal_id': line.journal_id.id,
            #     'state': 'draft',
            #     'ref': line.freight.name
            # }
            # pay_id_list = []
            # move_id = self.env['account.move'].create(vals)
            # temp = (0, 0, {
            #     'account_id': line.journal_id.default_debit_account_id.id,
            #     'name': line.freight.name,
            #     'move_id': move_id.id,
            #     'date': self.create_date,
            #     'partner_id': line.partner_id.id,
            #     'debit': line.amount,
            #     'credit': 0,
            # })
            # pay_id_list.append(temp)
            #
            # temp = (0, 0, {
            #     'account_id': line.journal_id.payment_credit_account_id.id,
            #     'name': line.freight.name,
            #     'move_id': move_id.id,
            #     'date': self.create_date,
            #     # 'partner_id': self.partner_id.id,
            #     'debit': 0,
            #     'credit': line.amount,
            # })
            # pay_id_list.append(temp)
            # move_id.line_ids = pay_id_list
            # move_id.action_post()
            # if line.journal_id.type == 'cash':
            #     # complete = sum(self.env['account.move.line'].search([('journal_id', '=', acc.id)]).mapped('debit'))
            #     complete = sum(self.env['account.move.line'].search(
            #         [('company_id', '=', self.env.user.company_id.id), ('account_id', '=', line.journal_id.payment_credit_account_id.id)]).mapped(
            #         'debit'))
            #     debit = 0
            #     credit = line.amount
            #     complete_new = complete - credit
            #     acc = acc
            #     self.env['cash.book.info'].create({
            #         'date': self.create_date,
            #         'account_journal': line.journal_id.id,
            #         'account': acc.id,
            #         'partner_id': self.partner_id.id,
            #         'company_id': 1,
            #         'description': line.freight.name + ' ' + line.partner_id.name,
            #         'debit': debit,
            #         'credit': credit,
            #         'balance': complete_new
            #
            #     })
            #


class FreightDiscountLines(models.Model):
    _name = 'freight.disc.lines'


    @api.model
    def _default_journal_id(self):
        return self.env['account.journal'].search(
            [('name', '=', 'Miscellaneous Operations'), ('company_id', '=', self.env.user.company_id.id)])


    freight_id = fields.Many2one('freight.disc')
    partner_id = fields.Many2one('res.partner', string='Partner', domain=[('estimator', '=', True)])
    freight = fields.Many2one('freight.disc.config', string='Discount/Charge', )
    amount = fields.Float('Amount')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade',default=_default_journal_id,
                                 help="This field is ignored in a bank statement reconciliation.")
    account_id = fields.Many2one('account.account', string='Account')


    @api.onchange('journal_id')
    def onchange_reason(self):
        if self.journal_id:
            expenses_accs = self.env['account.account'].search([('user_type_id.name', '=','Expenses')])
            return {'domain': {'account_id': [('id', 'in', expenses_accs.ids)]}}


class OwnerAreawise(models.Model):
    _name = "owner.areawise"
    _description = "Aged Report"
    _order = "id desc"

    name = fields.Char("Name", index=True, default=lambda self: _('New'))
    from_date = fields.Date('From Date', default=fields.Date.context_today, )
    to_date = fields.Date('To Date', default=fields.Date.context_today, )
    sequence = fields.Integer(index=True)
    exec = fields.Boolean(default=True)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Done'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")

    area = fields.Many2one('area.wise', string='Area')
    sales_executive = fields.Many2one('res.partner',string='Sales Executive',domain=[('user_id','!=',False)])
    area_lines = fields.One2many('owner.areawise.line', 'owner_area_id')
    read_executive = fields.Boolean(defalut=False)

    @api.onchange('exec')
    def onchange_exec(self):
        if self.exec == True:
            if not self.env.user.groups_id.filtered(lambda a:a.display_name == 'Cash Collection / Owner'):
               self.sales_executive = self.env.user.partner_id
               self.read_executive = True



    # @api.onchange('area', 'form_date', 'to_date')
    @api.onchange('area', 'from_date', 'to_date','sales_executive')
    def onchange_area(self):
        self.area_lines = False
        today_total_cheques = []
        if self.sales_executive:
            for each_cheque in self.env['owner.application'].search(
                    [('company_id','=',self.env.user.company_id.id),('create_date', '>=', self.from_date), ('create_date', '<=', self.to_date),
                     ('sales_executive','=',self.sales_executive.id),('area', '=', self.area.id)]):
                product_line = (0, 0, {
                    'date': each_cheque.create_date,
                    'partner_id': each_cheque.partner_id.id,
                    'product_id': each_cheque.product_id.id,
                    'area': each_cheque.area.id,
                    'quantity': each_cheque.quantity,
                    'company_id': each_cheque.company_id.id,
                    'outstanding_amount': each_cheque.outstanding_amount,
                })
                today_total_cheques.append(product_line)
        else:
            for each_cheque in self.env['owner.application'].search(
                    [('company_id','=',self.env.user.company_id.id),('create_date', '>=', self.from_date), ('create_date', '<=', self.to_date),
                     ('area', '=', self.area.id)]):
                product_line = (0, 0, {
                    'date': each_cheque.create_date,
                    'partner_id': each_cheque.partner_id.id,
                    'product_id': each_cheque.product_id.id,
                    'area': each_cheque.area.id,
                    'quantity': each_cheque.quantity,
                    'company_id': each_cheque.company_id.id,
                    'outstanding_amount': each_cheque.outstanding_amount,
                })
                today_total_cheques.append(product_line)
        self.area_lines = today_total_cheques

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'owner.areawise') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('owner.areawise') or _('New')
        return super(OwnerAreawise, self).create(vals)


class OwnerAreawiseLine(models.Model):
    _name = 'owner.areawise.line'
    _order = 'id desc'

    owner_area_id = fields.Many2one('owner.areawise', string='Area')
    area = fields.Many2one('area.wise', string='Area')
    partner_id = fields.Many2one('res.partner', string='Estimate')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float('Quantity')
    outstanding_amount = fields.Float('Outstanding Amount')
    date = fields.Date('Date')
    company_id = fields.Many2one('res.company', string='Company')

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', _('New')) == _('New'):
    #         if 'company_id' in vals:
    #             vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
    #                 'owner.areawise') or _('New')
    #         else:
    #             vals['name'] = self.env['ir.sequence'].next_by_code('owner.areawise') or _('New')
    #     return super(OwnerAreawise, self).create(vals)

    # @api.multi
    def _compute_outstanding_amount(self):
        for line in self:
            record_ref = self.env['partner.ledger.customer'].search(
                [('product_id', '=', line.product_id.id), ('partner_id', '=', line.partner_id.id)])
            if record_ref:
                if len(record_ref) > 1:
                    line.outstanding_amount = record_ref[-1].balance
                else:
                    line.outstanding_amount = record_ref[0].balance


class ExecutiveFullReport(models.Model):
    _inherit = "executive.full.report"

    type = fields.Selection(selection_add=[('collected', 'Collected'), ('visit', 'Visited')])
    collected_lines = fields.One2many('collected.full.line', 'coll_report')
    visited_lines = fields.One2many('visited.full.line', 'visit_report')
    executive = fields.Boolean(default=False)
    read_executive = fields.Boolean(default=False)

    @api.onchange('executive')
    def onchange_executive_new(self):
        if self.executive == True:
            if not self.env.user.groups_id.filtered(lambda a: a.display_name == 'Cash Collection / Owner'):
                self.sales_person = self.env.user.partner_id
                self.read_executive = True


    @api.onchange('sales_person', 'from_date', 'to_date', 'type')
    def onchange_from_date(self):
        self.executive_lines = False
        today_total_cheques = []
        if self.type == 'total':
            self.executive_lines = False
            self.collected_lines = False
            self.visited_lines = False
            if not self.sales_person:
                for each_cheque in self.env['sales.person.details'].search(
                        [('company_id', '=', self.company_id.id), ('create_date', '>=', self.from_date),
                         ('create_date', '<=', self.to_date)]):
                    # for each_target in each_cheque.target_lines:
                    product_line = (0, 0, {
                        'create_date': each_cheque.create_date,
                        'sales_person': each_cheque.sales_person.id,
                        'partner_id': each_cheque.partner_id.id,
                        'product_id': each_cheque.product_id.id,
                        'product_uom_qty': each_cheque.product_uom_qty,
                        'price': each_cheque.price,
                        'subtotal': each_cheque.subtotal,
                    })
                    today_total_cheques.append(product_line)
            else:
                for each_cheque in self.env['sales.person.details'].search(
                        [('sales_person','=',self.sales_person.id),('company_id', '=', self.company_id.id), ('create_date', '>=', self.from_date),
                         ('create_date', '<=', self.to_date)]):
                    # for each_target in each_cheque.target_lines:
                    product_line = (0, 0, {
                        'create_date': each_cheque.create_date,
                        'sales_person': each_cheque.sales_person.id,
                        'partner_id': each_cheque.partner_id.id,
                        'product_id': each_cheque.product_id.id,
                        'product_uom_qty': each_cheque.product_uom_qty,
                        'price': each_cheque.price,
                        'subtotal': each_cheque.subtotal,
                    })
                    today_total_cheques.append(product_line)
            self.executive_lines = today_total_cheques

        if self.type == 'collected':
            self.executive_lines = False
            self.collected_lines = False
            self.visited_lines = False
            for each_cheque in self.env['executive.collection'].search(
                    [('payment_date', '>=', self.from_date),
                     ('payment_date', '<=', self.to_date)]):
                for each_target in each_cheque.partner_invoices:
                    product_line = (0, 0, {
                        'date': each_cheque.payment_date,
                        'sales_person': each_cheque.user_id.partner_id.id,
                        'partner_id': each_target.partner_id.id,
                        'type': 'Cash',
                        'outstanding_balance': each_target.balance_amount,
                        'collected_amount': each_target.amount_total,
                        'balance': each_target.balance_amount - each_target.amount_total,
                    })
                    today_total_cheques.append(product_line)

            for each_cheque in self.env['executive.cheque.collection'].search(
                    [('payment_date', '>=', self.from_date),
                     ('payment_date', '<=', self.to_date)]):
                for each_target in each_cheque.partner_invoices:
                    product_line = (0, 0, {
                        'date': each_cheque.payment_date,
                        'sales_person': each_cheque.user_id.partner_id.id,
                        'partner_id': each_target.partner_id.id,
                        'outstanding_balance': each_target.balance_amount,
                        'collected_amount': each_target.amount_total,
                        'type':'Cheque',
                        'balance': each_target.balance_amount - each_target.amount_total,
                    })
                    today_total_cheques.append(product_line)

            self.collected_lines = today_total_cheques
        if self.type == 'visit':
            self.executive_lines = False
            self.collected_lines = False
            self.visited_lines = False
            for each_cheque in self.env['executive.areas.assign'].search(
                    [('company_id', '=', self.company_id.id), ('date', '>=', self.from_date),
                     ('date', '<=', self.to_date)]):
                for each_target in each_cheque.partner_lines:
                    product_line = (0, 0, {
                        'date': each_cheque.date,
                        'sales_person': each_cheque.sales_person.id,
                        'partner_id': each_target.partner_id.id,
                        'reason': each_target.reason,
                        'state': each_target.state,
                        'next_visit_date': each_target.next_visit_date,
                    })
                    today_total_cheques.append(product_line)
                for each_target in each_cheque.partner_other_lines:
                    product_line = (0, 0, {
                        'date': each_cheque.date,
                        'sales_person': each_cheque.sales_person.id,
                        'partner_id': each_target.partner_id.id,
                        'reason': each_target.reason,
                        'state': each_target.state,
                        'next_visit_date': each_target.next_visit_date,
                    })
                    today_total_cheques.append(product_line)

            self.visited_lines = today_total_cheques


class CollectedLineReport(models.Model):
    _name = 'collected.full.line'

    coll_report = fields.Many2one('executive.full.report', string='Target')
    sales_person = fields.Many2one('res.partner', string='Sales Person')
    partner_id = fields.Many2one('res.partner', string='Partner')
    outstanding_balance = fields.Float(string='Outstanding')
    collected_amount = fields.Float(string='Collected')
    balance = fields.Float('Balance')
    date = fields.Date(string='Date')
    type = fields.Char('Type')


class VisitedLineReport(models.Model):
    _name = 'visited.full.line'

    visit_report = fields.Many2one('executive.full.report', string='Target')
    sales_person = fields.Many2one('res.partner', string='Sales Person')
    partner_id = fields.Many2one('res.partner', string='Partner')
    state = fields.Selection([
        ('draft', 'Not Visited'),
        ('visit', 'visited'),
        ('n_visit', 'Next visit'),
    ], string='Status', copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    reason = fields.Text(string='Reason')
    next_visit_date = fields.Date(string='Date')
    date = fields.Date(string='Date')
