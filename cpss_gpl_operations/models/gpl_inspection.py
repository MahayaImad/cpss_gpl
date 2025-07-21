# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class GplInspection(models.Model):
    """
    Gestion des contrôles techniques GPL
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

    # Véhicule et client
    vehicle_id = fields.Many2one(
        'gpl_vehicle',  # CORRIGÉ
        string='Véhicule',
        required=True,
        tracking=True,
        index=True
    )

    client_id = fields.Many2one(
        'res.partner',
        string='Client',
        related='vehicle_id.client_id',
        store=True,
        readonly=True
    )

    # Informations du contrôle
    date_inspection = fields.Date(
        string='Date du contrôle',
        default=fields.Date.today,
        required=True,
        tracking=True
    )

    date_next_inspection = fields.Date(
        string='Prochaine inspection',
        compute='_compute_next_inspection',
        store=True
    )

    validity_months = fields.Integer(
        string='Validité (mois)',
        default=12,
        required=True
    )

    # Type de contrôle
    inspection_type = fields.Selection([
        ('periodic', 'Contrôle périodique'),
        ('initial', 'Contrôle initial'),
        ('counter_visit', 'Contre-visite'),
        ('voluntary', 'Contrôle volontaire'),
        ('administrative', 'Vérification administrative'),
    ], string='Type de contrôle', default='periodic', required=True)

    # Technicien
    technician_id = fields.Many2one(
        'hr.employee',
        string='Contrôleur',
        required=True
    )

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

    check_mounting = fields.Selection([
        ('pass', 'Conforme'),
        ('fail', 'Non conforme'),
        ('na', 'Non applicable'),
    ], string='Fixations et montage', default='na')

    check_ventilation = fields.Selection([
        ('pass', 'Conforme'),
        ('fail', 'Non conforme'),
        ('na', 'Non applicable'),
    ], string='Ventilation', default='na')

    check_marking = fields.Selection([
        ('pass', 'Conforme'),
        ('fail', 'Non conforme'),
        ('na', 'Non applicable'),
    ], string='Marquage et signalisation', default='na')

    # Résultat global
    result = fields.Selection([
        ('pass', 'Validé'),
        ('fail', 'Refusé'),
        ('pending', 'En attente'),
    ], string='Résultat', compute='_compute_result', store=True, tracking=True)

    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('scheduled', 'Planifié'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', tracking=True)

    # Commentaires et recommandations
    observations = fields.Text(
        string='Observations',
        help="Observations et remarques du contrôleur"
    )

    recommendations = fields.Text(
        string='Recommandations',
        help="Travaux recommandés ou points d'attention"
    )

    defects = fields.Text(
        string='Défauts constatés',
        help="Liste des défauts nécessitant une correction"
    )

    # Certificat
    certificate_number = fields.Char(
        string='N° Certificat',
        readonly=True
    )

    certificate_date = fields.Date(
        string='Date du certificat',
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gpl.inspection') or 'New'
        return super().create(vals_list)

    @api.depends('date_inspection', 'validity_months')
    def _compute_next_inspection(self):
        for inspection in self:
            if inspection.date_inspection and inspection.validity_months:
                inspection.date_next_inspection = inspection.date_inspection + timedelta(
                    days=inspection.validity_months * 30)
            else:
                inspection.date_next_inspection = False

    @api.depends('check_reservoir', 'check_piping', 'check_injectors',
                 'check_electronics', 'check_pressure', 'check_mounting',
                 'check_ventilation', 'check_marking')
    def _compute_result(self):
        for inspection in self:
            checks = [
                inspection.check_reservoir,
                inspection.check_piping,
                inspection.check_injectors,
                inspection.check_electronics,
                inspection.check_pressure,
                inspection.check_mounting,
                inspection.check_ventilation,
                inspection.check_marking,
            ]

            # Filtrer les checks qui ne sont pas 'na'
            relevant_checks = [c for c in checks if c != 'na']

            if not relevant_checks:
                inspection.result = 'pending'
            elif 'fail' in relevant_checks:
                inspection.result = 'fail'
            else:
                inspection.result = 'pass'

    def action_schedule(self):
        """Planifie le contrôle"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Seul un contrôle en brouillon peut être planifié."))
        self.state = 'scheduled'

    def action_start(self):
        """Démarre le contrôle"""
        self.ensure_one()
        if self.state not in ['draft', 'scheduled']:
            raise UserError(_("Le contrôle doit être en brouillon ou planifié pour être démarré."))
        self.state = 'in_progress'

    def action_done(self):
        """Termine le contrôle"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Le contrôle doit être en cours pour être terminé."))

        # Générer le numéro de certificat si validé
        if self.result == 'pass' and not self.certificate_number:
            self.certificate_number = self.env['ir.sequence'].next_by_code('gpl.certificate') or f'CERT-{self.id}'
            self.certificate_date = fields.Date.today()

        self.state = 'done'

        # Mettre à jour le véhicule
        if self.vehicle_id:
            self.vehicle_id.write({
                'last_inspection_date': self.date_inspection,
                'next_inspection_date': self.date_next_inspection,
                'inspection_result': self.result
            })

    def action_cancel(self):
        """Annule le contrôle"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Un contrôle terminé ne peut pas être annulé."))
        self.state = 'cancel'

    def action_print_certificate(self):
        """Imprime le certificat de contrôle"""
        self.ensure_one()
        if self.state != 'done' or self.result != 'pass':
            raise UserError(_("Le certificat ne peut être imprimé que pour un contrôle validé et terminé."))

        return self.env.ref('cpss_gpl_operations.report_gpl_inspection_certificate').report_action(self)
