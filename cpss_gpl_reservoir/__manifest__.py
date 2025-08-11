# -*- coding: utf-8 -*-
{
    'name': "CPSS GPL - Gestion des Réservoirs",
    'summary': "Module spécialisé pour la gestion des réservoirs et kits GPL",
    'description': """
        CPSS GPL - Gestion des Réservoirs
        ==================================

        **Module spécialisé pour la gestion complète des réservoirs GPL**

        🛢️ **Fonctionnalités Réservoirs :**
        - Suivi détaillé des lots de réservoirs
        - Gestion des dates de fabrication et certification
        - Calcul automatique des dates de réépreuve
        - Alertes d'expiration automatiques
        - Dashboard interactif avec statistiques

        🔧 **Kits GPL :**
        - Gestion des nomenclatures GPL
        - Produits avec traçabilité par lots
        - Configuration automatique des kits

        👥 **Fabricants :**
        - Base de données des fabricants
        - Référencement des modèles
        - Suivi des certifications

        📊 **Analytics :**
        - Dashboard temps réel
        - Statistiques par état/fabricant
        - Rapports d'expiration

        🏢 **Développé par CPSS :**
        Cedar Peak Systems & Solutions - Solutions GPL professionnelles
    """,

    'contributors': [
        'Cedar Peak Systems & Solutions Team',
    ],
    'author': 'Cedar Peak Systems & Solutions (CPSS)',
    'website': 'https://cedarpss.com/',
    'category': 'Industries/Automotive',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',

    # Dépendances
    'depends': [
        'cpss_gpl_base',  # Module de base CPSS
        'product',  # Gestion des produits
        'stock',  # Gestion des stocks et lots
        'mrp',  # Nomenclatures et kits
        'fleet'
    ],

    # Données à charger
    'data': [
        # === SÉCURITÉ ===
        'security/ir.model.access.csv',

        # === DONNÉES DE BASE ===
        'data/product_category_data.xml',
        'data/gpl_fabricant_data.xml',

        # === VUES PRINCIPALES ===
        # Fabricants
        'views/gpl_reservoir_fabricant_views.xml',

        # Produits et templates
        'views/product_template_views.xml',

        # Lots et réservoirs
        'views/stock_lot_views.xml',

        # Nomenclatures
        'views/mrp_bom_views.xml',

        # Dashboard
        'views/gpl_reservoir_dashboard_views.xml',

        # === MENUS ===
        'views/gpl_reservoir_menus.xml',
    ],

    # Assets JavaScript/CSS
    'assets': {
        'web.assets_backend': [
            'cpss_gpl_reservoir/static/src/css/reservoir_dashboard.css',
            'cpss_gpl_reservoir/static/src/js/reservoir_dashboard.js',
        ],
    },

    # Configuration
    'installable': True,
    'application': False,  # Module d'extension
    'auto_install': False,
    'sequence': 20,

    # Métadonnées
    'support': 'support@cedarpss.com',
    'maintainer': 'CPSS',

    # Images
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
}
