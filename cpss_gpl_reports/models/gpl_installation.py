from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GplInspection(models.Model):
    """Extension du modèle inspection pour intégration du rapport"""
    _inherit = 'gpl.service.installation'

    def action_print_certificate(self):
        """Imprime le certificat de contrôle"""
        self.ensure_one()

        if self.state != 'done':
            raise UserError(_("Le certificat ne peut être imprimé que pour un montage validé et terminé."))

        return self.env.ref('cpss_gpl_reports.action_report_gpl_montage_certificate').report_action(self)

    def action_print_gpl_invoice(self):
        """Imprime la facture de l'installation"""
        self.ensure_one()

        if self.state != 'done':
            raise UserError(_("La facture ne peut être imprimée que pour un montage validé et terminé."))

        return self.env.ref('cpss_gpl_reports.action_report_gpl_invoice').report_action(self)



