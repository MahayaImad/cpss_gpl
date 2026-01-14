# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Copyright (c) 2019

from . import models
from . import utils


def post_init_hook(env):
    """
    Hook appelé après l'installation du module.
    Crée les comptes comptables pour le timbre fiscal s'ils n'existent pas.
    """
    # Récupérer toutes les sociétés
    companies = env['res.company'].search([])

    for company in companies:
        # Vérifier/Créer le compte 445750 (Ventes - Passif)
        account_445750 = env['account.account'].search([
            ('code', '=', '445750'),
            ('company_id', '=', company.id)
        ], limit=1)

        if not account_445750:
            account_445750 = env['account.account'].create({
                'code': '445750',
                'name': 'Droits de timbre perçus au profit du Trésor',
                'account_type': 'liability_current',
                'reconcile': False,
                'company_id': company.id,
                'note': 'Compte pour enregistrer les droits de timbre perçus au profit du Trésor Public (Loi de Finances 2025)'
            })

        # Vérifier/Créer le compte 645700 (Achats - Charge)
        account_645700 = env['account.account'].search([
            ('code', '=', '645700'),
            ('company_id', '=', company.id)
        ], limit=1)

        if not account_645700:
            account_645700 = env['account.account'].create({
                'code': '645700',
                'name': 'Droits de timbre',
                'account_type': 'expense',
                'reconcile': False,
                'company_id': company.id,
                'note': 'Compte de charge pour les droits de timbre fiscal (Loi de Finances 2025)'
            })

        # Configurer les paramètres par défaut (seulement pour la première société)
        if company == companies[0]:
            env['ir.config_parameter'].sudo().set_param(
                'l10n_dz_on_timbre_fiscal.stamp_sale_account_id',
                account_445750.id
            )
            env['ir.config_parameter'].sudo().set_param(
                'l10n_dz_on_timbre_fiscal.stamp_purchase_account_id',
                account_645700.id
            )
