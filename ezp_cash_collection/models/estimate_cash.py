# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime
from datetime import date
import time
import fcntl
import socket
import struct
import macpath
from uuid import getnode as get_mac
from odoo.exceptions import UserError, ValidationError


class SaleEstimate(models.Model):
    _inherit = 'sale.estimate'

    type = fields.Selection([
        ('data', 'Data Entry'),
        ('executive', 'Sales Executive'),
        ('direct', 'Direct'),
        ('owner', 'Owner'),
    ], string='Type Of Order', copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='data')
    def create_main_partner(self,inv):
        for line in inv.invoice_line_ids:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', inv.partner_id.id), ('company_id', '=', inv.company_id.id),
                 ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                balance_amount = sum(invoices.mapped('amount_total'))
            balance_amount += self.env['partner.ledger.customer'].search(
                [('partner_id', '=', inv.partner_id.id), ('description', '=', 'Opening Balance')]).balance
            Previous_led = self.env['partner.ledger.customer'].search(
                [('company_id', '=', inv.company_id.id), ('partner_id', '=', inv.partner_id.id)])
            if Previous_led:
                balance_amount = Previous_led[-1].balance+ line.price_subtotal

            else:
                balance_amount = balance_amount + line.price_subtotal - inv.amount_total

            # bal = sum(
            #     self.env['account.move.line'].search([('journal_id', '=', self.account_journal.id)]).mapped('debit'))

            self.env['partner.ledger.customer'].sudo().create({
                'date': self.c_date,
                'invoice_id': inv.id,
                'description': line.product_id.name,
                'partner_id': inv.partner_id.id,
                'product_id': line.product_id.id,
                'company_id': inv.company_id.id,
                # 'price_units': inv.inv_mc_qty,
                'price_units': line.quantity,
                'uom': line.uom_id.id,
                'rate': line.price_unit,
                'estimate_id': self.id,
                'account_journal': inv.journal_id.id,
                'account_move': inv.move_id.id,
                # 'credit': inv.amount_total_signed,
                'debit': line.price_subtotal,
                # 'balance': 0,
                'executive_area': self.executive_areas.id or False,
                'area': self.area.id or False,
                'vehicle_id': self.estimate_ids[0].vahicle.id,
                'balance': balance_amount,
            })
            self.env['owner.application'].create({
                'create_date': self.c_date,
                'partner_id': inv.partner_id.id,
                'product_id': line.product_id.id,
                'quantity': inv.inv_mc_qty,
                'company_id': inv.company_id.id,
                'type': self.type,
                'area': self.area.id or False,
                'outstanding_amount': balance_amount,
                'sales_executive': self.user_id.partner_id.id
            })

    def action_partner_ledger(self):
        for inv in self.invoice_ids:
            if inv.company_id.id == 1:
                self.create_main_partner(inv)
            else:

                balance_amount = 0
                for line in inv.invoice_line_ids:
                    invoices = self.env['account.move'].search(
                        [('partner_id', '=', inv.partner_id.id), ('company_id', '=', inv.company_id.id),
                         ('state', '!=', 'paid')])
                    if invoices.mapped('amount_residual'):
                        balance_amount = sum(invoices.mapped('amount_residual'))
                    else:
                        balance_amount = sum(invoices.mapped('amount_total'))
                    balance_amount += self.env['partner.ledger.customer'].search(
                        [('partner_id', '=', inv.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                    Previous_led = self.env['partner.ledger.customer'].search(
                        [('company_id', '=', inv.company_id.id), ('partner_id', '=', inv.partner_id.id)])
                    if Previous_led:
                        # balance_amount = Previous_led[-1].balance + line.price_subtotal_signed + inv.amount_tax
                        balance_amount = Previous_led[-1].balance + line.price_subtotal + inv.amount_tax

                    # bal = sum(
                    #     self.env['account.move.line'].search([('journal_id', '=', self.account_journal.id)]).mapped('debit'))

                    self.env['partner.ledger.customer'].sudo().create({
                        'date': self.c_date,
                        'invoice_id': inv.id,
                        'description': line.product_id.name,
                        'partner_id': inv.partner_id.id,
                        'product_id': line.product_id.id,
                        'company_id': inv.company_id.id,
                        'price_units': inv.inv_mc_qty,
                        'uom': line.uom_id.id,
                        'rate': line.price_unit,
                        'estimate_id': self.id,
                        'account_journal': inv.journal_id.id,
                        'account_move': inv.move_id.id,
                        # 'credit': inv.amount_total_signed,
                        # 'debit': line.price_subtotal_signed + inv.amount_tax,
                        'debit': line.price_subtotal + inv.amount_tax,
                        # 'balance': 0,
                        'executive_area': self.executive_areas.id or False,
                        'area': self.area.id or False,
                        'vehicle_id': self.estimate_ids[0].vahicle.id,
                        'balance': balance_amount,
                    })
                    self.env['owner.application'].create({
                        'create_date': self.c_date,
                        'partner_id': inv.partner_id.id,
                        'product_id': line.product_id.id,
                        'quantity': inv.inv_mc_qty,
                        'company_id': inv.company_id.id,
                        'type': self.type,
                        'area': self.area.id or False,
                        'outstanding_amount': balance_amount,
                        'sales_executive': self.user_id.partner_id.id
                    })

    # @api.onchange('area')
    # def onchange_areas(self):
    #     if self.area:
    #         self.user_id = self.area.sales_person
    def main_cmp_partner(self,inv):
        for l in inv.invoice_line_ids:
            balance_amount = 0
            invoices = self.env['account.move'].search(
                [('partner_id', '=', inv.partner_id.id), ('company_id', '=', inv.company_id.id),
                 ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                balance_amount = sum(invoices.mapped('amount_total'))
            Previous_led = self.env['partner.ledger.customer'].search(
                [('company_id', '=', inv.company_id.id), ('partner_id', '=', inv.partner_id.id)])
            if Previous_led:
                balance_amount = Previous_led[-1].balance + inv.amount_total+l.price_subtotal
            else:
                balance_amount = balance_amount + l.price_subtotal - inv.amount_total

            complete_address = ''
            if l.partner_id.street2:
                complete_address += l.partner_id.street2 + ','
            if l.partner_id.street:
                complete_address += l.partner_id.street + ','
            if l.partner_id.city:
                complete_address += l.partner_id.city + ','
            if l.partner_id.state_id:
                complete_address += l.partner_id.state_id.name + ','
            if l.partner_id.country_id:
                complete_address += l.partner_id.country_id.name + ','
            if l.partner_id.mobile:
                complete_address += l.partner_id.mobile

            self.env['partner.ledgers.customer'].create({
                'date': self.c_date,
                'invoice_id': inv.id,
                'description': l.partner_id.name,
                'partner_id': inv.partner_id.id,
                'product_id': l.product_id.id,
                'company_id': inv.company_id.id,
                'price_units': l.quantity,
                'address': complete_address,
                'uom': l.product_id.uom_id.id,
                'rate': l.price_unit,
                'balance': balance_amount,
                'month': str(self.c_date.month),
                'credit': l.price_subtotal,
                'executive_area': self.executive_areas.id or False,
                'area': self.area.id or False,
                'vehicle_id': self.estimate_ids[0].vahicle.id,
            })

    def action_partner_ledgers(self):
        for inv in self.invoice_ids:
            if inv.company_id.id == 1:
                self.main_cmp_partner(inv)

            else:
                for l in inv.invoice_line_ids:
                    balance_amount = 0
                    invoices = self.env['account.move'].search(
                        [('partner_id', '=', inv.partner_id.id), ('company_id', '=', inv.company_id.id),
                         ('state', '!=', 'paid')])
                    if invoices.mapped('amount_residual'):
                        balance_amount = sum(invoices.mapped('amount_residual'))
                    else:
                        balance_amount = sum(invoices.mapped('amount_total'))
                    Previous_led = self.env['partner.ledger.customer'].search(
                        [('company_id', '=', inv.company_id.id), ('partner_id', '=', inv.partner_id.id)])
                    if Previous_led:
                        balance_amount = Previous_led[-1].balance + l.price_subtotal + inv.amount_tax

                    complete_address = ''
                    if l.partner_id.street2:
                        complete_address += l.partner_id.street2 + ','
                    if l.partner_id.street:
                        complete_address += l.partner_id.street + ','
                    if l.partner_id.city:
                        complete_address += l.partner_id.city + ','
                    if l.partner_id.state_id:
                        complete_address += l.partner_id.state_id.name + ','
                    if l.partner_id.country_id:
                        complete_address += l.partner_id.country_id.name + ','
                    if l.partner_id.mobile:
                        complete_address += l.partner_id.mobile

                    self.env['partner.ledgers.customer'].create({
                        'date': self.c_date,
                        'invoice_id': inv.id,
                        'description': l.partner_id.name,
                        'partner_id': inv.partner_id.id,
                        'product_id': l.product_id.id,
                        'company_id': inv.company_id.id,
                        'price_units': l.quantity,
                        'address': complete_address,
                        'uom': l.product_id.uom_id.id,
                        'rate': l.price_unit,
                        'balance': balance_amount,
                        'month': str(self.c_date.month),
                        'credit': l.price_subtotal,
                        'executive_area': self.executive_areas.id or False,
                        'area': self.area.id or False,
                        'vehicle_id': self.estimate_ids[0].vahicle.id,
                    })

    # def action_product_profit(self):
    #     for inv in self.invoice_ids.filtered(lambda a:a.company_id.id ==1):
    #         for line in inv.invoice_line_ids:
    #              profit_rec = self.env['purchase.profit.repo'].search([('product_id','=',line.product_id.id)])
    #              if profit_rec:
    #                  if profit_rec[0].price >= line.price_unit:
    #                      profit_rec.profit = profit_rec[0].price-line.price_unit
    #                  else:
    #                      profit_rec.profit = -(profit_rec[0].price-line.price_unit)
    #
    #                  profit_rec.sale_price = line.price_unit

    def action_approve(self):
        rec = super(SaleEstimate, self).action_approve()
        self.action_partner_ledger()
        self.action_partner_ledgers()
        # self.action_product_profit()

        rent_lines_list = []

        j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
        if self.direct_sale == True:
            entry = self.env['data.entry'].create(
                {'user_id': self.user_id.id, 'partner_id': self.partner_id.id, 'payment_method_id': j.id})
            for exp in self.estimate_ids:
                journal = self.env['account.journal'].search(
                    [('name', '=', 'Cash'), ('company_id', '=', self.company_id.id)])

                line = (0, 0, {
                    'partner_id': self.partner_id.id,
                    'date': self.c_date,
                    'journal_id': journal.id,
                    'invoice_id': self.total_invoice.id,
                    'estimate_id': self.id,
                    'vehicle_id': exp.vahicle.id,
                    'balance_amount': sum(self.mapped('estimate_ids').mapped('price_total')),
                })
                rent_lines_list.append(line)
            entry.partner_invoices = rent_lines_list
        self.create_purchase_remainder()
        return rec

    def create_purchase_remainder(self):
        prev = self.env['purchase.remainder']
        available = 0
        quantity = 0
        reserved = 0
        for line in self.estimate_ids:
            if line.product_id:
                quantity = sum(
                    line.product_id.stock_quant_ids.filtered(lambda a: a.company_id == line.company_ids).mapped(
                        'quantity'))
                reserved = sum(
                    line.product_id.stock_quant_ids.filtered(lambda a: a.company_id == line.company_ids).mapped(
                        'reserved_quantity'))
                prev = self.env['purchase.remainder'].search(
                    [('product_id', '=', line.product_id.id), ('state', '!=', 'done'),
                     ('company_id', '=', line.company_ids.id)])

                if not prev:
                    if quantity >= reserved:
                        available = quantity - reserved
                    if line.send_qty > available:
                        self.env['purchase.remainder'].create({
                            'company_id': line.company_ids.id,
                            'product_id': line.product_id.id,
                            'ordered_qty': line.send_qty - available,
                            'product_uom': line.product_uom.id,
                            'available_qty': quantity,
                            'reserved_qty': reserved,
                        })
                else:
                    prev.ordered_qty += line.send_qty
                    prev.available_qty = available
                    prev.reserved_qty = reserved

            quantity = sum(
                line.product_id.stock_quant_ids.filtered(lambda a: a.company_id == self.company_id).mapped('quantity'))
            reserved = sum(line.product_id.stock_quant_ids.filtered(lambda a: a.company_id == self.company_id).mapped(
                'reserved_quantity'))
            if quantity >= reserved:
                available = quantity - reserved
            prev = self.env['purchase.remainder'].search(
                [('product_id', '=', line.product_id.id), ('state', '!=', 'done'),
                 ('company_id', '=', self.company_id.id)])
            if not prev:
                if line.send_qty > available:
                    self.env['purchase.remainder'].create({
                        'company_id': self.company_id.id,
                        'product_id': line.product_id.id,
                        'ordered_qty': line.send_qty - available,
                        'product_uom': line.product_uom.id,
                        'available_qty': quantity,
                        'reserved_qty': reserved,
                    })
            else:
                prev.ordered_qty += line.send_qty
                prev.available_qty = available
                prev.reserved_qty = reserved


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    picking_type = fields.Char(related='picking_type_id.name', string='TYPE')


class CollectionReminderConfig(models.Model):
    _name = 'collection.reminder.config'
    _order = 'id desc'

    active = fields.Boolean(default=True)
    sales_person = fields.Many2one('res.partner',domain=[('user_id','!=',False)])




