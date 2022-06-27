# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons import decimal_precision as dp

from odoo.tests import tagged, Form
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_main = fields.Many2one('purchase.order')
    invoiced_number = fields.Char('Invoice No')
    invoiced_date = fields.Date('Invoice Date')
    vehicle_no = fields.Char(string='Vehicle Number')
    purchase_date = fields.Date()
    purchase_custom = fields.Many2one('purchase.order.custom',string='Req ref')
    # amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    amount_tcs = fields.Monetary(string='TCS Amount', store=True, readonly=True, compute='_amount_all')
    grand_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            if order.company_id.id != 1:
                order.grand_total = order.amount_untaxed + amount_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax+order.amount_tcs,
            })
            if order.company_id.id != 1:
                if order.partner_id.tcs == True:
                    order.amount_tcs = order.amount_total * 0.10 / 100
                order.update({
                    'amount_total': amount_untaxed + amount_tax + order.amount_tcs,
                })

    # @api.multi
    # def _amount_all(self):
    #     for each in self:
    #         super(PurchaseOrder, self)._amount_all()
    #         if each.amount_total:
    #             if each.partner_id.tcs == True:
    #                 self.amount_tcs = each.amount_total * 0.10/100
    #         each.grand_total = each.amount_total
    #         each.amount_total = each.amount_tcs+each.amount_total
    #     return
    # @api.constrains('grand_total','amount_tcs')
    # def _amount_m_constra(self):
    #     for each in self:
    #         # if each.amount_total:
    #         #     if each.partner_id.tcs == True:
    #         #         self.amount_tcs = each.amount_total * 0.10/100
    #         each.grand_total = each.amount_total
    #         each.amount_total = each.amount_tcs+each.amount_total
    #     return

    def automatic_bill_creation(self):
        if self.picking_ids.state == 'done':

            create_bill = self.env.context.get('create_bill', False)
            account_id = self.env['account.account'].search(
                [('name', '=', 'Purchase Expense'), ('company_id', '=', self.env.user.company_id.id)])
            # override the context to get rid of the default filtering
            po = self
            new_inv = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'invoiced_number':po.invoiced_number,
                'invoiced_date':po.invoiced_date,
                'purchase_date':po.purchase_date,
                'vehicle_no':po.vehicle_no,
                'partner_id': po.partner_id.id,
                'purchase_id': po.id,
                'currency_id': po.currency_id.id,
                'company_id': po.company_id.id,
                'ref': po.name,
                # 'tax_line_ids':po_line.taxes_id.ids
            })

            for po_line in self.order_line:
                new_line = self.env['account.move.line'].create({
                    'name': po_line.name,
                    # 'origin': po.name,
                    'account_id': account_id.id,
                    'price_unit': po_line.price_unit,
                    'quantity': po_line.product_uom_qty,
                    'discount': 0.0,
                    # 'uom_id': po_line.product_id.uom_id.id,
                    'product_id': po_line.product_id.id,
                    'move_id': new_inv.id,
                    'tax_ids': [(6, 0, po_line.taxes_id.ids)]})
                po_line.invoice_lines = new_line
            new_inv.compute_taxes()
            # new_inv.action_invoice_open()
            new_inv.action_post()

    def create_supplier_ledger(self):
        print('mmmmmmmmm')


        for line in self.order_line:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id),
                 ('company_id', '=', self.company_id.id), ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                balance_amount = sum(invoices.mapped('amount_total'))

            Previous_led = self.env['supplier.ledger.customer'].search(
                [('company_id', '=', self.company_id.id), ('partner_id', '=', self.partner_id.id)])
            if Previous_led:
                balance_amount = Previous_led[-1].balance + self.amount_total
            if not balance_amount:
                balance_amount = self.amount_total
            self.env['supplier.ledger.customer'].sudo().create({
                'date':datetime.today().date(),
                 'partner_id':self.partner_id.id,
                'purchase_id':self.id,
                # 'invoice_id':self.invoice_id.id or False,
                'company_id':self.company_id.id,
                'product_id':line.product_id.id,
                'price_units':line.price_unit,
                'uom':line.product_uom.id,
                'rate':line.price_unit,
                'month':str(datetime.today().date().month),
                'credit':self.amount_total,
                'balance':balance_amount







            }  )
    def create_product_profit(self):
        for line in self.order_line:
            old = self.env['purchase.profit.repo'].search([('product_id','=',line.product_id.id),('company_id','=',self.company_id.id)])
            if not old:
                self.env['purchase.profit.repo'].create({
                    # 'date':datetime.today().date(),
                    'company_id':self.company_id.id,
                    'product_id':line.product_id.id,
                    'qty':line.product_qty,
                    # 'uom':line.product_uom.id,
                    'price':line.price_unit,
                    'price_subtotal':line.price_subtotal,
                } )
            else:
                old.qty += line.product_qty
                old.price += line.price_unit
                old.price_subtotal += line.price_subtotal

    def button_confirm_ezp(self):
    # def button_confirm(self):
        po_mo = False
        print('kkkkkk')
        po = self.button_confirm()
        self.action_view_picking()
        self.create_supplier_ledger()
        self.create_product_profit()
        # if not self.picking_ids:
        #     self.picking_ids = self.env['stock.picking'].browse(m['id'])
        #
        # inventory = self.action_view_picking()
        # inventory = self.action_view_picking()
        # if self.picking_ids:
        m = self.picking_ids.button_validate()
        # immideate = self.env['stock.immediate.transfer'].browse(m['res_id'])
        # immideate = self.env['stock.immediate.transfer'].browse(m['res_id'])

        Form(self.env['stock.immediate.transfer'].with_context(m['context'])).save().process()
        # immideate.process()
        invv = self.automatic_bill_creation()
        # inv = self.action_view_invoice()
        # self.invoice_ids = self.env['account.move'].browse(inv['id'])
        # self.invoice_ids.action_invoice_open()
        self.invoice_ids = self.env['account.move'].search([('purchase_id','=',self.id)]).ids

        for company in self.order_line.mapped('to_company'):
            my_purchase = []
            po_created = self.env['purchase.order']
            for line in self.order_line:
                if line.to_company == company:
                    if not po_created:
                        po_created = self.env['purchase.order'].create({
                            'partner_id': self.partner_id.id,
                            'partner_ref': self.partner_ref,
                            'month': self.month,
                            'invoiced_number': self.invoiced_number,
                            'invoiced_date': self.invoiced_date,
                            'purchase_date': self.purchase_date,
                            'vehicle_no': self.vehicle_no,
                            'company_id': company.id,
                            'purchase_main': self.id,
                            'picking_type_id': self.env['stock.warehouse'].search(
                                [('company_id', '=', company.id)]).in_type_id.id

                        })
                    if po_created:
                        list = []
                        for tax in line.taxes_id:
                            list.append(self.env['account.tax'].search(
                                [('name', '=', tax.name), ('type_tax_use', '=', 'purchase'),
                                 ('company_id', '=', company.id)]).id)
                            # if company.tcs == True:
                            #     list.append(self.env['account.tax'].search(
                            #         [('name', '=', 'TCS 0.10%'), ('type_tax_use', '=', 'purchase'),
                            #          ('company_id', '=', company.id)]).id)

                        purchase_lines = (0, 0,
                                          {'product_id': line.product_id.id,
                                           'name': line.name,
                                           'company_id': line.to_company.id,
                                           'product_uom': line.product_uom.id,
                                           'product_qty': line.product_qty,
                                           'date_planned': datetime.now().date().strftime(DEFAULT_SERVER_DATE_FORMAT),
                                           'no_of_bags': line.no_of_bags,
                                           'including_price':line.including_price,
                                           'price_unit': line.price_unit,
                                           # 'fix_discount': line.fix_discount,
                                           'price_subtotal': line.price_subtotal,
                                           'taxes_id':[(6, 0, list)]})

                        my_purchase.append(purchase_lines)
                    # po_created.button_confirm()
                    # pick = po_created.action_view_picking()
                    # po_created.stock_picking = self.env['stock.picking'].browse(pick['id'])
                    # m = po_created.picking_ids.button_validate()
                    # immideate = self.env['stock.immediate.transfer'].browse(m['res_id'])
                    # immideate.process()

            po_created.order_line = my_purchase
            for each in po_created:
                each.button_confirm()
        payment_method = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
        other_company = False
        if self.env.user.company_id != self.company_id:
            other_company = True

        po_pay = self.env['purchase.payments'].create(
            {'payment_type': 'outbound',
             'user_id': self.env.user.id,
             'payment_method_id': payment_method.id,
             'partner_type': 'supplier',
             'purchase_id': self.id,
             'other_company': other_company
             })
        for line in self.order_line:
            self.env['purchase.payments.line'].create({'purchase_pay_id': po_pay.id,
                                                       'partner_id': self.partner_id.id,
                                                       'balance_amount': line.price_subtotal,
                                                       'company_id': line.company_id.id,
                                                       'product_id': line.product_id.id,
                                                       # 'product_uom':line.price_subtotal,

                                                       })

        # return po
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    remainder_id = fields.Many2one('purchase.remainder')


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def default_taxes_id(self):
            list = []
            # if self.partner_id.tcs == True:
            #
            #      list.append(self.env['account.tax'].search([('name', '=', 'TCS 0.10%'), ('type_tax_use', '=', 'purchase'),
            #                                             ('company_id', '=', self.env.user.company_id.id)]).id)
            list.append(self.env['account.tax'].search([('name', '=', 'GST 28%'), ('type_tax_use', '=', 'purchase'),
                                                        ('company_id', '=', self.env.user.company_id.id)]).id)
            return list


    to_company = fields.Many2one('res.company', 'To Company')
    price_unit = fields.Float(string='Unit Price', required=True, digits=dp.get_precision('Product Price Custom'))
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)],default=default_taxes_id)
    including_price = fields.Float(string='Grand Total Amount')
    # product_qty = fields.Float(string='Quantity', default=1,digits=dp.get_precision('Product Unit of Measure'), required=True)



    @api.onchange('product_id')
    def onchange_product_id_est(self):
        if self.product_id:
            if self.order_id.partner_id.tcs == True:
                # idss = self.env['account.tax'].search([('name', '=', 'TCS 0.10%'), ('type_tax_use', '=', 'purchase'),
                #                                             ('company_id', '=', self.env.user.company_id.id)])
                idss = self.env['account.tax'].search([('name', '=', 'GST 28%'), ('type_tax_use', '=', 'purchase'),
                                                            ('company_id', '=', self.env.user.company_id.id)])
                self.taxes_id = idss
            else:
                self.taxes_id = self.env['account.tax'].search([('name', '=', 'GST 28%'), ('type_tax_use', '=', 'purchase'),
                                                ('company_id', '=', self.env.user.company_id.id)])

            taxs = self.env['account.tax'].search([('type_tax_use', '=', 'purchase'),
                                                        ('company_id', '=', self.env.user.company_id.id)])

            return {'domain': {'taxes_id': [('id', 'in', taxs.ids)]}}



    @api.onchange('including_price','taxes_id','product_qty')
    def onchange_including_price(self):
        if self.including_price:
            tax = 0
            if self.freight_charge:
                self.including_price = self.including_price-self.freight_charge

            for each in self.taxes_id:
                if each.children_tax_ids:
                    for ch in each.children_tax_ids:
                        tax += ch.amount
                else:
                    tax += each.amount
            if self.order_id.partner_id.tcs == True:
                value = 100 + tax +0.128
            else:
                value = 100 + tax
            basic_value = self.including_price * 100 / value
            # basic_value = basic_value
            t= basic_value/self.product_qty
            self.price_unit = t -0.00002
            # self.price_unit = basic_value



