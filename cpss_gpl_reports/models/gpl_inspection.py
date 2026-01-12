from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GplInspection(models.Model):
    """Extension du modèle inspection pour intégration du rapport"""
    _inherit = 'gpl.inspection'

    def action_print_certificate(self):
        """Imprime le certificat de contrôle"""
        self.ensure_one()

        if self.state != 'done' or self.result != 'pass':
            raise UserError(_("Le certificat ne peut être imprimé que pour un contrôle validé et terminé."))

        # if self.inspection_type == 'initial':
        #     return self.env.ref('cpss_gpl_reports.action_report_gpl_authorization').report_action(self)
        #
        # if self.inspection_type == 'periodic':
        #     return self.env.ref('cpss_gpl_reports.action_report_gpl_triennial_certificate').report_action(self)

        return self.env.ref('cpss_gpl_reports.action_report_gpl_authorization').report_action(self)

    def action_print_card(self):
        """Imprime le certificat de contrôle"""
        self.ensure_one()

        if self.state != 'done' or self.result != 'pass':
            raise UserError(_("La carte ne peut être imprimé que pour un contrôle validé et terminé."))

        return self.env.ref('cpss_gpl_reports.action_report_gpl_card').report_action(self)

    def action_print_card_verso(self):
        """Imprime le certificat de contrôle"""
        self.ensure_one()

        if self.state != 'done' or self.result != 'pass':
            raise UserError(_("La carte ne peut être imprimé que pour un contrôle validé et terminé."))

        return self.env.ref('cpss_gpl_reports.action_report_gpl_card_verso').report_action(self)