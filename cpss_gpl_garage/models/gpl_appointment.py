from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class GplAppointment(models.Model):
    """Gestion des rendez-vous pour les véhicules GPL"""
    _name = 'gpl.appointment'
    _description = 'Rendez-vous GPL'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'appointment_date desc, id desc'
    _rec_name = 'display_name'

    # === IDENTIFICATION ===
    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default='New',
        copy=False,
        tracking=True
    )

    display_name = fields.Char(
        string='Nom',
        compute='_compute_display_name',
        store=True
    )

    # === VEHICLE & CLIENT ===
    vehicle_id = fields.Many2one(
        'gpl.vehicle',
        string='Véhicule',
        required=True,
        tracking=True,
        index=True,
        ondelete='cascade'
    )

    license_plate = fields.Char(
        related='vehicle_id.license_plate',
        string='Plaque',
        store=True,
        readonly=True
    )

    client_id = fields.Many2one(
        'res.partner',
        string='Client',
        related='vehicle_id.client_id',
        store=True,
        readonly=True
    )

    # === APPOINTMENT DETAILS ===
    appointment_date = fields.Datetime(
        string='Date rendez-vous',
        required=True,
        tracking=True,
        index=True
    )

    estimated_duration = fields.Float(
        string='Durée estimée (heures)',
        default=2.0,
        tracking=True
    )

    service_type = fields.Selection([
        ('installation', 'Installation GPL'),
        ('repair', 'Réparation'),
        ('inspection', 'Contrôle Technique'),
        ('testing', 'Réépreuve Réservoir'),
    ], string='Type de service', required=True, tracking=True, default='installation')

    # === ASSIGNMENT ===
    assigned_technician_ids = fields.Many2many(
        'hr.employee',
        'gpl_appointment_technician_rel',
        'appointment_id',
        'employee_id',
        string='Techniciens assignés',
        tracking=True
    )

    technician_names = fields.Char(
        string='Techniciens',
        compute='_compute_technician_names',
        store=True
    )

    # === STATE ===
    state = fields.Selection([
        ('scheduled', 'Programmé'),
        ('confirmed', 'Confirmé'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
        ('no_show', 'Absence client'),
    ], string='État', default='scheduled', required=True, tracking=True)

    # === OPERATION LINK ===
    operation_type = fields.Selection([
        ('gpl.service.installation', 'Installation'),
        ('gpl.repair.order', 'Réparation'),
        ('gpl.inspection', 'Contrôle'),
        ('gpl.reservoir.testing', 'Test réservoir'),
    ], string='Type opération')

    operation_id = fields.Integer(string='ID Opération')

    operation_reference = fields.Char(
        string='Référence opération',
        compute='_compute_operation_reference',
        store=True
    )

    # === NOTES ===
    notes = fields.Text(string='Notes')
    cancellation_reason = fields.Text(string='Raison annulation')

    # === COMPUTED FLAGS ===
    is_appointment_today = fields.Boolean(
        string='RDV aujourd\'hui',
        compute='_compute_appointment_flags',
        store=True
    )

    is_appointment_tomorrow = fields.Boolean(
        string='RDV demain',
        compute='_compute_appointment_flags',
        store=True
    )

    appointment_status = fields.Selection([
        ('none', 'Aucun'),
        ('today', 'Aujourd\'hui'),
        ('tomorrow', 'Demain'),
        ('upcoming', 'À venir'),
        ('overdue', 'En retard'),
    ], string='Statut RDV', compute='_compute_appointment_status', store=True)

    # === DISPLAY ===
    color = fields.Integer(string='Couleur', compute='_compute_color')

    # === COMPUTES ===
    @api.depends('name', 'vehicle_id.license_plate', 'service_type', 'appointment_date')
    def _compute_display_name(self):
        for appointment in self:
            if appointment.name and appointment.name != 'New':
                parts = [appointment.name]
                if appointment.vehicle_id:
                    parts.append(appointment.license_plate or '')
                if appointment.service_type:
                    service_dict = dict(self._fields['service_type'].selection)
                    parts.append(service_dict.get(appointment.service_type, ''))
                appointment.display_name = ' - '.join(filter(None, parts))
            else:
                appointment.display_name = 'Nouveau rendez-vous'

    @api.depends('assigned_technician_ids')
    def _compute_technician_names(self):
        for appointment in self:
            if appointment.assigned_technician_ids:
                appointment.technician_names = ', '.join(
                    appointment.assigned_technician_ids.mapped('name')
                )
            else:
                appointment.technician_names = ''

    @api.depends('operation_type', 'operation_id')
    def _compute_operation_reference(self):
        for appointment in self:
            if appointment.operation_type and appointment.operation_id:
                try:
                    operation = self.env[appointment.operation_type].browse(appointment.operation_id)
                    if operation.exists():
                        appointment.operation_reference = operation.name or f'#{appointment.operation_id}'
                    else:
                        appointment.operation_reference = ''
                except:
                    appointment.operation_reference = ''
            else:
                appointment.operation_reference = ''

    @api.depends('appointment_date')
    def _compute_appointment_flags(self):
        today = fields.Date.today()
        tomorrow = today + timedelta(days=1)
        for appointment in self:
            if appointment.appointment_date:
                appointment_date = appointment.appointment_date.date()
                appointment.is_appointment_today = appointment_date == today
                appointment.is_appointment_tomorrow = appointment_date == tomorrow
            else:
                appointment.is_appointment_today = False
                appointment.is_appointment_tomorrow = False

    @api.depends('appointment_date', 'state')
    def _compute_appointment_status(self):
        now = fields.Datetime.now()
        today = fields.Date.today()

        for appointment in self:
            if not appointment.appointment_date or appointment.state in ['completed', 'cancelled', 'no_show']:
                appointment.appointment_status = 'none'
            elif appointment.appointment_date.date() == today:
                appointment.appointment_status = 'today'
            elif appointment.appointment_date < now:
                appointment.appointment_status = 'overdue'
            elif appointment.appointment_date.date() == today + timedelta(days=1):
                appointment.appointment_status = 'tomorrow'
            else:
                appointment.appointment_status = 'upcoming'

    @api.depends('state', 'appointment_status')
    def _compute_color(self):
        for appointment in self:
            if appointment.state == 'cancelled':
                appointment.color = 1  # Red
            elif appointment.state == 'no_show':
                appointment.color = 8  # Orange
            elif appointment.state == 'completed':
                appointment.color = 10  # Green
            elif appointment.state == 'in_progress':
                appointment.color = 4  # Blue
            elif appointment.appointment_status == 'overdue':
                appointment.color = 1  # Red
            elif appointment.appointment_status == 'today':
                appointment.color = 7  # Yellow
            else:
                appointment.color = 0  # Default

    # === CONSTRAINTS ===
    @api.constrains('appointment_date')
    def _check_appointment_date(self):
        for appointment in self:
            if appointment.appointment_date and appointment.state == 'scheduled':
                if appointment.appointment_date < fields.Datetime.now():
                    raise ValidationError(_("La date de rendez-vous ne peut pas être dans le passé."))

    @api.constrains('estimated_duration')
    def _check_estimated_duration(self):
        for appointment in self:
            if appointment.estimated_duration <= 0:
                raise ValidationError(_("La durée estimée doit être positive."))

    # === CRUD ===
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gpl.appointment') or 'New'
        return super().create(vals_list)

    # === ACTIONS ===
    def action_confirm(self):
        """Confirmer le rendez-vous"""
        self.ensure_one()
        if self.state != 'scheduled':
            raise UserError(_("Seuls les rendez-vous programmés peuvent être confirmés."))
        self.write({'state': 'confirmed'})
        self.message_post(body=_("Rendez-vous confirmé"))

    def action_start(self):
        """Démarrer le service (crée le document d'opération)"""
        self.ensure_one()

        if self.state not in ['scheduled', 'confirmed']:
            raise UserError(_("Le rendez-vous doit être programmé ou confirmé pour démarrer."))

        # Mark as in progress
        self.write({'state': 'in_progress'})

        # Create operation document based on service type
        operation_action = self._create_operation_document()

        return operation_action

    def action_complete(self):
        """Marquer le rendez-vous comme terminé"""
        self.ensure_one()
        self.write({'state': 'completed'})
        self.message_post(body=_("Rendez-vous terminé"))

    def action_cancel(self):
        """Annuler le rendez-vous"""
        self.ensure_one()
        if self.state in ['completed']:
            raise UserError(_("Un rendez-vous terminé ne peut pas être annulé."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Annuler le rendez-vous'),
            'res_model': 'gpl.appointment.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_appointment_id': self.id}
        }

    def action_mark_no_show(self):
        """Marquer comme absence client"""
        self.ensure_one()
        self.write({'state': 'no_show'})
        self.message_post(body=_("Client absent au rendez-vous"))

    def action_reschedule(self):
        """Reprogrammer le rendez-vous"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reprogrammer le rendez-vous'),
            'res_model': 'gpl.appointment.reschedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_appointment_id': self.id,
                'default_current_date': self.appointment_date,
            }
        }

    def action_view_operation(self):
        """Voir le document d'opération lié"""
        self.ensure_one()
        if not self.operation_type or not self.operation_id:
            raise UserError(_("Aucune opération liée à ce rendez-vous."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Opération'),
            'res_model': self.operation_type,
            'res_id': self.operation_id,
            'view_mode': 'form',
            'target': 'current',
        }

    # === OPERATION CREATION ===
    def _create_operation_document(self):
        """Crée le document d'opération selon le type de service"""
        self.ensure_one()

        service_type = self.service_type

        # Données communes
        common_data = {
            'vehicle_id': self.vehicle_id.id,
            'client_id': self.client_id.id,
            'date_start': self.appointment_date or fields.Datetime.now(),
            'date_planned': self.appointment_date,
            'technician_ids': [(6, 0, self.assigned_technician_ids.ids)] if self.assigned_technician_ids else [],
            'notes': self.notes or '',
        }

        if service_type == 'installation':
            return self._create_installation_document(common_data)
        elif service_type == 'repair':
            return self._create_repair_document(common_data)
        elif service_type == 'inspection':
            return self._create_inspection_document(common_data)
        elif service_type == 'testing':
            return self._create_testing_document(common_data)
        else:
            raise UserError(_("Type de service '%s' non supporté.") % service_type)

    def _create_installation_document(self, common_data):
        """Crée un document d'installation GPL"""
        installation_vals = {
            **common_data,
            'state': 'planned',
        }

        installation = self.env['gpl.service.installation'].create(installation_vals)
        installation.action_start()

        # Link operation to appointment
        self.write({
            'operation_type': 'gpl.service.installation',
            'operation_id': installation.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Installation GPL - %s') % self.license_plate,
            'res_model': 'gpl.service.installation',
            'res_id': installation.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_repair_document(self, common_data):
        """Crée un document de réparation GPL"""
        repair_vals = {
            **common_data,
            'repair_type': 'repair',
            'priority': '0',
            'state': 'draft',
            'symptoms': self.notes or '',
            'date_planned': common_data['date_planned'],
        }

        repair = self.env['gpl.repair.order'].create(repair_vals)
        repair.action_start_repair()

        # Link operation to appointment
        self.write({
            'operation_type': 'gpl.repair.order',
            'operation_id': repair.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Réparation GPL - %s') % self.license_plate,
            'res_model': 'gpl.repair.order',
            'res_id': repair.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_inspection_document(self, common_data):
        """Crée un document d'inspection GPL"""
        inspection_vals = {
            **common_data,
            'inspection_type': 'periodic',
            'state': 'draft',
        }

        inspection = self.env['gpl.inspection'].create(inspection_vals)

        # Link operation to appointment
        self.write({
            'operation_type': 'gpl.inspection',
            'operation_id': inspection.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrôle Technique - %s') % self.license_plate,
            'res_model': 'gpl.inspection',
            'res_id': inspection.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_testing_document(self, common_data):
        """Crée un document de test de réservoir"""
        if not self.vehicle_id.reservoir_lot_id:
            raise UserError(_("Aucun réservoir associé à ce véhicule pour effectuer le test."))

        testing_vals = {
            **common_data,
            'reservoir_lot_id': self.vehicle_id.reservoir_lot_id.id,
            'test_type': 'periodic',
            'state': 'draft',
        }

        testing = self.env['gpl.reservoir.testing'].create(testing_vals)

        # Link operation to appointment
        self.write({
            'operation_type': 'gpl.reservoir.testing',
            'operation_id': testing.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Réépreuve Réservoir - %s') % self.license_plate,
            'res_model': 'gpl.reservoir.testing',
            'res_id': testing.id,
            'view_mode': 'form',
            'target': 'current',
        }
