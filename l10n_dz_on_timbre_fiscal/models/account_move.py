# -*- coding: utf-8 -*-

from email.policy import default

from odoo import fields, models, api,_
from odoo.exceptions import UserError
from ..utils import StampCalculator


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_type = fields.Char('Type de paiement')
    timbre = fields.Monetary(string='Timbre', store=True, readonly=True)
    timbre_signed = fields.Monetary(string='Timbre signé', store=True, readonly=True)

    invoice_line_ids_visible = fields.One2many(
        comodel_name='account.move.line',
        inverse_name='move_id',
        string='Invoice Lines (Filtered)',
        compute='_compute_invoice_line_ids_visible',
    )

    @api.depends('invoice_line_ids')
    def _compute_invoice_line_ids_visible(self):
        for move in self:
            move.invoice_line_ids_visible = move.invoice_line_ids.filtered(lambda l: not l.isStamp)


    @api.onchange('invoice_payment_term_id')
    def onchange_payment_term(self):
        for move in self :
            if not move.invoice_payment_term_id:
                move.update({
                    'payment_type': False,
                })
                self.deleteTimbreLine()
                return
            values = {
                'payment_type': move.invoice_payment_term_id and move.invoice_payment_term_id.payment_type or False,
            }
            move.update(values)
            if (move.invoice_payment_term_id and move.invoice_payment_term_id.payment_type != 'cash'):
                self.deleteTimbreLine()


    def deleteTimbreLine(self):
        for move in self:
            timbre_account_id = StampCalculator(self.env).GetStampAccount(move.move_type)
            timbre_lines = move.line_ids.filtered(
                lambda l: l.account_id.id == int(timbre_account_id))

            move.line_ids = move.line_ids - timbre_lines


    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.origin_payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.origin_payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'state',
        'invoice_payment_term_id'
    )
    def _compute_amount(self):
        super()._compute_amount()
        for move in self:
            timbre_account_id = StampCalculator(self.env).GetStampAccount(move.move_type)
            sign = move.direction_sign
            total_untaxed = 0.0
            base_timbre = 0.0

            if (move.invoice_payment_term_id and move.invoice_payment_term_id.payment_type == 'cash'):
                for line in move.line_ids:
                    if move.is_invoice(True):
                        if line.display_type in ('product', 'rounding') and line.account_id.id != int(timbre_account_id):
                            total_untaxed += line.amount_currency

                move.amount_untaxed = abs(total_untaxed)
                base_timbre = move.amount_untaxed + move.amount_tax
                c_timbre = StampCalculator(self.env).calculate(base_timbre)
                move.timbre = c_timbre['timbre']
                move.timbre_signed = -sign * move.timbre
                move.amount_total = c_timbre['amount_timbre']
                move.amount_total_signed = -sign * move.amount_total
                move.amount_total_in_currency_signed = -sign * move.amount_total
                move.amount_residual = c_timbre['amount_timbre']
                move.amount_residual_signed = -sign * move.amount_residual
                move.amount_untaxed_signed = -sign * move.amount_untaxed
                move.amount_untaxed_in_currency_signed = -sign * move.amount_untaxed
            else:
                move.timbre = 0
                move.timbre_signed = 0


    @api.depends_context('lang')
    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id'
    )
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for move in self:
            if move.is_invoice():
                move.tax_totals['total_amount_currency'] = move.amount_total
                move.tax_totals['total_amount'] = move.amount_total
                if move.tax_totals.get('subtotals') and len(move.tax_totals['subtotals']) > 0:
                    move.tax_totals['subtotals'][0]['base_amount_currency'] = move.amount_untaxed
                    move.tax_totals['subtotals'][0]['base_amount'] = move.amount_untaxed
                move.tax_totals['base_amount_currency'] = move.amount_untaxed
                move.tax_totals['base_amount'] = move.amount_untaxed

                if (move.invoice_payment_term_id and move.invoice_payment_term_id.payment_type == 'cash'):
                    move.tax_totals.setdefault('subtotals', []).append({
                        'name': "Timbre Fiscal",
                        'amount': move.timbre,
                        'base_amount': move.timbre,
                        'base_amount_currency': move.timbre,
                        'form_label': "Timbre Fiscal",
                        'tax_ids': [],
                        'display': True,
                        'sequence': 1000,
                        'code': "timbre",
                        'group': "timbre",
                        'tax_groups': [],
                    })


    def action_post(self):
        for move in self:
            if move.is_invoice() :
                if (move.invoice_payment_term_id and move.invoice_payment_term_id.payment_type == 'cash'):
                    timbre_account_id = StampCalculator(self.env).GetStampAccount(move.move_type)
                    timbre_account = self.env['account.account'].browse(int(timbre_account_id))
                    if not timbre_account:
                        raise UserError("Veuillez configurer les comptes pour le timbre.")

                    timbre_amount = move.timbre
                    sign = move.direction_sign
                    partner_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable'
                                                                 or l.account_id.account_type == 'liability_payable')

                    if not any(line.account_id.id == int(timbre_account_id) for line in move.line_ids):
                        self.write({
                            'line_ids': [
                                (1, partner_line.id, {
                                    'debit': partner_line.debit + (timbre_amount if -sign > 0 else 0.0),
                                    'credit': partner_line.credit + (0.0 if -sign > 0 else timbre_amount),
                                }),
                                (0, 0, {
                                    'name': 'Timbre Fiscal',
                                    'account_id': timbre_account.id,
                                    'debit': 0.0 if -sign > 0 else timbre_amount,
                                    'credit': timbre_amount if -sign > 0 else 0.0,
                                    'price_unit' : timbre_amount,
                                    'partner_id': move.partner_id.id,
                                    'isStamp' : True,
                                })
                            ]
                        })
                    else :
                        stamp_line = move.line_ids.filtered(lambda l: l.account_id.id == timbre_account.id)
                        self.write({
                            'line_ids': [
                                (1, partner_line.id, {
                                    'debit': partner_line.debit + (timbre_amount if -sign > 0 else 0.0),
                                    'credit': partner_line.credit + (0.0 if -sign > 0 else timbre_amount),
                                }),
                                (1, stamp_line.id, {
                                    'name': 'Timbre Fiscal',
                                    'debit': 0.0 if -sign > 0 else timbre_amount,
                                    'credit': timbre_amount if -sign > 0 else 0.0,
                                    'price_unit' : timbre_amount,
                                    'partner_id': move.partner_id.id,
                                    'isStamp' : True,
                                })
                            ]
                        })


        return super().action_post()

    def button_draft(self):
        super().button_draft()

        for move in self:
            timbre_account_id = StampCalculator(self.env).GetStampAccount(move.move_type)
            timbre_line = move.line_ids.filtered(lambda l: l.account_id.id == int(timbre_account_id))
            partner_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable' or l.account_id.account_type == 'liability_payable')

            if timbre_line :
                timbre_amount = move.timbre
                sign = move.direction_sign

                self.write({
                    'line_ids': [
                        (1, partner_line.id, {
                            'debit': partner_line.debit - (timbre_amount if -sign > 0 else 0.0),
                            'credit': partner_line.credit - (0.0 if -sign > 0 else timbre_amount),
                        }),
                        (1, timbre_line.id, {
                            'price_unit' : 0.0,
                            'debit' : 0.0,
                            'credit' : 0.0,
                        })]
                })
        self.deleteTimbreLine()

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    isStamp = fields.Boolean(default=False)
