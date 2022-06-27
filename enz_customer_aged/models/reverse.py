# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from datetime import date
from datetime import datetime
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import calendar
import re
import json
from dateutil.relativedelta import relativedelta
import pgeocode
import qrcode
from PIL import Image
from random import choice
from string import digits
import json
import re
import uuid
from functools import partial





class RtgsNeftCollections(models.Model):
    _inherit = "neft.rtgs.collection"


    def main_company_neft(self, type):
        stmt =state = self.env['account.bank.statement']
        # bal = sum(self.env['account.move'].search(
        #     [('company_id', '=', 1), ('partner_id', '=', self.accountant.id)]).mapped('amount_total_signed'))

        if not stmt:
            # journ = self.env['account.journal'].search(
            #     [('name', '=', 'Bank'), ('company_id', '=', 1)])
            journ = self.env['account.journal'].search(
                [('name', '=', 'Bank'), ('company_id', '=', 1)])
            # if not journ:
            #     journ = self.env['account.journal'].search(
            #         [('name', '=', 'SHIHAB'), ('company_id', '=', 1)])
            # bal = sum(self.env['account.move.line'].search([('journal_id', '=', journ.id)]).mapped(
            #     'debit'))

            if self.env['account.bank.statement'].search(
                    [('company_id', '=',journ.company_id.id), ('journal_id', '=', journ.id)]):
                bal = self.env['account.bank.statement'].search(
                    [('company_id', '=', journ.company_id.id), ('journal_id', '=', journ.id)])[
                    0].balance_end_real
            else:
                bal = 0

            # if self.env['partner.ledger.customer'].search(
            #     [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', self.accountant.id)]):
            #     bal = self.env['partner.ledger.customer'].search(
            #         [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', self.accountant.id)])[-1].balance

            stmt = self.env['account.bank.statement'].create({'name': self.accountant.name,
                                                              'balance_start': bal,
                                                              # 'journal_id': line.journal_id.id,
                                                              'journal_id': journ.id,
                                                              'balance_end_real': bal+self.amount_total
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
            # pay_id.post()
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
                'payment_ref': self.type,
                'amount': self.amount_total})
            payment_list.append(product_line)
            # invoices = self.env['account.move'].sudo().search(
            #     [('partner_id', '=', new_inv.partner_id.id), ('company_id', '=', new_inv.company_id.id),
            #      ('state', '!=', 'paid')])
            # if invoices.mapped('residual'):
            #     balance_amount = sum(invoices.mapped('residual'))
            # else:
            #     balance_amount = sum(invoices.mapped('amount_total'))
            balance_amount =0
            balance_amount += self.env['partner.ledger.customer'].sudo().search(
                [('partner_id', '=', self.accountant.id), ('description', '=', 'Opening Balance')]).balance
            Previous_led = self.env['partner.ledger.customer'].sudo().search(
                [('company_id', '=', 1), ('partner_id', '=', self.accountant.id)])
            if Previous_led:
                balance_amount = Previous_led[-1].balance

            self.env['partner.ledger.customer'].sudo().create({
                'date': datetime.today().date(),
                # 'invoice_id': inv.id,
                'description': type + '  ' + 'To' + '  ' + self.journal_id.company_id.name + ' ' + '& CO,' + 'A/C No:' + self.journal_id.payment_debit_account_id.display_name + ' ' + 'on' + ' ' + str(
                    self.cleared_date),
                'partner_id': self.accountant.id,
                'company_id': 1,
                'check_only':True,
                'neft_id':self.id,
                'credit': self.amount_total,
                'balance': balance_amount - self.amount_total,
                # 'account_move': pay_id.move_line_ids.mapped('move_id')[0].id,
                'account_move': pay_id.move_id.id,
                'account_journal': self.journal_id.id
            })

        if stmt:
            stmt.line_ids = payment_list
            # stmt.move_line_ids = pay_id_list
            # stmt.button_post()
            # stmt.write({'state': 'confirm'})



