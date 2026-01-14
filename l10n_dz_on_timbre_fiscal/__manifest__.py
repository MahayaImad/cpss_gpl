# -*- coding: utf-8 -*-
{

    'name': "Timbre fiscal",
    'summary': "Timbre fiscal",
    'description':
        """
        Ce module permet de gérer automatiquement le timbre fiscal pour les paiements
        en espèce sur les factures et avoirs clients/fournisseurs en Algérie,
        conformément à la Loi de Finances 2025.

        Fonctionnalités:
        ----------------
        * Application automatique du droit de timbre sur paiements espèce
        * Configuration des comptes comptables par société
        * Affichage du timbre sur les factures et avoirs
        * Gestion des conditions de paiement
        * Compatible avec la réglementation algérienne (LF 2025)

        Module Original:
        ----------------
        * Auteur original: OPENNEXT Technology
        * Website: http://www.opennext-dz.com

        Adaptation Odoo 17:
        -------------------
        * Maintenu par: CPSS
        * Version: 17.0.1.0
        * Compatible Odoo 17
            """
    ,
    'author': "OPENNEXT Technology",
    'website': "http://www.opennext-dz.com",
    'category': 'Accounting',
    'version': '17.0.1.0',

    'depends': ['base',
                'account',
                'sale_management',
                'purchase'
                ],

    'data': [
        'security/ir.model.access.csv',
        'data/timbre_data.xml',
        'views/account_move_view.xml',
        'views/purchase_view.xml',
        'views/sale_view.xml',
        'views/res_config_settings_views.xml',
        'views/report_invoice_inherit.xml',
    ],

    'images': [
        'static/description//banner.png',
        'static/description//icone.ico',
    ],

    "license": "LGPL-3",
    'price': 0.0,
    'currency': 'USD',

    'installable': True,
    'application': False,
    'auto_install': False,
}
