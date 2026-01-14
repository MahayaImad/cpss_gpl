# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Copyright (c) 2019

from odoo import fields, models, api,_
from ..utils import StampCalculator


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    payment_type = fields.Char('Type de paiement')
    timbre = fields.Monetary(string='Timbre', store=True, readonly=True)


    @api.onchange('payment_term_id')
    def onchange_payment_term(self):
        for order in self:
            if not order.payment_term_id:
                order.update({
                    'payment_type': False,
                })
                return
            values = {
                'payment_type': order.payment_term_id and order.payment_term_id.payment_type or False,
            }
            order.update(values)


    @api.depends('order_line.price_subtotal', 'company_id', 'payment_term_id')
    def _amount_all(self):
        super()._amount_all()
        for order in self:
            amount_timbre = order.amount_total
            if (order.payment_term_id and order.payment_term_id.payment_type == 'cash'):
                c_timbre = StampCalculator(self.env).calculate(amount_timbre)
                order.timbre = c_timbre['timbre']
                order.amount_total = c_timbre['amount_timbre']
                order.amount_total_cc = c_timbre['amount_timbre']
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

