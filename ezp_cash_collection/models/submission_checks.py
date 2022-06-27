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



class ChequeSubmission(models.Model):
    _name = "cheque.submission"
    _description = "Cheque Cheques"
    _order = "id desc"

    name = fields.Char("Collection Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)

    # type_state = fields.Selection([('submit', 'Submitted'),('postponed', 'Postponed'),('bounce', 'Bounced'), ('cleared', 'Cleared')], copy=False, string="Filtered By")
    type_state = fields.Selection([
        ('none', ''),
        ('submit', 'submitted'),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('cancel', 'Cancelled')], string='Status',
        default='none')
    create_date = fields.Date(string='Date', default=fields.Date.context_today, required=True, copy=False)
    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date', )
    date = fields.Date('Cheque Date')
    submitted_date = fields.Date('Submitted Date')
    clearing_date = fields.Date(string='Clear Date')
    sales_person = fields.Many2one('res.users', string="Sales Person")
    partner_id = fields.Many2one('res.partner')
    bulk_cheque = fields.Many2one('bulk.collections')
    check_line = fields.Many2one('executive.cheque.collection.line')
    advance_check_line = fields.Many2one('advance.cheque.collection.line')
    balance_amount = fields.Float(string='Bal Amount', )
    amount_total = fields.Float(string='Paid Amount', )
    ref_id = fields.Many2one('executive.cheque.collection', string="Source")
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    default='inbound', )
    payments = fields.Many2many('account.payment', 'payments_chequesub_rels')
    check_no = fields.Char(string='Cheque No')
    check_type = fields.Selection([('cash', 'Cash'), ('pdc', 'PDC'), ], string="Check Type", )
    check_manual_date = fields.Date(string='Check Date', )
    bank_name = fields.Char('Back Name')
    account_id = fields.Many2one('account.account')
    check_post_id = fields.Many2one('post.cheques.line')
    check_bounce_id = fields.Many2one('bounce.cheques.line')
    select = fields.Boolean('select')
    status = fields.Selection([
        ('none', ''),
        ('submit', 'submitted'),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('cancel', 'Cancelled')], string='Status',
        default='none')
    postpone_date = fields.Date(string='Post Date', )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('send', 'Sended'),
        ('postpone', 'Postpone'),
        ('deposit', 'Deposit'),
        ('bounce', 'Bounce'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='state', readonly=True,
        default='draft')
    holder_name = fields.Many2one('res.partner', string='Holder Name')
    debited_account = fields.Many2one('account.journal', string='Debit A/C')
    collected_cheque = fields.Many2one('collection.cheque')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'cheque.submission') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('cheque.submission') or _('New')
        return super(ChequeSubmission, self).create(vals)


class PartnerLedgerCustom(models.Model):
    _name = 'partner.ledger.customer'

    date = fields.Date('Date')
    paid_date = fields.Date('Paid Date')
    address = fields.Text('Address')
    executive_area = fields.Many2one('executive.area.wise', string='Executive Area')
    area = fields.Many2one('area.wise', string='Area')
    account = fields.Many2one('account.account')
    account_journal = fields.Many2one('account.journal')
    estimate_id = fields.Many2one('sale.estimate', string="Estimate")
    invoice_id = fields.Many2one('account.move', string='Invoice No')
    account_move = fields.Many2one('account.move', string='Account Move')
    product_id = fields.Many2one('product.product', string='Product Name')
    partner_id = fields.Many2one('res.partner', string='Partner')
    company_id = fields.Many2one('res.company', string='company')
    vehicle_id = fields.Many2one('fleet.vehicle')
    in_vehicle_id = fields.Char('Invoice Vehicle')
    transport_receipt = fields.Char('Transport Rec')
    gate_pass = fields.Char('Gate Pass')
    check_only = fields.Boolean('check')
    description = fields.Text(string='Description')
    uom = fields.Many2one('uom.uom', string='UoM')
    price_units = fields.Float('Unit')
    rate = fields.Float('Rate')
    debit = fields.Float('Debit')
    credit = fields.Float('Credit')
    balance = fields.Float('Balance')

    #
    # @api.onchange('debit', 'credit')
    # def onchange_debit_credit(self):
    #     bal = sum(
    #         self.env['account.move.line'].search([('journal_id', '=', self.account_journal.id)]).mapped('debit'))
    #     self.balance = bal
    #

    # @api.one
    # def _compute_balance(self):
    #     prev = self.env['partner.ledger.customer'].search([('id', '=', self.id - 1), ('company_id', '=', 1)])
    #     if not prev:
    #         self.balance = self.debit
    #     else:
    #         self.balance = prev.balance + self.debit

    # if self.debit:
    #     bal = sum(
    #         self.env['account.move.line'].search([('journal_id', '=', self.account_journal.id)]).mapped('debit'))
    #     self.balance = bal


class PartnerLedgersCustom(models.Model):
    _name = 'partner.ledgers.customer'

    date = fields.Date('Date')
    paid_date = fields.Date('Paid Date')
    address = fields.Text('Address')
    executive_area = fields.Many2one('executive.area.wise', string='Executive Area')
    area = fields.Many2one('area.wise', string='Area')
    account = fields.Many2one('account.account')
    account_journal = fields.Many2one('account.journal')
    invoice_id = fields.Many2one('account.move', string='Invoice No')
    product_id = fields.Many2one('product.product', string='Product Name')
    partner_id = fields.Many2one('res.partner', string='Partner')
    company_id = fields.Many2one('res.company', string='company')
    vehicle_id = fields.Many2one('fleet.vehicle')
    in_vehicle_id = fields.Char('Invoice Vehicle')
    transport_receipt = fields.Char('Transport Rec')
    gate_pass = fields.Char('Gate Pass')
    description = fields.Text(string='Description')
    uom = fields.Many2one('uom.uom', string='UoM')
    price_units = fields.Float('Unit')
    rate = fields.Float('Rate')
    debit = fields.Float('Debit')
    credit = fields.Float('Credit')
    balance = fields.Float('Balance', compute='_compute_balance')
    month = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
                              ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'), ('9', 'September'),
                              ('10', 'October'), ('11', 'November'), ('12', 'December')])

    # @api.one
    def _compute_balance(self):
        if self.debit:
            bal = sum(
                self.env['account.move.line'].search([('journal_id', '=', self.account_journal.id)]).mapped('debit'))
            self.balance = bal
        else:
            self.balance = 0


