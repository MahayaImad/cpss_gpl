from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # === PARAMÈTRES GÉNÉRAUX GPL ===
    gpl_company_name = fields.Char(
        string="Nom de l'entreprise GPL",
        config_parameter='cpss_gpl.company_name',
        help="Nom affiché sur les certificats et rapports"
    )

    gpl_company_license = fields.Char(
        string="Numéro d'agrément GPL",
        config_parameter='cpss_gpl.company_license',
        help="Numéro d'agrément officiel pour les installations GPL"
    )

    gpl_default_warranty_months = fields.Integer(
        string="Garantie par défaut (mois)",
        config_parameter='cpss_gpl.default_warranty_months',
        default=24,
        help="Durée de garantie par défaut pour les installations GPL"
    )

    # === PARAMÈTRES RÉSERVOIRS ===
    gpl_reservoir_test_frequency = fields.Integer(
        string="Fréquence test réservoir (années)",
        config_parameter='cpss_gpl.reservoir_test_frequency',
        default=5,
        help="Fréquence des tests de réservoir (par défaut : 5 ans)"
    )

    gpl_reservoir_max_age = fields.Integer(
        string="Âge maximum réservoir (années)",
        config_parameter='cpss_gpl.reservoir_max_age',
        default=15,
        help="Âge maximum autorisé pour un réservoir GPL"
    )

    gpl_control_periodic = fields.Integer(
        string="Contrôle périodique - triennal (mois)",
        config_parameter='cpss_gpl.control_periodic',
        default=36,
        help="Contrôle périodique obligatoire de l'installation par l'ingénieur des mines"
    )

    # === PARAMÈTRES WORKFLOW ===
    gpl_use_advanced_workflow = fields.Boolean(
        string="Workflow avancé",
        compute='_compute_advanced_workflow',
        store=False,
        readonly=True,
        help="Automatiquement défini comme l'inverse du mode simplifié"
    )

    gpl_require_appointment = fields.Boolean(
        string="RDV obligatoire",
        config_parameter='cpss_gpl.require_appointment',
        default=True,
        help="Rendre les rendez-vous obligatoires pour les interventions"
    )

    # === MODE SIMPLIFIÉ ===
    gpl_simplified_mode = fields.Boolean(
        string="Mode Simplifié GPL",
        config_parameter='cpss_gpl.simplified_mode',
        default=True,
        help="Active la création automatique : Commande → Livraison → Facture"
    )

    gpl_default_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string="Entrepôt par défaut",
        config_parameter='cpss_gpl.default_warehouse_id',
        help="Entrepôt utilisé pour les livraisons automatiques"
    )

    gpl_default_pricelist_id = fields.Many2one(
        'product.pricelist',
        string="Liste de prix par défaut",
        config_parameter='cpss_gpl.default_pricelist_id',
        help="Liste de prix pour les commandes automatiques"
    )

    # === PARAMÈTRES NOTIFICATIONS ===
    gpl_notification_test_days = fields.Integer(
        string="Alerte test réservoir (jours)",
        config_parameter='cpss_gpl.notification_test_days',
        default=30,
        help="Nombre de jours avant expiration pour envoyer l'alerte"
    )

    # === PARAMÈTRES RAPPORTS ===
    gpl_certificate_template = fields.Selection([
        ('standard', 'Standard CPSS'),
        ('custom', 'Personnalisé'),
    ], string="Template certificats",
        config_parameter='cpss_gpl.certificate_template',
        default='standard',
        help="Template à utiliser pour les certificats")

    @api.depends('gpl_simplified_mode')
    def _compute_advanced_workflow(self):
        """Le workflow avancé est automatiquement l'inverse du mode simplifié"""
        for record in self:
            record.gpl_use_advanced_workflow = not record.gpl_simplified_mode

    @api.model
    def get_values(self):
        res = super().get_values()

        # Récupérer les paramètres système
        params = self.env['ir.config_parameter'].sudo()

        res.update(
            gpl_company_name=params.get_param('cpss_gpl.company_name', ''),
            gpl_company_license=params.get_param('cpss_gpl.company_license', ''),
            gpl_default_warranty_months=int(params.get_param('cpss_gpl.default_warranty_months', 24)),
            gpl_reservoir_test_frequency=int(params.get_param('cpss_gpl.reservoir_test_frequency', 5)),
            gpl_reservoir_max_age=int(params.get_param('cpss_gpl.reservoir_max_age', 15)),
            gpl_control_periodic=int(params.get_param('cpss_gpl.gpl_control_periodic', 36)),
            gpl_require_appointment=params.get_param('cpss_gpl.require_appointment', True),
            gpl_simplified_mode=params.get_param('cpss_gpl.simplified_mode', True),
            gpl_default_warehouse_id=int(params.get_param('cpss_gpl.default_warehouse_id', 0)) or False,
            gpl_default_pricelist_id=int(params.get_param('cpss_gpl.default_pricelist_id', 0)) or False,
            gpl_notification_test_days=int(params.get_param('cpss_gpl.notification_test_days', 30)),
            gpl_certificate_template=params.get_param('cpss_gpl.certificate_template', 'standard'),
        )
        return res

    def set_values(self):
        super().set_values()

        # Sauvegarder les paramètres système
        params = self.env['ir.config_parameter'].sudo()

        params.set_param('cpss_gpl.company_name', self.gpl_company_name or '')
        params.set_param('cpss_gpl.company_license', self.gpl_company_license or '')
        params.set_param('cpss_gpl.default_warranty_months', self.gpl_default_warranty_months)
        params.set_param('cpss_gpl.reservoir_test_frequency', self.gpl_reservoir_test_frequency)
        params.set_param('cpss_gpl.gpl_control_periodic', self.gpl_control_periodic)
        params.set_param('cpss_gpl.reservoir_max_age', self.gpl_reservoir_max_age)
        params.set_param('cpss_gpl.require_appointment', self.gpl_require_appointment)
        params.set_param('cpss_gpl.simplified_mode', self.gpl_simplified_mode)
        params.set_param('cpss_gpl.default_warehouse_id',
                         self.gpl_default_warehouse_id.id if self.gpl_default_warehouse_id else 0)
        params.set_param('cpss_gpl.default_pricelist_id',
                         self.gpl_default_pricelist_id.id if self.gpl_default_pricelist_id else 0)
        params.set_param('cpss_gpl.notification_test_days', self.gpl_notification_test_days)
        params.set_param('cpss_gpl.certificate_template', self.gpl_certificate_template)

        # Sauvegarder automatiquement le workflow avancé (inverse du mode simplifié)
        params.set_param('cpss_gpl.use_advanced_workflow', not self.gpl_simplified_mode)
