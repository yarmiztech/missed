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


class SalesExecutivesComplete(models.Model):
    _name = 'sales.executive.complete'
    _order = 'id desc'

    sales_person = fields.Many2one('res.partner',string='Sales Person')
    product_id = fields.Many2one('product.product',string='Product')
    quantity = fields.Float('Total Sold')
    total_amount = fields.Float('Total Amount')
    collection_amount = fields.Float('Collection Amount')
    total_visited = fields.Integer('Total Visited')
    area = fields.Many2one('area.wise', string='Area')


