# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    credit_po_amount = fields.Float('Reverse Amount', compute='_compute_purchase_reverse')

    def _compute_purchase_reverse(self):
        for each in self:
            each.credit_po_amount=0.0
            for refund_ref in each.invoice_ids.filtered(lambda a:a.move_type == 'in_refund'):
                each.credit_po_amount += refund_ref.amount_total
