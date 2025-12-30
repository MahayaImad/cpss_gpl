from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # === GARAGE GPL ===
    gpl_vehicle_ids = fields.One2many('gpl.vehicle', 'client_id', 'Véhicules GPL')
    gpl_vehicle_count = fields.Integer('Nombre de véhicules GPL', compute='_compute_gpl_vehicle_count')

    # === INFORMATIONS CLIENT GARAGE ===
    is_gpl_client = fields.Boolean('Client GPL', compute='_compute_is_gpl_client', store=True)
    last_gpl_appointment = fields.Datetime('Dernier RDV GPL', compute='_compute_gpl_stats')
    next_gpl_appointment = fields.Datetime('Prochain RDV GPL', compute='_compute_gpl_stats')

    @api.depends('gpl_vehicle_ids')
    def _compute_gpl_vehicle_count(self):
        for partner in self:
            partner.gpl_vehicle_count = len(partner.gpl_vehicle_ids)

    @api.depends('gpl_vehicle_ids')
    def _compute_is_gpl_client(self):
        for partner in self:
            partner.is_gpl_client = bool(partner.gpl_vehicle_ids)

    def _compute_gpl_stats(self):
        """Compute appointment stats from gpl.appointment model"""
        for partner in self:
            if partner.gpl_vehicle_ids:
                # Get all appointments for this partner's vehicles
                appointments = self.env['gpl.appointment'].search([
                    ('vehicle_id', 'in', partner.gpl_vehicle_ids.ids)
                ])

                # Dernier RDV (last completed or past appointment)
                past_appointments = appointments.filtered(
                    lambda a: a.appointment_date and a.appointment_date < fields.Datetime.now()
                ).sorted('appointment_date', reverse=True)
                partner.last_gpl_appointment = past_appointments[0].appointment_date if past_appointments else False

                # Prochain RDV (next scheduled/confirmed appointment)
                future_appointments = appointments.filtered(
                    lambda a: a.appointment_date
                    and a.appointment_date >= fields.Datetime.now()
                    and a.state in ['scheduled', 'confirmed', 'in_progress']
                ).sorted('appointment_date')
                partner.next_gpl_appointment = future_appointments[0].appointment_date if future_appointments else False
            else:
                partner.last_gpl_appointment = False
                partner.next_gpl_appointment = False

    def action_view_gpl_vehicles(self):
        """Action pour voir les véhicules GPL du client"""
        return {
            'name': _('Véhicules GPL'),
            'type': 'ir.actions.act_window',
            'res_model': 'gpl.vehicle',
            'view_mode': 'tree,form',
            'domain': [('client_id', '=', self.id)],
            'context': {'default_client_id': self.id}
        }
