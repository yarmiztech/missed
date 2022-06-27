# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import date
from datetime import datetime
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import calendar
from dateutil.relativedelta import relativedelta


class CreditLimitRecord(models.Model):
    _name = "credit.limit.record"
    _order = "id desc"

    credit_limit_lines = fields.One2many('credit.limit.lines', 'credit_limit_id')

    date = fields.Date(string='Create Date', default=fields.Date.context_today)



    @api.onchange('date')
    def onchange_date(self):
        months = self.env['credit.limit.configuration'].search([('active', '=', True)]).months
        percentage = self.env['credit.limit.configuration'].search([('active', '=', True)]).percentage
        min_credit_amt = self.env['credit.limit.configuration'].search([('active', '=', True)]).min_credit_amount
        from_month = datetime.today().date() - relativedelta(months=months)
        to_month = datetime.today().date()
        list = []

        for partner_wise in self.env['partner.ledger.customer'].search(
                [('company_id', '=', 1), ('date', '>=', from_month), ('date', '<=', to_month),
                 ('debit', '!=', 0)]).filtered(lambda a: a.debit >= 1).mapped('partner_id'):
            avg_amt = 0
            for each in sorted(self.env['partner.ledger.customer'].search(
                    [('company_id', '=', 1), ('date', '>=', from_month), ('date', '<=', to_month),
                     ('partner_id', '=', partner_wise.id)])):
                avg_amt += each.debit
                balance = each.balance
            value = percentage / 100
            aveg_amount = avg_amt / months
            basic_value = aveg_amount * value
            print(partner_wise, 'partner_wise')
            credit_amount = 0
            if min_credit_amt > basic_value:
                credit_amount = min_credit_amt
            else:
                credit_amount = basic_value

            line = (0, 0, {
                'partner_id': each.partner_id.id,
                'balance': balance,
                'average_amount': aveg_amount,
                'credit_limit_amount': basic_value,
                'min_credit_amount': credit_amount
            })
            list.append(line)
        self.credit_limit_lines = list


class CreditLimitLines(models.Model):
    _name = "credit.limit.lines"
    _order = "id desc"

    credit_limit_id = fields.Many2one('credit.limit.record')
    partner_id = fields.Many2one('res.partner', string='Partner')
    balance = fields.Float('Balance')
    credit_limit_amount = fields.Float('Credit Limit Amount')
    average_amount = fields.Float('Average Amount')
    min_credit_amount = fields.Float(string="Approved Credit")


class CreditLimitOwner(models.Model):
    _name = "credit.limit.owner"
    _order = "id desc"

    ref_id = fields.Many2one('estimate.orders')
    partner_id = fields.Many2one('res.partner')
    credit_status = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting for Approval'),
        ('confirmed', 'Confirmed'),
    ], default='draft')
    total_amount = fields.Float(string='Total Amount')
    credit_limit_amount = fields.Float(string='Credit Limit Amount')
    min_credit_amount = fields.Float(string="Approved Credit")

    def action_send_to_owner(self):
        print('dfgfdg')

    @api.onchange('credit_status')
    def onchange_credit_status(self):
        self.ref_id.sudo().write({'credit_status': self.credit_status})


