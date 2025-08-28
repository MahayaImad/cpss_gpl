from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class GplVehicle(models.Model):
    _name = 'gpl.vehicle'
    _description = 'Véhicule GPL Garage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'appointment_date asc, name'
    _rec_name = 'display_name'

    # === INFORMATIONS DE BASE ===
    name = fields.Char('Nom véhicule', compute='_compute_name', store=True)
    display_name = fields.Char('Nom complet', compute='_compute_display_name', store=True)
    license_plate = fields.Char('Plaque d\'immatriculation', required=True, tracking=True)
    vin = fields.Char('Numéro de châssis (VIN)', tracking=True)
    vehicle_type_code = fields.Char(
        string="Type de véhicule",
        compute="_compute_vehicle_type_code",
        store=True,
        readonly=False,
        help="Code de type du véhicule (par défaut: caractères 3 à 8 du VIN)"
    )

    # === INFORMATIONS TECHNIQUES ===
    model_id = fields.Many2one('fleet.vehicle.model', 'Modèle', required=True, tracking=True)
    brand_id = fields.Many2one(related='model_id.brand_id', store=True, readonly=True)
    year = fields.Integer('Année', tracking=True)
    color = fields.Char('Couleur', tracking=True)

    # === CLIENT ET CONTACT ===
    client_id = fields.Many2one('res.partner', 'Client', required=True, tracking=True,
                                domain=[('is_company', '=', False)])
    client_phone = fields.Char(related='client_id.phone', readonly=True)
    client_mobile = fields.Char(related='client_id.mobile', readonly=True)
    client_email = fields.Char(related='client_id.email', readonly=True)

    # === PLANNING ET RENDEZ-VOUS ===
    appointment_date = fields.Datetime('Date rendez-vous', tracking=True)
    estimated_duration = fields.Float('Durée estimée (heures)', default=2.0)
    next_service_type = fields.Selection([
        ('installation', 'Installation GPL'),
        ('repair', 'Réparation'),
        ('inspection', 'Contrôle/Inspection'),
        ('testing', 'Réépreuve réservoir'),
    ], string='Type de service', tracking=True)

    # === ASSIGNATION TECHNICIENS ===
    assigned_technician_ids = fields.Many2many(
        'hr.employee',
        'gpl_vehicle_technician_rel',
        'vehicle_id', 'employee_id',
        string='Techniciens assignés',
        domain=[('department_id.name', 'ilike', 'atelier')]
    )

    # === STATUT ET WORKFLOW ===
    status_id = fields.Many2one('gpl.vehicle.status', 'Statut', default=lambda self: self._get_default_status())
    status_name = fields.Char(
        'Nom du statut',
        related='status_id.name',
        store=False
    )
    active = fields.Boolean('Actif', default=True)

    # === TAGS ET CLASSIFICATION ===
    tag_ids = fields.Many2many('gpl.vehicle.tag', string='Tags')

    # === INFORMATIONS COMPLÉMENTAIRES ===
    notes = fields.Text('Notes')

    # === INFORMATIONS RESERVOIR ===
    reservoir_lot_id = fields.Many2one('stock.lot', string="Réservoir installé",
                                       domain="[('product_id.is_gpl_reservoir', '=', True)]",
                                       tracking=True)

    # Informations du contrôle
    date_inspection = fields.Date(
        string='Date du contrôle',
        tracking=True
    )

    date_next_inspection = fields.Date(
        string='Prochaine inspection',
        tracking=True
    )

    image_128 = fields.Image(
        related='model_id.image_128',
        readonly=True
    )

    # === CHAMPS CALCULÉS ===
    technician_names = fields.Char('Techniciens', compute='_compute_technician_names')
    is_appointment_today = fields.Boolean('RDV aujourd\'hui', compute='_compute_appointment_flags')
    is_appointment_tomorrow = fields.Boolean('RDV demain', compute='_compute_appointment_flags')
    appointment_status = fields.Selection([
        ('none', 'Aucun RDV'),
        ('scheduled', 'Planifié'),
        ('today', 'Aujourd\'hui'),
        ('overdue', 'En retard'),
    ], compute='_compute_appointment_status')

    @api.depends('license_plate', 'model_id')
    def _compute_name(self):
        for vehicle in self:
            if vehicle.license_plate and vehicle.model_id:
                vehicle.name = f"{vehicle.model_id.name} - {vehicle.license_plate}"
            elif vehicle.license_plate:
                vehicle.name = vehicle.license_plate
            else:
                vehicle.name = "Nouveau véhicule"

    @api.depends('license_plate', 'client_id', 'model_id')
    def _compute_display_name(self):
        for vehicle in self:
            parts = []
            if vehicle.license_plate:
                parts.append(vehicle.license_plate)
            if vehicle.client_id:
                parts.append(f"({vehicle.client_id.name})")
            if vehicle.model_id and not vehicle.license_plate:
                parts.append(vehicle.model_id.name)

            vehicle.display_name = ' '.join(parts) if parts else 'Nouveau véhicule'

    @api.depends('assigned_technician_ids')
    def _compute_technician_names(self):
        for vehicle in self:
            vehicle.technician_names = ', '.join(vehicle.assigned_technician_ids.mapped('name'))

    @api.depends('appointment_date')
    def _compute_appointment_flags(self):
        today = fields.Date.today()
        tomorrow = today + timedelta(days=1)
        for vehicle in self:
            if vehicle.appointment_date:
                appointment_date = vehicle.appointment_date.date()
                vehicle.is_appointment_today = appointment_date == today
                vehicle.is_appointment_tomorrow = appointment_date == tomorrow
            else:
                vehicle.is_appointment_today = False
                vehicle.is_appointment_tomorrow = False

    @api.depends('appointment_date')
    def _compute_appointment_status(self):
        now = fields.Datetime.now()
        today = fields.Date.today()

        for vehicle in self:
            if not vehicle.appointment_date:
                vehicle.appointment_status = 'none'
            elif vehicle.appointment_date.date() == today:
                vehicle.appointment_status = 'today'
            elif vehicle.appointment_date < now:
                vehicle.appointment_status = 'overdue'
            else:
                vehicle.appointment_status = 'scheduled'

    @api.depends('vin')
    def _compute_vehicle_type_code(self):
        """Extrait les caractères 3 à 8 du VIN quand le champ est vide"""
        for vehicle in self:
            # Ne pas écraser une valeur déjà définie manuellement
            if not vehicle.vehicle_type_code and vehicle.vin and len(vehicle.vin) >= 8:
                vehicle.vehicle_type_code = vehicle.vin[3:8]
            elif not vehicle.vehicle_type_code:
                vehicle.vehicle_type_code = False

    # Méthode pour réinitialiser le code type selon le VIN
    def action_reset_vehicle_type_code(self):
        """Réinitialise le code type basé sur le VIN"""
        for vehicle in self:
            if vehicle.vin and len(vehicle.vin) >= 8:
                vehicle.vehicle_type_code = vehicle.vin[3:8]

    # Méthode onchange pour suggérer le type lors de la saisie du VIN
    @api.onchange('vin')
    def _onchange_vin(self):
        if self.vin and len(self.vin) >= 8 and not self.vehicle_type_code:
            self.vehicle_type_code = self.vin[3:8]

    @api.model
    def _get_need_inspection_domain(self):
        """Return domain for vehicles to control dynamically"""
        days = int(self.env["ir.config_parameter"].sudo().get_param(
            "cpss_gpl.notification_test_days", 30
        ))
        today = fields.Date.context_today(self)
        limit_date = today + relativedelta(days=days)
        return [
            ("date_next_inspection", ">=", today),
            ("date_next_inspection", "<=", limit_date),
        ]

    @api.model
    def action_vehicle_need_inspection(self):
        """Custom action with dynamic domain"""
        domain = self._get_need_inspection_domain()
        return {
            "name": "Véhicules à contrôler",
            "type": "ir.actions.act_window",
            "res_model": "gpl.vehicle",
            "view_mode": "tree,form,activity",
            "domain": domain,
        }

    def _get_default_status(self):
        """Statut par défaut"""
        return self.env.ref('cpss_gpl_garage.vehicle_status_nouveau', raise_if_not_found=False)

    def action_start_service(self):
        """Démarre le service"""
        self.ensure_one()
        in_progress_status = self.env.ref('cpss_gpl_garage.vehicle_status_en_cours', raise_if_not_found=False)
        if in_progress_status:
            self.status_id = in_progress_status

        # Log de démarrage
        self.message_post(
            body=f"Service démarré : {dict(self._fields['next_service_type'].selection)[self.next_service_type]}",
            message_type='comment'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_reschedule_appointment(self):
        """Reprogrammer le service"""
        self.ensure_one()
        vehicle_status_nouveau = self.env.ref('cpss_gpl_garage.vehicle_status_nouveau', raise_if_not_found=False)
        if vehicle_status_nouveau:
            self.status_id = vehicle_status_nouveau

        # Log de démarrage
        self.message_post(
            body=f"Service reprogrammer : {dict(self._fields['next_service_type'].selection)[self.next_service_type]}",
            message_type='comment'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_complete_appointment(self):
        """Termine le rendez-vous"""
        self.ensure_one()
        completed_status = self.env.ref('cpss_gpl_garage.vehicle_status_termine', raise_if_not_found=False)

        self.write({
            'status_id': completed_status.id if completed_status else False,
            'appointment_date': False,
            'next_service_type': False,
        })

        self.message_post(
            body="Rendez-vous terminé avec succès",
            message_type='comment'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def action_annuler(self):
        self.ensure_one()
        annule_status = self.env.ref('cpss_gpl_garage.vehicle_status_annule', raise_if_not_found=False)

        self.write({
            'status_id': annule_status.id if annule_status else False,
            'appointment_date': False,
            'next_service_type': False,
        })

        self.message_post(
            body="Service annulé",
            message_type='comment'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    # === CONTRAINTES ===
    @api.constrains('license_plate')
    def _check_license_plate(self):
        for vehicle in self:
            if vehicle.license_plate:
                # Vérifier l'unicité
                existing = self.search([
                    ('license_plate', '=', vehicle.license_plate),
                    ('id', '!=', vehicle.id)
                ])
                if existing:
                    raise ValidationError(_("Cette plaque d'immatriculation existe déjà!"))

    @api.constrains('appointment_date')
    def _check_appointment_date(self):
        for vehicle in self:
            if vehicle.appointment_date and vehicle.appointment_date < fields.Datetime.now():
                raise ValidationError(_("La date de rendez-vous ne peut pas être dans le passé."))

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override pour forcer l'affichage de toutes les colonnes de statuts dans kanban"""
        result = super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

        # Si groupé par status_id
        if groupby and len(groupby) > 0 and 'status_id' in groupby[0]:
            # Récupérer tous les statuts actifs
            all_statuses = self.env['gpl.vehicle.status'].search([('active', '=', True)], order='sequence, name')

            # Extraire les IDs de statut déjà présents dans les résultats
            existing_status_ids = []
            for group in result:
                if group.get('status_id') and isinstance(group['status_id'], (list, tuple)):
                    existing_status_ids.append(group['status_id'][0])

            # Ajouter les statuts manquants avec un count de 0
            for status in all_statuses:
                if status.id not in existing_status_ids:
                    # Créer un groupe vide pour ce statut
                    empty_group = {
                        'status_id': (status.id, status.name),
                        'status_id_count': 0,
                        '__domain': [('status_id', '=', status.id)] + domain,
                    }

                    # Ajouter les autres champs nécessaires selon le groupby
                    for field in fields:
                        if field not in empty_group and field != 'status_id':
                            empty_group[field] = 0 if 'count' in field else False

                    result.append(empty_group)

            # Trier les résultats par séquence des statuts
            def sort_key(group):
                if group.get('status_id') and isinstance(group['status_id'], (list, tuple)):
                    status_id = group['status_id'][0]
                    status = self.env['gpl.vehicle.status'].browse(status_id)
                    return (status.sequence, status.name)
                return (999, '')

            result.sort(key=sort_key)

        return result

class GplVehicleStatus(models.Model):
    _name = 'gpl.vehicle.status'
    _description = 'Statut du Véhicule GPL'
    _order = 'sequence, name'

    name = fields.Char('Nom', required=True)
    sequence = fields.Integer('Séquence', default=10)
    fold = fields.Boolean('Plié dans Kanban', default=False)
    active = fields.Boolean('Actif', default=True)
    description = fields.Text('Description')
    color = fields.Integer('Couleur', default=0)
    is_done = fields.Boolean('Étape finale', default=False)