class PurchasePayments(models.Model):
    _name = "purchase.payments"
    _description = "Purchase Payment"
    _order = "id desc"

    name = fields.Char(" Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='outbound', )

    user_id = fields.Many2one('res.users', string='Responsible', index=True, track_visibility='onchange',
                              track_sequence=2)
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Validate'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method Type', required=True,
                                        oldname="payment_method",
                                        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n" \
                                             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n" \
                                             "Check: Pay bill by check and print it from Odoo.\n" \
                                             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n" \
                                             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")

    payment_method_code = fields.Char(related='payment_method_id.code',
                                      help="Technical field used to adapt the interface to the payment type selected.",
                                      readonly=True)

    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], default='supplier')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False)
    partner_invoices = fields.One2many('purchase.payments.line', 'purchase_pay_id')
    cashier_id = fields.Many2one('res.users', string='Cashier')
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    paid_amount = fields.Float(string='Paid Amount', compute='compute_bal_amount')
    bal_amount = fields.Float(string='Bal Amount', compute='compute_bal_amount')
    other_company = fields.Boolean(default=False, string='Other Company')

    # @api.multi
    def compute_bal_amount(self):
        for each in self:
            each.bal_amount = sum(each.mapped('partner_invoices').mapped('balance_amount')) - sum(
                each.mapped('partner_invoices').mapped('amount_total'))
            each.paid_amount = sum(each.mapped('partner_invoices').mapped('amount_total'))

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'purchase.payments') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.payments') or _('New')
        return super(PurchasePayments, self).create(vals)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # @api.multi
    def action_statement(self):

        return self.env.ref('ezp_cash_collection.purchase_collection_id').report_action(self)

    # @api.multi
    def action_statement_cashier(self):

        return self.env.ref('ezp_cash_collection.purchase_collection_id').report_action(self)
        # return self.env.ref('ezp_cash_collection.test_div').report_action(self)

    def action_confirm(self):
        stmt = self.env['account.bank.statement']
        for line in self.partner_invoices:

            # j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
            #
            # pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
            #                                              'amount': line.amount_total,
            #                                              'partner_type': self.partner_type,
            #                                              'company_id':self.env.user.company_id.id,
            #                                              'payment_type':self.payment_type,
            #                                              'payment_method_id': self.payment_method_id.id,
            #                                              'journal_id': line.journal_id.id,
            #                                              'communication': 'Cash Collection',
            #                                              # 'invoice_ids': [(6, 0, line.invoice_id.ids)]
            #                                              })
            # pay_id.action_post()
            # line.payments = pay_id
            # self.write({'state':'validate'})
            #

            cv = 0
            if not stmt:
                # _get_payment_info_JSON
                bal = sum(self.env['account.move.line'].search([('journal_id', '=', line.journal_id.id)]).mapped(
                    'debit'))
                stmt = self.env['account.bank.statement'].create({'name': line.partner_id.name,
                                                                  'balance_start': bal,
                                                                  'journal_id': line.journal_id.id,
                                                                  'balance_end_real': line.amount_total

                                                                  })

            payment_list = []
            pay_id_list = []
            account = self.env['account.move'].search(
                [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.env.user.company_id.id),
                 ('state', '=', 'open')])
            for check_inv in account:
                product_line = (0, 0, {
                    'date': line.date,
                    'name': check_inv.display_name,
                    'partner_id': line.partner_id.id,
                    'ref': check_inv.display_name,
                    'amount': line.amount_total
                })

                payment_list.append(product_line)
                j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

                pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                             'amount': line.amount_total,
                                                             'partner_type': self.partner_type,
                                                             'company_id': self.env.user.company_id.id,
                                                             'payment_type': 'outbound',
                                                             'payment_method_id': self.payment_method_id.id,
                                                             'journal_id': line.journal_id.id,
                                                             'ref': 'Purchase Payments',
                                                             'invoice_ids': [(6, 0, check_inv.ids)]
                                                             })
                # pay_id.action_validate_invoice_payment()
                pay_id.action_post()
                # for k in pay_id.move_line_ids:
                for k in pay_id.line_ids:
                    pay_id_list.append(k.id)
                line.payments = pay_id

        if stmt:
            stmt.line_ids = payment_list
            stmt.move_line_ids = pay_id_list
            self.write({'state': 'validate'})
        self.othercompany_autovalidation()

    def othercompany_autovalidation(self):
        for each_po in self.env['purchase.order'].search([('purchase_main', '=', self.purchase_id.id)]):
            stmt = self.env['account.bank.statement']
            payments_rec = self.env['purchase.payments'].search([('purchase_id', '=', each_po.id)])
            for line in payments_rec.partner_invoices:
                line.amount_total = self.partner_invoices.search(
                    [('product_id', '=', line.product_id.id), ('purchase_pay_id', '=', self.id)]).amount_total

                # j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]
                #
                # pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                #                                              'amount': line.amount_total,
                #                                              'partner_type': self.partner_type,
                #                                              'company_id':self.env.user.company_id.id,
                #                                              'payment_type':self.payment_type,
                #                                              'payment_method_id': self.payment_method_id.id,
                #                                              'journal_id': line.journal_id.id,
                #                                              'ref': 'Cash Collection',
                #                                              # 'invoice_ids': [(6, 0, line.invoice_id.ids)]
                #                                              })
                # pay_id.action_post()
                # line.payments = pay_id
                # self.write({'state':'validate'})
                #

                cv = 0
                if not stmt:
                    # _get_payment_info_JSON
                    j = self.env['account.journal'].search(
                        [('name', '=', 'Cash'), ('company_id', '=', each_po.company_id.id)])
                    line.journal_id = j
                    bal = sum(self.env['account.move.line'].search([('journal_id', '=', j.id)]).mapped(
                        'debit'))
                    stmt = self.env['account.bank.statement'].create({'name': line.partner_id.name,
                                                                      'balance_start': bal,
                                                                      'journal_id': j.id,
                                                                      'balance_end_real': line.amount_total

                                                                      })

                payment_list = []
                pay_id_list = []
                account = self.env['account.move'].search(
                    [('partner_id', '=', line.partner_id.id), ('company_id', '=', each_po.company_id.id),
                     ('state', '=', 'open')])
                for check_inv in account:
                    product_line = (0, 0, {
                        'date': line.date,
                        'name': check_inv.display_name,
                        'partner_id': line.partner_id.id,
                        'ref': check_inv.display_name,
                        'amount': line.amount_total
                    })

                    payment_list.append(product_line)
                    j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

                    pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                                 'amount': line.amount_total,
                                                                 'partner_type': self.partner_type,
                                                                 'company_id': each_po.company_id.id,
                                                                 'payment_type': 'outbound',
                                                                 'payment_method_id': self.payment_method_id.id,
                                                                 'journal_id': line.journal_id.id,
                                                                 'ref': 'Purchase Payments',
                                                                 'invoice_ids': [(6, 0, check_inv.ids)]
                                                                 })
                    # pay_id.action_validate_invoice_payment()
                    pay_id.action_post()
                    # for k in pay_id.move_line_ids:
                    for k in pay_id.line_ids:
                        pay_id_list.append(k.id)
                    line.payments = pay_id

            if stmt:
                stmt.line_ids = payment_list
                stmt.move_line_ids = pay_id_list
                self.write({'state': 'validate'})