class FreightDiscount(models.Model):
    _inherit = 'freight.disc'



    # @api.onchange('journal_id')
    # def onchange_journal_id(self):
    #     if self.journal_id:
    #         # expenses_accs = self.env['account.account'].search([('user_type_id.name', '=','Expenses')])
    #         self.account_id  = self.journal_id.default_debit_account_id
    #         # return {'domain': {'account_id': [('id', 'in', expenses_accs.ids)]}}



    def action_post(self):
        self.write({'state': 'done'})
        for line in self.freight_lines:
            stmt = self.env['account.bank.statement']
            j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0].id
            if not stmt:
                # _get_payment_info_JSON
                # bal = sum(self.env['account.move.line'].search([('journal_id', '=', line.journal_id.id)]).mapped(
                #     'debit'))

                if self.env['account.bank.statement'].search([('company_id','=',line.journal_id.company_id.id),('journal_id', '=', line.journal_id.id)]):
                    bal = self.env['account.bank.statement'].search([('company_id','=',line.journal_id.company_id.id),('journal_id', '=', line.journal_id.id)])[0].balance_end_real
                else:
                    bal = 0

                stmt = self.env['account.bank.statement'].create({'name': line.partner_id.name,
                                                                  'balance_start': bal,
                                                                  # 'journal_id': line.journal_id.id,
                                                                  'journal_id': line.journal_id.id,
                                                                  'balance_end_real': bal+line.amount

                                                                  })

            payment_list = []
            pay_id_list = []
            account = self.env['account.move'].search(
                [('partner_id', '=', line.partner_id.id), ('state', '=', 'posted')])

            # for check_inv in account:
            product_line = (0, 0, {
                'date': self.creates_date,
                # 'name': check_inv.display_name,
                'name': self.name,
                'partner_id': line.partner_id.id,
                'payment_ref': self.name,
                'amount': line.amount
            })

            payment_list.append(product_line)

            pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                         'amount': line.amount,
                                                         'partner_type': 'customer',
                                                         'payment_type': 'inbound',
                                                         'payment_method_id': j,
                                                         'journal_id': line.journal_id.id,
                                                         'ref': line.partner_id.name + 'Freight/Charges',
                                                         # 'invoice_ids': [(6, 0, check_inv.ids)]
                                                         })

            # pay_id.post()
            pay_id.action_post()
            # for k in pay_id.move_line_ids:
            for k in pay_id.line_ids:
                pay_id_list.append(k.id)

            # vals = {
            #     'journal_id': line.journal_id.id,
            #     'state': 'draft',
            #     'ref': line.partner_id.name + 'Freight/Charges'
            # }
            # pay_id_list = []
            # move_id = self.env['account.move'].create(vals)
            # partner_id = line.partner_id.id
            # label = 'Freight/Charges' + '/' + line.partner_id.name
            #
            # # if self.type_of_partner == 'partner':
            # #     if self.type_of_credit == False:
            #
            # acc = line.account_id
            # temp = (0, 0, {
            #     'account_id': acc.id,
            #     'name': label,
            #     'move_id': move_id.id,
            #     'date': datetime.today().date(),
            #     'partner_id': line.partner_id.id,
            #     'debit': 0,
            #     'credit': line.amount,
            # })
            # pay_id_list.append(temp)
            # temp = (0, 0, {
            #     'account_id': self.env['account.account'].search(
            #         [('name', '=', 'Debtors'), ('company_id', '=', 1)]).id,
            #     'name': label,
            #     'move_id': move_id.id,
            #     'date': datetime.today().date(),
            #     'partner_id': line.partner_id.id,
            #     'debit': line.amount,
            #     'credit': 0,
            # })
            # pay_id_list.append(temp)
            #
            # move_id.line_ids = pay_id_list
            # move_id.action_post()
            # for k in move_id.line_ids:
            #     pay_id_list.append(k.id)


            if line.journal_id.type == 'cash':
                if not self.env['cash.book.info'].search([]):
                    complete = sum(
                        self.env['account.move.line'].search([('journal_id', '=', line.journal_id.id)]).mapped(
                            'debit'))
                else:
                    complete = self.env['cash.book.info'].search([])[-1].balance

                debit = 0
                credit = 0
                complete_new = 0
                acc = self.env['account.account']
                # if self.payment_type == 'outbound':
                debit = line.amount
                # complete_new = complete - credit
                complete_new = complete + debit
                acc = line.journal_id.payment_credit_account_id.id
                # if self.payment_type == 'inbound':
                #     debit = self.amount
                #     complete_new = complete + debit
                #     acc = self.journal_id.default_debit_account_id.id

                self.env['cash.book.info'].create({
                    'date': datetime.today().date(),
                    'account_journal': line.journal_id.id,
                    'partner_id': line.partner_id.id,
                    'company_id': 1,
                    # 'description': self.communication,
                    'description': line.partner_id.name,
                    'payment_type': 'outbound',
                    'partner_type': 'customer',
                    'debit': debit,
                    'credit': credit,
                    'account': acc,
                    # 'payment_id': self.id,
                    'balance': complete_new

                })

            # pay_id.post()
            # pay_id.action_cash_book()
            invoices = self.env['account.move'].search(
                [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.company_id.id),
                 ('state', '!=', 'paid')])
            if invoices.mapped('amount_residual'):
                balance_amount = sum(invoices.mapped('amount_residual'))
            else:
                balance_amount = sum(invoices.mapped('amount_total'))
            balance_amount += self.env['partner.ledger.customer'].search(
                [('partner_id', '=', line.partner_id.id), ('description', '=', 'Opening Balance')]).balance
            preview = self.env['partner.ledger.customer'].search(
                [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)])
            if preview:
                balance_amount = self.env['partner.ledger.customer'].search(
                    [('company_id', '=', self.company_id.id), ('partner_id', '=', line.partner_id.id)])[-1].balance
            self.env['partner.ledger.customer'].sudo().create({
                'date': datetime.today().date(),
                'description': line.freight.name,
                'partner_id': line.partner_id.id,
                'company_id': self.company_id.id,
                'account_journal': line.journal_id.id,
                'check_only':True,
                # 'account_move': move_id.id,
                # 'account_move': pay_id.move_line_ids.mapped('move_id').id,
                'account_move': pay_id.move_id.id,
                'credit': line.amount,
                # 'debit': line.op_amount,
                # 'balance': 0,
                # 'executive_area': self.executive_areas.id or False,
                # 'area': self.area.id or False,
                # 'vehicle_id': self.estimate_ids[0].vahicle.id,
                'balance': balance_amount - line.amount,
            })

            # vals = {
            #     'journal_id': line.journal_id.id,
            #     'state': 'draft',
            #     'ref': line.freight.name
            # }
            # pay_id_list = []
            # move_id = self.env['account.move'].create(vals)
            # temp = (0, 0, {
            #     'account_id': line.journal_id.default_debit_account_id.id,
            #     'name': line.freight.name,
            #     'move_id': move_id.id,
            #     'date': self.create_date,
            #     'partner_id': line.partner_id.id,
            #     'debit': line.amount,
            #     'credit': 0,
            # })
            # pay_id_list.append(temp)
            #
            # temp = (0, 0, {
            #     'account_id': line.journal_id.payment_credit_account_id.id,
            #     'name': line.freight.name,
            #     'move_id': move_id.id,
            #     'date': self.create_date,
            #     # 'partner_id': self.partner_id.id,
            #     'debit': 0,
            #     'credit': line.amount,
            # })
            # pay_id_list.append(temp)
            # move_id.line_ids = pay_id_list
            # move_id.action_post()
            # if line.journal_id.type == 'cash':
            #     # complete = sum(self.env['account.move.line'].search([('journal_id', '=', acc.id)]).mapped('debit'))
            #     complete = sum(self.env['account.move.line'].search(
            #         [('company_id', '=', self.env.user.company_id.id), ('account_id', '=', line.journal_id.payment_credit_account_id.id)]).mapped(
            #         'debit'))
            #     debit = 0
            #     credit = line.amount
            #     complete_new = complete - credit
            #     acc = acc
            #     self.env['cash.book.info'].create({
            #         'date': self.create_date,
            #         'account_journal': line.journal_id.id,
            #         'account': acc.id,
            #         'partner_id': self.partner_id.id,
            #         'company_id': 1,
            #         'description': line.freight.name + ' ' + line.partner_id.name,
            #         'debit': debit,
            #         'credit': credit,
            #         'balance': complete_new
            #
            #     })
            #
            if stmt:
                stmt.line_ids = payment_list
                # stmt.move_line_ids = pay_id_list
                # stmt.button_post()
                # stmt.write({'state': 'confirm'})






