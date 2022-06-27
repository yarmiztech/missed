# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import date
import time
import fcntl
import socket
import struct
import macpath
from uuid import getnode as get_mac
from odoo.exceptions import UserError, ValidationError


class ExecutiveAreaAssign(models.Model):
    _name = 'executive.areas.assign'
    _order = 'id desc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    @api.model
    def _default_sales_person(self):
        return self.env['res.users'].browse(self.env.user.id).partner_id

    @api.model
    def _default_executive_area(self):
        ass = self.env['areas.executive.config'].search(
            [('sales_person', '=', self.env['res.users'].browse(self.env.user.id).partner_id.id)])
        if ass:
            return ass.days_line.filtered(lambda a: a.week_list == str(datetime.today().weekday())).executive_area

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    executive_area = fields.Many2one('executive.area.wise', string='Assign Area', default=_default_executive_area)
    date = fields.Date('Date', default=fields.Date.context_today)
    user_id = fields.Many2one('res.users', string='User', default=_default_user)
    # partner_id = fields.Many2one('res.partner', string='Customer', domain="[('customer', '=', True)]")
    sales_person = fields.Many2one('res.partner', string='Sales Person', default=_default_sales_person)
    # partner_area = fields.Many2one('area.wise', string='Customer Area')
    read_sales_person = fields.Boolean(default=False)
    # out_standing_balance = fields.Float('Outstanding')
    state = fields.Selection([
        ('draft', 'Pending'),
        ('done', 'Completed'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    # collected_amount = fields.Float('Collected Amount')
    reason = fields.Text('Reason')
    select_all = fields.Boolean('Assigned to All')
    select_filter = fields.Boolean('filter')
    # balance = fields.Float('Balance Amount')
    next_visit_date = fields.Date('Next Visiting Date')
    partner_lines = fields.One2many('areas.customers', 'assign_id')
    partner_other_lines = fields.One2many('areas.customers.other', 'assign_other_id')
    partner_filter_lines = fields.One2many('areas.filter.lines', 'assign_filter_id')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)

    @api.model
    def cron_auto_collect_executive(self):
        for all_users in self.env['executive.areas.assign'].sudo().search([]).mapped('sales_person').mapped('user_id'):
            act = self.env['collection.reminder.config'].search([('sales_person', '=', all_users.partner_id.id)])
            if act:
                if act.active == True:
                    for each in self.env['executive.areas.assign'].sudo().search(
                            [('state', '=', 'draft'),
                             ('sales_person', '=', self.env['res.users'].browse(all_users.id).partner_id.id)]):
                        # for rec in self.env['areas.customers'].search(
                        #         [('next_visit_date', '=', datetime.today().date() + timedelta(days=2))]):
                        # self.env['res.users'].browse(all_users.id).notify_info(
                        #     message='You need to Collect Amount from customers today')
                        test_msg = {"message": "You need to Collect Amount from customers today",
                                    "title": "Today Collections",
                                    "sticky": True}
                        return self.env['res.users'].browse(all_users.id).notify_info(**test_msg)

    @api.onchange('sales_person')
    def _onchange_sales_person(self):
        if not self.env.user.groups_id.filtered(lambda a: a.display_name == 'Cash Collection / Owner'):
            self.read_sales_person = True
        # areas = self.env['area.wise'].search([('executive_area', '=', self.sales_person.id)])
        dom = self.env['res.partner'].search([('id', '=', self.sales_person.id)])
        if dom:
            return {'domain': {'executive_area': [('id', 'in', dom.executive_area.ids)]}}

    @api.onchange('select_all')
    def _onchange_select_all(self):
        for line in self.partner_lines:
            if line.state == 'draft':
                line.state = 'visit'
                line.reason = self.reason
                line.next_visit_date = self.next_visit_date

    @api.onchange('next_visit_date')
    def _onchange_next_visit_date(self):
        for line in self.partner_lines:
            if line.select == True and line.state == 'draft':
                if line.state == 'draft':
                    line.reason = self.reason
                    line.state = 'visit'
                    line.next_visit_date = self.next_visit_date
                # if line.next_visit_date:

    @api.onchange('select_filter')
    def _onchange_select_filter(self):
        if self.select_filter == True:
            list = []
            for each in self.partner_lines.filtered(lambda a:a.state == 'draft'):
                line = (0, 0, {
                    'partner_id':each.partner_id.id,
                    'out_standing_balance':each.out_standing_balance,
                    'state':each.state,
                    'collected_amount':each.collected_amount,
                    'reason':each.reason,
                    'balance':each.balance,
                    'next_visit_date':each.next_visit_date
                })
                list.append(line)
            self.partner_filter_lines = list
        else:
            self.partner_filter_lines = False



    @api.onchange('executive_area')
    def _onchange_executive_area(self):
        self.partner_lines = False
        areas = self.env['area.wise'].search([('executive_area', '=', self.executive_area.id)])
        dom = self.env['res.partner'].search([('estimator', '=', True)]).filtered(lambda a: a.area == areas)
        history_list = []
        for each in dom:
            balance = 0
            for details in self.env['account.move'].search(
                    [('company_id', '=', 1), ('state', '!=', 'paid'), ('partner_id', '=', each.id)]):
                # details
                outstand = 0
                if self.env['partner.ledger.customer'].search(
                        [('partner_id', '=', each.id), ('company_id', '=', self.company_id.id)]):
                    outstand = self.env['partner.ledger.customer'].search(
                        [('partner_id', '=', each.id), ('company_id', '=', self.company_id.id)])[-1].balance
                # if outstand > 0:
                    balance = outstand
            if self.env['partner.ledger.customer'].search(
                    [('partner_id', '=', each.id), ('company_id', '=', self.company_id.id)]):
                outstand = self.env['partner.ledger.customer'].search(
                    [('partner_id', '=', each.id), ('company_id', '=', self.company_id.id)])[-1].balance
                # if outstand > 0:
                balance = outstand
            print('fgrgrt')
            state = 'draft'
            if balance:
                cash_collection = self.env['executive.collection'].search(
                    [('payment_date', '=', datetime.today().date())]).mapped('partner_invoices')
                if cash_collection:
                    if cash_collection.filtered(lambda a: a.partner_id == each):
                        state = 'visit'
                        line = (0, 0, {
                            'executive_area': self.executive_area.id,
                            'partner_id': each.id,
                            'out_standing_balance': balance,
                            'state': state,
                        })
                        history_list.append(line)
                    else:
                        state = 'draft'

                if state == 'draft':
                    check_collection = self.env['executive.cheque.collection'].search(
                        [('payment_date', '=', datetime.today().date())]).mapped('partner_invoices')
                    if check_collection:
                        if check_collection.filtered(lambda a: a.partner_id == each):
                            state = 'visit'
                            line = (0, 0, {
                                'executive_area': self.executive_area.id,
                                'partner_id': each.id,
                                'out_standing_balance': balance,
                                'state': state,
                            })
                            history_list.append(line)
                        else:
                            state = 'draft'


                if state == 'draft':
                    estimate_order = self.env['estimate.orders'].search(
                        [('c_date', '=', datetime.today().date()), ('partner_id', '=', each.id)])
                    if estimate_order:
                        state = 'visit'
                        for each_order in estimate_order:
                            for l in each_order.order_lines:
                                balance += l.quantity * l.price

                        line = (0, 0, {
                            'executive_area': self.executive_area.id,
                            'partner_id': each.id,
                            'out_standing_balance': balance,
                            'state': state,
                        })
                        history_list.append(line)

                    else:
                        state = 'draft'
                        line = (0, 0, {
                            'executive_area': self.executive_area.id,
                            'partner_id': each.id,
                            'out_standing_balance': balance,
                            'state': state,
                        })
                        history_list.append(line)
                if state == 'drat':
                    if not cash_collection and not check_collection or not self.env['account.move'].search(
                            [('company_id', '=', 1), ('state', '!=', 'paid'), ('partner_id', '=', each.id)]):
                        line = (0, 0, {
                            'executive_area': self.executive_area.id,
                            'partner_id': each.id,
                            'out_standing_balance': balance,
                            'state': 'draft',
                        })
                        history_list.append(line)
            else:
                line = (0, 0, {
                    'executive_area': self.executive_area.id,
                    'partner_id': each.id,
                    'out_standing_balance': 0,
                    'state': 'draft',
                })
                history_list.append(line)

        self.partner_lines = history_list

    def action_submit(self):
        # self.cron_auto_collect_notification()
        for each_line in self.partner_lines:
            if each_line.next_visit_date:
                self.env['areas.customers.remainder'].create({
                    'partner_id': each_line.partner_id.id,
                    'executive_area': each_line.executive_area.id,
                    'out_standing_balance': each_line.out_standing_balance,
                    'collected_amount': each_line.collected_amount,
                    'reason': each_line.reason,
                    'balance': each_line.balance,
                    'next_visit_date': each_line.next_visit_date,
                    'state': each_line.state,
                })

            # each_line.cron_auto_collect_notification()
            if each_line.state == 'draft' and not each_line.reason:
                raise ValidationError(
                    _('Your not allowed to Submit this Record \n Please Collect All Payments related to %s Date') % (
                        self.date))
            else:
                self.write({'state': 'done'})
        #
        # for rec in self:
        #     return rec.sales_person.user_id.notify_danger(message='Mounika Testing')

    @api.onchange('user_id')
    def _onchange_user_id(self):
        # if not self.env['executive.areas.assign'].search([('state', '=', 'draft')]).mapped('sales_person').filtered(
        #         lambda a: a.user_id == self.user_id):
        if self.env['executive.areas.assign'].search([('state', '=', 'draft')]):
            view = self.env.ref('sh_message.sh_message_wizard')
            view_id = view or False
            context = dict(self._context or {})
            context['message'] = "You Have Pending Collection"
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.message.wizard',
                'views': [(view.id, 'form')],
                'view_id': view_id.id,
                'target': 'new',
                'context': context,
            }


class AreaCustomers(models.Model):
    _name = 'areas.customers'

    assign_id = fields.Many2one('executive.areas.assign')
    executive_area = fields.Many2one('executive.area.wise', string='Assign Area')
    partner_area = fields.Many2one('area.wise', string='Customer Area')
    partner_id = fields.Many2one('res.partner', string='Customer', domain=[('estimator', '=', True)])
    out_standing_balance = fields.Float('Outstanding')
    collected_amount = fields.Float('Collected Amount')
    select = fields.Boolean('Select')
    reason = fields.Text('Reason')
    balance = fields.Float('Balance Amount', compute='_compute_balance')
    next_visit_date = fields.Date('Next Visiting Date')
    state = fields.Selection([
        ('draft', 'Not Visited'),
        ('visit', 'visited'),
        ('call', 'Call'),
        ('n_visit', 'Next visit'),
    ], string='Status', copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            if self.env['partner.ledger.customer'].search(
                    [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.company_id.id)]):
                self.out_standing_balance = self.env['partner.ledger.customer'].search(
                    [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.company_id.id)])[-1].balance

    @api.onchange('executive_area')
    def _onchange_executive_area(self):
        if self.executive_area:
            areas = self.env['area.wise'].search([('executive_area', '=', self.executive_area.id)])
            dom = self.env['res.partner'].search([('area', '=', areas.id)])
            if dom:
                return {'domain': {'partner_id': [('id', 'in', dom.ids)]}}

    # @api.multi
    @api.depends('collected_amount')
    def _compute_balance(self):
        for line in self:
            if line.out_standing_balance:
                line.balance = line.out_standing_balance - line.collected_amount
            else:
                line.balance = 0

    @api.model
    def cron_auto_collect_notification(self):
        # if self.env['areas.customers'].search([]):
        from datetime import timedelta, date
        for all_users in self.env['executive.areas.assign'].sudo().search([]).mapped('sales_person').mapped('user_id'):
            act = self.env['collection.reminder.config'].search([('sales_person', '=', all_users.partner_id.id)])
            if act:
                if act.active == True:
                    for each in self.env['executive.areas.assign'].search(
                            [('state', '=', 'draft'),
                             ('sales_person', '=', self.env['res.users'].browse(all_users.id).partner_id.id)]):
                        for rec in self.env['areas.customers'].search(
                                [('next_visit_date', '=', datetime.today().date() + timedelta(days=2))]):
                            # self.env['res.users'].browse(all_users.id).notify_info(
                            #     message='You need to meet some customers After 2days')
                            test_msg = {"message": "You need to meet some customers After 2days",
                                        "title": "Collections",
                                        "sticky": True}
                            return self.env['res.users'].browse(all_users.id).notify_info(**test_msg)


