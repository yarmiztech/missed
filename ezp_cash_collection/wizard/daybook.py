from odoo import api, fields, models, tools, _
from datetime import date
from datetime import timedelta
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class DaybookSummary(models.TransientModel):
    _name = "daybook.summary"
    _description = "Daybook Reserved"

    def _get_default_start_date(self):
        year = fields.Date.from_string(fields.Date.today()).strftime('%Y')
        return '{}-01-01'.format(year)

    #
    # def _get_default_end_date(self):
    #     date = fields.Date.from_string(fields.Date.today())
    #     return date.strftime('%Y') + '-' + date.strftime('%m') + '-' + date.strftime('%d')

    # start_date = fields.Date(string='Start Date', required=True, default=_get_default_start_date)
    start_date = fields.Date(string='Date', required=True, default=fields.Date.context_today, )

    # end_date = fields.Date(string='End Date', required=True, default=_get_default_end_date)
    # estimator = fields.Many2one('res.partner', domain=[('estimator', '=', True)])

    # @api.multi
    def print_report(self):
        return self.env.ref('ezp_cash_collection.daybook_summary_record').report_action(self)

    def cash_executive(self):
        return self.env['executive.collection'].search([('payment_date', '=', self.start_date)])

    # def cash_direct_executive(self):
    #     return self.env['data.entry'].search([('payment_date','=',self.start_date)])
    def cash_direct_executive(self):
        return self.env['cashier.direct.collection'].search([('payment_date', '=', self.start_date)])

    def cash_purchase(self):
        return self.env['purchase.payments'].search([('payment_date', '=', self.start_date)])

    def cash_cheque_purchase(self):
        return self.env['neft.rtgs.collection'].search([('cleared_date', '=', self.start_date),('partner_type', '=', 'supplier')])

    def cash_expense(self):
        return self.env['expense.payments'].search([('payment_date', '=', self.start_date)])
    def cash_company_expense(self):
        return self.env['expenses.disc'].search([('creates_date', '=', self.start_date)])

    # def cash_check_executive(self):
    #     return self.env['executive.cheque.collection'].search([('payment_date', '=', self.start_date)])
    def cash_check_executive(self):
        return self.env['today.cheques'].search([('payment_date', '=', self.start_date)])

    def total(self):
        amount = 0
        for ev in self.env['executive.collection'].search([('payment_date', '=', self.start_date)]):
            amount += sum(ev.mapped('partner_invoices').mapped('amount_total'))
        return amount

    def direct_total(self):
        amount = 0
        for ev in self.env['cashier.direct.collection'].search([('payment_date', '=', self.start_date)]):
            amount += sum(ev.mapped('partner_invoices').mapped('amount_total'))
        return amount

    def purchase_total(self):
        amount = 0
        for ev in self.env['purchase.payments'].search([('payment_date', '=', self.start_date)]):
            amount += sum(ev.mapped('partner_invoices').mapped('amount_total'))
        amount += sum(self.env['neft.rtgs.collection'].search([('cleared_date', '=', self.start_date),('partner_type', '=', 'supplier')]).mapped('amount_total'))

        return amount

    def expense_total(self):
        amount = 0
        for ev in self.env['expense.payments'].search([('payment_date', '=', self.start_date)]):
            amount += sum(ev.mapped('partner_invoices').mapped('amount_total'))

        for each in self.env['expenses.disc'].search([('creates_date', '=', self.start_date)]):
            amount += sum(each.mapped('freight_lines').mapped('amount'))

        return amount

    def check_total(self):
        amount = 0
        # for ev in self.env['executive.cheque.collection'].search([('payment_date', '=', self.start_date)]):
        #     amount += sum(ev.mapped('partner_invoices').mapped('amount_total'))
        for ev in self.env['today.cheques'].search([('payment_date', '=', self.start_date)]):
            amount += sum(ev.mapped('today_lines').mapped('amount_total'))
        return amount

    def totall_collection(self):
        amount = 0
        # for ev in self.env['executive.cheque.collection'].search([('payment_date', '=', self.start_date)]):
        #     amount += sum(ev.mapped('partner_invoices').mapped('amount_total'))
        for e_ev in self.env['executive.collection'].search([('payment_date', '=', self.start_date)]):
            amount += sum(e_ev.mapped('partner_invoices').mapped('amount_total'))
        for d_ev in self.env['data.entry'].search([('payment_date', '=', self.start_date)]):
            amount += sum(d_ev.mapped('partner_invoices').mapped('amount_total'))
        return amount

    def totall_payment(self):
        amount = 0
        for ev in self.env['expense.payments'].search([('payment_date', '=', self.start_date)]):
            amount += sum(ev.mapped('partner_invoices').mapped('amount_total'))
        for ev_p in self.env['purchase.payments'].search([('payment_date', '=', self.start_date)]):
            amount += sum(ev_p.mapped('partner_invoices').mapped('amount_total'))
        return amount

    def bank_names(self):
        print('hhh')
        return self.env['executive.cheque.collection.line'].search([('date', '=', self.start_date)]).mapped(
            'debited_account')

    def today_balance(self, l):
        amount = 0
        records = self.env['collection.cheque'].search([('debited_account', '=', l.id)])
        for line in records:
            amount += line.amount_total
        return amount

    def today_withdraw(self, l):
        # amount =0
        withdraw = 0
        # acc = self.env['account.account'].search(
        #     [('code', '=', l.payment_debit_account_id.code), ('company_id', '=', self.env.user.company_id.id)])
        # amount = sum(self.env['account.move.line'].search([('account_id', '=', acc.id)]).mapped('debit'))
        withdraw = sum(self.env['amount.withdraw'].search([('journal_id', '=', l.id)]).mapped('amount'))

        return withdraw

    def bank_balance(self, l):
        print('hhh')
        acc = self.env['account.account'].search(
            [('code', '=', l.payment_debit_account_id.code), ('company_id', '=', self.env.user.company_id.id)])
        return sum(self.env['account.move.line'].search([('account_id', '=', acc.id)]).mapped('debit'))

    def total_bal(self, l):
        amount = 0
        acc = self.env['account.account'].search(
            [('code', '=', l.payment_debit_account_id.code), ('company_id', '=', self.env.user.company_id.id)])
        bank_bal = sum(self.env['account.move.line'].search([('account_id', '=', acc.id)]).mapped('debit'))
        withdraw = sum(self.env['amount.withdraw'].search([('journal_id', '=', l.id)]).mapped('amount'))
        records = self.env['collection.cheque'].search([('debited_account', '=', l.id)])
        for line in records:
            bank_bal += line.amount_total
        return bank_bal - withdraw

    def totall_collection_bank(self):
        amount = 0
        for ev in self.env['executive.cheque.collection'].search([('payment_date', '=', self.start_date)]):
            for line in ev.partner_invoices:
                if line.state == 'done':
                    if line.check_type == 'cash':
                        date = line.check_date
                    else:
                        date = line.check_manual_date
                    if date == self.start_date:
                        amount += line.amount_total
            # amount += sum(ev.mapped('partner_invoices').mapped('amount_total'),)

        return amount

    def totall_cash_withdraw(self):
        return sum(self.env['amount.withdraw'].search([('payment_date', '=', self.start_date)]).mapped('amount'))

    def totall_m_profit(self):
        amount = 0
        paid = 0
        for e_ev in self.env['executive.collection'].search([('payment_date', '=', self.start_date)]):
            amount += sum(e_ev.mapped('partner_invoices').mapped('amount_total'))
        for d_ev in self.env['data.entry'].search([('payment_date', '=', self.start_date)]):
            amount += sum(d_ev.mapped('partner_invoices').mapped('amount_total'))

        for ev in self.env['executive.cheque.collection'].search([('payment_date', '=', self.start_date)]):
            amount += sum(ev.mapped('partner_invoices').mapped('amount_total'))
        withdraw = sum(self.env['amount.withdraw'].search([('payment_date', '=', self.start_date)]).mapped('amount'))
        for ev in self.env['expense.payments'].search([('payment_date', '=', self.start_date)]):
            paid += sum(ev.mapped('partner_invoices').mapped('amount_total'))
        for ev_p in self.env['purchase.payments'].search([('payment_date', '=', self.start_date)]):
            paid += sum(ev_p.mapped('partner_invoices').mapped('amount_total'))
        neg = withdraw + paid
        return amount - neg

    def cash_withdraw_all(self):
        return self.env['amount.withdraw'].search([('payment_date', '=', self.start_date)])
