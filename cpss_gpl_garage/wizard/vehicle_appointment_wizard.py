from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VehicleAppointmentWizard(models.TransientModel):
    _name = 'vehicle.appointment.wizard'
    _description = 'Assistant de rendez-vous véhicule'

    # Champ pour la date sélectionnée
    appointment_date = fields.Datetime(
        'Date du rendez-vous',
        required=True,
        default=fields.Datetime.now
    )

    # Sélection du véhicule
    vehicle_choice = fields.Selection([
        ('existing', 'Véhicule existant'),
        ('new', 'Nouveau véhicule')
    ], string='Type', default='existing', required=True)

    vehicle_id = fields.Many2one(
        'gpl.vehicle',
        'Véhicule',
        domain=[('active', '=', True)]
    )

    # Détails du service
    service_type = fields.Selection([
        ('installation', 'Installation GPL'),
        ('repair', 'Réparation'),
        ('inspection', 'Contrôle/Inspection'),
        ('testing', 'Réépreuve réservoir'),
    ], string='Type de service', default='installation', required=True)

    technician_ids = fields.Many2many(
        'hr.employee',
        string='Techniciens assignés',
        domain=[('department_id.name', 'ilike', 'atelier')]
    )

    estimated_duration = fields.Float(
        'Durée estimée (heures)',
        default=2.0
    )

    notes = fields.Text('Notes')

    # Champs calculés pour affichage
    vehicle_count = fields.Integer(
        'Nombre de véhicules',
        compute='_compute_vehicle_count'
    )

    @api.depends('vehicle_choice')
    def _compute_vehicle_count(self):
        for wizard in self:
            wizard.vehicle_count = self.env['gpl.vehicle'].search_count([('active', '=', True)])

    @api.onchange('vehicle_choice')
    def _onchange_vehicle_choice(self):
        if self.vehicle_choice == 'new':
            self.vehicle_id = False

    def action_create_appointment(self):
        """Créer le rendez-vous"""
        self.ensure_one()

        if self.vehicle_choice == 'new':
            # Créer un nouveau véhicule
            return self._create_new_vehicle()
        else:
            # Mettre à jour un véhicule existant
            return self._update_existing_vehicle()

    def _create_new_vehicle(self):
        """Créer un nouveau véhicule avec RDV"""
        # Create vehicle first without appointment data
        return {
            'name': _('Nouveau véhicule GPL'),
            'type': 'ir.actions.act_window',
            'res_model': 'gpl.vehicle',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                '_create_appointment_after': {
                    'appointment_date': self.appointment_date.isoformat() if self.appointment_date else False,
                    'service_type': self.service_type,
                    'estimated_duration': self.estimated_duration,
                    'technician_ids': self.technician_ids.ids,
                    'notes': self.notes or '',
                }
            }
        }

    def _update_existing_vehicle(self):
        """Créer un rendez-vous pour un véhicule existant"""
        if not self.vehicle_id:
            raise UserError(_("Veuillez sélectionner un véhicule."))

        # Vérifier les conflits de RDV dans les appointments
        conflicting_appointments = self.env['gpl.appointment'].search([
            ('vehicle_id', '!=', self.vehicle_id.id),
            ('state', 'in', ['scheduled', 'confirmed', 'in_progress']),
            ('appointment_date', '>=', self.appointment_date),
            ('appointment_date', '<', self.appointment_date + fields.Datetime.to_datetime('1970-01-01 02:00:00'))
        ])

        if conflicting_appointments:
            conflicting_names = ', '.join(conflicting_appointments.mapped('license_plate'))
            raise UserError(_(
                "Conflit de rendez-vous détecté!\n"
                "Les véhicules suivants ont déjà un RDV à cette heure: %s\n"
                "Veuillez choisir un autre créneau."
            ) % conflicting_names)

        # Créer le rendez-vous
        appointment = self.env['gpl.appointment'].create({
            'vehicle_id': self.vehicle_id.id,
            'appointment_date': self.appointment_date,
            'service_type': self.service_type,
            'estimated_duration': self.estimated_duration,
            'assigned_technician_ids': [(6, 0, self.technician_ids.ids)],
            'notes': self.notes or '',
            'state': 'scheduled',
        })

        # Message de suivi sur le véhicule
        message = _(
            "Nouveau rendez-vous créé:\n"
            "• Référence: %s\n"
            "• Date: %s\n"
            "• Service: %s\n"
            "• Durée: %.1f heures"
        ) % (
            appointment.name,
            self.appointment_date.strftime('%d/%m/%Y %H:%M'),
            dict(self._fields['service_type'].selection)[self.service_type],
            self.estimated_duration
        )

        if self.technician_ids:
            message += _("\n• Techniciens: %s") % ', '.join(self.technician_ids.mapped('name'))

        self.vehicle_id.message_post(body=message)
        appointment.message_post(body=_("Rendez-vous créé via l'assistant"))

        # Notification de succès
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rendez-vous créé'),
                'message': _('Le rendez-vous %s pour %s a été programmé avec succès.') % (
                    appointment.name, self.vehicle_id.display_name
                ),
                'type': 'success',
            }
        }
