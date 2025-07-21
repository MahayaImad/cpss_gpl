from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
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
        ('maintenance', 'Maintenance'),
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
    active = fields.Boolean('Actif', default=True)

    # === TAGS ET CLASSIFICATION ===
    tag_ids = fields.Many2many('gpl.vehicle.tag', string='Tags')

    # === INFORMATIONS COMPLÉMENTAIRES ===
    notes = fields.Html('Notes')
    internal_notes = fields.Text('Notes internes')

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

    @api.depends('name', 'client_id')
    def _compute_display_name(self):
        for vehicle in self:
            if vehicle.client_id:
                vehicle.display_name = f"{vehicle.name} ({vehicle.client_id.name})"
            else:
                vehicle.display_name = vehicle.name or "Nouveau véhicule"

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

    def _get_default_status(self):
        """Statut par défaut"""
        return self.env.ref('cpss_gpl_garage.vehicle_status_nouveau', raise_if_not_found=False)

    # === ACTIONS PLANNING ===
    def action_reschedule_appointment(self):
        """Ouvre l'assistant de reprogrammation"""
        self.ensure_one()
        return {
            'name': _('Reprogrammer le rendez-vous'),
            'type': 'ir.actions.act_window',
            'res_model': 'gpl.reschedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_vehicle_id': self.id,
            }
        }

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
            'tag': 'display_notification',
            'params': {
                'title': _('Service démarré'),
                'message': _('Le service pour %s a été démarré.') % self.display_name,
                'type': 'success',
            }
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
            'tag': 'display_notification',
            'params': {
                'title': _('Rendez-vous terminé'),
                'message': _('Le rendez-vous pour %s a été marqué comme terminé.') % self.display_name,
                'type': 'success',
            }
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
