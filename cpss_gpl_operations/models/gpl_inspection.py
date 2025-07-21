# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GplInspection(models.Model):
    """
    Gestion des contrôles techniques et validations GPL
    """
    _name = 'gpl.inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Contrôle Technique GPL'
    _order = 'date_inspection desc'

    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default='New',
        copy=False
    )

    # Client et véhicule
    vehicle_id = fields.Many2one(
        'gpl.vehicle',
        string='Véhicule',
        required=True,
        tracking=True
    )
    client_id = fields.Many2one(
        'res.partner',
        string='Client',
        related='vehicle_id.client_id',
        store=True,
        readonly=True
    )

    # Dates
    date_inspection = fields.Date(
        string='Date du contrôle',
        default=fields.Date.today,
        required=True,
        tracking=True
    )
    date_expiry = fields.Date(
        string='Date d\'expiration',
        help="Date d'expiration de la validation"
    )

    # Inspecteur
    inspector_id = fields.Many2one(
        'hr.employee',
        string='Inspecteur',
        domain=[('department_id.name', 'ilike', 'technique')]
    )

    # Type de contrôle
    inspection_type = fields.Selection([
        ('initial', 'Contrôle initial'),
        ('periodic', 'Contrôle périodique'),
        ('special', 'Contrôle spécial'),
        ('validation', 'Validation officielle'),
    ], string='Type de contrôle', default='periodic', required=True)

    # Points de contrôle
    check_reservoir = fields.Selection([
        ('pass', 'Conforme'),
        ('fail', 'Non conforme'),
        ('na', 'Non applicable'),
    ], string='Réservoir', default='na')

    check_piping = fields.Selection([
        ('pass', 'Conforme'),
        ('fail', 'Non conforme'),
        ('na', 'Non applicable'),
    ], string='Tuyauterie', default='na')

    check_injectors = fields.Selection([
        ('pass', 'Conforme'),
        ('fail', 'Non conforme'),
        ('na', 'Non applicable'),
    ], string='Injecteurs', default='na')

    check_electronics = fields.Selection([
        ('pass', 'Conforme'),
        ('fail', 'Non conforme'),
        ('na', 'Non applicable'),
    ], string='Système électronique', default='na')

    check_pressure = fields.Selection([
        ('pass', 'Conforme'),
        ('fail', 'Non conforme'),
        ('na', 'Non applicable'),
    ], string='Test de pression', default='na')

    # Résultat global
    result = fields.Selection([
        ('pass', 'Validé'),
        ('fail', 'Refusé'),
        ('pending', 'En attente'),
    ], string='Résultat', compute='_compute_result', store=True)

    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('scheduled', 'Planifié'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', tracking=True)

    # Commentaires et recommandations
    comments = fields.Text(string='Commentaires')
    recommendations = fields.Text(string='Recommandations')

    # Certificat
    certificate_number = fields.Char(
        string='N° de certificat',
        help="Numéro du certificat de validation délivré"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gpl.inspection') or 'New'
        return super().create(vals_list)

    @api.depends('check_reservoir', 'check_piping', 'check_injectors',
                 'check_electronics', 'check_pressure')
    def _compute_result(self):
        for record in self:
            checks = [
                record.check_reservoir,
                record.check_piping,
                record.check_injectors,
                record.check_electronics,
                record.check_pressure
            ]

            # Filtrer les checks applicables (non 'na')
            applicable_checks = [c for c in checks if c != 'na']

            if not applicable_checks:
                record.result = 'pending'
            elif any(c == 'fail' for c in applicable_checks):
                record.result = 'fail'
            else:
                record.result = 'pass'

    def action_start(self):
        """Démarre le contrôle"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Le contrôle doit être en brouillon pour être démarré."))

        if not self.inspector_id:
            raise UserError(_("Veuillez assigner un inspecteur."))

        self.state = 'in_progress'

    def action_validate(self):
        """Valide le contrôle"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Le contrôle doit être en cours pour être validé."))

        if self.result == 'pending':
            raise UserError(_("Veuillez compléter tous les points de contrôle."))

        # Générer un numéro de certificat si validation réussie
        if self.result == 'pass' and self.inspection_type == 'validation':
            if not self.certificate_number:
                self.certificate_number = self.env['ir.sequence'].next_by_code('gpl.certificate') or 'CERT-001'

            # Calculer la date d'expiration (2 ans par défaut)
            from dateutil.relativedelta import relativedelta
            self.date_expiry = fields.Date.today() + relativedelta(years=2)

            # Créer une activité pour notifier de la validation
            if self.vehicle_id:
                self.vehicle_id.message_post(
                    body=f"Contrôle technique validé - Certificat N° {self.certificate_number}",
                    subject="Validation GPL réussie"
                )

        self.state = 'done'

    def action_cancel(self):
        """Annule le contrôle"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Un contrôle terminé ne peut pas être annulé."))

        self.state = 'cancel'

    def action_print_certificate(self):
        """Imprime le certificat de validation"""
        self.ensure_one()
        if self.state != 'done' or self.result != 'pass':
            raise UserError(_("Le certificat ne peut être imprimé que pour un contrôle validé."))

        return self.env.ref('cpss_gpl_operations.report_gpl_inspection_certificate').report_action(self)
