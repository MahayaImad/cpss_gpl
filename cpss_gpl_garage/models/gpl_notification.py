from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class GplNotification(models.Model):
    _name = 'gpl.notification'
    _description = 'Notification GPL'
    _order = 'create_date desc'

    name = fields.Char('Sujet', required=True)
    message = fields.Text('Message', required=True)

    # Destinataires
    technician_ids = fields.Many2many(
        'hr.employee',
        string='Techniciens',
        domain=[('department_id.name', 'ilike', 'atelier')]
    )

    # Type de notification
    notification_type = fields.Selection([
        ('appointment_tomorrow', 'RDV demain'),
        ('appointment_today', 'RDV aujourd\'hui'),
        ('appointment_overdue', 'RDV en retard'),
        ('maintenance_due', 'Maintenance due'),
        ('inspection_due', 'Inspection due'),
    ], string='Type', default='appointment_tomorrow')

    # Véhicule concerné
    vehicle_id = fields.Many2one('gpl.vehicle', 'Véhicule')

    # Statut
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé'),
        ('read', 'Lu'),
    ], default='draft')

    sent_date = fields.Datetime('Date d\'envoi')
    read_date = fields.Datetime('Date de lecture')

    # Paramètres d'envoi
    send_email = fields.Boolean('Envoyer par email', default=True)
    send_sms = fields.Boolean('Envoyer par SMS', default=False)
    send_internal = fields.Boolean('Notification interne', default=True)

    def action_send_now(self):
        """Envoyer la notification maintenant"""
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(_("Cette notification a déjà été envoyée."))

        # Appeler le système de notification
        notification_system = self.env['gpl.notification.system']
        notification_system._send_notification(self)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Notification envoyée'),
                'message': _('La notification a été envoyée avec succès.'),
                'type': 'success',
            }
        }
