from odoo import api, fields, models


class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    # === INFORMATIONS GPL ===
    is_gpl_compatible = fields.Boolean('Compatible GPL', default=False)
    gpl_installation_time = fields.Float('Temps installation GPL (heures)', default=4.0)

    # === STATISTIQUES ===
    gpl_vehicle_count = fields.Integer('Véhicules GPL', compute='_compute_gpl_vehicle_count')

    @api.depends()
    def _compute_gpl_vehicle_count(self):
        for model in self:
            model.gpl_vehicle_count = self.env['gpl.vehicle'].search_count([('model_id', '=', model.id)])

    def action_view_gpl_vehicles(self):
        """Action pour voir les véhicules GPL de ce modèle"""
        self.ensure_one()
        return {
            'name': f'Véhicules GPL - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'gpl.vehicle',
            'view_mode': 'tree,form',
            'domain': [('model_id', '=', self.id)],
            'context': {'default_model_id': self.id}
        }