class PurchasePaymentsLines(models.Model):
    _name = "purchase.payments.line"

    purchase_pay_id = fields.Many2one('purchase.payments')
    date = fields.Date('Date', default=fields.Date.context_today, )
    partner_id = fields.Many2one('res.partner', 'Vendor')
    balance_amount = fields.Float(string='Amount', )
    bal_amount = fields.Float(string='Bal Amount', compute='compute_bal_amount')
    amount_total = fields.Float(string='Paid Amount', )
    journal_id = fields.Many2one('account.journal', string='Payment Journal',
                                 domain=[('type', 'in', ('bank', 'cash', 'cheque'))])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='outbound', )
    payments = fields.Many2many('account.payment', 'payments_pay_rel')
    product_id = fields.Many2one('product.product', string='Product Name')
    company_id = fields.Many2one('res.company', string='Company Name')

    @api.onchange('date', 'amount_total')
    def onchange_date(self):
        journals = self.env['account.journal'].search(
            [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
        if journals:
            return {'domain': {'journal_id': [('id', 'in', journals.ids)]}}

    # @api.multi
    def compute_bal_amount(self):
        for line in self:
            line.bal_amount = line.balance_amount - line.amount_total

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id), ('state', '!=', 'paid'),
                 ('company_id', '=', self.env.user.company_id.id)])
            if sum(invoices.mapped('residual')):
                self.balance_amount = sum(invoices.mapped('residual'))
            else:
                self.balance_amount = sum(invoices.mapped('amount_total'))
            Previous_led = self.env['supplier.ledger.customer'].search(
                [('company_id', '=',1), ('partner_id', '=', self.partner_id.id)])
            if Previous_led:
                balance_amount = Previous_led[-1].balance
            if Previous_led:
                self.balance_amount = balance_amount
            journals = self.env['account.journal'].search(
                [('company_id', '=', self.env.user.company_id.id), ('type', 'in', ('cash', 'bank'))])
            if journals:
                return {'domain': {'journal_id': [('id', 'in', journals.ids)]}}