class SalesReportComp(models.Model):
    _name = "sale.report.custom"
    _description = "Sales Report"
    _order = "id desc"

    name = fields.Char("Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)

    state = fields.Selection([('draft', 'Draft'), ('validate', 'Done'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")
    payment_date = fields.Date(string='Create Date', default=fields.Date.context_today, required=True, copy=False)
    from_date = fields.Date(string='From Date', copy=False, default=fields.Date.context_today, )
    to_date = fields.Date(string='To Date', copy=False, default=fields.Date.context_today, )
    report_lines = fields.One2many('sale.report.custom.line', 'report_line')
    report_type = fields.Selection([('area', 'Area Wise'), ('partner', 'Party Wise'), ('vehicle', 'Vehicle Wise'),
                                    ('grouped', 'Product Group Wise'), ('product', 'Product Wise')],
                                   default='area', copy=False, string="Report Type")
    product_type = fields.Selection(
        [('grouped', 'Product Group Wise'), ('product', 'Product Wise'), ('categ', 'Product Category')],
        copy=False, string="Product Filter")
    style = fields.Selection(
        [('normal', 'Normal'), ('summary', 'Summary'), ('monthly', 'Monthly')],
        default='normal', copy=False, string="Style")
    area = fields.Many2one('area.wise', string='Area')
    partner_id = fields.Many2one('res.partner', string='Party Wise',domain=[('estimator','=',True)])
    vehicle_id = fields.Many2one('fleet.vehicle')
    month = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
                              ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'), ('9', 'September'),
                              ('10', 'October'), ('11', 'November'), ('12', 'December')])

    product_group = fields.Many2one('product.template', domain=[('grouped', '=', True)])
    product_groups = fields.Many2one('product.template', domain=[('grouped', '=', True)])
    product_id = fields.Many2one('product.product', domain=[('grouped', '=', False), ('type', '=', 'product')])
    product_ids = fields.Many2one('product.product', domain=[('grouped', '=', False), ('type', '=', 'product')])
    product_categ = fields.Many2one('product.category', string='Product Category')
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
        res = super(SalesReportComp, self).default_get(fields)
        # Added default datetime as today and date to as today + 30.
        from_dt = datetime.today()
        dt_from = from_dt.strftime(dt)
        to_dt = from_dt + relativedelta(days=30)
        dt_to = to_dt.strftime(dt)
        # res.update({"from_date": dt_from, "to_date": dt_to})

        if not self.from_date and self.to_date:
            date_today = datetime.datetime.today()
            first_day = datetime.datetime(
                date_today.year, date_today.month, 1, 0, 0, 0
            )
            first_temp_day = first_day + relativedelta(months=1)
            last_temp_day = first_temp_day - relativedelta(days=1)
            last_day = datetime.datetime(
                last_temp_day.year,
                last_temp_day.month,
                last_temp_day.day,
                23,
                59,
                59,
            )
            date_froms = first_day.strftime(dt)
            date_ends = last_day.strftime(dt)
            res.update({"date_from": date_froms, "date_to": date_ends})
        return res

    @api.onchange("report_type", "product_id","product_group","partner_id","from_date","to_date")
    def get_room_summary(self):
        # if self.from_date:
        #     self.to_date = self.from_date + relativedelta(months=1)
        """
        @param self: object pointer
         """
        res = {}
        all_detail = []
        room_obj = self.env["partner.ledgers.customer"]
        reservation_line_obj = self.env["partner.ledgers.customer"]
        folio_room_line_obj = self.env["partner.ledgers.customer"]
        user_obj = self.env["res.users"]
        date_range_list = []
        main_header = []
        main_footer = []
        footer_details =[]
        # footer_details.append('')
        # footer_details.append('Total')
        summary_header_list = ['SI.No']
        summary_header_list.append('Party Name')
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                raise UserError(
                    _(
                        "Please Check Time period Date From can't \
                                   be greater than Date To !"
                    )
                )
            if self._context.get("tz", False):
                timezone = pytz.timezone(self._context.get("tz", False))
            else:
                timezone = pytz.timezone("UTC")
            d_frm_obj = (
                (self.from_date)
                    # .replace(tzinfo=pytz.timezone("UTC"))
                    # .astimezone(timezone)
            )
            d_to_obj = (
                (self.to_date)
                    # .replace(tzinfo=pytz.timezone("UTC"))
                    # .astimezone(timezone)
            )
            temp_date = d_frm_obj
            while temp_date <= d_to_obj:
                val = ""
                # val = (
                #         str(temp_date.strftime("%a"))
                #         + " "
                #         + str(temp_date.strftime("%b"))
                #         + " "
                #         + str(temp_date.strftime("%d"))
                # )
                date_range_list.append(temp_date.strftime(dt))
                val = (
                        str(temp_date.strftime("%a"))
                        + " "
                        + str(temp_date.strftime("%b"))
                        + " "
                        + str(temp_date.strftime("%d"))
                )
                summary_header_list.append(val+' '+'Qty')
                temp_date = temp_date + relativedelta(months=1)

            summary_header_list.append('Total Qty')
            all_detail.append(summary_header_list)
            room_ids = room_obj.search([('company_id','=',self.env.user.company_id.id),('month','>=',str(self.from_date.month))])
            all_room_detail = []
            if room_ids:
                if self.report_type not in ('product', 'grouped'):

                    if self.partner_id:
                        if room_ids.filtered(lambda a:a.partner_id == self.partner_id):
                            room_ids = room_ids.filtered(lambda a:a.partner_id == self.partner_id)[0]
                        else:
                            room_ids={}
                    k=0
                    total = 0
                    total_qty = 0

                    for room in room_ids:

                        k = k+1

                        room_detail = {}
                        foot_detail = {}
                        room_list_stats = []
                        room_detail.update({"sno": k})
                        room_detail.update({"name": room.partner_id.name or ""})
                        # if (
                        #         not room.room_reservation_line_ids
                        #         and not room.room_line_ids
                        # ):
                        i=0
                        next_month = None
                        footer_details = []
                        for chk_date in date_range_list:
                                total_qty = 0

                                i=i+1
                                qty=0

                                total=0
                                if not next_month:
                                   # last_month = self.from_date + relativedelta(months=-i)
                                   last_month = self.from_date

                                   if self.partner_id:
                                       # qty = sum(reservation_line_obj.search(
                                       #     [('company_id','=',self.env.user.company_id.id),('partner_id', '=', self.partner_id.id), ('date', '>=', last_month),
                                       #      ('date', '<=', chk_date)]).mapped('price_units'))
                                       qty = sum(reservation_line_obj.search(
                                           [('company_id','=',self.env.user.company_id.id),('partner_id', '=', self.partner_id.id),('month','=',str(last_month.month))]).mapped('price_units'))

                                       # total_qty = sum(reservation_line_obj.search(
                                       #     [('company_id','=',self.env.user.company_id.id),('partner_id', '=', self.partner_id.id), ('date', '>=', last_month),
                                       #      ('date', '<=', chk_date)]).mapped('price_units'))
                                       total_qty = sum(reservation_line_obj.search(
                                           [('company_id','=',self.env.user.company_id.id),('partner_id', '=', self.partner_id.id),('month','=',str(last_month.month))]).mapped('price_units'))
                                       # footer_details.update({total_qty})
                                       # footer_details.append(str(total_qty))

                                       # total = sum(reservation_line_obj.search(
                                       #     [('company_id','=',self.env.user.company_id.id),('partner_id', '=', self.partner_id.id), ('date', '>=', last_month),
                                       #      ('date', '<=', self.to_date)]).mapped('price_units'))
                                       total = sum(reservation_line_obj.search(
                                           [('company_id','=',self.env.user.company_id.id),('partner_id', '=', self.partner_id.id), ('month','>=',str(last_month.month)),
                                            ('month', '<=', str(self.to_date.month))]).mapped('price_units'))
                                       room_detail.update({"total": total})
                                   else:

                                       # total = sum(reservation_line_obj.search(
                                       #     [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('date', '>=', self.from_date),
                                       #      ('date', '<=', self.to_date)]).mapped('price_units'))
                                       total = sum(reservation_line_obj.search(
                                           [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('month', '>=', str(self.from_date.month)),
                                            ('month', '<=', str(self.to_date.month))]).mapped('price_units'))
                                       # qty = sum(reservation_line_obj.search(
                                       #     [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('date', '>=', self.from_date),
                                       #      ('date', '<=',chk_date)]).mapped('price_units'))
                                       qty = sum(reservation_line_obj.search(
                                           [('company_id','=',self.env.user.company_id.id),('id', '=', room.id),('month','=',str(last_month.month))]).mapped('price_units'))


                                       room_detail.update({"total": total})
                                       total_qty = sum(reservation_line_obj.search(
                                           [('company_id','=',self.env.user.company_id.id),('month','=',str(last_month.month))]).mapped('price_units'))

                                   next_month = last_month + relativedelta(months=i)
                                else:
                                    if self.partner_id:
                                        # qty = sum(reservation_line_obj.search([('company_id','=',self.env.user.company_id.id),('partner_id','=',self.partner_id.id),('date','>=', next_month),('date','<=',chk_date)]).mapped('price_units'))
                                        qty = sum(reservation_line_obj.search([('company_id','=',self.env.user.company_id.id),('partner_id','=',self.partner_id.id),('month','=',str(next_month.month))]).mapped('price_units'))
                                        # total = sum(reservation_line_obj.search([('company_id','=',self.env.user.company_id.id),('partner_id','=',self.partner_id.id),('date','>=', self.from_date),('date','<=',self.to_date)]).mapped('price_units'))
                                        total = sum(reservation_line_obj.search([('company_id','=',self.env.user.company_id.id),('partner_id','=',self.partner_id.id),('month','>=', str(self.from_date.month)),('month','<=',str(self.to_date.month))]).mapped('price_units'))
                                        room_detail.update({"total": total})
                                        # total_qty = sum(reservation_line_obj.search(
                                        #     [('company_id','=',self.env.user.company_id.id),('partner_id', '=', self.partner_id.id), ('date', '>=', next_month),
                                        #      ('date', '<=', chk_date)]).mapped('price_units'))
                                        total_qty = sum(reservation_line_obj.search(
                                            [('company_id','=',self.env.user.company_id.id),('partner_id', '=', self.partner_id.id),('month','=',str(next_month.month))]).mapped('price_units'))
                                    else:
                                        # total = sum(reservation_line_obj.search([('company_id','=',self.env.user.company_id.id),('id','=',room.id),('date','>=', self.from_date),('date','<=',self.to_date)]).mapped('price_units'))
                                        total = sum(reservation_line_obj.search([('company_id','=',self.env.user.company_id.id),('id','=',room.id),('month','>=', str(self.from_date.month)),('month','<=',str(self.to_date.month))]).mapped('price_units'))
                                        # qty = sum(reservation_line_obj.search([('company_id','=',self.env.user.company_id.id),('id','=',room.id),('date','>=', next_month),('date','<=',chk_date)]).mapped('price_units'))
                                        qty = sum(reservation_line_obj.search([('company_id','=',self.env.user.company_id.id),('id','=',room.id),('month','=',str(next_month.month))]).mapped('price_units'))
                                        room_detail.update({"total": total})
                                        # total_qty = sum(reservation_line_obj.search(
                                        #     [('company_id','=',self.env.user.company_id.id),('date', '>=', next_month),
                                        #      ('date', '<=', chk_date)]).mapped('price_units'))
                                        total_qty = sum(reservation_line_obj.search(
                                            [('company_id','=',self.env.user.company_id.id),('month','=',str(next_month.month))]).mapped('price_units'))

                                    next_month = last_month+ relativedelta(months=i)
                                room_list_stats.append(
                                    {
                                        "state": "Free",
                                        "date": chk_date,
                                        "room_id": room.product_id.name,
                                        "qty": qty,
                                        "count": total,


                                    }
                                )
                                footer_details.append(str(total_qty))
                        print(room_detail)
                        room_detail.update({"value": room_list_stats})
                        all_room_detail.append(room_detail)

                    if not self.partner_id:
                        total_qty = sum(reservation_line_obj.search(
                            [('company_id','=',self.env.user.company_id.id),('month', '>=', str(self.from_date.month)),
                             ('month', '<=', str(self.to_date.month))]).mapped('price_units'))
                        # total_qty = sum(reservation_line_obj.search(
                        #     [('company_id','=',self.env.user.company_id.id),('month','=',str(next_month.month))]).mapped('price_units'))
                        footer_details.append(str(total_qty))
                    else:
                        footer_details.append(str(total))

                    main_header.append({"header": summary_header_list})
                    main_footer.append({"footer": footer_details})
                    self.summary_header = str(main_header)
                    self.summary_footer = str(main_footer)
                    self.room_summary = str(all_room_detail)
                if self.report_type == 'product':

                    summary_header_list.pop(1)
                    summary_header_list.insert(1,'Product Name')

                    if self.product_id:
                        if room_ids.filtered(lambda a: a.product_id == self.product_id):
                           room_ids = room_ids.filtered(lambda a: a.product_id == self.product_id)[0]
                        else:
                            room_ids ={}

                    k = 0
                    total = 0
                    total_qty = 0


                    for room in room_ids:

                        k = k + 1

                        room_detail = {}
                        foot_detail = {}
                        room_list_stats = []
                        room_detail.update({"sno": k})
                        room_detail.update({"name": room.product_id.name})
                        # if (
                        #         not room.room_reservation_line_ids
                        #         and not room.room_line_ids
                        # ):
                        i = 0
                        next_month = None
                        footer_details = []
                        for chk_date in date_range_list:
                            total_qty = 0

                            i = i + 1
                            qty = 0

                            total = 0
                            if not next_month:
                                # last_month = self.from_date + relativedelta(months=-i)
                                last_month = self.from_date

                                if self.product_id:
                                    # qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('product_id', '=', self.product_id.id), ('date', '>=', last_month),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('product_id', '=', self.product_id.id),('month','=',str(last_month.month))]).mapped('price_units'))

                                    # total_qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('product_id', '=', self.product_id.id), ('date', '>=', last_month),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    total_qty = sum(reservation_line_obj.search(
                                    [('company_id','=',self.env.user.company_id.id),('product_id', '=', self.product_id.id),('month','=',str(last_month.month))]).mapped('price_units'))
                                # footer_details.update({total_qty})
                                    # footer_details.append(str(total_qty))

                                    # total = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('product_id', '=', self.product_id.id), ('date', '>=', last_month),
                                    #      ('date', '<=', self.to_date)]).mapped('price_units'))
                                    total = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('product_id', '=', self.product_id.id), ('month', '>=', str(last_month.month)),
                                         ('month', '<=', str(self.to_date.month))]).mapped('price_units'))
                                    room_detail.update({"total": total})
                                else:

                                    # total = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('date', '>=', self.from_date),
                                    #      ('date', '<=', self.to_date)]).mapped('price_units'))
                                    total = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('month', '>=', str(self.from_date.month)),
                                         ('month', '<=', str(self.to_date.month))]).mapped('price_units'))
                                    # qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('date', '>=', self.from_date),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('id', '=', room.id),('month','=',str(last_month.month))]).mapped('price_units'))
                                    room_detail.update({"total": total})
                                    # total_qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('date', '>=', self.from_date),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    total_qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('month','=',str(last_month.month))]).mapped('price_units'))

                                next_month = last_month + relativedelta(months=i)
                            else:
                                if self.product_id:
                                    # qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('product_id', '=', self.product_id.id), ('date', '>=', next_month),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('product_id', '=', self.product_id.id),('month','=',str(next_month.month))]).mapped('price_units'))
                                    # total = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('product_id', '=', self.product_id.id), ('date', '>=', self.from_date),
                                    #      ('date', '<=', self.to_date)]).mapped('price_units'))
                                    total = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('product_id', '=', self.product_id.id), ('month', '>=', str(self.from_date.month)),
                                         ('month', '<=', str(self.to_date.month))]).mapped('price_units'))
                                    room_detail.update({"total": total})
                                    # total_qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('product_id', '=', self.product_id.id), ('date', '>=', next_month),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    total_qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('product_id', '=', self.product_id.id),('month','=',str(next_month.month))]).mapped('price_units'))
                                else:
                                    # total = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('date', '>=', self.from_date),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    total = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('month', '>=', str(self.from_date.month)),
                                         ('month','=',str(next_month.month))]).mapped('price_units'))
                                    # qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('date', '>=', next_month),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('id', '=', room.id),('month','=',str(next_month.month))]).mapped('price_units'))
                                    room_detail.update({"total": total})
                                    # total_qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('date', '>=', next_month),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    total_qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('month','=',str(next_month.month))]).mapped('price_units'))
                                next_month = last_month + relativedelta(months=i)
                            room_list_stats.append(
                                {
                                    "state": "Free",
                                    "date": chk_date,
                                    "room_id": room.product_id.name,
                                    "qty": qty,
                                    "count": total,

                                }
                            )
                            footer_details.append(str(total_qty))
                        print(room_detail)
                        room_detail.update({"value": room_list_stats})
                        all_room_detail.append(room_detail)

                    if not self.product_id:
                        total_qty = sum(reservation_line_obj.search(
                            [('company_id','=',self.env.user.company_id.id),('month', '>=', str(self.from_date.month)),
                             ('month', '<=', str(self.to_date.month))]).mapped('price_units'))
                        footer_details.append(str(total_qty))
                    else:
                        footer_details.append(str(total))

                    main_header.append({"header": summary_header_list})
                    main_footer.append({"footer": footer_details})
                    self.summary_header = str(main_header)
                    self.summary_footer = str(main_footer)
                    self.room_summary = str(all_room_detail)
                if self.report_type == 'grouped':

                    summary_header_list.pop(1)
                    summary_header_list.insert(1,'Group Name')

                    if self.product_group:
                        # if each_coll.product_id.parent_id == self.product_groups:
                        if room_ids.filtered(lambda a: a.product_id.parent_id == self.product_group):
                            room_ids = room_ids.filtered(lambda a: a.product_id.parent_id == self.product_group)[0]
                        else:
                            room_ids = {}
                    k = 0
                    total = 0
                    total_qty = 0

                    for room in room_ids:

                        k = k + 1

                        room_detail = {}
                        foot_detail = {}
                        room_list_stats = []
                        room_detail.update({"sno": k})
                        if self.product_group:
                            room_detail.update({"name": self.product_group.name})
                        else:
                            room_detail.update({"name": room.product_id.parent_id.name})
                        # if (
                        #         not room.room_reservation_line_ids
                        #         and not room.room_line_ids
                        # ):
                        i = 0
                        next_month = None
                        footer_details = []
                        for chk_date in date_range_list:
                            total_qty = 0

                            i = i + 1
                            qty = 0

                            total = 0
                            if not next_month:
                                # last_month = self.from_date + relativedelta(months=-i)
                                last_month = self.from_date

                                if self.product_group:
                                    # qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('date', '>=', last_month),
                                    #      ('date', '<=', chk_date)]).filtered(lambda a: a.product_id.parent_id == self.product_group).mapped('price_units'))
                                    qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('month','=',str(last_month.month))]).filtered(lambda a: a.product_id.parent_id == self.product_group).mapped('price_units'))

                                    # total_qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('date', '>=', last_month),
                                    #      ('date', '<=', chk_date)]).filtered(lambda a: a.product_id.parent_id == self.product_group).mapped('price_units'))
                                    total_qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('month','=',str(last_month.month))]).filtered(lambda a: a.product_id.parent_id == self.product_group).mapped('price_units'))
                                    # footer_details.update({total_qty})
                                    # footer_details.append(str(total_qty))

                                    # total = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('date', '>=', last_month),
                                    #      ('date', '<=', self.to_date)]).filtered(lambda a: a.product_id.parent_id == self.product_group).mapped('price_units'))
                                    total = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('month', '>=', str(last_month.month)),
                                         ('month', '<=', str(self.to_date.month))]).filtered(lambda a: a.product_id.parent_id == self.product_group).mapped('price_units'))
                                    room_detail.update({"total": total})
                                else:
                                    #
                                    # total = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('date', '>=', self.from_date),
                                    #      ('date', '<=', self.to_date)]).mapped('price_units'))
                                    total = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('month', '>=', str(self.from_date.month)),
                                         ('month', '<=', str(self.to_date.month))]).mapped('price_units'))
                                    # qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('date', '>=', self.from_date),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('id', '=', room.id),('month','=',str(last_month.month))]).mapped('price_units'))
                                    room_detail.update({"total": total})
                                    # total_qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('date', '>=',self.from_date),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    total_qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('month','=',str(last_month.month))]).mapped('price_units'))

                                next_month = last_month+ relativedelta(months=i)
                            else:
                                if self.product_group:
                                    # reservation_line_obj.search(
                                    #     [('date', '>=', last_month), ('date', '<=', chk_date)]).filtered(lambda a: a.product_id.parent_id == self.product_groups)
                                    # qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('date', '>=', next_month),
                                    #      ('date', '<=', chk_date)]).filtered(lambda a: a.product_id.parent_id == self.product_group).mapped('price_units'))
                                    qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('month','=',str(next_month.month))]).filtered(lambda a: a.product_id.parent_id == self.product_group).mapped('price_units'))
                                    # total = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('date', '>=', self.from_date),
                                    #      ('date', '<=', self.to_date)]).filtered(lambda a: a.product_id.parent_id == self.product_group).mapped('price_units'))
                                    total = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('month', '>=', str(self.from_date.month)),
                                         ('month', '<=', str(self.to_date.month))]).filtered(lambda a: a.product_id.parent_id == self.product_group).mapped('price_units'))
                                    room_detail.update({"total": total})
                                    # total_qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('date', '>=', next_month),
                                    #      ('date', '<=', chk_date)]).filtered(lambda a: a.product_id.parent_id == self.product_group).mapped('price_units'))
                                    total_qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('month','=',str(next_month.month))]).filtered(lambda a: a.product_id.parent_id == self.product_group).mapped('price_units'))
                                else:
                                    # total = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('date', '>=', self.from_date),
                                    #      ('date', '<=', self.to_date)]).mapped('price_units'))
                                    total = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('month', '>=', str(self.from_date.month)),
                                         ('month', '<=', str(self.to_date.month))]).mapped('price_units'))
                                    # qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('id', '=', room.id), ('date', '>=', next_month),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('id', '=', room.id),('month','=',str(next_month.month))]).mapped('price_units'))
                                    room_detail.update({"total": total})
                                    # total_qty = sum(reservation_line_obj.search(
                                    #     [('company_id','=',self.env.user.company_id.id),('date', '>=', next_month),
                                    #      ('date', '<=', chk_date)]).mapped('price_units'))
                                    total_qty = sum(reservation_line_obj.search(
                                        [('company_id','=',self.env.user.company_id.id),('month','=',str(next_month.month))]).mapped('price_units'))
                                next_month = last_month + relativedelta(months=i)
                            room_list_stats.append(
                                {
                                    "state": "Free",
                                    "date": chk_date,
                                    "room_id": room.product_id.name,
                                    "qty": qty,
                                    "count": total,

                                }
                            )
                            footer_details.append(str(total_qty))
                        print(room_detail)
                        room_detail.update({"value": room_list_stats})
                        all_room_detail.append(room_detail)

                    if not self.product_group:
                        total_qty = sum(reservation_line_obj.search(
                            [('company_id','=',self.env.user.company_id.id),('month', '>=', str(self.from_date.month)),
                             ('month', '<=', str(self.to_date.month))]).mapped('price_units'))
                        footer_details.append(str(total_qty))
                    else:
                        footer_details.append(str(total))

                    main_header.append({"header": summary_header_list})
                    main_footer.append({"footer": footer_details})
                    self.summary_header = str(main_header)
                    self.summary_footer = str(main_footer)
                    self.room_summary = str(all_room_detail)
            else:
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
                    'sale.report.custom') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('sale.report.custom') or _('New')
        return super(SalesReportComp, self).create(vals)

    @api.onchange('from_date', 'product_categ', 'product_groups', 'product_ids', 'product_type', 'style', 'month',
                  'product_group', 'product_id', 'to_date', 'report_type', 'area', 'partner_id', 'vehicle_id')
    def onchange_form_date(self):
        if self.style != 'monthly':

            self.report_lines = False
            if self.report_type == 'area':
                self.report_lines = False
                if self.area:
                    if self.product_groups and not self.product_ids and not self.product_categ:

                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('company_id', '=', 1), ('area', '=', self.area.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.parent_id == self.product_groups:
                                product_line = (0, 0, {
                                    'date': each_coll.date,
                                    'address': each_coll.address,
                                    'invoice_id': each_coll.invoice_id.id,
                                    'partner_id': each_coll.partner_id.id,
                                    'product_id': each_coll.product_id.id,
                                    'company_id': each_coll.company_id.id,
                                    'price_units': each_coll.price_units,
                                    'uom': each_coll.uom.id,
                                    'rate': each_coll.rate,
                                    'credit': each_coll.credit,
                                    'area': each_coll.area.id,
                                    'debit': each_coll.debit,
                                    'description': each_coll.description,
                                    'account_journal': each_coll.account_journal.id,
                                    'account': each_coll.account.id,
                                    'paid_date': each_coll.paid_date

                                })
                                today_total_cheques.append(product_line)
                    elif self.product_ids and not self.product_categ and not self.product_groups:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('product_id', '=', self.product_ids.id), ('company_id', '=', 1),
                                 ('area', '=', self.area.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'address': each_coll.address,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)
                    elif self.product_categ and not self.product_ids and not self.product_groups:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('company_id', '=', 1), ('area', '=', self.area.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.categ_id == self.product_categ:
                                product_line = (0, 0, {
                                    'date': each_coll.date,
                                    'address': each_coll.address,
                                    'invoice_id': each_coll.invoice_id.id,
                                    'partner_id': each_coll.partner_id.id,
                                    'product_id': each_coll.product_id.id,
                                    'company_id': each_coll.company_id.id,
                                    'price_units': each_coll.price_units,
                                    'uom': each_coll.uom.id,
                                    'rate': each_coll.rate,
                                    'credit': each_coll.credit,
                                    'area': each_coll.area.id,
                                    'debit': each_coll.debit,
                                    'description': each_coll.description,
                                    'account_journal': each_coll.account_journal.id,
                                    'account': each_coll.account.id,
                                    'paid_date': each_coll.paid_date

                                })
                                today_total_cheques.append(product_line)
                    elif self.product_groups and self.product_categ and not self.product_ids:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('company_id', '=', 1), ('area', '=', self.area.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.parent_id == self.product_groups:
                                if each_coll.product_id.categ_id == self.product_categ:
                                    product_line = (0, 0, {
                                        'date': each_coll.date,
                                        'address': each_coll.address,
                                        'invoice_id': each_coll.invoice_id.id,
                                        'partner_id': each_coll.partner_id.id,
                                        'product_id': each_coll.product_id.id,
                                        'company_id': each_coll.company_id.id,
                                        'price_units': each_coll.price_units,
                                        'uom': each_coll.uom.id,
                                        'rate': each_coll.rate,
                                        'credit': each_coll.credit,
                                        'area': each_coll.area.id,
                                        'debit': each_coll.debit,
                                        'description': each_coll.description,
                                        'account_journal': each_coll.account_journal.id,
                                        'account': each_coll.account.id,
                                        'paid_date': each_coll.paid_date

                                    })
                                    today_total_cheques.append(product_line)
                    elif self.product_groups and self.product_categ and self.product_ids:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('product_id', '=', self.product_ids.id), ('company_id', '=', 1),
                                 ('area', '=', self.area.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.parent_id == self.product_groups:
                                if each_coll.product_id.categ_id == self.product_categ:
                                    product_line = (0, 0, {
                                        'date': each_coll.date,
                                        'address': each_coll.address,
                                        'invoice_id': each_coll.invoice_id.id,
                                        'partner_id': each_coll.partner_id.id,
                                        'product_id': each_coll.product_id.id,
                                        'company_id': each_coll.company_id.id,
                                        'price_units': each_coll.price_units,
                                        'uom': each_coll.uom.id,
                                        'rate': each_coll.rate,
                                        'credit': each_coll.credit,
                                        'area': each_coll.area.id,
                                        'debit': each_coll.debit,
                                        'description': each_coll.description,
                                        'account_journal': each_coll.account_journal.id,
                                        'account': each_coll.account.id,
                                        'paid_date': each_coll.paid_date

                                    })
                                    today_total_cheques.append(product_line)
                    elif self.product_groups and not self.product_categ and self.product_ids:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('product_id', '=', self.product_ids.id), ('company_id', '=', 1),
                                 ('area', '=', self.area.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.parent_id == self.product_groups:
                                product_line = (0, 0, {
                                    'date': each_coll.date,
                                    'address': each_coll.address,
                                    'invoice_id': each_coll.invoice_id.id,
                                    'partner_id': each_coll.partner_id.id,
                                    'product_id': each_coll.product_id.id,
                                    'company_id': each_coll.company_id.id,
                                    'price_units': each_coll.price_units,
                                    'uom': each_coll.uom.id,
                                    'rate': each_coll.rate,
                                    'credit': each_coll.credit,
                                    'area': each_coll.area.id,
                                    'debit': each_coll.debit,
                                    'description': each_coll.description,
                                    'account_journal': each_coll.account_journal.id,
                                    'account': each_coll.account.id,
                                    'paid_date': each_coll.paid_date

                                })
                                today_total_cheques.append(product_line)




                    else:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('company_id', '=', 1), ('area', '=', self.area.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'address': each_coll.address,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)

                else:
                    today_total_cheques = []
                    for each_coll in self.env['partner.ledgers.customer'].search(
                            [('company_id', '=', 1), ('date', '>=', self.from_date),
                             ('date', '<=', self.to_date)]):
                        product_line = (0, 0, {
                            'date': each_coll.date,
                            'invoice_id': each_coll.invoice_id.id,
                            'address': each_coll.address,
                            'partner_id': each_coll.partner_id.id,
                            'product_id': each_coll.product_id.id,
                            'company_id': each_coll.company_id.id,
                            'price_units': each_coll.price_units,
                            'uom': each_coll.uom.id,
                            'rate': each_coll.rate,
                            'credit': each_coll.credit,
                            'area': each_coll.area.id,
                            'debit': each_coll.debit,
                            'description': each_coll.description,
                            'account_journal': each_coll.account_journal.id,
                            'account': each_coll.account.id,
                            'paid_date': each_coll.paid_date

                        })
                        today_total_cheques.append(product_line)
                self.report_lines = today_total_cheques
            if self.report_type == 'partner':
                self.report_lines = False
                if self.partner_id:
                    if self.product_groups and not self.product_ids and not self.product_categ:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('company_id', '=', 1), ('partner_id', '=', self.partner_id.id),
                                 ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.parent_id == self.product_groups:
                                product_line = (0, 0, {
                                    'date': each_coll.date,
                                    'address': each_coll.address,
                                    'invoice_id': each_coll.invoice_id.id,
                                    'partner_id': each_coll.partner_id.id,
                                    'product_id': each_coll.product_id.id,
                                    'company_id': each_coll.company_id.id,
                                    'price_units': each_coll.price_units,
                                    'uom': each_coll.uom.id,
                                    'rate': each_coll.rate,
                                    'credit': each_coll.credit,
                                    'area': each_coll.area.id,
                                    'debit': each_coll.debit,
                                    'description': each_coll.description,
                                    'account_journal': each_coll.account_journal.id,
                                    'account': each_coll.account.id,
                                    'paid_date': each_coll.paid_date

                                })
                                today_total_cheques.append(product_line)
                    elif self.product_ids and not self.product_categ and not self.product_groups:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('product_id', '=', self.product_ids.id), ('company_id', '=', 1),
                                 ('partner_id', '=', self.partner_id.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'address': each_coll.address,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)
                    elif self.product_categ and not self.product_ids and not self.product_groups:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('company_id', '=', 1), ('partner_id', '=', self.partner_id.id),
                                 ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.categ_id == self.product_categ:
                                product_line = (0, 0, {
                                    'date': each_coll.date,
                                    'address': each_coll.address,
                                    'invoice_id': each_coll.invoice_id.id,
                                    'partner_id': each_coll.partner_id.id,
                                    'product_id': each_coll.product_id.id,
                                    'company_id': each_coll.company_id.id,
                                    'price_units': each_coll.price_units,
                                    'uom': each_coll.uom.id,
                                    'rate': each_coll.rate,
                                    'credit': each_coll.credit,
                                    'area': each_coll.area.id,
                                    'debit': each_coll.debit,
                                    'description': each_coll.description,
                                    'account_journal': each_coll.account_journal.id,
                                    'account': each_coll.account.id,
                                    'paid_date': each_coll.paid_date

                                })
                                today_total_cheques.append(product_line)
                    elif self.product_groups and self.product_categ and not self.product_ids:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('company_id', '=', 1), ('partner_id', '=', self.partner_id.id),
                                 ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.parent_id == self.product_groups:
                                if each_coll.product_id.categ_id == self.product_categ:
                                    product_line = (0, 0, {
                                        'date': each_coll.date,
                                        'address': each_coll.address,
                                        'invoice_id': each_coll.invoice_id.id,
                                        'partner_id': each_coll.partner_id.id,
                                        'product_id': each_coll.product_id.id,
                                        'company_id': each_coll.company_id.id,
                                        'price_units': each_coll.price_units,
                                        'uom': each_coll.uom.id,
                                        'rate': each_coll.rate,
                                        'credit': each_coll.credit,
                                        'area': each_coll.area.id,
                                        'debit': each_coll.debit,
                                        'description': each_coll.description,
                                        'account_journal': each_coll.account_journal.id,
                                        'account': each_coll.account.id,
                                        'paid_date': each_coll.paid_date

                                    })
                                    today_total_cheques.append(product_line)
                    elif self.product_groups and self.product_categ and self.product_ids:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('product_id', '=', self.product_ids.id), ('company_id', '=', 1),
                                 ('partner_id', '=', self.partner_id.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.parent_id == self.product_groups:
                                if each_coll.product_id.categ_id == self.product_categ:
                                    product_line = (0, 0, {
                                        'date': each_coll.date,
                                        'address': each_coll.address,
                                        'invoice_id': each_coll.invoice_id.id,
                                        'partner_id': each_coll.partner_id.id,
                                        'product_id': each_coll.product_id.id,
                                        'company_id': each_coll.company_id.id,
                                        'price_units': each_coll.price_units,
                                        'uom': each_coll.uom.id,
                                        'rate': each_coll.rate,
                                        'credit': each_coll.credit,
                                        'area': each_coll.area.id,
                                        'debit': each_coll.debit,
                                        'description': each_coll.description,
                                        'account_journal': each_coll.account_journal.id,
                                        'account': each_coll.account.id,
                                        'paid_date': each_coll.paid_date

                                    })
                                    today_total_cheques.append(product_line)
                    elif self.product_groups and not self.product_categ and self.product_ids:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('product_id', '=', self.product_ids.id), ('company_id', '=', 1),
                                 ('partner_id', '=', self.partner_id.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.parent_id == self.product_groups:
                                product_line = (0, 0, {
                                    'date': each_coll.date,
                                    'address': each_coll.address,
                                    'invoice_id': each_coll.invoice_id.id,
                                    'partner_id': each_coll.partner_id.id,
                                    'product_id': each_coll.product_id.id,
                                    'company_id': each_coll.company_id.id,
                                    'price_units': each_coll.price_units,
                                    'uom': each_coll.uom.id,
                                    'rate': each_coll.rate,
                                    'credit': each_coll.credit,
                                    'area': each_coll.area.id,
                                    'debit': each_coll.debit,
                                    'description': each_coll.description,
                                    'account_journal': each_coll.account_journal.id,
                                    'account': each_coll.account.id,
                                    'paid_date': each_coll.paid_date

                                })
                                today_total_cheques.append(product_line)



                    else:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('company_id', '=', 1), ('partner_id', '=', self.partner_id.id),
                                 ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'address': each_coll.address,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)
                else:
                    today_total_cheques = []
                    for each_coll in self.env['partner.ledgers.customer'].search(
                            [('company_id', '=', 1), ('date', '>=', self.from_date),
                             ('date', '<=', self.to_date)]):
                        product_line = (0, 0, {
                            'date': each_coll.date,
                            'invoice_id': each_coll.invoice_id.id,
                            'partner_id': each_coll.partner_id.id,
                            'product_id': each_coll.product_id.id,
                            'company_id': each_coll.company_id.id,
                            'price_units': each_coll.price_units,
                            'address': each_coll.address,
                            'uom': each_coll.uom.id,
                            'rate': each_coll.rate,
                            'credit': each_coll.credit,
                            'area': each_coll.area.id,
                            'debit': each_coll.debit,
                            'description': each_coll.description,
                            'account_journal': each_coll.account_journal.id,
                            'account': each_coll.account.id,
                            'paid_date': each_coll.paid_date

                        })
                        today_total_cheques.append(product_line)
                self.report_lines = today_total_cheques
            if self.report_type == 'vehicle':
                self.report_lines = False
                if self.vehicle_id:
                    if self.product_groups and not self.product_ids and not self.product_categ:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('company_id', '=', 1), ('vehicle_id', '=', self.vehicle_id.id),
                                 ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.parent_id == self.product_groups:
                                product_line = (0, 0, {
                                    'date': each_coll.date,
                                    'address': each_coll.address,
                                    'invoice_id': each_coll.invoice_id.id,
                                    'partner_id': each_coll.partner_id.id,
                                    'product_id': each_coll.product_id.id,
                                    'company_id': each_coll.company_id.id,
                                    'price_units': each_coll.price_units,
                                    'uom': each_coll.uom.id,
                                    'rate': each_coll.rate,
                                    'credit': each_coll.credit,
                                    'area': each_coll.area.id,
                                    'debit': each_coll.debit,
                                    'description': each_coll.description,
                                    'account_journal': each_coll.account_journal.id,
                                    'account': each_coll.account.id,
                                    'paid_date': each_coll.paid_date

                                })
                                today_total_cheques.append(product_line)
                    elif self.product_ids and not self.product_categ and not self.product_groups:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('product_id', '=', self.product_ids.id), ('company_id', '=', 1),
                                 ('vehicle_id', '=', self.vehicle_id.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'address': each_coll.address,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)
                    elif self.product_categ and not self.product_ids and not self.product_groups:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('company_id', '=', 1), ('vehicle_id', '=', self.vehicle_id.id),
                                 ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.categ_id == self.product_categ:
                                product_line = (0, 0, {
                                    'date': each_coll.date,
                                    'address': each_coll.address,
                                    'invoice_id': each_coll.invoice_id.id,
                                    'partner_id': each_coll.partner_id.id,
                                    'product_id': each_coll.product_id.id,
                                    'company_id': each_coll.company_id.id,
                                    'price_units': each_coll.price_units,
                                    'uom': each_coll.uom.id,
                                    'rate': each_coll.rate,
                                    'credit': each_coll.credit,
                                    'area': each_coll.area.id,
                                    'debit': each_coll.debit,
                                    'description': each_coll.description,
                                    'account_journal': each_coll.account_journal.id,
                                    'account': each_coll.account.id,
                                    'paid_date': each_coll.paid_date

                                })
                                today_total_cheques.append(product_line)
                    elif self.product_groups and self.product_categ and not self.product_ids:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('company_id', '=', 1), ('vehicle_id', '=', self.vehicle_id.id),
                                 ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.parent_id == self.product_groups:
                                if each_coll.product_id.categ_id == self.product_categ:
                                    product_line = (0, 0, {
                                        'date': each_coll.date,
                                        'address': each_coll.address,
                                        'invoice_id': each_coll.invoice_id.id,
                                        'partner_id': each_coll.partner_id.id,
                                        'product_id': each_coll.product_id.id,
                                        'company_id': each_coll.company_id.id,
                                        'price_units': each_coll.price_units,
                                        'uom': each_coll.uom.id,
                                        'rate': each_coll.rate,
                                        'credit': each_coll.credit,
                                        'area': each_coll.area.id,
                                        'debit': each_coll.debit,
                                        'description': each_coll.description,
                                        'account_journal': each_coll.account_journal.id,
                                        'account': each_coll.account.id,
                                        'paid_date': each_coll.paid_date

                                    })
                                    today_total_cheques.append(product_line)
                    elif self.product_groups and self.product_categ and self.product_ids:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('product_id', '=', self.product_ids.id), ('company_id', '=', 1),
                                 ('vehicle_id', '=', self.vehicle_id.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.parent_id == self.product_groups:
                                if each_coll.product_id.categ_id == self.product_categ:
                                    product_line = (0, 0, {
                                        'date': each_coll.date,
                                        'address': each_coll.address,
                                        'invoice_id': each_coll.invoice_id.id,
                                        'partner_id': each_coll.partner_id.id,
                                        'product_id': each_coll.product_id.id,
                                        'company_id': each_coll.company_id.id,
                                        'price_units': each_coll.price_units,
                                        'uom': each_coll.uom.id,
                                        'rate': each_coll.rate,
                                        'credit': each_coll.credit,
                                        'area': each_coll.area.id,
                                        'debit': each_coll.debit,
                                        'description': each_coll.description,
                                        'account_journal': each_coll.account_journal.id,
                                        'account': each_coll.account.id,
                                        'paid_date': each_coll.paid_date

                                    })
                                    today_total_cheques.append(product_line)
                    elif self.product_groups and not self.product_categ and self.product_ids:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('product_id', '=', self.product_ids.id), ('company_id', '=', 1),
                                 ('vehicle_id', '=', self.vehicle_id.id), ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            if each_coll.product_id.parent_id == self.product_groups:
                                product_line = (0, 0, {
                                    'date': each_coll.date,
                                    'address': each_coll.address,
                                    'invoice_id': each_coll.invoice_id.id,
                                    'partner_id': each_coll.partner_id.id,
                                    'product_id': each_coll.product_id.id,
                                    'company_id': each_coll.company_id.id,
                                    'price_units': each_coll.price_units,
                                    'uom': each_coll.uom.id,
                                    'rate': each_coll.rate,
                                    'credit': each_coll.credit,
                                    'area': each_coll.area.id,
                                    'debit': each_coll.debit,
                                    'description': each_coll.description,
                                    'account_journal': each_coll.account_journal.id,
                                    'account': each_coll.account.id,
                                    'paid_date': each_coll.paid_date

                                })
                                today_total_cheques.append(product_line)

                    else:
                        today_total_cheques = []
                        for each_coll in self.env['partner.ledgers.customer'].search(
                                [('company_id', '=', 1), ('vehicle_id', '=', self.vehicle_id.id),
                                 ('date', '>=', self.from_date),
                                 ('date', '<=', self.to_date)]):
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'address': each_coll.address,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)
                else:
                    today_total_cheques = []
                    for each_coll in self.env['partner.ledgers.customer'].search(
                            [('company_id', '=', 1), ('date', '>=', self.from_date),
                             ('date', '<=', self.to_date)]):
                        product_line = (0, 0, {
                            'date': each_coll.date,
                            'invoice_id': each_coll.invoice_id.id,
                            'partner_id': each_coll.partner_id.id,
                            'product_id': each_coll.product_id.id,
                            'company_id': each_coll.company_id.id,
                            'price_units': each_coll.price_units,
                            'uom': each_coll.uom.id,
                            'address': each_coll.address,
                            'rate': each_coll.rate,
                            'credit': each_coll.credit,
                            'area': each_coll.area.id,
                            'debit': each_coll.debit,
                            'description': each_coll.description,
                            'account_journal': each_coll.account_journal.id,
                            'account': each_coll.account.id,
                            'paid_date': each_coll.paid_date

                        })
                        today_total_cheques.append(product_line)

                self.report_lines = today_total_cheques
            if self.report_type == 'product':
                self.report_lines = False
                if self.product_id:
                    today_total_cheques = []
                    for each_coll in self.env['partner.ledgers.customer'].search(
                            [('company_id', '=', 1), ('product_id', '=', self.product_id.id),
                             ('date', '>=', self.from_date),
                             ('date', '<=', self.to_date)]):
                        product_line = (0, 0, {
                            'date': each_coll.date,
                            'invoice_id': each_coll.invoice_id.id,
                            'partner_id': each_coll.partner_id.id,
                            'product_id': each_coll.product_id.id,
                            'company_id': each_coll.company_id.id,
                            'price_units': each_coll.price_units,
                            'uom': each_coll.uom.id,
                            'address': each_coll.address,
                            'rate': each_coll.rate,
                            'credit': each_coll.credit,
                            'area': each_coll.area.id,
                            'debit': each_coll.debit,
                            'description': each_coll.description,
                            'account_journal': each_coll.account_journal.id,
                            'account': each_coll.account.id,
                            'paid_date': each_coll.paid_date

                        })
                        today_total_cheques.append(product_line)
                else:
                    today_total_cheques = []
                    for each_coll in self.env['partner.ledgers.customer'].search(
                            [('company_id', '=', 1), ('date', '>=', self.from_date),
                             ('date', '<=', self.to_date)]):
                        product_line = (0, 0, {
                            'date': each_coll.date,
                            'invoice_id': each_coll.invoice_id.id,
                            'partner_id': each_coll.partner_id.id,
                            'product_id': each_coll.product_id.id,
                            'company_id': each_coll.company_id.id,
                            'price_units': each_coll.price_units,
                            'uom': each_coll.uom.id,
                            'address': each_coll.address,
                            'rate': each_coll.rate,
                            'credit': each_coll.credit,
                            'area': each_coll.area.id,
                            'debit': each_coll.debit,
                            'description': each_coll.description,
                            'account_journal': each_coll.account_journal.id,
                            'account': each_coll.account.id,
                            'paid_date': each_coll.paid_date

                        })
                        today_total_cheques.append(product_line)

                self.report_lines = today_total_cheques
            if self.report_type == 'grouped':
                self.report_lines = False
                if self.product_group:
                    today_total_cheques = []
                    for each_coll in self.env['partner.ledgers.customer'].search(
                            [('company_id', '=', 1), ('date', '>=', self.from_date),
                             ('date', '<=', self.to_date)]):
                        if each_coll.product_id.parent_id == self.product_group:
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'invoice_id': each_coll.invoice_id.id,
                                'address': each_coll.address,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)
                else:
                    today_total_cheques = []
                    for each_coll in self.env['partner.ledgers.customer'].search(
                            [('company_id', '=', 1), ('date', '>=', self.from_date),
                             ('date', '<=', self.to_date)]):
                        product_line = (0, 0, {
                            'date': each_coll.date,
                            'invoice_id': each_coll.invoice_id.id,
                            'partner_id': each_coll.partner_id.id,
                            'product_id': each_coll.product_id.id,
                            'company_id': each_coll.company_id.id,
                            'address': each_coll.address,
                            'price_units': each_coll.price_units,
                            'uom': each_coll.uom.id,
                            'rate': each_coll.rate,
                            'credit': each_coll.credit,
                            'area': each_coll.area.id,
                            'debit': each_coll.debit,
                            'description': each_coll.description,
                            'account_journal': each_coll.account_journal.id,
                            'account': each_coll.account.id,
                            'paid_date': each_coll.paid_date

                        })
                        today_total_cheques.append(product_line)

                self.report_lines = today_total_cheques
        else:
            self.report_lines = False
            all = self.env['partner.ledgers.customer'].search([('company_id', '=', 1)]).filtered(
                lambda a: a.month == self.month)
            if all:
                if self.report_type == 'area':
                    self.report_lines = False
                    if self.area:
                        today_total_cheques = []
                        self.report_lines = False
                        for each_coll in all.filtered(lambda a: a.area == self.area):
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'address': each_coll.address,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)
                    else:
                        self.report_lines = False
                        today_total_cheques = []
                        for each_coll in all:
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'address': each_coll.address,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)
                    self.report_lines = today_total_cheques
                if self.report_type == 'partner':
                    self.report_lines = False
                    if self.partner_id:
                        self.report_lines = False
                        today_total_cheques = []
                        for each_coll in all.filtered(lambda a: a.partner_id == self.partner_id):
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'debit': each_coll.debit,
                                'address': each_coll.address,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)
                    else:
                        today_total_cheques = []
                        self.report_lines = False
                        for each_coll in all:
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'address': each_coll.address,
                                'area': each_coll.area.id,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)
                    self.report_lines = today_total_cheques
                if self.report_type == 'vehicle':
                    self.report_lines = False
                    if self.vehicle_id:
                        self.report_lines = False
                        today_total_cheques = []
                        for each_coll in all.filtered(lambda a: a.vehicle_id == self.vehicle_id):
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'address': each_coll.address,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)
                    else:
                        today_total_cheques = []
                        self.report_lines = False
                        for each_coll in all:
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'address': each_coll.address,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)

                    self.report_lines = today_total_cheques
                if self.report_type == 'grouped':
                    self.report_lines = False
                    if self.product_group:
                        self.report_lines = False
                        today_total_cheques = []
                        for each_coll in all:
                            if each_coll.product_id.parent_id == self.product_group:
                                product_line = (0, 0, {
                                    'date': each_coll.date,
                                    'invoice_id': each_coll.invoice_id.id,
                                    'partner_id': each_coll.partner_id.id,
                                    'product_id': each_coll.product_id.id,
                                    'company_id': each_coll.company_id.id,
                                    'price_units': each_coll.price_units,
                                    'uom': each_coll.uom.id,
                                    'rate': each_coll.rate,
                                    'credit': each_coll.credit,
                                    'area': each_coll.area.id,
                                    'address': each_coll.address,
                                    'debit': each_coll.debit,
                                    'description': each_coll.description,
                                    'account_journal': each_coll.account_journal.id,
                                    'account': each_coll.account.id,
                                    'paid_date': each_coll.paid_date

                                })
                                today_total_cheques.append(product_line)
                    else:
                        today_total_cheques = []
                        self.report_lines = False
                        for each_coll in all:
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'address': each_coll.address,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)

                    self.report_lines = today_total_cheques
                if self.report_type == 'product':
                    self.report_lines = False
                    if self.product_id:
                        self.report_lines = False
                        today_total_cheques = []
                        for each_coll in all.filtered(lambda a: a.product_id == self.product_id):
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'address': each_coll.address,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)
                    else:
                        today_total_cheques = []
                        self.report_lines = False
                        for each_coll in all:
                            product_line = (0, 0, {
                                'date': each_coll.date,
                                'invoice_id': each_coll.invoice_id.id,
                                'partner_id': each_coll.partner_id.id,
                                'product_id': each_coll.product_id.id,
                                'company_id': each_coll.company_id.id,
                                'price_units': each_coll.price_units,
                                'uom': each_coll.uom.id,
                                'rate': each_coll.rate,
                                'credit': each_coll.credit,
                                'area': each_coll.area.id,
                                'address': each_coll.address,
                                'debit': each_coll.debit,
                                'description': each_coll.description,
                                'account_journal': each_coll.account_journal.id,
                                'account': each_coll.account.id,
                                'paid_date': each_coll.paid_date

                            })
                            today_total_cheques.append(product_line)

                    self.report_lines = today_total_cheques

    # @api.multi
    def action_cheque_statement(self):

        return self.env.ref('ezp_cash_collection.executive_cheque_collection_id1').report_action(self)

    @api.onchange('report_type')
    def onchange_report_type(self):
        self.product_ids = False
        self.area = False
        self.partner_id = False
        self.vehicle_id = False
        self.product_categ = False
        self.product_groups = False