class EstimateOrders(models.Model):
    _inherit = 'estimate.orders'
    _order = 'id desc'

    def action_oder_confirm(self):
        if self.another_area == True:
            old = self.env['executive.areas.assign'].search(
                [('date', '=', self.c_date), ('sales_person', '=', self.user_id.partner_id.id)])
            if old:
                balance = 0
                if self.env['partner.ledger.customer'].search(
                        [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.company_id.id)]):
                    outstand = self.env['partner.ledger.customer'].search(
                        [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.company_id.id)])[-1].balance
                    balance = outstand
                line_id = self.env['areas.customers.other'].sudo().create({
                    'assign_other_id': old.id,
                    'partner_id': self.partner_id.id,
                    'partner_area': self.partner_id.area.id,
                    'out_standing_balance': balance,
                    'state': 'visit',
                    'collected_amount': self.total_amount
                })
                old.partner_other_lines += line_id
            else:
                balance = 0
                list = []
                if self.env['partner.ledger.customer'].search(
                        [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.company_id.id)]):
                    outstand = self.env['partner.ledger.customer'].search(
                        [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.company_id.id)])[-1].balance
                    balance = outstand
                call_list = (0, 0, {'partner_id': self.partner_id.id,
                                    'partner_area': self.partner_id.area.id,
                                    'out_standing_balance': balance,
                                    'state': 'visit',
                                    # 'collected_amount': line.amount_total
                                    # 'reason': line.reason,
                                    # 'next_visit_date': line.next_visit_date,
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
        if self.env['credit.limit.configuration'].search([('active','=',True)]):
            credit_limit = self.env['credit.limit.lines'].search([('partner_id', '=', self.partner_id.id)])
            if self.credit_status == 'draft':
                if credit_limit:
                # if self.total_amount > credit_limit.credit_limit_amount:
                    if self.total_amount > credit_limit.min_credit_amount:
                        view_id = self.env.ref('ezp_cash_collection.credit_limit_pop_forms')
                        return {
                            'name': _('Warning'),
                            'type': 'ir.actions.act_window',
                            'res_model': 'credit.limit.pop',
                            'view_type': 'form',
                            'view_mode': 'form',
                            'target': 'new',
                            'view_id': view_id.id,
                            'views': [(view_id.id, 'form')],
                            'context': {
                                'default_ref_id': self.id,
                                'default_partner_id': self.partner_id.id,
                                'default_total_amount': self.total_amount,
                                'default_credit_status': self.credit_status,
                                'default_credit_limit_amount': credit_limit.credit_limit_amount,
                                'default_min_credit_amount': credit_limit.min_credit_amount,
                                'default_message': "This Partner Having" + '  ' + str(
                                    credit_limit.min_credit_amount) + ' ' + "But Now Order Amount is" + ' ' + str(
                                    self.total_amount)

                            }
                        }

        return super(EstimateOrders, self).action_oder_confirm()


class CreditLimitPop(models.TransientModel):
    _name = "credit.limit.pop"
    _order = "id desc"

    ref_id = fields.Many2one('estimate.orders')
    partner_id = fields.Many2one('res.partner')
    credit_status = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting for Approval'),
        ('confirmed', 'Confirmed'),
    ], default='draft')
    total_amount = fields.Float(string='Total Amount')
    credit_limit_amount = fields.Float(string='Credit Limit Amount')
    min_credit_amount = fields.Float(string='Min Credit Amount')
    message = fields.Text()

    def action_send_to_owner(self):
        self.ref_id.write({'credit_status': 'waiting'})
        self.write({'credit_status': 'waiting'})
        self.env['credit.limit.owner'].sudo().create({'ref_id': self.ref_id.id,
                                                      'partner_id': self.partner_id.id,
                                                      'credit_status': self.credit_status,
                                                      'total_amount': self.total_amount,
                                                      'credit_limit_amount': self.credit_limit_amount,
                                                      'min_credit_amount': self.min_credit_amount,
                                                      })


class OwnerAreawiseDiscounts(models.Model):
    _name = "area.wise.discounts"
    _order = "id desc"

    name = fields.Char("Name", index=True, default=lambda self: _('New'))
    from_date = fields.Date('From Date', default=fields.Date.context_today, )
    to_date = fields.Date('To Date', default=fields.Date.context_today, )
    area_wise_lines = fields.One2many('area.discount.lines', 'area_wise_id')
    confirmed = fields.Boolean(default=False,string='Confirmed')



    def action_create_offers(self):
        for line in self.area_wise_lines:
            self.env['area.offers'].sudo().create({
                'from_date':self.from_date,
                'to_date':self.to_date,
                'area':line.area.id,
                'sales_person':line.sales_person.id,
                'product_id':line.product_id.id,
                'discount':line.discount,
                'selling_price':line.selling_price
            })
        self.confirmed =True


class OwnerDiscountsLines(models.Model):
    _name = "area.discount.lines"
    _order = "id desc"

    area_wise_id = fields.Many2one('area.wise.discounts')
    area = fields.Many2one('executive.area.wise')
    sales_person = fields.Many2one('res.partner', string='Sales Person',domain=[('user_id','!=',False)])
    product_id = fields.Many2one('product.product', string='Product')
    discount = fields.Float(string='Discount')
    selling_price = fields.Float(string='Selling Price')


class AreaOffers(models.Model):
    _name = "area.offers"
    _order = "id desc"

    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    area = fields.Many2one('executive.area.wise')
    sales_person = fields.Many2one('res.partner', string='Sales Person')
    product_id = fields.Many2one('product.product', string='Product')
    discount = fields.Float(string='Discount')
    selling_price = fields.Float(string='Selling Price')
