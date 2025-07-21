from odoo import models, fields


class GplVehicleTag(models.Model):
    _name = 'gpl.vehicle.tag'
    _description = 'Tags pour véhicules GPL'
    _order = 'name'

    name = fields.Char('Nom', required=True)
    color = fields.Integer('Couleur', default=0)
    active = fields.Boolean('Actif', default=True)
    description = fields.Text('Description')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Ce tag existe déjà!')
    ]