class SalesReportCompLine(models.Model):
    _name = "sale.report.custom.line"
    _description = "Sales Report Line"

    report_line = fields.Many2one('sale.report.custom')
    date = fields.Date('Date')
    paid_date = fields.Date('Paid Date')
    address = fields.Text('Address')
    executive_area = fields.Many2one('executive.area.wise', string='Executive Area')
    area = fields.Many2one('area.wise', string='Area')
    account = fields.Many2one('account.account')
    account_journal = fields.Many2one('account.journal')
    invoice_id = fields.Many2one('account.move', string='Invoice No')
    product_id = fields.Many2one('product.product', string='Product Name')
    partner_id = fields.Many2one('res.partner', string='Partner')
    company_id = fields.Many2one('res.company', string='company')
    vehicle_id = fields.Many2one('fleet.vehicle')
    in_vehicle_id = fields.Char('Invoice Vehicle')
    transport_receipt = fields.Char('Transport Rec')
    gate_pass = fields.Char('Gate Pass')
    description = fields.Text(string='Description')
    uom = fields.Many2one('uom.uom', string='UoM')
    price_units = fields.Float('Unit')
    rate = fields.Float('Rate')
    debit = fields.Float('Debit')
    credit = fields.Float('Credit')
    balance = fields.Float('Balance')


