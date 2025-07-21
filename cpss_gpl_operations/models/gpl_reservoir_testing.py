# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GplReservoirTesting(models.Model):
    """
    Gestion des réépreuves de réservoirs GPL
    """
    _name = 'gpl.reservoir.testing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Réépreuve Réservoir GPL'
    _order = 'date_testing desc'

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

    # Réservoir
    reservoir_lot_id = fields.Many2one(
        'stock.lot',
        string='Réservoir',
        related='vehicle_id.reservoir_lot_id',
        store=True,
        readonly=True
    )
    reservoir_serial = fields.Char(
        string='N° de série',
        related='reservoir_lot_id.name',
        readonly=True
    )

    # Dates
    date_testing = fields.Date(
        string='Date de réépreuve',
        default=fields.Date.today,
        required=True,
        tracking=True
    )
    date_next_testing = fields.Date(
        string='Prochaine réépreuve',
        help="Date de la prochaine réépreuve obligatoire"
    )
    date_last_testing = fields.Date(
        string='Dernière réépreuve',
        compute='_compute_last_testing',
        help="Date de la dernière réépreuve effectuée"
    )

    # Technicien
    technician_id = fields.Many2one(
        'hr.employee',
        string='Technicien',
        domain=[('department_id.name', 'ilike', 'technique')]
    )

    # Tests effectués
    pressure_test = fields.Float(
        string='Pression de test (bar)',
        help="Pression utilisée pour le test hydraulique"
    )
    test_duration = fields.Float(
        string='Durée du test (min)',
        help="Durée du test de pression en minutes"
    )

    # Résultats
    test_result = fields.Selection([
        ('pass', 'Conforme'),
        ('fail', 'Non conforme'),
        ('pending', 'En attente'),
    ], string='Résultat', default='pending', tracking=True)

    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('scheduled', 'Planifié'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', tracking=True)

    # Certificat
    certificate_number = fields.Char(
        string='N° certificat de réépreuve',
        help="Numéro du certificat délivré après la réépreuve"
    )

    # Observations
    observations = fields.Text(string='Observations')
    defects_found = fields.Text(string='Défauts constatés')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gpl.reservoir.testing') or 'New'
        return super().create(vals_list)

    @api.depends('vehicle_id', 'reservoir_lot_id')
    def _compute_last_testing(self):
        for record in self:
            if record.reservoir_lot_id:
                # Chercher la dernière réépreuve pour ce réservoir
                last_testing = self.search([
                    ('reservoir_lot_id', '=', record.reservoir_lot_id.id),
                    ('state', '=', 'done'),
                    ('id', '!=', record.id)
                ], order='date_testing desc', limit=1)

                record.date_last_testing = last_testing.date_testing if last_testing else False
            else:
                record.date_last_testing = False

    def action_start(self):
        """Démarre la réépreuve"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("La réépreuve doit être en brouillon pour être démarrée."))

        if not self.technician_id:
            raise UserError(_("Veuillez assigner un technicien."))

        if not self.reservoir_lot_id:
            raise UserError(_("Le véhicule doit avoir un réservoir installé."))

        self.state = 'in_progress'

    def action_validate(self):
        """Valide la réépreuve"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("La réépreuve doit être en cours pour être validée."))

        if self.test_result == 'pending':
            raise UserError(_("Veuillez saisir le résultat du test."))

        if not self.pressure_test or not self.test_duration:
            raise UserError(_("Veuillez saisir la pression et la durée du test."))

        # Si le test est réussi
        if self.test_result == 'pass':
            # Générer un certificat
            if not self.certificate_number:
                self.certificate_number = self.env['ir.sequence'].next_by_code('gpl.testing.certificate') or 'TEST-001'

            # Calculer la prochaine date (10 ans par défaut)
            from dateutil.relativedelta import relativedelta
            self.date_next_testing = fields.Date.today() + relativedelta(years=10)

            # Mettre à jour le réservoir
            if self.reservoir_lot_id:
                self.reservoir_lot_id.write({
                    'gpl_last_testing_date': self.date_testing,
                    'gpl_next_testing_date': self.date_next_testing,
                    'gpl_testing_certificate': self.certificate_number
                })

        self.state = 'done'

    def action_cancel(self):
        """Annule la réépreuve"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Une réépreuve terminée ne peut pas être annulée."))

        self.state = 'cancel'

    def action_print_certificate(self):
        """Imprime le certificat de réépreuve"""
        self.ensure_one()
        if self.state != 'done' or self.test_result != 'pass':
            raise UserError(_("Le certificat ne peut être imprimé que pour une réépreuve réussie."))

        return self.env.ref('cpss_gpl_operations.report_gpl_testing_certificate').report_action(self)
