from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    # === INFORMATIONS GPL ===
    gpl_company_name = fields.Char(
        string="Nom de l'entreprise GPL",
        help="Nom affiché sur les certificats et rapports GPL"
    )

    gpl_company_license = fields.Char(
        string="Numéro d'agrément GPL",
        help="Numéro d'agrément officiel pour les installations GPL"
    )