class AreaCustomersOther(models.Model):
    _name = 'areas.customers.other'

    assign_other_id = fields.Many2one('executive.areas.assign')
    executive_area = fields.Many2one('executive.area.wise', string='Assign Area')
    partner_area = fields.Many2one('area.wise', string='Customer Area')
    partner_id = fields.Many2one('res.partner', string='Customer', domain=[('estimator', '=', True)])
    out_standing_balance = fields.Float('Outstanding')
    collected_amount = fields.Float('Collected Amount')
    reason = fields.Text('Reason')
    balance = fields.Float('Balance Amount', compute='_compute_balance')
    next_visit_date = fields.Date('Next Visiting Date')
    state = fields.Selection([
        ('draft', 'Not Visited'),
        ('visit', 'visited'),
        ('call', 'Call'),
        ('n_visit', 'Next visit'),
    ], string='Status', copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    reason = fields.Text('Reason')
    next_visit_date = fields.Date('Next Visiting Date')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_area = self.partner_id.area
            if self.env['partner.ledger.customer'].search(
                    [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.company_id.id)]):
                self.out_standing_balance = self.env['partner.ledger.customer'].search(
                    [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.company_id.id)])[-1].balance

    @api.onchange('executive_area')
    def _onchange_executive_area(self):
        if self.executive_area:
            areas = self.env['area.wise'].search([('executive_area', '=', self.executive_area.id)])
            dom = self.env['res.partner'].search([('area', '=', areas.id)])
            if dom:
                return {'domain': {'partner_id': [('id', 'in', dom.ids)]}}

    # @api.multi
    @api.depends('collected_amount')
    def _compute_balance(self):
        for line in self:
            if line.out_standing_balance:
                line.balance = line.out_standing_balance - line.collected_amount

    @api.model
    def cron_auto_collect_notification(self):
        # if self.env['areas.customers'].search([]):
        from datetime import timedelta, date
        for all_users in self.env['executive.areas.assign'].sudo().search([]).mapped('sales_person').mapped('user_id'):
            act = self.env['collection.reminder.config'].search([('sales_person', '=', all_users.partner_id.id)])
            if act:
                if act.active == True:
                    for each in self.env['executive.areas.assign'].search(
                            [('state', '=', 'draft'),
                             ('sales_person', '=', self.env['res.users'].browse(all_users.id).partner_id.id)]):
                        for rec in self.env['areas.customers'].search(
                                [('next_visit_date', '=', datetime.today().date() + timedelta(days=2))]):
                            # self.env['res.users'].browse(all_users.id).notify_info(
                            #     message='You need to meet some customers After 2days')
                            test_msg = {"message": "You need to meet some customers After 2days",
                                        "title": "Collections",
                                        "sticky": True}
                            return self.env['res.users'].browse(all_users.id).notify_info(**test_msg)


