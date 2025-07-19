# -*- coding: utf-8 -*-

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

    # === PARAMÈTRES WORKFLOW ===
    gpl_use_advanced_workflow = fields.Boolean(
        string="Utiliser le workflow avancé",
        config_parameter='cpss_gpl.use_advanced_workflow',
        default=False,
        help="Activer le workflow détaillé avec plus d'étapes de validation"
    )

    gpl_require_appointment = fields.Boolean(
        string="RDV obligatoire",
        config_parameter='cpss_gpl.require_appointment',
        default=True,
        help="Rendre les rendez-vous obligatoires pour les interventions"
    )

    # === PARAMÈTRES NOTIFICATIONS ===
    gpl_notification_test_days = fields.Integer(
        string="Alerte test réservoir (jours)",
        config_parameter='cpss_gpl.notification_test_days',
        default=30,
        help="Nombre de jours avant expiration pour envoyer l'alerte"
    )

    gpl_notification_email = fields.Char(
        string="Email notifications",
        config_parameter='cpss_gpl.notification_email',
        help="Email pour recevoir les notifications système"
    )

    # === PARAMÈTRES RAPPORTS ===
    gpl_certificate_template = fields.Selection([
        ('standard', 'Standard CPSS'),
        ('custom', 'Personnalisé'),
    ], string="Template certificats",
        config_parameter='cpss_gpl.certificate_template',
        default='standard',
        help="Template à utiliser pour les certificats")

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
            gpl_use_advanced_workflow=params.get_param('cpss_gpl.use_advanced_workflow', False),
            gpl_require_appointment=params.get_param('cpss_gpl.require_appointment', True),
            gpl_notification_test_days=int(params.get_param('cpss_gpl.notification_test_days', 30)),
            gpl_notification_email=params.get_param('cpss_gpl.notification_email', ''),
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
        params.set_param('cpss_gpl.reservoir_max_age', self.gpl_reservoir_max_age)
        params.set_param('cpss_gpl.use_advanced_workflow', self.gpl_use_advanced_workflow)
        params.set_param('cpss_gpl.require_appointment', self.gpl_require_appointment)
        params.set_param('cpss_gpl.notification_test_days', self.gpl_notification_test_days)
        params.set_param('cpss_gpl.notification_email', self.gpl_notification_email or '')
        params.set_param('cpss_gpl.certificate_template', self.gpl_certificate_template)

    def action_run_setup_wizard(self):
        """Lance l'assistant de configuration GPL"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assistant de Configuration GPL'),
            'res_model': 'gpl.setup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_from_settings': True}
        }
