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
    _order = 'date_start desc'

    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default='New',
        copy=False
    )

    # Véhicule et client
    vehicle_id = fields.Many2one(
        'gpl.vehicle',  # CORRIGÉ
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
    date_start = fields.Date(
        string='Date du contrôle',
        default=fields.Date.today,
        required=True,
        tracking=True
    )

    date_planned = fields.Datetime(
        string='Date planifiée',
        tracking=True
    )

    date_next_inspection = fields.Date(
        string='Prochaine inspection',
        compute='_compute_next_inspection',
        store=True
    )

    # Type de contrôle
    inspection_type = fields.Selection([
        ('periodic', 'Contrôle triennal'),
        ('initial', 'Contrôle d\'homologation initial'),
        ('voluntary', 'Contrôle volontaire'),
    ], string='Type de contrôle', default='periodic', required=True)

    # Technicien
    technician_ids = fields.Many2many(
        'hr.employee',
        'gpl_inspection_technician_rel',
        'inspection_id',
        'employee_id',
        string='Contrôleurs'
    )

    inspector_id = fields.Many2one(
        'hr.employee',
        string='Inspecteur',
        help="Ingérieur des mines"
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
        ('planned', 'Planifié'),
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

    gpl_control_periodic = fields.Integer(
        string="Contrôle périodique (mois)",
        default=lambda self: int(self.env['ir.config_parameter'].sudo().get_param('cpss_gpl.control_periodic', 36)),
        help="Contrôle périodique obligatoire de l'installation par l'ingénieur des mines"
    )
    # Notes
    notes = fields.Text(string='Notes internes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gpl.inspection') or 'New'
        return super().create(vals_list)

    @api.depends('date_start', 'gpl_control_periodic')
    def _compute_next_inspection(self):
        for inspection in self:
            if inspection.date_start and inspection.gpl_control_periodic:
                inspection.date_next_inspection = inspection.date_start + timedelta(
                    days=inspection.gpl_control_periodic * 30)
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
        self.state = 'planned'

    def action_start(self):
        """Démarre le contrôle"""
        self.ensure_one()
        if self.state not in ['draft', 'planned']:
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
        if self.result == 'fail':
            return

        # Mettre à jour le véhicule
        if self.inspection_type != 'voluntary':
            if self.vehicle_id:
                self.vehicle_id.write({
                    'date_inspection': self.date_start,
                    'date_next_inspection': self.date_next_inspection
                })

    def action_cancel(self):
        """Annule le contrôle"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Un contrôle terminé ne peut pas être annulé."))
        self.state = 'cancel'

    def action_set_all_checks_pass(self):
        """Marque tous les contrôles comme conformes"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Cette action n'est disponible que pour un contrôle en cours."))

        self.write({
            'check_reservoir': 'pass',
            'check_piping': 'pass',
            'check_injectors': 'pass',
            'check_electronics': 'pass',
            'check_pressure': 'pass',
            'check_mounting': 'pass',
            'check_ventilation': 'pass',
            'check_marking': 'pass',
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
                            elif field in ['conformity_percentage']:
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