class CashierDirectCollection(models.Model):
    _inherit = "cashier.direct.collection"

    def action_confirm(self):
        # stmt = self.env['account.bank.statement']

        for line in self.partner_invoices:
            if line.partner_id:
                if line.amount_total == 0.0:
                    raise UserError(_("Please mention paid amount for this partner %s ") % (line.partner_id.name))
                cv = 0
                # if line.check_type == 'cheque':

                stmt = self.env['account.bank.statement']
                if not stmt:
                    journ = line.journal_id
                    # bal = sum(self.env['account.move.line'].search([('journal_id', '=', journ.id)]).mapped(
                    #     'debit'))

                    if self.env['account.bank.statement'].search(
                            [('company_id', '=', journ.company_id.id), ('journal_id', '=', journ.id)]):
                        bal = self.env['account.bank.statement'].search(
                            [('company_id', '=', journ.company_id.id), ('journal_id', '=', journ.id)])[
                            0].balance_end_real
                    else:
                        bal = 0
                    stmt = self.env['account.bank.statement'].create({'name': line.partner_id.name,
                                                                  'balance_start': bal,
                                                                  # 'journal_id': line.journal_id.id,
                                                                  'journal_id': line.journal_id.id,
                                                                  'balance_end_real': bal + line.amount_total

                                                                  })
                    payment_list = []
                    product_line = (0, 0, {
                        'date': self.payment_date,
                        # 'name': check_inv.display_name,
                        'name': self.name,
                        'partner_id': line.partner_id.id,
                        'payment_ref': self.name,
                        'amount': line.amount_total
                    })

                    payment_list.append(product_line)

                    pay_id_list = []


                journal = self.env['account.journal'].search(
                    [('name', '=', 'Cash'), ('company_id', '=', self.env.user.company_id.id)])
                j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

                pay_id = self.env['account.payment'].create({'partner_id': line.partner_id.id,
                                                             'amount': line.amount_total,
                                                             'partner_type': 'customer',
                                                             'payment_type': 'inbound',
                                                             'payment_method_id': j.id,
                                                             'journal_id': journal.id,
                                                             'ref': 'Direct Cash Collection',
                                                             })
                # pay_id.post()
                pay_id.action_post()
                # for k in pay_id.move_line_ids:
                for k in pay_id.line_ids:
                    pay_id_list.append(k.id)

                pay_id.action_cash_book()

                invoices = self.env['account.move'].search(
                    [('partner_id', '=', line.partner_id.id), ('company_id', '=', self.env.user.company_id.id),
                     ('state', '!=', 'paid')])
                if invoices.mapped('amount_residual'):
                    balance_amount = sum(invoices.mapped('amount_residual'))
                else:
                    balance_amount = sum(invoices.mapped('amount_total'))
                balance_amount += self.env['partner.ledger.customer'].search(
                    [('partner_id', '=', self.env.user.company_id.id), ('description', '=', 'Opening Balance')]).balance

                preveious = self.env['partner.ledger.customer'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', line.partner_id.id)])
                if preveious:
                    balance_amount = self.env['partner.ledger.customer'].search(
                        [('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', line.partner_id.id)])[-1].balance

                self.env['partner.ledger.customer'].sudo().create({
                    'date': datetime.today().date(),
                    'description': 'Direct Cash Collection',
                    'partner_id': line.partner_id.id,
                    'company_id': self.env.user.company_id.id,
                    'account_journal': journal.id,
                    'credit': line.amount_total,
                    'check_only':True,
                    'balance': balance_amount - line.amount_total,
                })
                if stmt:
                    stmt.line_ids = payment_list
                    # stmt.move_line_ids = pay_id_list
                    # stmt.button_post()
                    # stmt.write({'state': 'confirm'})


            else:
                if line.journal_id.company_id == self.env.user.company_id:
                    # vals = {
                    #     'journal_id': line.journal_id.id,
                    #     'state': 'draft',
                    #     'ref': line.reason
                    # }
                    # pay_id_list = []
                    # move_id = self.env['account.move'].create(vals)
                    # # if self.partner_id:
                    # #     partner_id = self.partner_id.id
                    # # else:
                    # #     partner_id = False
                    # # if self.account_id.user_type_id.display_name == 'equity':
                    # #     label = 'Withdraw Amount'
                    # # else:
                    # label = line.reason
                    #
                    # temp = (0, 0, {
                    #     'account_id': line.journal_id.payment_debit_account_id.id,
                    #     'name': label,
                    #     'move_id': move_id.id,
                    #     'date': self.payment_date,
                    #     # 'partner_id': partner_id,
                    #     'debit': line.amount_total,
                    #     'credit': 0,
                    # })
                    # pay_id_list.append(temp)
                    #
                    # temp = (0, 0, {
                    #     'account_id': line.journal_id.payment_credit_account_id.id,
                    #     'name': 'Credit Amount',
                    #     'move_id': move_id.id,
                    #     'date': self.payment_date,
                    #     # 'partner_id': self.partner_id.id,
                    #     'debit': 0,
                    #     'credit': line.amount_total,
                    # })
                    # pay_id_list.append(temp)
                    # move_id.line_ids = pay_id_list
                    # move_id.action_post()
                    pay_id_list = []
                    j = self.env['account.payment.method'].search([('name', '=', 'Manual')])[0]

                    pay_id = self.env['account.payment'].create({'partner_id': line.journal_id.company_id.partner_id.id,
                                                                 'amount': line.amount_total,
                                                                 'partner_type': 'customer',
                                                                 'payment_type': 'inbound',
                                                                 'payment_method_id': j.id,
                                                                 'journal_id': line.journal_id.id,
                                                                 'ref': 'Direct Cash Collection',
                                                                 })
                    # pay_id.post()
                    pay_id.action_post()
                    # for k in pay_id.move_line_ids:
                    for k in pay_id.line_ids:
                        pay_id_list.append(k.id)

                    stmt = self.env['account.bank.statement']
                    if not stmt:
                        journ = line.journal_id
                        # bal = sum(self.env['account.move.line'].search([('journal_id', '=', journ.id)]).mapped(
                        #     'debit'))

                        if self.env['account.bank.statement'].search(
                                [('company_id', '=', journ.company_id.id), ('journal_id', '=', journ.id)]):
                            bal = self.env['account.bank.statement'].search(
                                [('company_id', '=', journ.company_id.id), ('journal_id', '=', journ.id)])[
                                0].balance_end_real
                        else:
                            bal = 0
                        stmt = self.env['account.bank.statement'].create({'name': line.journal_id.company_id.partner_id.name,
                                                                          'balance_start': bal,
                                                                          # 'journal_id': line.journal_id.id,
                                                                          'journal_id': line.journal_id.id,
                                                                          'balance_end_real': bal + line.amount_total

                                                                          })
                        payment_list = []
                        product_line = (0, 0, {
                            'date': self.payment_date,
                            # 'name': check_inv.display_name,
                            'name': self.name,
                            'partner_id': line.journal_id.company_id.partner_id.id,
                            'payment_ref': self.name,
                            'amount': line.amount_total
                        })

                        payment_list.append(product_line)


                    # complete = sum(self.env['account.move.line'].search([('journal_id', '=', acc.id)]).mapped('debit'))
                    complete = sum(self.env['account.move.line'].search(
                        [('company_id', '=', self.env.user.company_id.id),
                         ('account_id', '=', line.journal_id.payment_debit_account_id.id)]).mapped(
                        'debit'))
                    if not self.env['cash.book.info'].search([]):
                        complete = sum(
                            self.env['account.move.line'].search([('journal_id', '=', line.journal_id.id)]).mapped('debit'))
                    else:
                        complete = self.env['cash.book.info'].search([])[-1].balance

                    debit = 0
                    credit = 0
                    complete_new = 0
                    type_m = 'inbound'

                    self.env['cash.book.info'].create({
                        'date': self.payment_date,
                        'account_journal': line.journal_id.id,
                        'account': line.journal_id.payment_debit_account_id.id,
                        # 'partner_id': self.partner_id.id,
                        'company_id': 1,
                        'description': line.reason,
                        'payment_type': type_m,
                        # 'partner_type': self.partner_type,
                        'debit': line.amount_total,
                        'credit': 0,
                        'balance': complete + line.amount_total

                    })
                if stmt:
                    stmt.line_ids = payment_list
                    # stmt.button_post()
                    # # stmt.move_line_ids = pay_id_list
                    # stmt.write({'state': 'confirm'})
        self.write({'state': 'validate'})
