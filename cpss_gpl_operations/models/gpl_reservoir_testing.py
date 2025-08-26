# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, date


class GplReservoirTesting(models.Model):
    """
    Gestion des réépreuves de réservoirs GPL
    """
    _name = 'gpl.reservoir.testing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Réépreuve Réservoir GPL'
    _order = 'start_date desc'

    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default='New',
        copy=False
    )

    # Réservoir

    reservoir_lot_id = fields.Many2one(
        'stock.lot',
        string='Réservoir',
        related='vehicle_id.reservoir_lot_id',
        store=True,
        readonly=False,  # si tu veux permettre de modifier via ce champ et que ça modifie aussi le véhicule
        domain="[('product_id.is_gpl_reservoir', '=', True)]",
        tracking=True
    )

    # Informations du réservoir
    reservoir_serial = fields.Char(
        string='N° de série',
        related='reservoir_lot_id.name',
        readonly=True
    )

    fabrication_date = fields.Date(
        string='Date de fabrication',
        related='reservoir_lot_id.manufacturing_date',
        readonly=True
    )

    test_frequency_years = fields.Integer(
        string='Fréquence tests (années)',
        related='reservoir_lot_id.test_frequency_years',
        readonly=True
    )

    age_years = fields.Integer(
        string='Âge (années)',
        related='reservoir_lot_id.age_years',
        readonly=True
    )

    last_test_date = fields.Date(
        string='Dernière réépreuve',
        related='reservoir_lot_id.last_test_date',
        store=True
    )

    # Véhicule associé (optionnel)
    vehicle_id = fields.Many2one(
        'gpl.vehicle',
        string='Véhicule',
        help="Véhicule sur lequel le réservoir est installé"
    )

    client_id = fields.Many2one(
        'res.partner',
        string='Client',
        compute='_compute_client_id',
        store=True
    )

    # Test information
    start_date = fields.Date(
        string='Date du test',
        default=fields.Date.today,
        required=True,
        tracking=True
    )

    date_planned = fields.Datetime(
        string='Date planifiée',
        tracking=True
    )

    test_type = fields.Selection([
        ('periodic', 'Réépreuve périodique'),
        ('initial', 'Épreuve initiale'),
        ('exceptional', 'Réépreuve exceptionnelle'),
        ('repair', 'Après réparation'),
    ], string='Type de test', default='periodic', required=True)

    # Technicien/Organisme
    technician_ids = fields.Many2many(
        'hr.employee',
        'gpl_testing_technician_rel',
        'testing_id',
        'employee_id',
        string='Techniciens'
    )

    # Paramètres du test
    test_pressure = fields.Float(
        string='Pression de test (bar)',
        default=30.0,
        required=True
    )

    test_duration = fields.Integer(
        string='Durée du test (min)',
        default=10,
        required=True
    )

    ambient_temperature = fields.Float(
        string='Température ambiante (°C)'
    )

    # Mesures
    initial_pressure = fields.Float(
        string='Pression initiale (bar)'
    )

    final_pressure = fields.Float(
        string='Pression finale (bar)'
    )

    pressure_drop = fields.Float(
        string='Chute de pression (%)',
        compute='_compute_pressure_drop',
        store=True
    )

    # Résultats
    visual_inspection = fields.Selection([
        ('pass', 'Conforme'),
        ('fail', 'Non conforme'),
    ], string='Inspection visuelle', required=True)

    pressure_test = fields.Selection([
        ('pass', 'Conforme'),
        ('fail', 'Non conforme'),
    ], string='Test de pression', required=True)

    marking_check = fields.Selection([
        ('pass', 'Conforme'),
        ('fail', 'Non conforme'),
    ], string='Vérification marquage', required=True)

    result = fields.Selection([
        ('pass', 'Validé'),
        ('fail', 'Refusé'),
        ('pending', 'En attente'),
    ], string='Résultat global', compute='_compute_result', store=True, tracking=True)

    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('planned', 'Planifié'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', tracking=True)

    # Validité

    next_test_date = fields.Date(
        string='Prochaine réépreuve',
        compute='_compute_next_test_date',
        store=True
    )

    # Observations
    observations = fields.Text(
        string='Observations'
    )

    defects_found = fields.Text(
        string='Défauts constatés'
    )

    corrective_actions = fields.Text(
        string='Actions correctives'
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

    can_cancel = fields.Boolean(compute='_compute_permissions', store=True)
    can_validate = fields.Boolean(compute='_compute_permissions', store=True)
    can_start = fields.Boolean(compute='_compute_permissions', store=True)
    can_schedule = fields.Boolean(compute='_compute_permissions', store=True)

    # Notes
    notes = fields.Text(string='Notes')

    @api.depends('state')
    def _compute_permissions(self):
        for rec in self:
            rec.can_cancel = rec.state in ['draft', 'planned', 'in_progress']
            rec.can_validate = rec.state == 'in_progress'
            rec.can_start = rec.state == 'planned'
            rec.can_schedule = rec.state == 'draft'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gpl.reservoir.testing') or 'New'
        return super().create(vals_list)

    @api.depends('vehicle_id')
    def _compute_client_id(self):
        for test in self:
            if test.vehicle_id:
                test.client_id = test.vehicle_id.client_id
            else:
                test.client_id = False

    @api.depends('initial_pressure', 'final_pressure')
    def _compute_pressure_drop(self):
        for test in self:
            if test.initial_pressure and test.initial_pressure > 0:
                test.pressure_drop = ((test.initial_pressure - test.final_pressure) / test.initial_pressure) * 100
            else:
                test.pressure_drop = 0

    @api.depends('visual_inspection', 'pressure_test', 'marking_check')
    def _compute_result(self):
        for test in self:
            if test.visual_inspection and test.pressure_test and test.marking_check:
                if all(check == 'pass' for check in [test.visual_inspection, test.pressure_test, test.marking_check]):
                    test.result = 'pass'
                else:
                    test.result = 'fail'
            else:
                test.result = 'pending'

    @api.depends('start_date', 'test_frequency_years')
    def _compute_next_test_date(self):
        for test in self:
            if test.start_date and test.test_frequency_years:
                test.next_test_date = test.start_date + timedelta(days=test.test_frequency_years * 365)
            else:
                test.next_test_date = False

    @api.constrains('reservoir_lot_id', 'start_date')
    def _check_reservoir_age(self):
        for test in self:
            if test.reservoir_lot_id and test.reservoir_lot_id.fabrication_date:
                age_years_res = (test.start_date - test.reservoir_lot_id.fabrication_date).days / 365
                if age_years_res > self.age_years:
                    raise UserError(_("Ce réservoir a plus de 15 ans et ne peut plus être rééprouvé."))

    def action_schedule(self):
        """Planifie le test"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Seul un test en brouillon peut être planifié."))
        self.state = 'planned'

    def action_validate_fail(self):
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Le test doit être en cours pour être terminé."))

        if self.result == 'pending':
            raise UserError(_("Veuillez compléter tous les résultats de test."))
        self.result = 'fail'

    def action_start(self):
        """Démarre le test"""
        self.ensure_one()
        if self.state not in ['draft', 'planned']:
            raise UserError(_("Le test doit être en brouillon ou planifié pour être démarré."))
        self.state = 'in_progress'

    def action_done(self):
        """Termine le test"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Le test doit être en cours pour être terminé."))

        if self.result == 'pending':
            raise UserError(_("Veuillez compléter tous les résultats de test."))

        # Générer le certificat si validé
        if self.result == 'pass' and not self.certificate_number:
            self.certificate_number = self.env['ir.sequence'].next_by_code(
                'gpl.reepreuve.certificate') or f'REEP-{self.id}'
            self.certificate_date = fields.Date.today()

        self.state = 'done'

        # Mettre à jour le réservoir
        if self.reservoir_lot_id:
            self.reservoir_lot_id.write({
                'last_test_date': self.start_date,
                'next_test_date': self.next_test_date,
                'reservoir_status': 'valid' if self.result == 'pass' else 'expired'
            })

    def action_cancel(self):
        """Annule le test"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Un test terminé ne peut pas être annulé."))
        self.state = 'cancel'

    def action_reset_to_draft(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Un test terminé ne peut pas être brouillon."))
        self.state = 'draft'

    def action_print_certificate(self):
        """Imprime le certificat de réépreuve"""
        self.ensure_one()
        if self.state != 'done' or self.result != 'pass':
            raise UserError(_("Le certificat ne peut être imprimé que pour un test validé et terminé."))

        return self.env.ref('cpss_gpl_operations.report_gpl_installation_document').report_action(self)
