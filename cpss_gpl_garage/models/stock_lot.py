from odoo import models, fields, api, _


class StockLot(models.Model):
    _inherit = 'stock.lot'

    # === LOCALISATION ===
    vehicle_id = fields.Many2one(
        'gpl.vehicle',
        string="Véhicule installé",
        help="Véhicule sur lequel ce réservoir est installé"
    )
