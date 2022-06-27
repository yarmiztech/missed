# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ChequeRepo(models.Model):
    _name = "check.repo"
    _order = "id desc"

    date = fields.Date(string='Cheque Date')
    partner_id = fields.Many2one('res.partner', 'Estimator')
    amount_total = fields.Float(string='Check Amount', )
    check_no = fields.Char(string='Cheque No')
    bank_name = fields.Char('Back Name')
    holder_name = fields.Many2one('res.partner', string='Holder Name')
    debited_account = fields.Many2one('account.journal', string='Debit A/C')
    line_id = fields.Many2one('executive.cheque.collection.line',string='line Ref')


class PartnerLedgerReport(models.Model):
    _name = "partner.ledger.report"

    name = fields.Char("Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    payment_date = fields.Date(string='Create Date', default=fields.Date.context_today, required=True, copy=False)
    from_date = fields.Date(string='From Date', copy=False, default=fields.Date.context_today, )
    to_date = fields.Date(string='To Date', copy=False, default=fields.Date.context_today, )
    report_lines = fields.One2many('sale.report.custom.line', 'report_line')
    partner_id = fields.Many2one('res.partner', string='Party Wise',domain=[('estimator','=',True)])
    company_id = fields.Many2one('res.company', string='Company',  index=True, default=lambda self: self.env.user.company_id)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'partner.ledger.report') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('partner.ledger.report') or _('New')
        return super(PartnerLedgerReport, self).create(vals)

    def print_report(self):
        if self.company_id:
            total_ledgers = self.env['partner.ledger.customer'].search(
                [('company_id', '=', self.company_id.id), ('date', '>=', self.from_date), ('date', '<=', self.to_date),
                 ('partner_id', '=', self.partner_id.id)])
        else:
            total_ledgers = self.env['partner.ledger.customer'].search(
                [('date', '>=', self.from_date), ('date', '<=', self.to_date), ('partner_id', '=', self.partner_id.id)])
        action_vals = {
            'name': _(self.partner_id.name + '  ' + 'Ledger Report'),
            'domain': [('id', 'in', total_ledgers.ids)],
            'view_type': 'form',
            'res_model': 'partner.ledger.customer',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        if len(total_ledgers) == 1:
            action_vals.update({'res_id': total_ledgers[0].id, 'view_mode': 'form'})
        else:
            action_vals['view_mode'] = 'tree,form'
        return action_vals

    # @api.multi
    def print_reports(self):
        return self.env.ref('ezp_cash_collection.partner_ledger_customerss').report_action(self)

    def print_all(self):
        if self.company_id:
            total_ledgers = self.env['partner.ledger.customer'].search(
                [('company_id', '=', self.company_id.id), ('date', '>=', self.from_date), ('date', '<=', self.to_date),
                 ('partner_id', '=', self.partner_id.id)])
            return total_ledgers
        else:
            total_ledgers = self.env['partner.ledger.customer'].search(
                [('date', '>=', self.from_date), ('date', '<=', self.to_date), ('partner_id', '=', self.partner_id.id)])

            return total_ledgers