class ExpCashier(models.Model):
    _name = "exp.cashier"

    name = fields.Char("Collection Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True, default='inbound', )

    user_id = fields.Many2one('res.users', string='Sales Executive', index=True,
                              track_visibility='onchange',
                              track_sequence=2)
    expense_name = fields.Char('Expense Name')
    partner_id = fields.Many2one('hr.employee', string='Employee')
    exp_cashier_lines = fields.One2many('exp.cashier.line', 'exp_cashier_id')
    state = fields.Selection([('draft', 'Draft'), ('validate', 'Validate'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")
    payment_method_id = fields.Many2one('account.payment.method',
                                        string='Payment Method Type', required=True,
                                        oldname="payment_method",
                                        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n" \
                                             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n" \
                                             "Check: Pay bill by check and print it from Odoo.\n" \
                                             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n" \
                                             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")

    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False)
    cashier_id = fields.Many2one('res.users', string='Cashier')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float('Quantity')
    unit_amount = fields.Float('Unit Amount')
    total_amount = fields.Float('Total Amount')
    journal_id = fields.Many2one('account.journal', string='journal')
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    hr_expense_sheet = fields.Many2one('hr.expense.sheet', string='EXP Sheet Ref')

    def action_confirm(self):
        stmt = self.env['account.bank.statement']
        for line in self.exp_cashier_lines:
            cv = 0
            if not stmt:
                # _get_payment_info_JSON
                bal = sum(self.env['account.move.line'].search([('journal_id', '=', self.journal_id.id)]).mapped(
                    'debit'))
                stmt = self.env['account.bank.statement'].create({'name': self.partner_id.name,
                                                                  'balance_start': bal,
                                                                  'journal_id': self.journal_id.id,
                                                                  'balance_end_real': line.total_amount

                                                                  })

            payment_list = []
            pay_id_list = []
            # account = self.env['account.move'].search([('partner_id','=',self.partner_id.id),('company_id','=',self.env.user.company_id.id),('state','=','open')])
            # for check_inv in account:
            #     product_line = (0, 0, {
            #         'date': line.date,
            #         'name': check_inv.display_name,
            #         'partner_id': self.partner_id.id,
            #         'ref': check_inv.display_name,
            #         'amount': line.total_amount
            #     })
            #
            #     payment_list.append(product_line)
            j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

            pay_id = self.env['account.payment'].create({'partner_id': self.partner_id.id,
                                                         'amount': line.total_amount,
                                                         'partner_type': 'supplier',
                                                         'company_id': self.env.user.company_id.id,
                                                         'payment_type': 'outbound',
                                                         'payment_method_id': self.payment_method_id.id,
                                                         'journal_id': self.journal_id.id,
                                                         'ref': 'Expense Payments',
                                                         # 'invoice_ids': [(6, 0, check_inv.ids)]
                                                         })
            pay_id.action_post()
            pay_id.action_cash_book()
            # for k in pay_id.move_line_ids:
            for k in pay_id.line_ids:
                pay_id_list.append(k.id)
            line.payments = pay_id

        if stmt:
            # stmt.line_ids = payment_list
            stmt.move_line_ids = pay_id_list
            self.write({'state': 'validate'})
        # self.othercompany_autovalidation()


class ExpCashierLine(models.Model):
    _name = "exp.cashier.line"

    exp_cashier_id = fields.Many2one('exp.cashier')
    date = fields.Date('Date', default=fields.Date.context_today, )
    name = fields.Char('Description')
    tax_ids = fields.Many2many('account.tax')
    exp_line_id = fields.Many2one('hr.expense')
    total_amount = fields.Float('Total')


class HrExpenseSheet(models.Model):
    """
        Here are the rights associated with the expense flow

        Action       Group                   Restriction
        =================================================================================
        Submit      Employee                Only his own
                    Officer                 If he is expense manager of the employee, manager of the employee
                                             or the employee is in the department managed by the officer
                    Manager                 Always
        Approve     Officer                 Not his own and he is expense manager of the employee, manager of the employee
                                             or the employee is in the department managed by the officer
                    Manager                 Always
        Post        Anybody                 State = approve and journal_id defined
        Done        Anybody                 State = approve and journal_id defined
        Cancel      Officer                 Not his own and he is expense manager of the employee, manager of the employee
                                             or the employee is in the department managed by the officer
                    Manager                 Always
        =================================================================================
    """
    _inherit = "hr.expense.sheet"

    # @api.multi
    def approve_expense_sheets(self):
        super(HrExpenseSheet, self).approve_expense_sheets()
        rec = self.env['exp.cashier']
        if not rec:
            exp_rec = self.env['exp.cashier'].create({
                'payment_type': 'outbound',
                'payment_method_id': self.env['account.payment.method'].search([])[0].id,
                'partner_id': self.employee_id.id,
                'user_id': self.env.user.id,
                'journal_id': self.journal_id.id,
                'hr_expense_sheet': self.id,
            })
        for line in self.expense_line_ids:
            self.env['exp.cashier.line'].create({
                'exp_cashier_id': exp_rec.id,
                'date': line.date,
                'exp_line_id': line.id,
                'name': line.name,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
                'total_amount': line.total_amount,
            })


class PurcahseRemainder(models.Model):
    _name = "purchase.remainder"

    name = fields.Char("Reference Name", index=True, default=lambda self: _('New'))
    sequence = fields.Integer(index=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'), ('cancelled', 'Cancelled')], readonly=True,
                             default='draft', copy=False, string="Status")

    company_id = fields.Many2one('res.company', string='Company Name')
    product_id = fields.Many2one('product.product', string='Product Name')
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure')
    ordered_qty = fields.Float(default=0.0, string='Ordered Qty')
    available_qty = fields.Float(default=0.0, string='Available Qty')
    reserved_qty = fields.Float(default=0.0, string='Reserved Qty')

    def action_confirm(self):
        lines = []

        product_line = (0, 0, {'product_id': self.product_id.id,
                               'state': 'draft',
                               'product_uom': self.product_id.uom_po_id.id,
                               'price_unit': 0,
                               'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                               #                                    'taxes_id' : [(6,0,[taxes_id])],
                               'product_qty': self.ordered_qty,
                               'name': self.product_id.name
                               })
        lines.append(product_line)
        view_id = self.env.ref('purchase.purchase_order_form')
        self.write({'state': 'done'})
        return {
            'name': _('New Purchase Quotation'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_company_id': self.company_id.id, 'default_picking_type_id': self.env['stock.warehouse'].search(
                    [('company_id', '=', self.company_id.id)]).in_type_id.id,

                'default_remainder_id': self.id, 'default_order_line': lines, 'default_state': 'draft', }
        }


class PurchaseOrderCustom(models.Model):
    _name = 'purchase.order.custom'
    _order = 'id desc'

    def default_fiscal_id(self):
        # list = []
        return self.env['account.fiscal.position'].search([('name', '=', 'Intra State Purchase'),
                                                  ('company_id', '=', self.company_id.id)])
        # list.append(self.env['account.fiscal.position'].search([('name', '=', 'Inter State Purchase'),
        #                                             ('company_id', '=', self.company_id.id)]).id)
        # return {'domain': {'fiscal_position_id': [('id', 'in', list)]}}

    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    status = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Req Confirmed'), ('cancel', 'Cancel'),

    ], default='draft')
    invoiced_number = fields.Char('Invoice No')
    invoiced_date = fields.Date('Invoice Date')
    partner_id = fields.Many2one('res.partner',string='Vendor',domain=[('supplier_rank','=',1)])
    purchase_date = fields.Date()
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id)
    custom_lines = fields.One2many('purchase.custom.lines','custom_id')
    create_date = fields.Date(string='Create Date', default=fields.Date.context_today, required=True)
    user_id = fields.Many2one('res.users', 'Created By', required=True, default=lambda self: self.env.user)
    purchase_ids = fields.One2many('purchase.order','purchase_custom')
    po_count = fields.Integer(string='Delivery Orders', compute='_compute_po_count')
    fiscal_position_id = fields.Many2one('account.fiscal.position',default=default_fiscal_id, oldname='fiscal_position', string='Fiscal Position')
    vehicle_no = fields.Char(string='Vehicle Number')

    @api.onchange('fiscal_position_id')
    def onchange_fiscal_position_id(self):
        list = []
        list.append(self.env['account.fiscal.position'].search([('name', '=', 'Intra State Purchase'),
                                                                ('company_id', '=', self.company_id.id)]).id)
        list.append(self.env['account.fiscal.position'].search([('name', '=', 'Inter State Purchase'),
                                                                ('company_id', '=', self.company_id.id)]).id)
        return {'domain': {'fiscal_position_id': [('id', 'in', list)]}}

    @api.depends('purchase_ids')
    def _compute_po_count(self):
        for order in self:
            order.po_count = len(order.purchase_ids)


    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'purchase.order.custom') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.custom') or _('New')
        return super(PurchaseOrderCustom, self).create(vals)


    def main_company_po(self):
        my_purchase = []

        po_created = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            # 'partner_ref': self.partner_ref,
            # 'month': self.month,
            'purchase_custom': self.id,
            'purchase_payment_term': self.purchase_payment_term.id,
            'reduced_amount': self.reduced_amount,
            'percentage':self.percentage,
            'invoiced_number': self.invoiced_number,
            'invoiced_date': self.invoiced_date,
            'purchase_date': self.purchase_date,
            'company_id': self.company_id.id,
            'vehicle_no': self.vehicle_no,
            'picking_type_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.company_id.id)]).in_type_id.id

        })
        for line in self.custom_lines:
            if po_created:
                list = []
                # if line.including_price:
                #     tax = 0
                #     for each in self.taxes_id:
                #         if each.children_tax_ids:
                #             for ch in each.children_tax_ids:
                #                 tax += ch.amount
                #         else:
                #             tax += each.amount
                #     value = 100 + tax
                #     basic_value = line.including_price * 100 / value
                #     price_unit = basic_value / line.product_qty
                #
                #     if self.company_id.tcs == False:
                #         tax_ids = self.env['account.tax']
                #         tax_ids = self.env['account.tax'].search([('name', '=', 'GST 28%'), ('type_tax_use', '=', 'purchase'),
                #                                         ('company_id', '=', self.company_id.id)])
                #         list.append(self.env['account.tax'].search([('name', '=', 'GST 28%'),('type_tax_use', '=', 'purchase'),
                #              ('company_id', '=', self.company_id.id)]).id)
                #         tax = 0
                #         for each in tax_ids:
                #             if each.children_tax_ids:
                #                 for ch in each.children_tax_ids:
                #                     tax += ch.amount
                #             else:
                #                 tax += each.amount
                #         value = 100 + tax
                #         basic_value = line.including_price * 100 / value
                #         price_unit = basic_value / line.product_qty
                #
                #     if self.company_id.tcs == True:
                #         tax_ids = self.env['account.tax']
                #         list.append(self.env['account.tax'].search(
                #             [('name', '=', 'TCS 0.10%'), ('type_tax_use', '=', 'purchase'),
                #              ('company_id', '=', self.company_id.id)]).id)
                #         list.append(self.env['account.tax'].search(
                #             [('name', '=', 'GST 28%'), ('type_tax_use', '=', 'purchase'),
                #              ('company_id', '=', self.company_id.id)]))
                #         tax_ids = self.env['account.tax'].search(
                #             [('name', '=', 'GST 28%'), ('type_tax_use', '=', 'purchase'),
                #              ('company_id', '=', self.company_id.id)])
                #
                #         tax_ids += self.env['account.tax'].search(
                #             [('name', '=', 'GST 28%'), ('type_tax_use', '=', 'purchase'),
                #              ('company_id', '=', self.company_id.id)])
                #         tax = 0
                #         for each in tax_ids:
                #             if each.children_tax_ids:
                #                 for ch in each.children_tax_ids:
                #                     tax += ch.amount
                #             else:
                #                 tax += each.amount
                #         value = 100 + tax
                #         basic_value = line.including_price * 100 / value
                #         price_unit = basic_value / line.product_qty

                purchase_lines = (0, 0,
                                  {'product_id': line.product_id.id,
                                   'name': line.product_id.name,
                                   'product_uom': line.product_uom.id,
                                   'product_qty': line.product_qty,
                                   'date_planned': datetime.now().date().strftime(DEFAULT_SERVER_DATE_FORMAT),
                                   # 'no_of_bags': line.product_qty,
                                   'including_price': line.including_price,
                                   'dippo': line.dippo.id,
                                   'freight_charge':line.freight_charge,
                                   'price_unit': line.including_price/line.product_qty,
                                   'taxes_id': [(6, 0, list)]})
                my_purchase.append(purchase_lines)
        po_created.order_line = my_purchase
        my_purchase.append(purchase_lines)

        po_created.button_confirm_ezp()

    # @api.multi
    def action_view_invoice(self):
        '''
        This function returns an action that display existing dispatch orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env.ref('purchase.purchase_rfq').read()[0]

        sales = self.mapped('purchase_ids')
        if len(sales) > 1:
            action['domain'] = [('id', 'in', sales.ids)]
        elif sales:
            form_view = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = sales.id
        return action


    def action_oder_confirm(self):

        for line in self.custom_lines:
            my_purchase = []
            po_created = self.env['purchase.order']
            self.main_company_po()
            if line.company_id:
                    company = line.company_id
                    if not po_created:
                        po_created = self.env['purchase.order'].create({
                            'partner_id': self.partner_id.id,
                            # 'partner_ref': self.partner_ref,
                            # 'month': self.month,
                            'purchase_custom':self.id,
                            'percentage': self.percentage,
                            'invoiced_number': self.invoiced_number,
                            'purchase_payment_term':self.purchase_payment_term.id,
                            'reduced_amount':self.reduced_amount,
                            'invoiced_date': self.invoiced_date,
                            'vehicle_no': self.vehicle_no,
                            'purchase_date': self.purchase_date,
                            'company_id': company.id,
                            'fiscal_position_id':self.fiscal_position_id.id,
                            'picking_type_id': self.env['stock.warehouse'].search(
                                [('company_id', '=', company.id)]).in_type_id.id

                        })
                    if po_created:
                        list = []
                        if line.including_price:
                            # tax = 0
                            # for each in self.taxes_id:
                            #     if each.children_tax_ids:
                            #         for ch in each.children_tax_ids:
                            #             tax += ch.amount
                            #     else:
                            #         tax += each.amount
                            # value = 100 + tax
                            # basic_value = line.including_price * 100 / value
                            # price_unit = basic_value / line.product_qty

                            if self.partner_id.tcs == False:
                                tax_ids = self.env['account.tax']
                                if self.fiscal_position_id.name == "Intra State Purchase":
                                    tax_ids = self.env['account.tax'].search(
                                        [('name', '=', 'GST 28%'), ('type_tax_use', '=', 'purchase'),
                                         ('company_id', '=', line.company_id.id)])
                                    list.append(self.env['account.tax'].search(
                                        [('name', '=', 'GST 28%'), ('type_tax_use', '=', 'purchase'),
                                         ('company_id', '=', line.company_id.id)]).id)
                                if self.fiscal_position_id.name == "Inter State Purchase":
                                    tax_ids = self.env['account.tax'].search(
                                        [('name', '=', 'IGST 28%'), ('type_tax_use', '=', 'purchase'),
                                         ('company_id', '=', line.company_id.id)])
                                    list.append(self.env['account.tax'].search(
                                        [('name', '=', 'IGST 28%'), ('type_tax_use', '=', 'purchase'),
                                         ('company_id', '=', line.company_id.id)]).id)

                                tax = 0
                                for each in tax_ids:
                                    if each.children_tax_ids:
                                        for ch in each.children_tax_ids:
                                            tax += ch.amount
                                    else:
                                        tax += each.amount
                                value = 100 + tax
                                basic_value = line.including_price * 100 / value
                                price_unit = basic_value / line.product_qty

                            if self.partner_id.tcs == True:
                                tax_ids = self.env['account.tax']
                                # list.append(self.env['account.tax'].search(
                                #     [('name', '=', 'TCS 0.10%'), ('type_tax_use', '=', 'purchase'),
                                #      ('company_id', '=', self.company_id.id)]).id)
                                if self.fiscal_position_id.name == "Intra State Purchase":

                                    list.append(self.env['account.tax'].search(
                                        [('name', '=', 'GST 28%'), ('type_tax_use', '=', 'purchase'),
                                         ('company_id', '=', self.company_id.id)]).id)
                                    tax_ids = self.env['account.tax'].search(
                                        [('name', '=', 'GST 28%'), ('type_tax_use', '=', 'purchase'),
                                         ('company_id', '=', self.company_id.id)])
                                if self.fiscal_position_id.name == "Inter State Purchase":
                                    list.append(self.env['account.tax'].search(
                                        [('name', '=', 'IGST 28%'), ('type_tax_use', '=', 'purchase'),
                                         ('company_id', '=', self.company_id.id)]).id)
                                    tax_ids = self.env['account.tax'].search(
                                        [('name', '=', 'IGST 28%'), ('type_tax_use', '=', 'purchase'),
                                         ('company_id', '=', self.company_id.id)])
                                # tax_ids += self.env['account.tax'].search(
                                #     [('name', '=', 'TCS 0.10%'), ('type_tax_use', '=', 'purchase'),
                                #      ('company_id', '=', self.company_id.id)])
                                tax = 0
                                for each in tax_ids:
                                    if each.children_tax_ids:
                                        for ch in each.children_tax_ids:
                                            tax += ch.amount
                                    else:
                                        tax += each.amount
                                value = 100 + tax
                                value = value+0.128
                                basic_value = line.including_price * 100 / value
                                price_unit = basic_value / line.product_qty

                        purchase_lines = (0, 0,
                                          {'product_id': line.product_id.id,
                                           'name': line.product_id.name,
                                           'dippo':line.dippo.id,
                                           'freight_charge':line.freight_charge,
                                           'product_uom': line.product_uom.id,
                                           'product_qty': line.product_qty,
                                           'date_planned': datetime.now().date().strftime(DEFAULT_SERVER_DATE_FORMAT),
                                           'including_price': line.including_price,
                                           'price_unit': price_unit,
                                           # 'price_subtotal': line.price_subtotal,
                                           'taxes_id': [(6, 0, list)]
                                           })

                        my_purchase.append(purchase_lines)
            po_created.order_line = my_purchase
            for each in po_created:
                each.button_confirm_ezp()
        self.write({'status':'done'})

class PurchaseOrderCustomLines(models.Model):
    _name = 'purchase.custom.lines'

    def default_product_uom(self):
        return self.env['uom.uom'].search([('name', '=', 'bag')])

    custom_id = fields.Many2one('purchase.order.custom')
    company_id = fields.Many2one('res.company')
    product_id = fields.Many2one('product.product',string='Product',domain=[('grouped', '=', False),('purchase_ok', '=', True)])
    product_uom = fields.Many2one('uom.uom',string='Uom',default=default_product_uom)
    product_qty = fields.Float(string='No Of Bags')
    including_price = fields.Float(string='Total Amount')

class Partner(models.Model):
    _inherit = 'res.partner'

    tcs = fields.Boolean(default=False)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # @api.multi
    def _action_confirm(self):
        self.create_product_profit()
        return super(SaleOrder, self)._action_confirm()



    def create_product_profit(self):
        for line in self.order_line:
            old = self.env['purchase.profit.repo'].search([('product_id','=',line.product_id.id),('company_id','=',self.company_id.id)])
            if not old:
                self.env['purchase.profit.repo'].create({
                    # 'date':datetime.today().date(),
                    'company_id':self.company_id.id,
                    'product_id':line.product_id.id,
                    'sale_qty':line.product_uom_qty,
                    'sale_price':line.price_unit,
                    'sale_price_subtotal':line.price_subtotal,
                } )
            else:
                old.sale_qty += line.product_uom_qty
                old.sale_price += line.price_unit
                old.sale_price_subtotal += line.price_subtotal



