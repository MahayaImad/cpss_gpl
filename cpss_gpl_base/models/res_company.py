from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    # === INFORMATIONS GPL ===

    gpl_company_license = fields.Char(
        string="Numéro d'agrément GPL",
        help="Numéro d'agrément officiel pour les installations GPL"
    )
