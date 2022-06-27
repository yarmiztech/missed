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


class CustomerAgedReport(models.Model):
    _name = "customer.area.aged"
    _description = "Aged Report"
    _order = "id desc"

    name = fields.Char("Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)

    state = fields.Selection([('draft', 'Draft'), ('validate', 'Done'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")
    report_type = fields.Selection([('area', 'Area Wise'), ('partner', 'Party Wise')],
                                   default='partner', copy=False, string="Report Type")

    area = fields.Many2one('area.wise', string='Area')
    partner_id = fields.Many2one('res.partner', string='Party Wise', domain=[('estimator', '=', True)])
    summary_header = fields.Text("Summary Header")
    summary_footer = fields.Text("Summary Footer")
    room_summary = fields.Text("Building Summary")
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")
    name = fields.Char("Name")

    @api.model
    def default_get(self, fields):
        """
        To get default values for the object.
        @param self: The object pointer.
        @param fields: List of fields for which we want default values
        @return: A dictionary which of fields with values.
        """
        if self._context is None:
            self._context = {}
        res = super(CustomerAgedReport, self).default_get(fields)
        # Added default datetime as today and date to as today + 30.
        from_dt = datetime.today()
        dt_from = from_dt.strftime(dt)
        to_dt = from_dt + relativedelta(days=30)
        dt_to = to_dt.strftime(dt)
        # res.update({"from_date": dt_from, "to_date": dt_to})
        #
        # if not self.from_date and self.to_date:
        #     date_today = datetime.datetime.today()
        #     first_day = datetime.datetime(
        #         date_today.year, date_today.month, 1, 0, 0, 0
        #     )
        #     first_temp_day = first_day + relativedelta(months=1)
        #     last_temp_day = first_temp_day - relativedelta(days=1)
        #     last_day = datetime.datetime(
        #         last_temp_day.year,
        #         last_temp_day.month,
        #         last_temp_day.day,
        #         23,
        #         59,
        #         59,
        #     )
        #     date_froms = first_day.strftime(dt)
        #     date_ends = last_day.strftime(dt)
        res.update({})
        return res

    @api.onchange("report_type", "partner_id", "area")
    def get_room_summary(self):
        # if self.from_date:
        #     self.to_date = self.from_date + relativedelta(months=1)
        """
        @param self: object pointer
         """
        res = {}
        all_detail = []
        room_obj = self.env["partner.ledger.customer"]
        reservation_line_obj = self.env["partner.ledger.customer"]
        folio_room_line_obj = self.env["partner.ledger.customer"]
        user_obj = self.env["res.users"]
        date_range_list = []
        main_header = []
        main_footer = []
        footer_details = []
        # footer_details.append('')
        # footer_details.append('Total')
        summary_header_list = ['SI.No']
        summary_header_list.append('Party Name')
        if self:
            temp_month = 1
            while temp_month <= 8:
                if temp_month == 1:
                    month_val = '<= 7'
                if temp_month == 2:
                    month_val = '<= 15'
                if temp_month == 3:
                    month_val = '<= 30'
                if temp_month == 4:
                    month_val = '<= 40'
                if temp_month == 5:
                    month_val = '<= 50'
                if temp_month == 6:
                    month_val = '<= 60'
                if temp_month == 7:
                    month_val = '<= 90'
                if temp_month == 8:
                    # month_val = '>90'
                    month_val = 'Older'
                summary_header_list.append(month_val)
                date_range_list.append(month_val)
                temp_month += 1
                # # date_range_list(12)
                #
                # temp_date = temp_date + timedelta(days=1)

            summary_header_list.append('Total')
            room_ids = room_obj.search([])
            all_detail.append(summary_header_list)
            if self.report_type == 'partner':
                room_obj = self.env['account.move']
                # room_ids = room_obj.search([('state', 'in', ('draft', 'open'))])
                room_ids = room_obj.search([('state', 'in', ('draft', 'posted'))])
            all_room_detail = []
            # if room_ids:
            amount = 0

            if self.report_type == 'partner':
                room_detail = {}
                if self.partner_id:
                    room_ids = room_ids.search(
                        [('partner_id', '=', self.partner_id.id), ('company_id', '=', self.env.user.company_id.id),
                         ('state', '=', 'posted')])
                    k = 0
                    room_detail = {}
                    foot_detail = {}
                    room_list_stats = []

                    room_detail.update({"name": self.partner_id.name or ""})

                    i = 0
                    next_month = None
                    footer_details = []
                    for chk_date in date_range_list:
                        total_qty = 0
                        k = k + 1
                        room_detail.update({"sno": 1})
                        i = i + 1
                        qty = 0
                        total = 0
                        if i == 1:
                            first = datetime.today().date() + relativedelta(days=-7)
                            amount = round(sum(room_ids.search([('partner_id', '=', self.partner_id.id),
                                                                ('company_id', '=', self.env.user.company_id.id),
                                                                ('invoice_date', '>=', first),
                                                                ('state', '=', 'posted')]).mapped('amount_residual')))
                            amount -= sum(self.env["partner.ledger.customer"].search(
                                [('partner_id', '=', self.partner_id.id), ('check_only', '=', True),
                                 ('date', '>=', first),
                                 ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                        elif i == 2:
                            first = datetime.today().date() + relativedelta(days=-8)
                            to = datetime.today().date() + relativedelta(days=-15)

                            amount = round(sum(room_ids.search([('partner_id', '=', self.partner_id.id),
                                                                ('company_id', '=', self.env.user.company_id.id),
                                                                ('invoice_date', '<=', first),
                                                                ('invoice_date', '>=', to),
                                                                ('state', '=', 'posted')]).mapped('amount_residual')))

                            amount -= sum(self.env["partner.ledger.customer"].search(
                                [('partner_id', '=', self.partner_id.id), ('check_only', '=', True),
                                 ('date', '<=', first), ('date', '>=', to),
                                 ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                        elif i == 3:
                            first = datetime.today().date() + relativedelta(days=-16)
                            to = datetime.today().date() + relativedelta(days=-30)

                            amount = round(sum(room_ids.search([('partner_id', '=', self.partner_id.id),
                                                                ('company_id', '=', self.env.user.company_id.id),
                                                                ('invoice_date', '<=', first),
                                                                ('invoice_date', '>=', to),
                                                                ('state', '=', 'posted')]).mapped('amount_residual')))

                            amount -= sum(self.env["partner.ledger.customer"].search(
                                [('partner_id', '=', self.partner_id.id), ('check_only', '=', True),
                                 ('date', '<=', first), ('date', '>=', to),
                                 ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                        elif i == 4:
                            first = datetime.today().date() + relativedelta(days=-31)
                            to = datetime.today().date() + relativedelta(days=-40)

                            amount = round(sum(room_ids.search([('partner_id', '=', self.partner_id.id),
                                                                ('company_id', '=', self.env.user.company_id.id),
                                                                ('invoice_date', '<=', first),
                                                                ('invoice_date', '>=', to),
                                                                ('state', '=', 'posted')]).mapped('amount_residual')))

                            amount -= sum(self.env["partner.ledger.customer"].search(
                                [('partner_id', '=', self.partner_id.id), ('check_only', '=', True),
                                 ('date', '<=', first), ('date', '>=', to),
                                 ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                        elif i == 5:
                            first = datetime.today().date() + relativedelta(days=-41)
                            to = datetime.today().date() + relativedelta(days=-50)

                            amount = round(sum(room_ids.search([('partner_id', '=', self.partner_id.id),
                                                                ('company_id', '=', self.env.user.company_id.id),
                                                                ('invoice_date', '<=', first),
                                                                ('invoice_date', '>=', to),
                                                                ('state', '=', 'posted')]).mapped('amount_residual')))

                            amount -= sum(self.env["partner.ledger.customer"].search(
                                [('partner_id', '=', self.partner_id.id), ('check_only', '=', True),
                                 ('date', '<=', first), ('date', '>=', to),
                                 ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                        elif i == 6:
                            first = datetime.today().date() + relativedelta(days=-51)
                            to = datetime.today().date() + relativedelta(days=-60)

                            amount = round(sum(room_ids.search([('partner_id', '=', self.partner_id.id),
                                                                ('company_id', '=', self.env.user.company_id.id),
                                                                ('invoice_date', '<=', first),
                                                                ('invoice_date', '>=', to),
                                                                ('state', '=', 'posted')]).mapped('amount_residual')))

                            amount -= sum(self.env["partner.ledger.customer"].search(
                                [('partner_id', '=', self.partner_id.id), ('check_only', '=', True),
                                 ('date', '<=', first), ('date', '>=', to),
                                 ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                        elif i == 7:
                            first = datetime.today().date() + relativedelta(days=-61)
                            to = datetime.today().date() + relativedelta(days=-90)

                            amount = round(sum(room_ids.search([('partner_id', '=', self.partner_id.id),
                                                                ('company_id', '=', self.env.user.company_id.id),
                                                                ('invoice_date', '<=', first),
                                                                ('invoice_date', '>=', to),
                                                                ('state', '=', 'posted')]).mapped('amount_residual')))

                            amount -= sum(self.env["partner.ledger.customer"].search(
                                [('partner_id', '=', self.partner_id.id), ('check_only', '=', True),
                                 ('date', '<=', first), ('date', '>=', to),
                                 ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                        elif i == 8:
                            first = datetime.today().date() + relativedelta(days=-91)
                            # to = datetime.today().date() + relativedelta(days=-51)

                            amount = round(sum(room_ids.search([('partner_id', '=', self.partner_id.id),
                                                                ('company_id', '=', self.env.user.company_id.id),
                                                                ('invoice_date', '<=', first),
                                                                ('state', '=', 'posted')]).mapped('amount_residual')))
                            amount -= sum(self.env["partner.ledger.customer"].search(
                                [('partner_id', '=', self.partner_id.id), ('check_only', '=', True),
                                 ('date', '<=', first), ('date', '>=', to),
                                 ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                            amount += sum(self.env["partner.ledger.customer"].search(
                                [('partner_id', '=', self.partner_id.id),
                                 ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                lambda a: a.description == 'Opening Balance').mapped('debit'))
                            if amount == 0:
                                amount = -sum(self.env["partner.ledger.customer"].search(
                                    [('partner_id', '=', self.partner_id.id),
                                     ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                    lambda a: a.description == 'Opening Balance').mapped('credit'))

                        room_list_stats.append(
                            {
                                "state": "Free",
                                # "date": chk_date,
                                "room_id": self.partner_id.name,
                                "qty": amount,
                                "count": amount,

                            }
                        )

                        all_amount = round(
                            sum(room_ids.search([('partner_id', '=', self.partner_id.id), ('state', '=', 'posted'),
                                                 ('company_id', '=', self.env.user.company_id.id), (
                                                     'invoice_date', '<=',
                                                     datetime.today().date())]).mapped('amount_residual')))
                        all_amount += sum(self.env["partner.ledger.customer"].search(
                            [('partner_id', '=', self.partner_id.id),
                             ('company_id', '=', self.env.user.company_id.id)]).filtered(
                            lambda a: a.description == 'Opening Balance').mapped('debit'))
                        if all_amount == 0 and i == 8:
                            all_amount = -sum(self.env["partner.ledger.customer"].search(
                                [('partner_id', '=', self.partner_id.id),
                                 ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                lambda a: a.description == 'Opening Balance').mapped('credit'))


                        all_amount -= sum(self.env["partner.ledger.customer"].search(
                            [('partner_id', '=', self.partner_id.id), ('check_only', '=', True),
                             ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                        room_detail.update({"total": all_amount})
                        footer_details.append(str(amount))
                    room_detail.update({"value": room_list_stats})
                    all_room_detail.append(room_detail)
                    footer_details.append(str(all_amount))
            if self.report_type == 'area':
                    room_ids = room_obj.search([('area', '=', self.area.id)])
                    room_ids = room_ids.mapped('estimate_id').mapped('invoice_ids').filtered(
                        lambda a: a.state == 'posted')
                    if not room_ids:
                        room_ids = room_obj.search([('area', '=', self.area.id)])
                    room_detail = {}
                    if self.area:
                        k = 0
                        for each_partner in room_ids.filtered(
                                lambda a: a.company_id == self.env.user.company_id).mapped('partner_id'):
                            # room_ids = room_ids.search([('company_id','=',self.env.user.company_id.id)])
                                if room_ids.mapped('estimate_id').mapped('invoice_ids').filtered(lambda a: a.state == 'posted'):
                                    if round(sum(room_ids.filtered(lambda a: a.company_id == self.env.user.company_id and a.partner_id == each_partner and a.invoice_date <= datetime.today().date()).mapped(
                                        'amount_residual'))):
                                        k = k + 1
                                        room_detail = {}
                                        foot_detail = {}
                                        room_list_stats = []
                                        # summary_header_list.pop(1)
                                        # summary_header_list.insert(1, 'Area Name')

                                        room_detail.update({"name": each_partner.name or ""})
                                        room_detail.update({"sno": k})

                                        i = 0
                                        next_month = None
                                        footer_details = []
                                        for chk_date in date_range_list:
                                            total_qty = 0

                                            i = i + 1

                                            qty = 0
                                            total = 0
                                            total_coumn = 0
                                            complete_total_coumn = 0
                                            if i == 1:
                                                first = datetime.today().date() + relativedelta(days=-7)
                                                amount = round(sum(room_ids.filtered(lambda
                                                                                         a: a.company_id == self.env.user.company_id and a.invoice_date >= first and a.partner_id == each_partner and a.state == 'posted').mapped(
                                                    'amount_residual')))

                                                amount -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '>=', first),
                                                     ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                total_coumn = round(sum(room_ids.filtered(lambda
                                                                                        a: a.company_id == self.env.user.company_id and a.invoice_date >= first and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '>=', first),
                                                     ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))

                                                complete_total_coumn = round(sum(room_ids.filtered(lambda
                                                                                                 a: a.company_id == self.env.user.company_id and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                print(complete_total_coumn, '1')
                                                complete_total_coumn = complete_total_coumn - sum(
                                                    self.env["partner.ledger.customer"].search(
                                                        [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                         ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                            elif i == 2:
                                                first = datetime.today().date() + relativedelta(days=-8)
                                                to = datetime.today().date() + relativedelta(days=-15)

                                                amount = round(sum(room_ids.filtered(lambda
                                                                                         a: a.company_id == self.env.user.company_id and a.state == 'posted' and a.partner_id == each_partner and a.invoice_date <= first and a.invoice_date >= to).mapped(
                                                    'amount_residual')))

                                                amount -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                     ('date', '<=', first), ('date', '>=', to),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                total_coumn = round(sum(room_ids.filtered(lambda
                                                                                        a: a.company_id == self.env.user.company_id and a.invoice_date <= first and a.invoice_date >= to and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('date', '>=', to), ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))

                                                complete_total_coumn = round(sum(room_ids.filtered(lambda
                                                                                                 a: a.company_id == self.env.user.company_id and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                print(complete_total_coumn, '2')
                                                complete_total_coumn = complete_total_coumn - sum(
                                                    self.env["partner.ledger.customer"].search(
                                                        [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                         ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))


                                            elif i == 3:
                                                first = datetime.today().date() + relativedelta(days=-16)
                                                to = datetime.today().date() + relativedelta(days=-30)

                                                amount = round(sum(room_ids.filtered(lambda
                                                                                         a: a.company_id == self.env.user.company_id and a.invoice_date <= first and a.partner_id == each_partner and a.state == 'posted' and a.invoice_date >= to).mapped(
                                                    'amount_residual')))
                                                amount -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('date', '>=', to), ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                total_coumn = round(sum(room_ids.filtered(lambda
                                                                                        a: a.company_id == self.env.user.company_id and a.invoice_date <= first and a.invoice_date >= to and a.state == 'posted').mapped(
                                                    'amount_residual')))

                                                total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('date', '>=', to), ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))

                                                complete_total_coumn = round(sum(room_ids.filtered(lambda
                                                                                                 a: a.company_id == self.env.user.company_id and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                print(complete_total_coumn, '3')
                                                complete_total_coumn = complete_total_coumn - sum(
                                                    self.env["partner.ledger.customer"].search(
                                                        [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                         ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))


                                            elif i == 4:
                                                first = datetime.today().date() + relativedelta(days=-31)
                                                to = datetime.today().date() + relativedelta(days=-40)

                                                amount = round(sum(room_ids.filtered(lambda
                                                                                         a: a.company_id == self.env.user.company_id and a.invoice_date <= first and a.state == 'posted' and a.partner_id == each_partner and a.invoice_date >= to).mapped(
                                                    'amount_residual')))
                                                amount -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('date', '>=', to), ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                total_coumn = round(sum(room_ids.filtered(lambda
                                                                                        a: a.company_id == self.env.user.company_id and a.invoice_date <= first and a.invoice_date >= to and a.state == 'posted').mapped(
                                                    'amount_residual')))

                                                total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('date', '>=', to), ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))

                                                complete_total_coumn = round(sum(room_ids.filtered(lambda
                                                                                                 a: a.company_id == self.env.user.company_id and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                print(complete_total_coumn, '4')
                                                complete_total_coumn = complete_total_coumn - sum(
                                                    self.env["partner.ledger.customer"].search(
                                                        [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                         ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                            elif i == 5:
                                                first = datetime.today().date() + relativedelta(days=-41)
                                                to = datetime.today().date() + relativedelta(days=-50)

                                                amount = round(sum(room_ids.filtered(lambda
                                                                                         a: a.company_id == self.env.user.company_id and a.invoice_date <= first and a.partner_id == each_partner and a.state == 'posted' and a.invoice_date >= to).mapped(
                                                    'amount_residual')))
                                                amount -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('date', '>=', to), ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                total_coumn = round(sum(room_ids.filtered(lambda
                                                                                        a: a.company_id == self.env.user.company_id and a.invoice_date <= first and a.invoice_date >= to and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))
                                                total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('date', '>=', to), ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                complete_total_coumn = round(sum(room_ids.filtered(lambda
                                                                                                 a: a.company_id == self.env.user.company_id and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                print(complete_total_coumn, '5')
                                                complete_total_coumn = complete_total_coumn - sum(
                                                    self.env["partner.ledger.customer"].search(
                                                        [('partner_id', '=', each_partner.id), ('check_only', '=', True),

                                                         ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))


                                            elif i == 6:
                                                first = datetime.today().date() + relativedelta(days=-51)
                                                to = datetime.today().date() + relativedelta(days=-60)

                                                amount = round(sum(room_ids.filtered(lambda
                                                                                         a: a.company_id == self.env.user.company_id and a.partner_id == each_partner and a.invoice_date <= first and a.state == 'posted' and a.invoice_date >= to).mapped(
                                                    'amount_residual')))
                                                amount -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('date', '>=', to), ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                total_coumn = round(sum(room_ids.filtered(lambda
                                                                                        a: a.company_id == self.env.user.company_id and a.invoice_date <= first and a.invoice_date >= to and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('date', '>=', to), ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))
                                                #
                                                # complete_total_coumn = sum(room_ids.filtered(lambda a: a.company_id == self.env.user.company_id and a.state == 'posted').mapped('amount_residual'))
                                                complete_total_coumn = round(sum(room_ids.filtered(lambda
                                                                                                 a: a.company_id == self.env.user.company_id and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                print(complete_total_coumn, '6')

                                                complete_total_coumn = complete_total_coumn - sum(
                                                    self.env["partner.ledger.customer"].search(
                                                        [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                         ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))


                                            elif i == 7:
                                                first = datetime.today().date() + relativedelta(days=-61)
                                                to = datetime.today().date() + relativedelta(days=-90)

                                                amount = round(sum(room_ids.filtered(lambda
                                                                                         a: a.company_id == self.env.user.company_id and a.partner_id == each_partner and a.invoice_date <= first and a.state == 'posted' and a.invoice_date >= to).mapped(
                                                    'amount_residual')))
                                                amount -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('date', '>=', to), ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                total_coumn = round(sum(room_ids.filtered(lambda
                                                                                        a: a.company_id == self.env.user.company_id and a.invoice_date <= first and a.invoice_date >= to and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('date', '>=', to), ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))

                                                complete_total_coumn = round(sum(room_ids.filtered(lambda
                                                                                                 a: a.company_id == self.env.user.company_id and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                print(complete_total_coumn, '7')
                                                complete_total_coumn = complete_total_coumn - sum(
                                                    self.env["partner.ledger.customer"].search(
                                                        [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                         ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))


                                            elif i == 8:
                                                first = datetime.today().date() + relativedelta(days=-91)
                                                # to = datetime.today().date() + relativedelta(days=-51)

                                                amount = round(sum(room_ids.filtered(lambda
                                                                                         a: a.company_id == self.env.user.company_id and a.partner_id == each_partner and a.invoice_date <= first and a.state == 'posted').mapped(
                                                    'amount_residual')))

                                                amount += sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id),
                                                     ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                    lambda a: a.description == 'Opening Balance').mapped('debit'))
                                                amount -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                total_coumn = round(sum(room_ids.filtered(lambda
                                                                                        a: a.company_id == self.env.user.company_id and a.invoice_date <= first and a.invoice_date >= to and a.state == 'posted').mapped(
                                                    'amount_residual')))

                                                total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('check_only', '=', True),
                                                     ('date', '>=', to),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                complete_total_coumn = round(sum(room_ids.filtered(lambda
                                                                                                 a: a.company_id == self.env.user.company_id and a.state == 'posted').mapped(
                                                    'amount_residual')))
                                                amt = 0

                                                for each_test in room_ids.filtered(
                                                        lambda a: a.company_id == self.env.user.company_id).mapped('partner_id'):
                                                    amt += sum(self.env["partner.ledger.customer"].search(
                                                        [('partner_id', '=', each_test.id),
                                                         ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                        lambda a: a.description == 'Opening Balance').mapped('debit'))
                                                    print(amt, 'amt')
                                                complete_total_coumn += amt
                                                total_coumn += amt
                                                complete_total_coumn = complete_total_coumn - sum(
                                                    self.env["partner.ledger.customer"].search(
                                                        [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                         ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                            all_amount = round(sum(room_ids.filtered(lambda
                                                                                         a: a.company_id == self.env.user.company_id and a.partner_id == each_partner and a.invoice_date <= datetime.today().date()).mapped(
                                                'amount_residual')))
                                            all_amount += sum(self.env["partner.ledger.customer"].search(
                                                [('partner_id', '=', each_partner.id),
                                                 ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                lambda a: a.description == 'Opening Balance').mapped('debit'))
                                            print(all_amount, 'all_amount', total_coumn, 'total_coumn', complete_total_coumn,
                                                  'complete_total_coumn')
                                            all_amount -= sum(self.env["partner.ledger.customer"].search(
                                                [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                 ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                            room_list_stats.append(
                                                {
                                                    "state": "Free",
                                                    # "date": chk_date,
                                                    "room_id": self.partner_id.name,
                                                    "qty": amount,
                                                    "count": amount,

                                                }
                                            )

                                            room_detail.update({"total": all_amount})
                                            footer_details.append(str(total_coumn))
                                        room_detail.update({"value": room_list_stats})
                                        all_room_detail.append(room_detail)
                                        footer_details.append(str(complete_total_coumn))
                                else:
                                        k = k + 1
                                        room_detail = {}
                                        foot_detail = {}
                                        room_list_stats = []
                                        # summary_header_list.pop(1)
                                        # summary_header_list.insert(1, 'Area Name')

                                        room_detail.update({"name": each_partner.name or ""})
                                        room_detail.update({"sno": k})

                                        i = 0
                                        next_month = None
                                        footer_details = []
                                        for chk_date in date_range_list:
                                            total_qty = 0

                                            i = i + 1

                                            qty = 0
                                            total = 0
                                            total_coumn = 0
                                            complete_total_coumn = 0
                                            if i == 1:
                                                first = datetime.today().date() + relativedelta(days=-7)
                                                # amount = round(sum(room_ids.filtered(lambda
                                                #                                          a: a.company_id == self.env.user.company_id and a.date >= first and a.partner_id == each_partner).mapped(
                                                #     'balance')))
                                                amount =0


                                                # amount -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '>=', first),
                                                #      ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # total_coumn = sum(room_ids.filtered(lambda
                                                #                                         a: a.company_id == self.env.user.company_id and a.date >= first).mapped(
                                                #     'balance'))
                                                # total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '>=', first),
                                                #      ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))
                                                total_coumn =0
                                                # complete_total_coumn = sum(room_ids.filtered(lambda
                                                #                                                  a: a.company_id == self.env.user.company_id).mapped(
                                                #     'balance'))
                                                complete_total_coumn =0
                                                print(complete_total_coumn, '1')
                                                # complete_total_coumn = complete_total_coumn - sum(
                                                #     self.env["partner.ledger.customer"].search(
                                                #         [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                #          ('company_id', '=', self.env.user.company_id.id)]).mapped(
                                                #         'credit'))
                                                # complete_total_coumn

                                            elif i == 2:
                                                first = datetime.today().date() + relativedelta(days=-8)
                                                to = datetime.today().date() + relativedelta(days=-15)

                                                # amount = round(sum(room_ids.filtered(lambda
                                                #                                          a: a.company_id == self.env.user.company_id  and a.partner_id == each_partner and a.date <= first and a.date >= to).mapped(
                                                #     'balance')))
                                                amount =0

                                                # amount -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                #      ('date', '<=', first), ('date', '>=', to),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # total_coumn = sum(room_ids.filtered(lambda
                                                #                                         a: a.company_id == self.env.user.company_id and a.date <= first and a.date >= to).mapped(
                                                #     'balance'))
                                                # total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                #      ('date', '>=', to), ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                                                total_coumn =0
                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))

                                                # complete_total_coumn = sum(room_ids.filtered(lambda
                                                #                                                  a: a.company_id == self.env.user.company_id).mapped(
                                                #     'balance'))
                                                # print(complete_total_coumn, '2')
                                                # complete_total_coumn = complete_total_coumn - sum(
                                                #     self.env["partner.ledger.customer"].search(
                                                #         [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                #          ('company_id', '=', self.env.user.company_id.id)]).mapped(
                                                #         'credit'))
                                                complete_total_coumn =0


                                            elif i == 3:
                                                first = datetime.today().date() + relativedelta(days=-16)
                                                to = datetime.today().date() + relativedelta(days=-30)

                                                # amount = round(sum(room_ids.filtered(lambda
                                                #                                          a: a.company_id == self.env.user.company_id and a.date <= first and a.partner_id == each_partner  and a.date >= to).mapped(
                                                #     'balance')))
                                                amount =0

                                                # amount -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                #      ('date', '>=', to), ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # total_coumn = sum(room_ids.filtered(lambda
                                                #                                         a: a.company_id == self.env.user.company_id and a.date <= first and a.date >= to ).mapped(
                                                #     'balance'))
                                                #
                                                # total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                #      ('date', '>=', to), ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                                                total_coumn = 0
                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))

                                                # complete_total_coumn = sum(room_ids.filtered(lambda
                                                #                                                  a: a.company_id == self.env.user.company_id).mapped(
                                                #     'balance'))
                                                # print(complete_total_coumn, '3')
                                                # complete_total_coumn = complete_total_coumn - sum(
                                                #     self.env["partner.ledger.customer"].search(
                                                #         [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                #          ('company_id', '=', self.env.user.company_id.id)]).mapped(
                                                #         'credit'))
                                                complete_total_coumn =0


                                            elif i == 4:
                                                first = datetime.today().date() + relativedelta(days=-31)
                                                to = datetime.today().date() + relativedelta(days=-40)

                                                # amount = round(sum(room_ids.filtered(lambda
                                                #                                          a: a.company_id == self.env.user.company_id and a.date <= first  and a.partner_id == each_partner and a.date >= to).mapped(
                                                #     'balance')))
                                                # amount -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                #      ('date', '>=', to), ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                                                amount =0
                                                # total_coumn = sum(room_ids.filtered(lambda
                                                #                                         a: a.company_id == self.env.user.company_id and a.date <= first and a.date >= to ).mapped(
                                                #     'balance'))
                                                #
                                                # total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                #      ('date', '>=', to), ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))
                                                total_coumn =0
                                                # complete_total_coumn = sum(room_ids.filtered(lambda
                                                #                                                  a: a.company_id == self.env.user.company_id).mapped(
                                                #     'balance'))
                                                # print(complete_total_coumn, '4')
                                                # complete_total_coumn = complete_total_coumn - sum(
                                                #     self.env["partner.ledger.customer"].search(
                                                #         [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                #          ('company_id', '=', self.env.user.company_id.id)]).mapped(
                                                #         'credit'))
                                                complete_total_coumn =0

                                            elif i == 5:
                                                first = datetime.today().date() + relativedelta(days=-41)
                                                to = datetime.today().date() + relativedelta(days=-50)

                                                # amount = round(sum(room_ids.filtered(lambda
                                                #                                          a: a.company_id == self.env.user.company_id and a.date <= first and a.partner_id == each_partner  and a.date >= to).mapped(
                                                #     'balance')))
                                                # amount -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                #      ('date', '>=', to), ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                                                amount =0
                                                # total_coumn = sum(room_ids.filtered(lambda
                                                #                                         a: a.company_id == self.env.user.company_id and a.date <= first and a.date >= to).mapped(
                                                #     'balance'))
                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))
                                                # total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                #      ('date', '>=', to), ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                                                total_coumn =0
                                                # complete_total_coumn = sum(room_ids.filtered(lambda
                                                #                                                  a: a.company_id == self.env.user.company_id).mapped(
                                                #     'balance'))
                                                # print(complete_total_coumn, '5')
                                                # complete_total_coumn = complete_total_coumn - sum(
                                                #     self.env["partner.ledger.customer"].search(
                                                #         [('partner_id', '=', each_partner.id), ('check_only', '=', True),

                                                        #  ('company_id', '=', self.env.user.company_id.id)]).mapped(
                                                        # 'credit'))
                                                complete_total_coumn =0


                                            elif i == 6:
                                                first = datetime.today().date() + relativedelta(days=-51)
                                                to = datetime.today().date() + relativedelta(days=-60)

                                                # amount = round(sum(room_ids.filtered(lambda
                                                #                                          a: a.company_id == self.env.user.company_id and a.partner_id == each_partner and a.date <= first and a.date >= to).mapped(
                                                #     'balance')))
                                                # amount -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                #      ('date', '>=', to), ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                                                amount =0
                                                # total_coumn = sum(room_ids.filtered(lambda
                                                #                                         a: a.company_id == self.env.user.company_id and a.date <= first and a.date >= to).mapped(
                                                #     'balance'))
                                                # total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                #      ('date', '>=', to), ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                                                total_coumn =0
                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))
                                                #
                                                # complete_total_coumn = sum(room_ids.filtered(lambda a: a.company_id == self.env.user.company_id and a.state == 'posted').mapped('amount_residual'))
                                                # complete_total_coumn = sum(room_ids.filtered(lambda
                                                #                                                  a: a.company_id == self.env.user.company_id).mapped(
                                                #     'balance'))
                                                # print(complete_total_coumn, '6')
                                                #
                                                # complete_total_coumn = complete_total_coumn - sum(
                                                #     self.env["partner.ledger.customer"].search(
                                                #         [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                #          ('company_id', '=', self.env.user.company_id.id)]).mapped(
                                                #         'credit'))
                                                complete_total_coumn =0


                                            elif i == 7:
                                                first = datetime.today().date() + relativedelta(days=-61)
                                                to = datetime.today().date() + relativedelta(days=-90)

                                                # amount = round(sum(room_ids.filtered(lambda
                                                #                                          a: a.company_id == self.env.user.company_id and a.partner_id == each_partner and a.date <= first  and a.date >= to).mapped(
                                                #     'balance')))
                                                # amount -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                #      ('date', '>=', to), ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))
                                                amount = 0
                                                # total_coumn = sum(room_ids.filtered(lambda
                                                #                                         a: a.company_id == self.env.user.company_id and a.date <= first and a.date >= to).mapped(
                                                #     'balance'))
                                                # total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                #      ('date', '>=', to), ('check_only', '=', True),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # total_coumn += sum(self.env["partner.ledger.customer"].search(
                                                #     [('partner_id', '=', each_partner.id),
                                                #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                #     lambda a: a.description == 'Opening Balance').mapped('debit'))

                                                # complete_total_coumn = sum(room_ids.filtered(lambda
                                                #                                                  a: a.company_id == self.env.user.company_id).mapped(
                                                #     'balance'))
                                                # print(complete_total_coumn, '7')
                                                # complete_total_coumn = complete_total_coumn - sum(
                                                #     self.env["partner.ledger.customer"].search(
                                                #         [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                #          ('company_id', '=', self.env.user.company_id.id)]).mapped(
                                                #         'credit'))

                                                complete_total_coumn =0
                                                total_coumn =0


                                            elif i == 8:
                                                first = datetime.today().date() + relativedelta(days=-91)
                                                # to = datetime.today().date() + relativedelta(days=-51)

                                                amount = round(sum(room_ids.filtered(lambda
                                                                                         a: a.company_id == self.env.user.company_id and a.partner_id == each_partner and a.date <= first).mapped(
                                                    'balance')))

                                                amount += sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id),
                                                     ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                    lambda a: a.description == 'Opening Balance').mapped('debit'))
                                                amount -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('check_only', '=', True),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                total_coumn = sum(room_ids.filtered(lambda
                                                                                        a: a.company_id == self.env.user.company_id and a.date <= first and a.date >= to).mapped(
                                                    'balance'))

                                                total_coumn -= sum(self.env["partner.ledger.customer"].search(
                                                    [('partner_id', '=', each_partner.id), ('date', '<=', first),
                                                     ('check_only', '=', True),
                                                     ('date', '>=', to),
                                                     ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                                # complete_total_coumn = sum(room_ids.filtered(lambda
                                                #                                                  a: a.company_id == self.env.user.company_id).mapped(
                                                #     'balance'))
                                                amt = 0

                                                for each_test in room_ids.mapped('partner_id').filtered(
                                                        lambda a: a.company_id == self.env.user.company_id):
                                                    amt += sum(self.env["partner.ledger.customer"].search(
                                                        [('partner_id', '=', each_test.id),
                                                         ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                                        lambda a: a.description == 'Opening Balance').mapped('debit'))
                                                    print(amt, 'amt')
                                                complete_total_coumn += amt
                                                total_coumn += amt
                                                complete_total_coumn = complete_total_coumn - sum(
                                                    self.env["partner.ledger.customer"].search(
                                                        [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                         ('company_id', '=', self.env.user.company_id.id)]).mapped(
                                                        'credit'))

                                            all_amount = round(sum(room_ids.filtered(lambda
                                                                                         a: a.company_id == self.env.user.company_id and a.partner_id == each_partner and a.date <= datetime.today().date()).mapped(
                                                'balance')))
                                            # all_amount += sum(self.env["partner.ledger.customer"].search(
                                            #     [('partner_id', '=', each_partner.id),
                                            #      ('company_id', '=', self.env.user.company_id.id)]).filtered(
                                            #     lambda a: a.description == 'Opening Balance').mapped('debit'))
                                            print(all_amount, 'all_amount', total_coumn, 'total_coumn',
                                                  complete_total_coumn,
                                                  'complete_total_coumn')
                                            all_amount -= sum(self.env["partner.ledger.customer"].search(
                                                [('partner_id', '=', each_partner.id), ('check_only', '=', True),
                                                 ('company_id', '=', self.env.user.company_id.id)]).mapped('credit'))

                                            room_list_stats.append(
                                                {
                                                    "state": "Free",
                                                    # "date": chk_date,
                                                    "room_id": self.partner_id.name,
                                                    "qty": amount,
                                                    "count": amount,

                                                }
                                            )

                                            room_detail.update({"total": all_amount})
                                            footer_details.append(str(total_coumn))
                                        room_detail.update({"value": room_list_stats})
                                        all_room_detail.append(room_detail)
                                        footer_details.append(str(complete_total_coumn))

            main_header.append({"header": summary_header_list})
            main_footer.append({"footer": footer_details})
            self.summary_header = str(main_header)
            self.summary_footer = str(main_footer)
            self.room_summary = str(all_room_detail)
        return res

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'customer.area.aged') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('customer.area.aged') or _('New')
        return super(CustomerAgedReport, self).create(vals)


class OpeningBalanceCustomers(models.Model):
    _inherit = "opening.balance.customers"

    def action_opening_bal(self):
        self.write({'state': 'close'})
        # if self.type_of_partner == 'partner':
        #     for line in self.op_lines:
        #         vals = {
        #             'journal_id': self.env['account.journal'].search(
        #                 [('name', '=', 'Miscellaneous Operations'), ('company_id', '=', self.company_id.id)]).id,
        #             'state': 'draft',
        #             'ref': line.partner_id.name + 'Opening Balance'
        #         }
        #         pay_id_list = []
        #         move_id = self.env['account.move'].create(vals)
        #         partner_id = line.partner_id.id
        #         label = 'Opening Balance' + '/' + line.partner_id.name
        #
        #         temp = (0, 0, {
        #             'account_id': self.env['account.account'].search(
        #                 [('name', '=', 'Debtors'), ('company_id', '=', self.company_id.id)]).id,
        #             'name': label,
        #             'move_id': move_id.id,
        #             'date': datetime.today().date(),
        #             'partner_id': partner_id,
        #             'debit': line.op_amount,
        #             'credit': 0,
        #         })
        #         pay_id_list.append(temp)
        #
        #         acc = self.env['account.account'].search(
        #             [('name', '=', 'Local Sales'), ('company_id', '=', self.company_id.id)])
        #         temp = (0, 0, {
        #             'account_id': acc.id,
        #             'name': label,
        #             'move_id': move_id.id,
        #             'date': datetime.today().date(),
        #             'partner_id': partner_id,
        #             'debit': 0,
        #             'credit': line.op_amount,
        #         })
        #         pay_id_list.append(temp)
        #         move_id.line_ids = pay_id_list
        #         move_id.action_post()
        #         invoices = self.env['account.move'].search(
        #             [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.company_id.id),
        #              ('state', '!=', 'paid')])
        #         if invoices.mapped('amount_residual'):
        #             balance_amount = sum(invoices.mapped('amount_residual'))
        #         else:
        #             balance_amount = sum(invoices.mapped('amount_total'))
        #         balance_amount += self.env['partner.ledger.customer'].search(
        #             [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
        #         balance_amount = self.env['partner.ledger.customer'].search(
        #             [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)])[-1].balance
        #
        #         self.env['partner.ledger.customer'].create({
        #             'date': datetime.today().date(),
        #             # 'invoice_id': inv.id,
        #             'description': 'Opening Balance',
        #             'partner_id': line.partner_id.id,
        #             # 'product_id': line.product_id.id,
        #             'company_id': self.company_id.id,
        #             # 'price_units': inv.inv_mc_qty,
        #             # 'uom': line.uom_id.id,
        #             # 'rate': line.price_unit,
        #             # 'estimate_id': self.id,
        #             'account_journal': self.env['account.journal'].search([('name', '=', 'Miscellaneous Operations'), ('company_id', '=', self.company_id.id)]).id,
        #             'account_move': move_id.id,
        #             # 'credit': inv.amount_total_signed,
        #             'debit': line.op_amount,
        #             # 'balance': 0,
        #             # 'executive_area': self.executive_areas.id or False,
        #             # 'area': self.area.id or False,
        #             # 'vehicle_id': self.estimate_ids[0].vahicle.id,
        #             'balance': line.op_amount-balance_amount,
        #         })

        for line in self.op_lines:
            vals = {
                'journal_id': self.env['account.journal'].search(
                    [('name', '=', 'Miscellaneous Operations'), ('company_id', '=', self.company_id.id)]).id,
                'state': 'draft',
                'ref': line.partner_id.name + 'Opening Balance'
            }
            pay_id_list = []
            move_id = self.env['account.move'].create(vals)
            partner_id = line.partner_id.id
            label = 'Opening Balance' + '/' + line.partner_id.name
            if self.type_of_partner == 'partner':
                if self.type_of_credit == False:

                    temp = (0, 0, {
                        'account_id': self.env['account.account'].search(
                            [('name', '=', 'Debtors'), ('company_id', '=', self.company_id.id)]).id,
                        'name': label,
                        'move_id': move_id.id,
                        'date': datetime.today().date(),
                        'partner_id': partner_id,
                        'debit': line.op_amount,
                        'credit': 0,
                    })
                    pay_id_list.append(temp)

                    acc = self.env['account.account'].search(
                        [('name', '=', 'Undistributed Profits/Losses'), ('company_id', '=', self.company_id.id)])
                    temp = (0, 0, {
                        'account_id': acc.id,
                        'name': label,
                        'move_id': move_id.id,
                        'date': datetime.today().date(),
                        'partner_id': partner_id,
                        'debit': 0,
                        'credit': line.op_amount,
                    })
                    pay_id_list.append(temp)
                    move_id.line_ids = pay_id_list
                    move_id.action_post()
                    invoices = self.env['account.move'].search(
                        [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.company_id.id),
                         ('state', '!=', 'paid')])
                    if invoices.mapped('amount_residual'):
                        balance_amount = sum(invoices.mapped('amount_residual'))
                    else:
                        balance_amount = sum(invoices.mapped('amount_total'))
                    # balance_amount += self.env['partner.ledger.customer'].search(
                    #     [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                    previous = self.env['partner.ledger.customer'].search(
                        [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)])
                    if previous:
                        balance_amount = self.env['partner.ledger.customer'].search(
                            [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)])[-1].balance

                    self.env['partner.ledger.customer'].sudo().create({
                        'date': datetime.today().date(),
                        # 'invoice_id': inv.id,
                        'description': 'Opening Balance',
                        'partner_id': line.partner_id.id,
                        # 'product_id': line.product_id.id,
                        'company_id': self.company_id.id,
                        # 'price_units': inv.inv_mc_qty,
                        # 'uom': line.uom_id.id,
                        # 'rate': line.price_unit,
                        # 'estimate_id': self.id,
                        'account_journal': self.env['account.journal'].search(
                            [('name', '=', 'Miscellaneous Operations'), ('company_id', '=', self.company_id.id)]).id,
                        'account_move': move_id.id,
                        # 'credit': inv.amount_total_signed,
                        'debit': line.op_amount,
                        # 'balance': 0,
                        # 'executive_area': self.executive_areas.id or False,
                        'area': line.partner_id.area.id or False,
                        # 'vehicle_id': self.estimate_ids[0].vahicle.id,
                        'balance': line.op_amount + balance_amount,
                    })
                else:
                    temp = (0, 0, {
                        'account_id': self.env['account.account'].search(
                            [('name', '=', 'Creditors'), ('company_id', '=', self.company_id.id)]).id,
                        'name': label,
                        'move_id': move_id.id,
                        'date': datetime.today().date(),
                        'partner_id': partner_id,
                        'debit': 0,
                        'credit': line.op_amount,
                    })
                    pay_id_list.append(temp)

                    acc = self.env['account.account'].search(
                        [('name', '=', 'Undistributed Profits/Losses'), ('company_id', '=', self.company_id.id)])
                    temp = (0, 0, {
                        'account_id': acc.id,
                        'name': label,
                        'move_id': move_id.id,
                        'date': datetime.today().date(),
                        'partner_id': partner_id,
                        'debit': line.op_amount,
                        'credit': 0,
                    })
                    pay_id_list.append(temp)
                    move_id.line_ids = pay_id_list
                    move_id.action_post()
                    invoices = self.env['account.move'].search(
                        [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.company_id.id),
                         ('state', '!=', 'paid')])
                    if invoices.mapped('amount_residual'):
                        balance_amount = sum(invoices.mapped('amount_residual'))
                    else:
                        balance_amount = sum(invoices.mapped('amount_total'))
                    # balance_amount += self.env['partner.ledger.customer'].search(
                    #     [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
                    previous = self.env['partner.ledger.customer'].search(
                        [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)])
                    if previous:
                        balance_amount = self.env['partner.ledger.customer'].search(
                            [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)])[
                            -1].balance

                    self.env['partner.ledger.customer'].sudo().create({
                        'date': datetime.today().date(),
                        # 'invoice_id': inv.id,
                        'description': 'Opening Balance',
                        'partner_id': line.partner_id.id,
                        # 'product_id': line.product_id.id,
                        'company_id': self.company_id.id,
                        # 'price_units': inv.inv_mc_qty,
                        # 'uom': line.uom_id.id,
                        # 'rate': line.price_unit,
                        # 'estimate_id': self.id,
                        'account_journal': self.env['account.journal'].search(
                            [('name', '=', 'Miscellaneous Operations'), ('company_id', '=', self.company_id.id)]).id,
                        'account_move': move_id.id,
                        'credit': line.op_amount,
                        # 'debit': ,
                        # 'balance': 0,
                        # 'executive_area': self.executive_areas.id or False,
                        'area': line.partner_id.area.id or False,
                        # 'vehicle_id': self.estimate_ids[0].vahicle.id,
                        'balance':  balance_amount-line.op_amount,
                    })



            else:
                temp = (0, 0, {
                    'account_id': self.env['account.account'].search(
                        [('name', '=', 'Creditors'), ('company_id', '=', self.company_id.id)]).id,
                    'name': label,
                    'move_id': move_id.id,
                    'date': datetime.today().date(),
                    'partner_id': partner_id,
                    'debit': 0,
                    'credit': line.op_amount,
                })
                pay_id_list.append(temp)

                acc = self.env['account.account'].search(
                    [('name', '=', 'Undistributed Profits/Losses'), ('company_id', '=', self.company_id.id)])
                temp = (0, 0, {
                    'account_id': acc.id,
                    'name': label,
                    'move_id': move_id.id,
                    'date': datetime.today().date(),
                    'partner_id': partner_id,
                    'debit': line.op_amount,
                    'credit': 0,
                })
                pay_id_list.append(temp)
                move_id.line_ids = pay_id_list
                move_id.action_post()

                balance_amount = 0
                invoices = self.env['account.move'].search(
                    [('partner_id', '=', line.partner_id.id),
                     ('company_id', '=', self.env.user.company_id.id), ('state', '!=', 'paid')])
                if invoices.mapped('amount_residual'):
                    balance_amount = sum(invoices.mapped('amount_residual'))
                else:
                    balance_amount = sum(invoices.mapped('amount_total'))
                balance_amount += self.env['supplier.ledger.customer'].search(
                    [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.company_id.id),
                     ('description', '=', 'Opening Balance')]).balance
                if self.env['supplier.ledger.customer'].search(
                        [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)]):
                    balance_amount = self.env['supplier.ledger.customer'].search(
                        [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)])[
                        -1].balance
                self.env['supplier.ledger.customer'].sudo().create({
                    'date': datetime.today().date(),
                    'partner_id': line.partner_id.id,
                    'description': 'Opening Balance',
                    # 'invoice_id': self.invoice_ids.id or False,
                    'company_id': self.company_id.id,
                    'credit': line.op_amount,
                    'month': str(datetime.today().date().month),
                    'balance': balance_amount + line.op_amount

                })


class OpeningBalanceLines(models.Model):
    _inherit = "opening.balance.lines"

    address = fields.Char('Address')
    mobile = fields.Char('Mobile')
    vat = fields.Char(string="GSTIN")
    area = fields.Many2one('area.wise', string='Area')
    sales_person = fields.Many2one('res.partner', string='Rep')

    @api.onchange("vat", "area", "address", "mobile")
    def get_room_vat(self):
        if self.partner_id:
            if self.vat:
                self.partner_id.vat = self.vat

            if self.area:
                self.partner_id.area = self.area

            if self.mobile:
                self.partner_id.mobile = self.mobile

            if self.address:
                self.partner_id.street = self.address
