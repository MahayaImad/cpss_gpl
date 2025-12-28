{
    'name': 'CPSS GPL - Opérations & Services',
    'version': '1.0.0',
    'category': 'Services/GPL',
    'summary': 'Gestion simplifiée des opérations GPL : installations, réparations et contrôles',
    'description': """
CPSS GPL - Module Opérations & Services
=======================================

Ce module gère les opérations quotidiennes du centre GPL :
- Installations de systèmes GPL
- Réparations et maintenance
- Contrôles techniques et validations
- Réépreuves de réservoirs

Caractéristiques principales :
- Flux de travail simplifié
- Interface utilisateur intuitive
- Suivi des interventions
- Gestion des techniciens
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
        'base',
        'mail',  # Pour le chatter et les suivis
        'hr',  # Pour les techniciens
        'stock',  # Pour les réservoirs (stock.lot)
        'sale',
        #'cpss_gpl_base',
        #'cpss_gpl_reservoir',  # Module de reservoir CPSS
        'cpss_gpl_garage',  # Module de garage CPSS
    ],

    'data': [
        # Security
        'security/ir.model.access.csv',

        # Views
        'views/gpl_installation_views.xml',
        'views/gpl_repair_views.xml',
        'views/gpl_inspection_views.xml',
        'views/gpl_reservoir_testing_views.xml',
        'views/gpl_bordereau_views.xml',
        'views/gpl_operations_menus.xml',

    ],
    'assets': {
        'web.assets_frontend': [
            'cpss_gpl_operations/static/src/css/kanban_modern.css',
        ],
        'web.assets_backend': [
            'cpss_gpl_operations/static/src/css/kanban_modern.css',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,

    # Icône du module dans les paramètres
    'web_icon': 'cpss_gpl_operations,static/description/icon.png',

    # Métadonnées
    'support': 'support@cedarpss.com',
    'maintainer': 'CPSS',

    # Images
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
}