class RtgsNeftCollections(models.Model):
    _name = "neft.rtgs.collection"
    _description = "Neft Collection"
    _order = "id desc"

    def default_payment_method_id(self):
        return self.env['account.payment.method'].search([('code', '=', 'electronic')])[0]

    def default_user_id(self):
        return self.env['res.users'].search([('id', '=', self.env.user.id)])

    name = fields.Char("Collection Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )

    user_id = fields.Many2one('res.users', default=default_user_id, string='Sales Executive', index=True,
                              track_visibility='onchange',
                              track_sequence=2)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Validate'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")
    payment_method_id = fields.Many2one('account.payment.method', default=default_payment_method_id,
                                        string='Payment Method Type', required=True,
                                        oldname="payment_method",
                                        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n" \
                                             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n" \
                                             "Check: Pay bill by check and print it from Odoo.\n" \
                                             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n" \
                                             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")

    payment_method_code = fields.Char(related='payment_method_id.code',
                                      help="Technical field used to adapt the interface to the payment type selected.",
                                      readonly=True)

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], default='customer')
    partner_id = fields.Many2one('res.partner', string='Partner')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False)
    partner_invoices = fields.One2many('neft.rtgs.collection.line', 'collection_id')
    cashier_id = fields.Many2one('res.users', string='Cashier')
    collected = fields.Boolean('Collected')
    type = fields.Selection([('neft', 'NEFT'), ('rtgs', 'RTGS'), ('deposit', 'Deposit'), ('internal', 'Transfer')],
                            string='Payment Type',
                            required=True, default='neft', )
    amount_total = fields.Float(string='Amount')
    bank_state = fields.Selection([('cleared', 'Cleared'), ('cancelled', 'Cancelled')],
                                  default='cleared', copy=False, string="Status")
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', '=', 'bank')])
    description = fields.Text('Description')
    amount_in_word = fields.Text('Amount In Word')
    accountant = fields.Many2one('res.partner', string='Account')
    sub_partner = fields.Many2one('res.partner', string='Sub Account')
    address = fields.Text('Address')
    bank_name = fields.Char('Bank Name')
    cleared_date = fields.Date(string='Cleared Date', copy=False)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'neft.rtgs.collection') or _('New')
                if 'type' in vals:
                    if vals['type'] == "neft":
                        vals['name'] = 'NEFT' + '/' + vals['name']
                    if vals['type'] == 'rtgs':
                        vals['name'] = 'RTGS' + '/' + vals['name']
                    if vals['type'] == 'deposit':
                        vals['type'] = 'Depo' + '/' + vals['name']
                    if vals['type'] == 'internal':
                        vals['type'] = 'Transf' + '/' + vals['name']





            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('neft.rtgs.collection') or _('New')
                if 'type' in vals:
                    if vals['type'] == 'neft':
                        vals['name'] = 'NEFT' + '/' + vals['name']
                    if vals['type'] == 'rtgs':
                        vals['name'] = 'RTGS' + '/' + vals['name']
                    if vals['type'] == 'deposit':
                        vals['name'] = 'Depo' + '/' + vals['name']
                    if vals['type'] == 'internal':
                        vals['name'] = 'Transfer' + '/' + vals['name']

        return super(RtgsNeftCollections, self).create(vals)

    @api.onchange('amount_total')
    def onchange_amount_total(self):
        if self.amount_total:
            self.amount_in_word = self.env.user.company_id.currency_id.amount_to_text(self.amount_total)

    @api.onchange('bank_state')
    def onchange_bank_state(self):
        if self.bank_state == 'cleared':
            self.cleared_date = datetime.today().date()

    @api.onchange('accountant')
    def onchange_accountant(self):
        if self.accountant:
            address = ''
            partner = self.accountant
            if partner.street2:
                address += partner.street2 + ','
            if partner.street:
                address += partner.street + ','
            if partner.city:
                address += partner.city + ','
            if partner.state_id:
                address += partner.state_id.name + ','
            if partner.country_id:
                address += partner.country_id.name + ','
            if partner.mobile:
                address += partner.mobile
            self.address = address

            return {'domain': {'sub_partner': [('id', 'in', self.accountant.sub_customers.mapped('partner').ids)]}}

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # @api.multi
    def action_statement(self):

        return self.env.ref('ezp_cash_collection.executive_collection_id').report_action(self)

    # @api.multi
    def action_statement_cashier(self):

        return self.env.ref('ezp_cash_collection.casheir_collection_id').report_action(self)

    def collection_record_coll(self):
        for line in self.partner_invoices:
            self.env['executive.collection.record'].create({
                'collection_id': self.id,
                'collection_line_id': line.id,
                'date': self.payment_date,
                'partner_id': line.partner_id.id,
                'balance_amount': line.balance_amount,
                'amount_total': line.amount_total,
                'journal_id': line.journal_id.id,
                'payment_type': self.payment_type,
                'payments': [(6, 0, line.payments.ids)],
                'sales_person': self.user_id.id,
                'cashier_id': self.cashier_id.id,
                'pending_amount': line.balance_amount - line.amount_total
            })

    def action_exe_confirm(self):
        self.collection_record_coll()
        self.collected = True

    def main_company_neft(self, type):
        stmt = self.env['account.bank.statement']
        bal = sum(self.env['account.move'].search(
            [('company_id', '=', 1), ('partner_id', '=', self.accountant.id)]).mapped('amount_total_signed'))

        if not stmt:
            journ = self.env['account.journal'].search(
                [('name', '=', 'Bank'), ('company_id', '=', 1)])
            bal = sum(self.env['account.move.line'].search([('journal_id', '=', journ.id)]).mapped(
                'debit'))
            bal = self.env['partner.ledger.customer'].search(
                [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', self.accountant.id)])[-1].balance

            stmt = self.env['account.bank.statement'].create({'name': self.accountant.name,
                                                              'balance_start': bal,
                                                              # 'journal_id': line.journal_id.id,
                                                              'journal_id': journ.id,
                                                              'balance_end_real': self.amount_total

                                                              })

            j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

            pay_id = self.env['account.payment'].create({'partner_id': self.accountant.id,
                                                         # 'amount': datev.amount_total,
                                                         'amount': self.amount_total,
                                                         'partner_type': self.partner_type,
                                                         'company_id': 1,
                                                         'payment_type': self.payment_type,
                                                         'payment_method_id': self.payment_method_id.id,
                                                         # 'journal_id': line.journal_id.id,
                                                         'journal_id': journ.id,
                                                         'ref': type + 'to ,from' + self.accountant.name + '=>' + journ.company_id.name + ',' + journ.name,

                                                         })
            pay_id.action_post()
            pay_id.action_cash_book()
            pay_id_list = []
            payment_list = []
            # for k in pay_id.move_line_ids:
            for k in pay_id.line_ids:
                pay_id_list.append(k.id)
            product_line = (0, 0, {
                'date': self.payment_date,
                'name': self.type,
                'partner_id': self.partner_id.id,
                'ref': self.type,
                'amount': self.amount_total})
            payment_list.append(product_line)
            self.env['partner.ledger.customer'].sudo().create({
                'date': datetime.today().date(),
                # 'invoice_id': inv.id,
                'description': type + '  ' + 'To' + '  ' + self.journal_id.company_id.name + ' ' + '& CO,' + 'A/C No:' + self.journal_id.payment_debit_account_id.display_name + ' ' + 'on' + ' ' + str(
                    self.cleared_date),
                'partner_id': self.accountant.id,
                'company_id': 1,
                'check_only':True,
                'credit': self.amount_total,
                'balance': bal - self.amount_total,
                # 'account_move': pay_id.move_line_ids.mapped('move_id')[0].id,
                'account_move': pay_id.move_id.id,
                'account_journal': self.journal_id.id
            })

        if stmt:
            stmt.line_ids = payment_list
            # stmt.button_post()
            # stmt.move_line_ids = pay_id_list

    def action_confirm(self):
        stmt = self.env['account.bank.statement']
        partner_led = self.env['partner.ledger.customer']
        if self.type == 'neft':
            type = 'NEFT'
        if self.type == 'rtgs':
            type = 'RTGS'
        if self.type == 'deposit':
            type = 'Deposit'
        if self.type == 'internal':
            type = 'Transfer'

        self.main_company_neft(type)

        # if not stmt:
        #     bal = sum(self.env['account.move.line'].search([('journal_id', '=', self.journal_id.id)]).mapped(
        #         'debit'))
        #
        #     stmt = self.env['account.bank.statement'].create({'name': self.sub_partner.name,
        #                                                           'balance_start': bal,
        #                                                           # 'journal_id': line.journal_id.id,
        #                                                           'journal_id': self.journal_id.id,
        #                                                           'balance_end_real': self.amount_total
        #
        #                                                           })
        #
        #
        #     j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

        # pay_id = self.env['account.payment'].create({'partner_id': self.sub_partner.id,
        #                                              # 'amount': datev.amount_total,
        #                                              'amount': self.amount_total,
        #                                              'partner_type': self.partner_type,
        #                                              'company_id': self.journal_id.company_id.id,
        #                                              'payment_type': self.payment_type,
        #                                              'payment_method_id': self.payment_method_id.id,
        #                                              # 'journal_id': line.journal_id.id,
        #                                              'journal_id': self.journal_id.id,
        #                                              'ref': type +'to ,from'+self.sub_partner.name +'=>'+self.journal_id.company_id.name+','+self.journal_id.name,
        #
        #                                              })
        # pay_id.action_post()
        # pay_id_list = []
        # payment_list = []
        # for k in pay_id.move_line_ids:
        #      pay_id_list.append(k.id)
        # product_line = (0, 0, {
        #                   'date': self.payment_date,
        #                 'name': self.type,
        #                 'partner_id': self.sub_partner.id,
        #                  'ref': self.type,
        #                 'amount': self.amount_total})
        # payment_list.append(product_line)
        #

        payment_list = []
        pay_id_list = []
        account = self.env['account.move'].search([('partner_id', '=', self.sub_partner.id), ('state', '=', 'open')])
        amount = self.amount_total
        actual = 0
        for datev in account:
            if not stmt:
                bal = sum(self.env['account.move.line'].search([('journal_id', '=', self.journal_id.id)]).mapped(
                    'debit'))
                journ = self.env['account.journal'].search(
                    [('name', '=', 'Bank'), ('company_id', '=', datev.company_id.id)])

                stmt = self.env['account.bank.statement'].create({'name': self.sub_partner.name,
                                                                  'balance_start': bal,
                                                                  # 'journal_id': line.journal_id.id,
                                                                  'journal_id': journ.id,
                                                                  'balance_end_real': self.amount_total

                                                                  })

            if amount:
                if datev.amount_total >= amount:
                    actual = amount

                    product_line = (0, 0, {
                        'date': self.payment_date,
                        'name': datev.display_name,
                        'partner_id': self.sub_partner.id,
                        'ref': datev.display_name,
                        'amount': amount
                    })
                    amount = amount - amount
                    payment_list.append(product_line)
                else:
                    if datev.amount_total != 0:
                        amount = amount - datev.amount_total
                        actual = datev.amount_total
                        product_line = (0, 0, {
                            'date': self.payment_date,
                            'name': datev.display_name,
                            'partner_id': self.sub_partner.id,
                            'ref': datev.display_name,
                            'amount': datev.amount_total
                        })
                        payment_list.append(product_line)

                j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
                journ = self.env['account.journal'].search(
                    [('name', '=', 'Bank'), ('company_id', '=', datev.company_id.id)])
                pay_id = self.env['account.payment'].create({'partner_id': self.sub_partner.id,
                                                             'amount': actual,
                                                             'partner_type': self.partner_type,
                                                             'company_id': datev.company_id.id,
                                                             'payment_type': self.payment_type,
                                                             'payment_method_id': self.payment_method_id.id,
                                                             'journal_id': journ.id,
                                                             'ref': type,
                                                             'invoice_ids': [(6, 0, datev.ids)]
                                                             })
                pay_id.action_post()
                pay_id.action_cash_book()
                # for k in pay_id.move_line_ids:
                for k in pay_id.line_ids:
                    pay_id_list.append(k.id)

        if stmt:
            stmt.line_ids = payment_list
            # stmt.move_line_ids = pay_id_list
            stmt.button_post()
            self.write({'state': 'validate'})
            bal = sum(self.env['account.move'].search([('partner_id', '=', self.sub_partner.id)]).mapped(
                'amount_total_signed'))
            bal = self.env['partner.ledger.customer'].search(
                [('company_id', '=', account[0].company_id.id), ('partner_id', '=', self.sub_partner.id)])[-1].balance


            if not partner_led:
                self.env['partner.ledger.customer'].sudo().create({
                    'date': datetime.today().date(),
                    # 'invoice_id': inv.id,
                    'description': type + '  ' + 'To' + '  ' + self.journal_id.company_id.name + ' ' + '& CO,' + 'A/C No:' + self.journal_id.payment_debit_account_id.display_name + ' ' + 'on' + ' ' + str(
                        self.cleared_date),
                    'partner_id': self.sub_partner.id,
                    'company_id': datev.company_id.id,
                    'credit': self.amount_total,
                    'balance': bal - self.amount_total,
                    # 'account_move':pay_id.move_line_ids.mapped('move_id')[0].id,
                    'account_journal': journ.id

                })
        self.action_accountant_record()

    def action_accountant_record(self):
        accountant = self.env['accountant.record'].create({
            'payment_type': self.payment_type,
            'user_id': self.user_id.id,
            'payment_method_id': self.payment_method_id.id,
            'partner_type': self.partner_type,
            'payment_date': self.payment_date,
            'source': self.name
        })

        self.env['accountant.record.line'].create({
            'date': self.cleared_date,
            'partner_id': self.accountant.id,
            'balance_amount': 0,
            'amount_total': self.amount_total,
            'journal_id': self.journal_id.id,
            'collection_id': accountant.id,
        })


class NeftRtgsCollectionLines(models.Model):
    _name = "neft.rtgs.collection.line"

    collection_id = fields.Many2one('neft.rtgs.collection')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Partner')
    amount_total = fields.Float(string='Amount')
    state = fields.Selection([('cleared', 'Cleared'), ('cancelled', 'Cancelled')],
                             default='cleared', copy=False, string="Status")
    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        journals = self.env['account.journal'].search(
            [('company_id', '=', self.env.user.company_id.id), ('type', '=', 'bank')])
        if journals:
            return {'domain': {'journal_id': [('id', 'in', journals.ids)]}}
