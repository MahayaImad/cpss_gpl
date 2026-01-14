# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    default_payment_term_id = fields.Many2one(
        'account.payment.term',
        string="Conditions de paiement par défaut",
        help="Définir les conditions de paiement par défaut pour les nouvelles factures et commandes (ex: Espèce Timbre)"
    )