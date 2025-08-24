# wizard/notification_test_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class NotificationTestWizard(models.TransientModel):
    _name = 'notification.test.wizard'
    _description = 'Test du système de notification'

    test_type = fields.Selection([
        ('technician_emails', 'Test emails techniciens'),
        ('manager_notifications', 'Test notifications managers'),
        ('single_technician', 'Test email technicien spécifique'),
    ], string='Type de test', default='technician_emails', required=True)

    technician_id = fields.Many2one(
        'hr.employee',
        string='Technicien',
        domain=[('department_id.name', 'ilike', 'atelier')],
        help="Pour test d'un technicien spécifique"
    )

    def action_test_notifications(self):
        """Lancer le test des notifications"""
        notification_system = self.env['gpl.notification.system']

        try:
            if self.test_type == 'technician_emails':
                notification_system.send_daily_technician_emails()
                message = "Emails de test envoyés à tous les techniciens"

            elif self.test_type == 'manager_notifications':
                notification_system.send_manager_notifications()
                message = "Notifications de test envoyées aux managers"

            elif self.test_type == 'single_technician':
                if not self.technician_id:
                    raise UserError("Veuillez sélectionner un technicien")

                notification_system._send_daily_email_to_technician(self.technician_id)
                message = f"Email de test envoyé à {self.technician_id.name}"

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Test réussi',
                    'message': message,
                    'type': 'success',
                }
            }

        except Exception as e:
            raise UserError(f"Erreur lors du test : {str(e)}")
