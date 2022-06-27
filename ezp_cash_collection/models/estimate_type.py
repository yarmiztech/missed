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


class EstimateTypeReport(models.Model):
    _name = "estimate.type.report"
    _description = "Estimate Type Report"
    _order = "id desc"

    name = fields.Char("Name", index=True, default=lambda self: _('New'))
    from_date = fields.Date('From Date', default=fields.Date.context_today, )
    to_date = fields.Date('To Date', default=fields.Date.context_today, )
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    sequence = fields.Integer(index=True)
    type = fields.Selection([
        ('data', 'Data Entry'),
        ('executive', 'Sales Executive'),
        ('direct', 'Direct'),
        ('owner', 'Owner'),
    ], string='Type Of Order', copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='data')
    # sales_person = fields.Many2one('res.partner', string="Sales Person", domain=[('user_id', '!=', False)])
    est_lines = fields.One2many('estimate.type.line', 'exe_report')

    @api.onchange('from_date', 'to_date','type')
    def onchange_from_date(self):
        self.est_lines = False
        today_total_cheques = []
        for each_cheque in self.env['owner.application'].search(
                    [('company_id', '=', self.company_id.id),('type','=',self.type),('create_date', '>=', self.from_date),
                     ('create_date', '<=', self.to_date)]):
                # for each_target in each_cheque.target_lines:
                    product_line = (0, 0, {
                        'create_date': each_cheque.create_date,
                        'partner_id': each_cheque.partner_id.id,
                        'product_id': each_cheque.product_id.id,
                        'product_uom_qty': each_cheque.quantity,
                        'outstanding': each_cheque.outstanding_amount,
                        # 'subtotal': each_cheque.subtotal,
                    })
                    today_total_cheques.append(product_line)
        # if self.type == 'collection':
        self.est_lines = today_total_cheques

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'estimate.type.report') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('estimate.type.report') or _('New')
        return super(EstimateTypeReport, self).create(vals)


class EstimateTypeLineReport(models.Model):
    _name = 'estimate.type.line'

    exe_report = fields.Many2one('estimate.type.report', string='Target')
    create_date = fields.Date(string='Date')
    company_id = fields.Many2one('res.company', string='Company')
    partner_id = fields.Many2one('res.partner', string='Partner')
    sales_person = fields.Many2one('res.partner', string='Sales Person')
    product_id = fields.Many2one('product.product', string='Product')
    product_uom_qty = fields.Float('qty')
    price = fields.Float('Rate')
    subtotal = fields.Float('Total')
    outstanding = fields.Float('Outstanding Amount')
