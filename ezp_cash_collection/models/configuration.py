# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import date
from datetime import datetime
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import calendar


class PdcConfiguration(models.Model):
    _name = "pdc.configuration"
    _order = "id desc"

    days = fields.Integer(string='PDC Cheque Up to Days')
    active = fields.Boolean(default=True)


class CreditLimitConfiguration(models.Model):
    _name = "credit.limit.configuration"
    _order = "id desc"

    months = fields.Integer(string='Credit Limit Months')
    percentage = fields.Integer(string='Credit Percentage(%)')
    active = fields.Boolean(default=True)
    min_credit_amount = fields.Float(string='Min Credit Limit Amt')