class AreaCustomersFilter(models.Model):
    _name = 'areas.filter.lines'

    assign_filter_id = fields.Many2one('executive.areas.assign')
    executive_area = fields.Many2one('executive.area.wise', string='Assign Area')
    partner_area = fields.Many2one('area.wise', string='Customer Area')
    partner_id = fields.Many2one('res.partner', string='Customer', domain=[('estimator', '=', True)])
    out_standing_balance = fields.Float('Outstanding')
    collected_amount = fields.Float('Collected Amount')
    reason = fields.Text('Reason')
    balance = fields.Float('Balance Amount', compute='_compute_balance')
    next_visit_date = fields.Date('Next Visiting Date')
    state = fields.Selection([
        ('draft', 'Not Visited'),
        ('visit', 'visited'),
        ('call', 'Call'),
        ('n_visit', 'Next visit'),
    ], string='Status', copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    reason = fields.Text('Reason')
    next_visit_date = fields.Date('Next Visiting Date')

    # @api.multi
    @api.depends('collected_amount')
    def _compute_balance(self):
        for line in self:
            if line.out_standing_balance:
                line.balance = line.out_standing_balance - line.collected_amount


class AreaExecutiveConfig(models.Model):
    _name = 'areas.executive.config'

    create_date = fields.Date(string='Create Date', default=fields.Date.context_today, required=True)
    sales_person = fields.Many2one('res.partner', string='Sales Person', domain=[('user_id', '!=', False)])
    days_line = fields.One2many('executive.days.lines', 'day_executive')


class AreaExecutiveLineConfig(models.Model):
    _name = 'executive.days.lines'

    day_executive = fields.Many2one('areas.executive.config')
    week_list = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], string='Weekday')
    executive_area = fields.Many2one('executive.area.wise', string='Assign Area')


