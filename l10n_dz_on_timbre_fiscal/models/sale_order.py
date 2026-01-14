# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Copyright (c) 2010


from odoo import fields, models, api,_
from ..utils.stamp_calculator import StampCalculator


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_type = fields.Char('Type de paiement')
    timbre = fields.Monetary(string='Timbre', store=True, readonly=True)


    @api.onchange('payment_term_id')
    def onchange_payment_term(self):
        if not self.payment_term_id:
            self.update({
                'payment_type': False,
            })
            return
        values = {
            'payment_type': self.payment_term_id and self.payment_term_id.payment_type or False,
        }
        self.update(values)


    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'payment_term_id')
    def _compute_amounts(self):
        super()._compute_amounts()
        for order in self:
            amount_timbre = order.amount_total
            if (order.payment_term_id and order.payment_term_id.payment_type == 'cash'):
                c_timbre = StampCalculator(self.env).calculate(amount_timbre)
                order.timbre = c_timbre['timbre']
                order.amount_total = c_timbre['amount_timbre']
            else :
                order.timbre = 0

    @api.depends_context('lang')
    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'payment_term_id')
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for order in self:
            order.tax_totals['total_amount_currency'] = order.amount_total
            order.tax_totals['total_amount'] = order.amount_total

            if (order.payment_term_id and order.payment_term_id.payment_type == 'cash'):
                order.tax_totals.setdefault('subtotals', []).append({
                    'name': "Timbre Fiscal",
                    'amount': order.timbre,
                    'base_amount': order.timbre,
                    'base_amount_currency': order.timbre,
                    'form_label': "Timbre Fiscal",
                    'tax_ids': [],
                    'display': True,
                    'sequence': 1000,
                    'code': "timbre",
                    'group': "timbre",
                    'tax_groups': [],
                })



    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        res['payment_type'] =  self.payment_type
        return res

