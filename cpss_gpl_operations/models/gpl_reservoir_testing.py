# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, date


class GplReservoirTesting(models.Model):
    """
    Gestion des réépreuves de réservoirs GPL
    Modifié pour suivre le même format que les inspections
    """
    _name = 'gpl.reservoir.testing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Réépreuve Réservoir GPL'
    _order = 'date_start desc'

    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default='New',
        copy=False
    )

    # === INFORMATIONS GÉNÉRALES (comme inspections) ===
    date_start = fields.Date(
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

    # === RÉSERVOIR ===
    reservoir_lot_id = fields.Many2one(
        'stock.lot',
        string='Réservoir',
        required=True,
        domain="[('product_id.is_gpl_reservoir', '=', True)]",
        tracking=True
    )

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

    # === VÉHICULE ET CLIENT ===
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

    # === TECHNICIENS ===
    technician_ids = fields.Many2many(
        'hr.employee',
        'gpl_testing_technician_rel',
        'testing_id',
        'employee_id',
        string='Techniciens'
    )
    inspector_id = fields.Many2one(
        'hr.employee',
        string='Inspecteur',
        help="Ingérieur des mines"
    )

    # === ÉTAT ===
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('planned', 'Planifié'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', tracking=True, copy=False)

    # =====================================
    # === TESTS ET RÉSULTATS (comme inspections) ===
    # =====================================

    # === A. INSPECTION VISUELLE ===
    visual_inspection_ok = fields.Boolean('Inspection visuelle conforme', default=False)
    visual_notes = fields.Text('Notes inspection visuelle')

    # Détail inspection visuelle
    reservoir_external_ok = fields.Boolean('État externe réservoir', default=False)
    reservoir_marking_ok = fields.Boolean('Marquage réservoir', default=False)
    reservoir_fixation_ok = fields.Boolean('Fixation réservoir', default=False)
    reservoir_support_ok = fields.Boolean('Support réservoir', default=False)

    # === B. TESTS DE PRESSION ===
    pressure_test_ok = fields.Boolean('Test de pression conforme', default=False)
    pressure_notes = fields.Text('Notes test de pression')

    # Paramètres et mesures de pression
    test_pressure = fields.Float(
        string='Pression de test (bar)',
        default=30.0,
        required=True
    )
    initial_pressure = fields.Float('Pression initiale (bar)')
    final_pressure = fields.Float('Pression finale (bar)')
    pressure_drop = fields.Float(
        string='Chute de pression (%)',
        compute='_compute_pressure_drop',
        store=True
    )
    test_duration = fields.Integer('Durée du test (min)', default=10)

    # === C. TESTS D'ÉTANCHÉITÉ ===
    tightness_test_ok = fields.Boolean('Test d\'étanchéité conforme', default=False)
    tightness_notes = fields.Text('Notes test d\'étanchéité')

    # Détail étanchéité
    valve_tightness_ok = fields.Boolean('Étanchéité vanne', default=False)
    fitting_tightness_ok = fields.Boolean('Étanchéité raccords', default=False)
    weld_tightness_ok = fields.Boolean('Étanchéité soudures', default=False)

    # === D. VÉRIFICATIONS COMPLÉMENTAIRES ===
    safety_systems_ok = fields.Boolean('Systèmes de sécurité conformes', default=False)
    safety_notes = fields.Text('Notes systèmes de sécurité')

    ambient_temperature = fields.Float('Température ambiante (°C)')
    humidity = fields.Float('Humidité (%)')

    # === RÉSULTAT FINAL ===
    result = fields.Selection([
        ('pending', 'En attente'),
        ('pass', 'Validé'),
        ('fail', 'Non validé'),
    ], string='Résultat', default='pending', compute='_compute_result', store=True, tracking=True)

    # Résultat détaillé
    test_passed = fields.Boolean('Test réussi', compute='_compute_test_passed', store=True)
    conformity_percentage = fields.Float('% Conformité', compute='_compute_conformity', store=True)

    # === CERTIFICAT ===
    certificate_number = fields.Char('N° Certificat', readonly=True, copy=False)
    certificate_date = fields.Date('Date certificat', readonly=True, copy=False)
    next_test_date = fields.Date(
        string='Prochaine réépreuve',
        compute='_compute_next_test_date',
        store=True
    )

    # === NOTES ET OBSERVATIONS ===
    notes = fields.Text('Observations générales')
    corrective_actions = fields.Text('Actions correctives nécessaires')
    recommendations = fields.Text('Recommandations')

    # =====================================
    # === MÉTHODES CALCULÉES ===
    # =====================================

    @api.depends('vehicle_id', 'vehicle_id.client_id')
    def _compute_client_id(self):
        for record in self:
            record.client_id = record.vehicle_id.client_id if record.vehicle_id else False

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        """Met à jour les informations du réservoir quand le véhicule change"""
        for record in self:
            if record.vehicle_id:
                record.reservoir_lot_id = record.vehicle_id.reservoir_lot_id
                record.reservoir_serial = record.reservoir_lot_id.name
                record.fabrication_date = record.reservoir_lot_id.manufacturing_date
            else:
                record.reservoir_lot_id = False
                record.reservoir_serial = False
                record.fabrication_date = False

    @api.onchange('reservoir_lot_id')
    def _onchange_reservoir_lot_id(self):
        for record in self:
            if record.reservoir_lot_id:
                record.reservoir_serial = record.reservoir_lot_id.name
                record.fabrication_date = record.reservoir_lot_id.manufacturing_date
                if record.reservoir_lot_id.vehicle_id:
                    record.vehicle_id = record.reservoir_lot_id.vehicle_id
                else: record.vehicle_id = False
            else:
                record.reservoir_lot_id = False
                record.reservoir_serial = False
                record.fabrication_date = False
                record.vehicle_id = False


    @api.depends('initial_pressure', 'final_pressure')
    def _compute_pressure_drop(self):
        for record in self:
            if record.initial_pressure and record.final_pressure:
                if record.initial_pressure > 0:
                    drop = ((record.initial_pressure - record.final_pressure) / record.initial_pressure) * 100
                    record.pressure_drop = abs(drop)
                else:
                    record.pressure_drop = 0.0
            else:
                record.pressure_drop = 0.0

    @api.depends(
        'visual_inspection_ok', 'pressure_test_ok',
        'tightness_test_ok', 'safety_systems_ok'
    )
    def _compute_result(self):
        """Calcul du résultat final comme les inspections"""
        for record in self:
            if record.state != 'done':
                record.result = 'pending'
            else:
                # Tous les tests principaux doivent être conformes
                main_tests = [
                    record.visual_inspection_ok,
                    record.pressure_test_ok,
                    record.tightness_test_ok,
                    record.safety_systems_ok
                ]

                if all(main_tests):
                    record.result = 'pass'
                else:
                    record.result = 'fail'

    @api.depends('result')
    def _compute_test_passed(self):
        for record in self:
            record.test_passed = record.result == 'pass'

    @api.depends(
        'visual_inspection_ok', 'pressure_test_ok',
        'tightness_test_ok', 'safety_systems_ok',
        'reservoir_external_ok', 'reservoir_marking_ok',
        'valve_tightness_ok', 'fitting_tightness_ok'
    )
    def _compute_conformity(self):
        """Calcul du pourcentage de conformité"""
        for record in self:
            total_checks = 8  # Nombre total de vérifications
            passed_checks = sum([
                record.visual_inspection_ok,
                record.pressure_test_ok,
                record.tightness_test_ok,
                record.safety_systems_ok,
                record.reservoir_external_ok,
                record.reservoir_marking_ok,
                record.valve_tightness_ok,
                record.fitting_tightness_ok,
            ])

            record.conformity_percentage = (passed_checks / total_checks) * 100 if total_checks > 0 else 0

    @api.depends('date_start', 'reservoir_lot_id', 'reservoir_lot_id.test_frequency_years')
    def _compute_next_test_date(self):
        for record in self:
            if record.date_start and record.reservoir_lot_id:
                frequency = record.reservoir_lot_id.test_frequency_years or 5
                record.next_test_date = record.date_start + timedelta(days=frequency * 365)
            else:
                record.next_test_date = False

    # =====================================
    # === MÉTHODES D'ACTION ===
    # =====================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gpl.reservoir.testing') or 'TEST-NEW'
        return super().create(vals_list)

    def action_plan(self):
        """Planifie le test"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Seuls les tests en brouillon peuvent être planifiés."))
        self.state = 'planned'

    def action_start(self):
        """Démarre le test"""
        self.ensure_one()
        if self.state not in ['draft', 'planned']:
            raise UserError(_("Le test doit être en brouillon ou planifié pour être démarré."))
        self.state = 'in_progress'

    def action_validate_pass(self):
        """Valide le test avec succès"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Le test doit être en cours pour être validé."))

        # Générer le certificat
        if not self.certificate_number:
            self.certificate_number = self.env['ir.sequence'].next_by_code(
                'gpl.reepreuve.certificate') or f'REEP-{self.id}'
            self.certificate_date = fields.Date.today()

        self.state = 'done'
        self.result = 'pass'


        # Mettre à jour le réservoir
        if self.reservoir_lot_id:
            self.reservoir_lot_id.write({
                'last_test_date': self.date_start,
                'next_test_date': self.next_test_date,
                'reservoir_status': 'valid' if self.result == 'pass' else 'expired'
            })

    def action_validate_fail(self):
        """Valide le test avec échec"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Le test doit être en cours pour être terminé."))

        self.state = 'done'
        self.result = 'fail'

        # Mettre à jour le réservoir
        if self.reservoir_lot_id:
            self.reservoir_lot_id.write({
                'reservoir_status': 'expired'
            })

    def action_cancel(self):
        """Annule le test"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Un test terminé ne peut pas être annulé."))
        self.state = 'cancel'

    def action_reset_to_draft(self):
        """Remet en brouillon"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Un test terminé ne peut pas être remis en brouillon."))
        self.state = 'draft'

    def action_print_certificate(self):
        """Imprime le certificat de réépreuve"""
        self.ensure_one()
        if self.state != 'done' or self.result != 'pass':
            raise UserError(_("Le certificat ne peut être imprimé que pour un test validé et terminé."))

        return

    # =====================================
    # === ACTIONS RAPIDES ===
    # =====================================

    def action_mark_all_visual_ok(self):
        """Marque tous les points d'inspection visuelle comme conformes"""
        self.write({
            'visual_inspection_ok': True,
            'reservoir_external_ok': True,
            'reservoir_marking_ok': True,
            'reservoir_fixation_ok': True,
            'reservoir_support_ok': True,
        })

    def action_mark_all_pressure_ok(self):
        """Marque tous les tests de pression comme conformes"""
        self.write({
            'pressure_test_ok': True,
        })

    def action_mark_all_tightness_ok(self):
        """Marque tous les tests d'étanchéité comme conformes"""
        self.write({
            'tightness_test_ok': True,
            'valve_tightness_ok': True,
            'fitting_tightness_ok': True,
            'weld_tightness_ok': True,
        })

    def action_mark_all_safety_ok(self):
        """Marque tous les systèmes de sécurité comme conformes"""
        self.write({
            'safety_systems_ok': True,
        })


    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override pour forcer l'affichage de toutes les colonnes d'états dans kanban"""
        result = super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

        # Si groupé par state
        if groupby and len(groupby) > 0 and 'state' in groupby[0]:
            # Définir tous les états possibles dans l'ordre souhaité
            all_states = [
                ('draft', 'Brouillon'),
                ('planned', 'Planifié'),
                ('in_progress', 'En cours'),
                ('done', 'Terminé'),
                ('cancel', 'Annulé'),
            ]

            # Extraire les états déjà présents dans les résultats
            existing_states = []
            for group in result:
                if group.get('state'):
                    existing_states.append(group['state'])

            # Ajouter les états manquants avec un count de 0
            for state_key, state_name in all_states:
                if state_key not in existing_states:
                    # Créer un groupe vide pour cet état
                    empty_group = {
                        'state': state_key,
                        'state_count': 0,
                        '__count': 0,  # AJOUT DU CHAMP __count REQUIS
                        '__domain': [('state', '=', state_key)] + domain,
                    }

                    # Ajouter les autres champs nécessaires selon le groupby
                    for field in fields:
                        if field not in empty_group and field != 'state':
                            if 'count' in field:
                                empty_group[field] = 0
                            elif field in ['conformity_percentage', 'test_pressure', 'pressure_drop']:
                                empty_group[field] = 0.0
                            else:
                                empty_group[field] = False

                    result.append(empty_group)

            # Trier les résultats dans l'ordre souhaité: draft > planned > in_progress > done > cancel
            def sort_key(group):
                state = group.get('state', '')
                order_map = {
                    'draft': 1,
                    'planned': 2,
                    'in_progress': 3,
                    'done': 4,
                    'cancel': 5
                }
                return order_map.get(state, 999)

            result.sort(key=sort_key)

        return result
