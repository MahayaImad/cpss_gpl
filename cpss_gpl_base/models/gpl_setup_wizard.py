# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class GplSetupWizard(models.TransientModel):
    _name = 'gpl.setup.wizard'
    _description = "Assistant de Configuration GPL CPSS"

    # === ÉTAPES DU WIZARD ===
    step = fields.Selection([
        ('company', 'Informations Entreprise'),
        ('workflow', 'Configuration Workflow'),
        ('notifications', 'Notifications'),
        ('complete', 'Configuration Terminée')
    ], string="Étape", default='company', required=True)

    # === INFORMATIONS ENTREPRISE ===
    company_name = fields.Char(
        string="Nom de l'entreprise",
        required=True,
        help="Nom qui apparaîtra sur tous les documents GPL"
    )

    company_license = fields.Char(
        string="Numéro d'agrément GPL",
        required=True,
        help="Numéro d'agrément officiel délivré par les autorités"
    )

    company_phone = fields.Char(string="Téléphone")
    company_email = fields.Char(string="Email")
    company_address = fields.Text(string="Adresse complète")

    # === CONFIGURATION WORKFLOW ===
    use_advanced_workflow = fields.Boolean(
        string="Workflow avancé",
        default=False,
        help="Activer le workflow détaillé avec plus d'étapes de validation"
    )

    require_appointment = fields.Boolean(
        string="RDV obligatoire",
        default=True,
        help="Rendre les rendez-vous obligatoires"
    )

    default_warranty_months = fields.Integer(
        string="Garantie par défaut (mois)",
        default=24,
        help="Durée de garantie standard"
    )

    # === PARAMÈTRES RÉSERVOIRS ===
    reservoir_test_frequency = fields.Integer(
        string="Fréquence test (années)",
        default=5,
        help="Fréquence des tests de réservoir"
    )

    reservoir_max_age = fields.Integer(
        string="Âge maximum (années)",
        default=15,
        help="Âge maximum autorisé pour un réservoir"
    )

    # === NOTIFICATIONS ===
    enable_notifications = fields.Boolean(
        string="Activer les notifications",
        default=True
    )

    notification_email = fields.Char(
        string="Email notifications",
        help="Email pour recevoir les alertes système"
    )

    notification_test_days = fields.Integer(
        string="Alerte avant expiration (jours)",
        default=30,
        help="Nombre de jours avant expiration pour alerter"
    )

    # === DONNÉES D'EXEMPLE ===
    create_demo_data = fields.Boolean(
        string="Créer des données d'exemple",
        default=True,
        help="Créer quelques exemples pour tester le système"
    )

    from_settings = fields.Boolean(string="Lancé depuis paramètres", default=False)

    @api.constrains('company_license')
    def _check_company_license(self):
        for record in self:
            if record.company_license and len(record.company_license) < 3:
                raise ValidationError(_("Le numéro d'agrément doit contenir au moins 3 caractères."))

    @api.constrains('notification_email')
    def _check_notification_email(self):
        for record in self:
            if record.notification_email and '@' not in record.notification_email:
                raise ValidationError(_("L'email de notification n'est pas valide."))

    def action_next_step(self):
        """Passe à l'étape suivante"""
        self.ensure_one()

        if self.step == 'company':
            self._validate_company_step()
            self.step = 'workflow'
        elif self.step == 'workflow':
            self.step = 'notifications'
        elif self.step == 'notifications':
            self.step = 'complete'
            self._apply_configuration()

        return self._return_wizard_action()

    def action_previous_step(self):
        """Retourne à l'étape précédente"""
        self.ensure_one()

        if self.step == 'notifications':
            self.step = 'workflow'
        elif self.step == 'workflow':
            self.step = 'company'
        elif self.step == 'complete':
            self.step = 'notifications'

        return self._return_wizard_action()

    def _validate_company_step(self):
        """Valide les informations de l'entreprise"""
        if not self.company_name:
            raise UserError(_("Le nom de l'entreprise est obligatoire."))
        if not self.company_license:
            raise UserError(_("Le numéro d'agrément GPL est obligatoire."))

    def _apply_configuration(self):
        """Applique la configuration choisie"""
        params = self.env['ir.config_parameter'].sudo()

        # Informations entreprise
        params.set_param('cpss_gpl.company_name', self.company_name)
        params.set_param('cpss_gpl.company_license', self.company_license)

        # Workflow
        params.set_param('cpss_gpl.use_advanced_workflow', self.use_advanced_workflow)
        params.set_param('cpss_gpl.require_appointment', self.require_appointment)
        params.set_param('cpss_gpl.default_warranty_months', self.default_warranty_months)

        # Réservoirs
        params.set_param('cpss_gpl.reservoir_test_frequency', self.reservoir_test_frequency)
        params.set_param('cpss_gpl.reservoir_max_age', self.reservoir_max_age)

        # Notifications
        params.set_param('cpss_gpl.notification_email', self.notification_email or '')
        params.set_param('cpss_gpl.notification_test_days', self.notification_test_days)

        # Créer les données d'exemple si demandé
        if self.create_demo_data:
            self._create_demo_data()

        # Marquer la configuration comme terminée
        params.set_param('cpss_gpl.setup_complete', True)

    def _create_demo_data(self):
        """Crée des données d'exemple pour tester"""
        # Cette méthode sera étendue dans les autres modules
        # pour créer des données spécifiques à chaque module
        pass

    def _return_wizard_action(self):
        """Retourne l'action pour continuer le wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gpl.setup.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_finish(self):
        """Termine la configuration"""
        if self.from_settings:
            # Retourner aux paramètres
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'res.config.settings',
                'view_mode': 'form',
                'target': 'current',
                'context': {'module': 'cpss_gpl_base'}
            }
        else:
            # Aller au menu principal GPL
            return {
                'type': 'ir.actions.act_window_close',
            }

    @api.model
    def is_setup_complete(self):
        """Vérifie si la configuration initiale est terminée"""
        return self.env['ir.config_parameter'].sudo().get_param('cpss_gpl.setup_complete', False)