class AreaCustomersRemainder(models.Model):
    _name = 'areas.customers.remainder'

    assign_id = fields.Many2one('executive.areas.assign')
    executive_area = fields.Many2one('executive.area.wise', string='Assign Area')
    partner_area = fields.Many2one('area.wise', string='Customer Area')
    partner_id = fields.Many2one('res.partner', string='Customer')
    out_standing_balance = fields.Float('Outstanding')
    collected_amount = fields.Float('Collected Amount')
    reason = fields.Text('Reason')
    balance = fields.Float('Balance Amount', )
    next_visit_date = fields.Date('Next Visiting Date')
    state = fields.Selection([
        ('draft', 'Not Visited'),
        ('visit', 'visited'),
        ('n_visit', 'Next visit'),
    ], string='Status', copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)


class NextDayRemainder(models.Model):
    _name = 'areas.customers.next'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    create_date = fields.Date(string='Create Date', default=fields.Date.context_today, required=True)
    sales_person = fields.Many2one('res.partner', string='Sales Person')
    next_v_lines = fields.Many2one('areas.customers.remainder.next', 'assign_id')
    next_lines = fields.Many2one('areas.customers.remainder.next', 'assign_id')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'areas.customers.next') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('areas.customers.next') or _('New')
        return super(NextDayRemainder, self).create(vals)


