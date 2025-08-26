from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VehicleAppointmentWizardOverride(models.TransientModel):
    """Extension de l'assistant de rendez-vous pour intégration opérations"""
    _inherit = 'vehicle.appointment.wizard'

    # === NOUVEAUX CHAMPS ===
    create_operation_immediately = fields.Boolean(
        string="Créer l'opération immédiatement",
        default=True,
        help="Créer directement le document d'opération après le rendez-vous"
    )

    estimated_cost = fields.Float(
        string="Coût estimé (DZD)",
        help="Estimation du coût de l'intervention"
    )

    required_parts = fields.Text(
        string="Pièces nécessaires",
        help="Liste des pièces qui seront nécessaires"
    )

    priority = fields.Selection([
        ('0', 'Normale'),
        ('1', 'Urgente'),
        ('2', 'Très urgente'),
    ], string='Priorité', default='0')

    # Champs visibles selon le type de service
    show_reservoir_fields = fields.Boolean(
        string="Afficher champs réservoir",
        compute='_compute_show_fields'
    )

    show_repair_fields = fields.Boolean(
        string="Afficher champs réparation",
        compute='_compute_show_fields'
    )

    @api.depends('service_type')
    def _compute_show_fields(self):
        """Affiche les champs selon le type de service"""
        for wizard in self:
            wizard.show_reservoir_fields = wizard.service_type in ['installation', 'testing']
            wizard.show_repair_fields = wizard.service_type in ['repair']

    def _update_existing_vehicle(self):
        """Surcharge pour créer l'opération si demandé"""
        # Appeler la méthode parente
        result = super()._update_existing_vehicle()

        # Créer l'opération immédiatement si demandé
        if self.create_operation_immediately and self.vehicle_id:
            try:
                # Mettre à jour les informations supplémentaires
                self.vehicle_id.write({
                    'notes': (self.vehicle_id.notes or '') + '\n' + (self.notes or ''),
                    'estimated_cost': self.estimated_cost,
                })

                # Créer l'opération
                operation_result = self._create_operation_from_appointment()

                if operation_result:
                    return operation_result

            except Exception as e:
                # En cas d'erreur, continuer avec le résultat normal
                # et afficher un message d'information
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Rendez-vous créé'),
                        'message': _(
                            'Le rendez-vous a été créé, mais l\'opération n\'a pas pu être générée automatiquement. Vous pouvez la créer manuellement.'),
                        'type': 'warning',
                    }
                }

        return result

    def _create_operation_from_appointment(self):
        """Crée l'opération correspondante au rendez-vous"""
        if not self.vehicle_id:
            return False

        # Préparer les données communes
        common_data = {
            'vehicle_id': self.vehicle_id.id,
            'client_id': self.vehicle_id.client_id.id,
            'date_start': self.appointment_date,
            'date_planned': self.appointment_date,
            'technician_ids': [(6, 0, self.technician_ids.ids)],
            'notes': f"{self.notes or ''}\n{self.required_parts or ''}".strip(),
        }

        if self.service_type == 'installation':
            return self._create_installation_from_appointment(common_data)
        elif self.service_type == 'repair':
            return self._create_repair_from_appointment(common_data)
        elif self.service_type == 'inspection':
            return self._create_inspection_from_appointment(common_data)
        elif self.service_type == 'testing':
            return self._create_testing_from_appointment(common_data)

        return False

    def _create_installation_from_appointment(self, common_data):
        """Crée une installation depuis le rendez-vous"""
        installation = self.env['gpl.service.installation'].create({
            **common_data,
            'state': 'planned',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Installation GPL Planifiée'),
            'res_model': 'gpl.service.installation',
            'res_id': installation.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_repair_from_appointment(self, common_data):
        """Crée une réparation depuis le rendez-vous"""
        repair = self.env['gpl.repair.order'].create({
            **common_data,
            'repair_type': 'repair',
            'priority': self.priority,
            'symptoms': self.notes or '',
            'date_scheduled': common_data['date_planned'],
            'state': 'draft',
        })

        # Planifier automatiquement
        repair.action_confirm()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Réparation GPL Planifiée'),
            'res_model': 'gpl.repair.order',
            'res_id': repair.id,
            'view_mode': 'form',
            'target': 'current',
        }


    def _create_inspection_from_appointment(self, common_data):
        """Crée un contrôle depuis le rendez-vous"""
        inspection = self.env['gpl.inspection'].create({
            **common_data,
            'inspection_type': 'periodic',
            'state': 'draft',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrôle Technique GPL'),
            'res_model': 'gpl.inspection',
            'res_id': inspection.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_testing_from_appointment(self, common_data):
        """Crée un test de réservoir depuis le rendez-vous"""
        if not self.vehicle_id.reservoir_lot_id:
            raise UserError(_("Aucun réservoir associé à ce véhicule pour le test."))

        testing = self.env['gpl.reservoir.testing'].create({
            **common_data,
            'reservoir_lot_id': self.vehicle_id.reservoir_lot_id.id,
            'test_type': 'hydraulic',
            'state': 'draft',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Test Réservoir GPL'),
            'res_model': 'gpl.reservoir.testing',
            'res_id': testing.id,
            'view_mode': 'form',
            'target': 'current',
        }
