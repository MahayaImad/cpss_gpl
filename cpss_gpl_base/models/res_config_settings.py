from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

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
        default=30,
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

    # === MODE SIMPLIFIÉ ===
    gpl_simplified_mode = fields.Boolean(
        string="Mode Simplifié GPL",
        config_parameter='cpss_gpl.simplified_mode',
        default=True,
        help="Active la création automatique : Commande → Livraison → Facture"
    )

    # === PARAMÈTRES NOTIFICATIONS ===
    gpl_notification_test_days = fields.Integer(
        string="Alerte test réservoir (jours)",
        config_parameter='cpss_gpl.notification_test_days',
        default=30,
        help="Nombre de jours avant expiration pour envoyer l'alerte"
    )

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
            gpl_reservoir_test_frequency=int(params.get_param('cpss_gpl.reservoir_test_frequency', 5)),
            gpl_reservoir_max_age=int(params.get_param('cpss_gpl.reservoir_max_age', 15)),
            gpl_control_periodic=int(params.get_param('cpss_gpl.gpl_control_periodic', 36)),
            gpl_simplified_mode=params.get_param('cpss_gpl.simplified_mode', True),
            gpl_notification_test_days=int(params.get_param('cpss_gpl.notification_test_days', 30)),
        )
        return res

    def set_values(self):
        super().set_values()

        # Sauvegarder les paramètres système
        params = self.env['ir.config_parameter'].sudo()

        params.set_param('cpss_gpl.reservoir_test_frequency', self.gpl_reservoir_test_frequency)
        params.set_param('cpss_gpl.gpl_control_periodic', self.gpl_control_periodic)
        params.set_param('cpss_gpl.reservoir_max_age', self.gpl_reservoir_max_age)
        params.set_param('cpss_gpl.simplified_mode', self.gpl_simplified_mode)
        params.set_param('cpss_gpl.notification_test_days', self.gpl_notification_test_days)

        # Sauvegarder automatiquement le workflow avancé (inverse du mode simplifié)
        params.set_param('cpss_gpl.use_advanced_workflow', not self.gpl_simplified_mode)
