from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class GplRescheduleWizard(models.TransientModel):
    _name = 'gpl.reschedule.wizard'
    _description = 'Assistant de reprogrammation de rendez-vous'

    vehicle_id = fields.Many2one('gpl.vehicle', 'Véhicule', required=True)
    current_date = fields.Datetime('Rendez-vous actuel', readonly=True)
    new_date = fields.Datetime('Nouveau rendez-vous', required=True)
    new_technician_ids = fields.Many2many('hr.employee', string='Nouveaux techniciens')
    reason = fields.Text('Raison du changement')
    notify_client = fields.Boolean('Notifier le client', default=True)

    # Champs calculés pour affichage
    service_type = fields.Selection(related='vehicle_id.next_service_type', readonly=True)
    client_id = fields.Many2one(related='vehicle_id.client_id', readonly=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        vehicle_id = self.env.context.get('default_vehicle_id')
        if vehicle_id:
            vehicle = self.env['gpl.vehicle'].browse(vehicle_id)
            res.update({
                'current_date': vehicle.appointment_date,
                'new_technician_ids': [(6, 0, vehicle.assigned_technician_ids.ids)],
            })
        return res

    def action_reschedule(self):
        """Effectue la reprogrammation"""
        self.ensure_one()

        if not self.new_date:
            raise UserError(_("Veuillez sélectionner une nouvelle date."))

        if self.new_date <= fields.Datetime.now():
            raise UserError(_("La nouvelle date doit être dans le futur."))

        # Mise à jour du véhicule
        values = {'appointment_date': self.new_date}
        if self.new_technician_ids:
            values['assigned_technician_ids'] = [(6, 0, self.new_technician_ids.ids)]

        self.vehicle_id.write(values)

        # Historique
        message = f"Rendez-vous reprogrammé:\n• Ancienne date: {self.current_date}\n• Nouvelle date: {self.new_date}"
        if self.reason:
            message += f"\n• Raison: {self.reason}"

        self.vehicle_id.message_post(body=message)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rendez-vous reprogrammé'),
                'message': _('Le rendez-vous a été reprogrammé avec succès.'),
                'type': 'success',
            }
        }
