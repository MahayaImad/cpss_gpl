from odoo import models, fields, api, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class GplNotificationSystem(models.Model):
    _name = 'gpl.notification.system'
    _description = 'Système de notification automatique'

    @api.model
    def send_daily_notifications(self):
        """Méthode appelée par le cron pour envoyer les notifications quotidiennes"""
        _logger.info("Début des notifications quotidiennes GPL")

        # Notifications pour demain
        self._send_tomorrow_appointments()

        # Notifications pour aujourd'hui
        self._send_today_appointments()

        # Notifications pour retards
        self._send_overdue_appointments()

        # Notifications de maintenance
        self._send_maintenance_notifications()

        _logger.info("Fin des notifications quotidiennes GPL")

        return True

    def _send_tomorrow_appointments(self):
        """Envoyer notifications pour RDV de demain"""
        tomorrow = fields.Date.today() + timedelta(days=1)
        tomorrow_start = datetime.combine(tomorrow, datetime.min.time())
        tomorrow_end = datetime.combine(tomorrow, datetime.max.time())

        # Trouver les véhicules avec RDV demain
        vehicles = self.env['gpl.vehicle'].search([
            ('appointment_date', '>=', tomorrow_start),
            ('appointment_date', '<=', tomorrow_end),
            ('assigned_technician_ids', '!=', False)
        ])

        for vehicle in vehicles:
            self._create_and_send_notification(
                vehicle=vehicle,
                notification_type='appointment_tomorrow',
                subject=f"RDV demain: {vehicle.license_plate}",
                message=self._get_appointment_message(vehicle, 'demain')
            )

    def _send_today_appointments(self):
        """Envoyer notifications pour RDV d'aujourd'hui"""
        today = fields.Date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        vehicles = self.env['gpl.vehicle'].search([
            ('appointment_date', '>=', today_start),
            ('appointment_date', '<=', today_end),
            ('assigned_technician_ids', '!=', False)
        ])

        for vehicle in vehicles:
            self._create_and_send_notification(
                vehicle=vehicle,
                notification_type='appointment_today',
                subject=f"RDV aujourd'hui: {vehicle.license_plate}",
                message=self._get_appointment_message(vehicle, 'aujourd\'hui')
            )

    def _send_overdue_appointments(self):
        """Envoyer notifications pour RDV en retard"""
        now = datetime.now()

        vehicles = self.env['gpl.vehicle'].search([
            ('appointment_date', '<', now),
            ('status_id.name', '!=', 'Terminé'),
            ('assigned_technician_ids', '!=', False)
        ])

        for vehicle in vehicles:
            days_overdue = (now.date() - vehicle.appointment_date.date()).days
            self._create_and_send_notification(
                vehicle=vehicle,
                notification_type='appointment_overdue',
                subject=f"RDV en retard: {vehicle.license_plate}",
                message=self._get_overdue_message(vehicle, days_overdue)
            )

    def _send_maintenance_notifications(self):
        """Envoyer notifications pour maintenances dues"""
        # Exemple: véhicules sans maintenance depuis 6 mois
        six_months_ago = datetime.now() - timedelta(days=180)

        vehicles = self.env['gpl.vehicle'].search([
            '|',
            ('last_maintenance_date', '<', six_months_ago),
            ('last_maintenance_date', '=', False)
        ])

        # Regrouper par technicien
        technician_vehicles = {}
        for vehicle in vehicles:
            for technician in vehicle.assigned_technician_ids:
                if technician not in technician_vehicles:
                    technician_vehicles[technician] = []
                technician_vehicles[technician].append(vehicle)

        # Envoyer une notification groupée par technicien
        for technician, vehicle_list in technician_vehicles.items():
            self._send_maintenance_summary(technician, vehicle_list)

    def _create_and_send_notification(self, vehicle, notification_type, subject, message):
        """Créer et envoyer une notification"""
        notification = self.env['gpl.notification'].create({
            'name': subject,
            'message': message,
            'vehicle_id': vehicle.id,
            'notification_type': notification_type,
            'technician_ids': [(6, 0, vehicle.assigned_technician_ids.ids)],
            'send_email': True,
            'send_internal': True,
        })

        self._send_notification(notification)

    def _send_notification(self, notification):
        """Envoyer la notification via différents canaux"""
        for technician in notification.technician_ids:

            # 1. Notification interne Odoo
            if notification.send_internal:
                self._send_internal_notification(technician, notification)

            # 2. Email
            if notification.send_email and technician.work_email:
                self._send_email_notification(technician, notification)

            # 3. SMS (si configuré)
            if notification.send_sms and technician.mobile_phone:
                self._send_sms_notification(technician, notification)

        notification.write({
            'state': 'sent',
            'sent_date': datetime.now()
        })

    def _send_internal_notification(self, technician, notification):
        """Envoyer notification interne Odoo - VERSION CORRIGÉE"""
        try:
            # SOLUTION SIMPLE: Utiliser uniquement les messages chatter
            if notification.vehicle_id:
                message_body = f"""
                <div style='background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 10px 0;'>
                    <h4 style='color: #1976d2; margin: 0 0 10px 0;'>
                        🔔 Notification pour {technician.name}
                    </h4>
                    <p><strong>{notification.name}</strong></p>
                    <div style='background-color: white; padding: 10px; border-radius: 3px;'>
                        {notification.message}
                    </div>
                    <small style='color: #666;'>
                        Envoyé le {fields.Datetime.now().strftime('%d/%m/%Y à %H:%M')}
                    </small>
                </div>
                """

                notification.vehicle_id.message_post(
                    body=message_body,
                    subject=f"📧 {notification.name}",
                    message_type='comment',
                    partner_ids=[technician.user_id.partner_id.id] if technician.user_id else []
                )

            # Notification popup si possible
            if technician.user_id:
                self.env['bus.bus']._sendone(
                    technician.user_id.partner_id,
                    'notification',
                    {
                        'type': 'info',
                        'title': f"🔧 {notification.name}",
                        'message': notification.message[:200],
                        'sticky': True,
                    }
                )

        except Exception as e:
            _logger.error(f"Erreur notification interne: {e}")

    def _send_email_notification(self, technician, notification):
        """Envoyer notification par email"""
        try:
            template = self.env.ref('cpss_gpl_garage.email_template_technician_notification')

            template.with_context({
                'technician': technician,
                'notification': notification,
                'vehicle': notification.vehicle_id
            }).send_mail(
                notification.id,
                email_values={
                    'email_to': technician.work_email,
                    'subject': notification.name
                },
                force_send=True
            )

        except Exception as e:
            _logger.error(f"Erreur email notification: {e}")

    def _send_sms_notification(self, technician, notification):
        """Envoyer notification par SMS"""
        try:
            # Utiliser le module SMS d'Odoo si disponible
            sms_api = self.env['sms.api']
            if sms_api:
                sms_api.send_sms(
                    numbers=[technician.mobile_phone],
                    message=f"{notification.name}: {notification.message[:100]}..."
                )
        except Exception as e:
            _logger.error(f"Erreur SMS notification: {e}")

    def _get_appointment_message(self, vehicle, when):
        """Générer le message pour RDV"""
        service_type = dict(vehicle._fields['next_service_type'].selection).get(
            vehicle.next_service_type, 'Service'
        )

        return f"""
🚗 Véhicule: {vehicle.license_plate}
👤 Client: {vehicle.client_id.name if vehicle.client_id else 'N/A'}
🔧 Service: {service_type}
📅 Date: {vehicle.appointment_date.strftime('%d/%m/%Y à %H:%M')}
⏱️ Durée estimée: {vehicle.estimated_duration or 2.0} heures

📝 Notes: {vehicle.notes or 'Aucune note particulière'}

Bonne intervention !
        """.strip()

    def _get_overdue_message(self, vehicle, days_overdue):
        """Générer le message pour RDV en retard"""
        return f"""
⚠️ RETARD DÉTECTÉ ⚠️

🚗 Véhicule: {vehicle.license_plate}
👤 Client: {vehicle.client_id.name if vehicle.client_id else 'N/A'}
📅 RDV prévu: {vehicle.appointment_date.strftime('%d/%m/%Y à %H:%M')}
⏰ Retard: {days_overdue} jour(s)

Merci de traiter ce dossier en priorité.
        """.strip()