class AreaCustomersRemainderNext(models.Model):
    _name = 'areas.customers.remainder.next'

    assign_id = fields.Many2one('areas.customers.next')
    executive_area = fields.Many2one('executive.area.wise', string='Assign Area')
    partner_area = fields.Many2one('area.wise', string='Customer Area')
    partner_id = fields.Many2one('res.partner', string='Customer')
    out_standing_balance = fields.Float('Outstanding')
    collected_amount = fields.Float('Collected Amount')
    reason = fields.Text('Reason')
    balance = fields.Float('Balance Amount', )
    next_visit_date = fields.Date('Next Visiting Date')
    state = fields.Selection([
        ('draft', 'Not Visited'),
        ('visit', 'visited'),
        ('n_visit', 'Next visit'),
    ], string='Status', copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)


class TargetAchievementReport(models.Model):
    _inherit = "target.achievement.report"

    executive = fields.Boolean(default=False)

    @api.onchange('sales_person', 'from_date', 'to_date', 'type')
    def onchange_from_date(self):
        if self.type == 'draft':
            self.target_lines = False
            today_total_cheques = []
            if self.executive == False:
                for each_cheque in self.env['sales.person.target'].search(
                        [('company_id', '=', self.company_id.id), ('start_date', '>=', self.from_date),
                         ('start_date', '<=', self.to_date)]):
                    for each_target in each_cheque.target_lines:
                        product_line = (0, 0, {
                            'sales_person': each_target.sales_person.id,
                            'target_qty': each_target.target_qty,
                            'target_amount': each_target.target_amount,
                            'achievement_qty': each_target.achievement_qty,
                            'achievement_amount': each_target.achievement_amount,
                            'pending_qty': each_target.pending_qty,
                            'pending_amount': each_target.pending_amount,
                        })
                        today_total_cheques.append(product_line)
            else:
                for each_cheque in self.env['sales.person.target'].search(
                        [('company_id', '=', self.company_id.id), ('start_date', '>=', self.from_date),
                         ('start_date', '<=', self.to_date)]):
                    for each_target in each_cheque.target_lines.filtered(
                            lambda a: a.sales_person == self.env.user.partner_id):
                        product_line = (0, 0, {
                            'sales_person': each_target.sales_person.id,
                            'target_qty': each_target.target_qty,
                            'target_amount': each_target.target_amount,
                            'achievement_qty': each_target.achievement_qty,
                            'achievement_amount': each_target.achievement_amount,
                            'pending_qty': each_target.pending_qty,
                            'pending_amount': each_target.pending_amount,
                        })
                        today_total_cheques.append(product_line)
            self.target_lines = today_total_cheques


class TodayVisitingRemainder(models.Model):
    _name = 'today.visiting.remainder'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
    ], string='Status', copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    create_date = fields.Date(string='Create Date', default=fields.Date.context_today, required=True)
    sales_person = fields.Many2one('res.partner', string='Sales Person')
    next_v_lines = fields.One2many('today.visiting.remainder.line', 'today_id')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'today.visiting.remainder') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('today.visiting.remainder') or _('New')
        return super(TodayVisitingRemainder, self).create(vals)

    def action_submit(self):
        list = []
        already = self.env['executive.areas.assign'].search(
            [('date', '=', self.create_date), ('sales_person', '=', self.sales_person.id)])

        if not already:
            for line in self.next_v_lines:
                call_list = (0, 0, {'partner_id': line.partner_id.id,
                                    'partner_area': line.partner_id.area.id,
                                    'out_standing_balance': line.out_standing_balance,
                                    'state': line.state,
                                    'reason': line.reason,
                                    'next_visit_date': line.next_visit_date,
                                    })
                list.append(call_list)

            self.env['executive.areas.assign'].sudo().create({
                'sales_person': self.sales_person.id,
                'executive_area': self.sales_person.executive_area[0].id,
                'partner_other_lines': list

            })
        else:
            for line in self.next_v_lines:
                rec = already.partner_other_lines.search([('partner_id', '=', line.partner_id.id)])
                if rec:
                    line.state = line.state
                    line.reason = line.reason
                    line.next_visit_date = line.next_visit_date
                else:
                    call_list = (0, 0, {'partner_id': line.partner_id.id,
                                        'partner_area': line.partner_id.area.id,
                                        'out_standing_balance': line.out_standing_balance,
                                        'state': line.state,
                                        'reason': line.reason,
                                        'next_visit_date': line.next_visit_date,
                                        })
                    list.append(call_list)
                    already.partner_other_lines = list
            self.write({'state': 'confirm'})


class TodayVisitingRemainderline(models.Model):
    _name = 'today.visiting.remainder.line'

    today_id = fields.Many2one('today.visiting.remainder')
    executive_area = fields.Many2one('executive.area.wise', string='Assign Area')
    partner_area = fields.Many2one('area.wise', string='Customer Area')
    partner_id = fields.Many2one('res.partner', string='Customer')
    out_standing_balance = fields.Float('Outstanding')
    collected_amount = fields.Float('Collected Amount')
    reason = fields.Text('Reason')
    balance = fields.Float('Balance Amount', )
    next_visit_date = fields.Date('Next Visiting Date')
    state = fields.Selection([
        ('draft', 'Not Visited'),
        ('visit', 'visited'),
        ('call', 'Call'),
        ('n_visit', 'Next visit'),
    ], string='Status', copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_area = self.partner_id.area
            if self.env['partner.ledger.customer'].search(
                    [('partner_id', '=', self.partner_id.id), ('company_id', '=', 1)]):
                self.out_standing_balance = self.env['partner.ledger.customer'].search(
                    [('partner_id', '=', self.partner_id.id), ('company_id', '=', 1)])[-1].balance


class SaleTargetLines(models.Model):
    _name = "sale.target.lines"

    product_id = fields.Many2one('product.product', string="Product")
    date = fields.Date(string='Date')
    target_qty = fields.Integer(string="Target Qty")
    target_amount = fields.Integer(string="Target Amount")
    achievement_qty = fields.Integer(string="Achievement Qty")
    achievement_amount = fields.Integer(string="Achievement Amount")
    achievement_percentage = fields.Integer(string='Achievement Percentage(%)')
    pending_amount = fields.Integer(string='Pending Amount', compute='_compute_all_targets')
    pending_qty = fields.Integer(string='Pending Qty', compute='_compute_all_targets')
    achievement_amount_percentage = fields.Integer(string='Amount(%)', compute='_compute_all_targets')
    achievement_percentage = fields.Integer(string='Achievement(%)', compute='_compute_all_targets')
    sales_person = fields.Many2one('res.partner', string="Sales Person", domain=[('user_id', '!=', False)])

    @api.depends('achievement_amount', 'achievement_qty')
    def _compute_all_targets(self):
        for each_month in self:
            each_month.achievement_amount_percentage = 0
            each_month.pending_qty = 0
            each_month.pending_amount = 0
            each_month.achievement_percentage = 0
            each_month.target_amount = 0
            if each_month.achievement_qty:
                each_month.pending_qty = each_month.target_qty - each_month.achievement_qty
                if each_month.target_qty:
                    each_month.achievement_percentage = (each_month.achievement_qty / each_month.target_qty) * 100
            if each_month.achievement_amount:
                each_month.pending_amount = each_month.target_amount - each_month.achievement_amount
                if each_month.target_amount:
                    each_month.achievement_amount_percentage = (
                                                                       each_month.achievement_amount / each_month.target_amount) * 100


class SalesPersonTarget(models.Model):
    _inherit = "sales.person.target"
    _order = "id desc, name desc"

    def action_confirm(self):
        for line in self.target_lines:
            self.env['sale.target.lines'].sudo().create({
                'sales_person': line.sales_person.id,
                'target_qty': line.target_qty,
                'target_amount': line.target_amount,
                'achievement_qty': line.achievement_qty,
                'achievement_percentage': line.achievement_percentage,
                'date': self.start_date
            })
        self.write({'state': 'done'})
