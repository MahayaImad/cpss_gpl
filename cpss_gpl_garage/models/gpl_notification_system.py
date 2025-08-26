from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class GplNotificationSystem(models.Model):
    _name = 'gpl.notification.system'
    _description = 'Système de notification simplifié GPL'

    @api.model
    def send_daily_technician_emails(self):
        """
        Méthode principale : Envoie un email quotidien à tous les techniciens
        avec leurs tâches du jour
        """
        try:
            # 1. Récupérer tous les techniciens de l'atelier
            technicians = self.env['hr.employee'].search([
                ('department_id.name', 'ilike', 'atelier'),
                ('work_email', '!=', False),  # Seulement ceux avec email
                ('active', '=', True)
            ])

            if not technicians:
                _logger.warning("Aucun technicien trouvé avec email")
                return

            # 2. Pour chaque technicien, préparer et envoyer l'email
            sent_count = 0
            for technician in technicians:
                if self._send_daily_email_to_technician(technician):
                    sent_count += 1

            _logger.info(f"Emails quotidiens envoyés à {sent_count}/{len(technicians)} techniciens")

        except Exception as e:
            _logger.error(f"Erreur envoi emails quotidiens: {e}")

    def _send_daily_email_to_technician(self, technician):
        """Envoyer l'email quotidien à un technicien"""
        try:
            # Récupérer les tâches du technicien
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)

            # RDV d'aujourd'hui
            today_appointments = self.env['gpl.vehicle'].search([
                ('assigned_technician_ids', 'in', technician.id),
                ('appointment_date', '>=', today),
                ('appointment_date', '<', tomorrow)
            ])

            # RDV de demain
            tomorrow_appointments = self.env['gpl.vehicle'].search([
                ('assigned_technician_ids', 'in', technician.id),
                ('appointment_date', '>=', tomorrow),
                ('appointment_date', '<', tomorrow + timedelta(days=1))
            ])

            # RDV en retard
            overdue_appointments = self.env['gpl.vehicle'].search([
                ('assigned_technician_ids', 'in', technician.id),
                ('appointment_date', '<', today),
                ('next_service_type', '!=', False)  # RDV non traité
            ])


            # Créer le contenu de l'email
            email_content = self._generate_daily_email_content(
                technician, today_appointments, tomorrow_appointments,
                overdue_appointments
            )

            # Envoyer l'email
            return self._send_simple_email(
                technician.work_email,
                f"📧 Vos tâches du {today.strftime('%d/%m/%Y')} - Atelier GPL",
                email_content
            )

        except Exception as e:
            _logger.error(f"Erreur email pour {technician.name}: {e}")
            return False

    def _generate_daily_email_content(self, technician, today, tomorrow, overdue):
        """Générer le contenu HTML de l'email quotidien"""
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #007bff; color: white; padding: 20px; text-align: center;">
                <h2>🔧 Bonjour {technician.name}</h2>
                <p>Voici vos tâches pour aujourd'hui</p>
            </div>

            <div style="padding: 20px; background-color: #f8f9fa;">
        """

        # -----------------------
        # RDV d'aujourd'hui
        # -----------------------
        if today:
            html_content += """
                <div style="background-color: #d4edda; border: 1px solid #c3e6cb;
                            padding: 15px; margin: 10px 0; border-radius: 5px;">
                    <h3 style="color: #155724; margin-top: 0;">📅 RDV AUJOURD'HUI</h3>
            """
            for vehicle in today:
                service_type = "Service GPL"
                if getattr(vehicle, "next_service_type", False):
                    try:
                        if hasattr(vehicle._fields.get("next_service_type"), "selection"):
                            service_dict = dict(vehicle._fields["next_service_type"].selection)
                            service_type = service_dict.get(vehicle.next_service_type, vehicle.next_service_type)
                        else:
                            service_type = vehicle.next_service_type
                    except Exception:
                        service_type = "Service GPL"

                html_content += f"""
                    <div style="background-color: white; padding: 10px;
                                margin: 5px 0; border-radius: 3px;">
                        <strong>🚗 {vehicle.license_plate or 'N/A'}</strong><br/>
                        👤 Client: {vehicle.client_id.name if vehicle.client_id else 'N/A'}<br/>
                        ⏰ {vehicle.appointment_date.strftime('%H:%M') if vehicle.appointment_date else 'N/A'}<br/>
                        🔧 {service_type}
                    </div>
                """
            html_content += "</div>"
        else:
            html_content += """
                <div style="background-color: #d1ecf1; border: 1px solid #bee5eb;
                            padding: 15px; margin: 10px 0; border-radius: 5px;">
                    <h3 style="color: #0c5460; margin-top: 0;">📅 RDV AUJOURD'HUI</h3>
                    <p>✅ Aucun rendez-vous prévu aujourd'hui</p>
                </div>
            """

        # -----------------------
        # RDV de demain
        # -----------------------
        if tomorrow:
            html_content += """
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7;
                            padding: 15px; margin: 10px 0; border-radius: 5px;">
                    <h3 style="color: #856404; margin-top: 0;">📋 PRÉPARATION DEMAIN</h3>
            """
            for vehicle in tomorrow:
                service_type = "Service GPL"
                if getattr(vehicle, "next_service_type", False):
                    try:
                        if hasattr(vehicle._fields.get("next_service_type"), "selection"):
                            service_dict = dict(vehicle._fields["next_service_type"].selection)
                            service_type = service_dict.get(vehicle.next_service_type, vehicle.next_service_type)
                        else:
                            service_type = vehicle.next_service_type
                    except Exception:
                        service_type = "Service GPL"

                html_content += f"""
                    <div style="background-color: white; padding: 10px;
                                margin: 5px 0; border-radius: 3px;">
                        <strong>🚗 {vehicle.license_plate or 'N/A'}</strong><br/>
                        👤 Client: {vehicle.client_id.name if vehicle.client_id else 'N/A'}<br/>
                        ⏰ {vehicle.appointment_date.strftime('%H:%M') if vehicle.appointment_date else 'N/A'}<br/>
                        🔧 {service_type}
                    </div>
                """
            html_content += "</div>"

        # -----------------------
        # RDV en retard
        # -----------------------
        if overdue:
            html_content += """
                <div style="background-color: #f8d7da; border: 1px solid #f5c6cb;
                            padding: 15px; margin: 10px 0; border-radius: 5px;">
                    <h3 style="color: #721c24; margin-top: 0;">⚠️ RETARDS À TRAITER</h3>
            """
            for vehicle in overdue:
                days_late = (
                    (datetime.now().date() - vehicle.appointment_date.date()).days
                    if vehicle.appointment_date else 0
                )
                html_content += f"""
                    <div style="background-color: white; padding: 10px;
                                margin: 5px 0; border-radius: 3px;">
                        <strong>🚗 {vehicle.license_plate or 'N/A'}</strong><br/>
                        👤 Client: {vehicle.client_id.name if vehicle.client_id else 'N/A'}<br/>
                        ⏰ Prévu: {vehicle.appointment_date.strftime('%d/%m/%Y %H:%M') if vehicle.appointment_date else 'N/A'}<br/>
                        🔴 Retard: {days_late} jour(s)
                    </div>
                """
            html_content += "</div>"

        # -----------------------
        # Pied de mail
        # -----------------------
        html_content += """
            </div>
            <div style="background-color: #6c757d; color: white;
                        padding: 15px; text-align: center;">
                <p style="margin: 0;">
                    Bonne journée ! 💪<br/>
                    <small>Email automatique - Système GPL CPSS</small>
                </p>
            </div>
        </div>
        """

        return html_content

    def _send_simple_email(self, email_to, subject, html_content):
        """Envoyer un email simple sans template"""
        try:
            # Utiliser le système de mail d'Odoo
            mail_values = {
                'subject': subject,
                'body_html': html_content,
                'email_to': email_to,
                'email_from': self.env.user.company_id.email or 'noreply@localhost',
                'auto_delete': True,
            }

            mail = self.env['mail.mail'].create(mail_values)
            mail.send()
            _logger.info(f"Email envoyé avec succès à {email_to}")
            return True

        except Exception as e:
            _logger.error(f"Erreur envoi email à {email_to}: {e}")
            return False

    @api.model
    def send_manager_notifications(self):
        """
        Envoyer notifications internes aux managers
        (notifications dans Odoo pour ceux qui ont un compte)
        """
        try:
            # Récupérer les managers/superviseurs
            managers = self.env['hr.employee'].search([
                ('user_id', '!=', False),  # Seulement ceux avec compte Odoo
                ('active', '=', True),
                '|',
                ('category_ids.name', 'ilike', 'manager'),
                ('department_id.manager_id', '!=', False)
            ])

            if not managers:
                # Fallback : utiliser les utilisateurs admin ou avec droits sur véhicules
                admin_users = self.env['res.users'].search([
                    ('groups_id', 'in', self.env.ref('base.group_system').id)
                ])
                managers = self.env['hr.employee'].search([
                    ('user_id', 'in', admin_users.ids),
                    ('active', '=', True)
                ])

            # Générer le rapport quotidien
            daily_summary = self._generate_daily_manager_summary()

            # Envoyer notification interne à chaque manager
            sent_count = 0
            for manager in managers:
                if self._send_internal_notification_to_manager(manager, daily_summary):
                    sent_count += 1

            _logger.info(f"Notifications envoyées à {sent_count}/{len(managers)} managers")

        except Exception as e:
            _logger.error(f"Erreur notifications managers: {e}")

    def _generate_daily_manager_summary(self):
        """Générer le résumé quotidien pour les managers"""
        today = datetime.now().date()

        # Statistiques du jour
        stats = {
            'total_appointments_today': self.env['gpl.vehicle'].search_count([
                ('appointment_date', '>=', today),
                ('appointment_date', '<', today + timedelta(days=1))
            ]),
            'overdue_appointments': self.env['gpl.vehicle'].search_count([
                ('appointment_date', '<', today),
                ('next_service_type', '!=', False)
            ]),
            'total_technicians_active': self.env['hr.employee'].search_count([
                ('department_id.name', 'ilike', 'atelier'),
                ('active', '=', True)
            ])
        }

        return stats

    def _send_internal_notification_to_manager(self, manager, stats):
        """Envoyer notification interne au manager"""
        try:
            priority_alerts = self._get_priority_alerts()
            alert_icon = "⚠️" if priority_alerts else "✅"

            message = f"""📊 Rapport quotidien atelier GPL - {datetime.now().strftime('%d/%m/%Y')}

📅 RDV aujourd'hui: {stats['total_appointments_today']}
⚠️ RDV en retard: {stats['overdue_appointments']}
👥 Techniciens actifs: {stats['total_technicians_active']}

{alert_icon} {priority_alerts}"""

            # Utiliser le système de notification bus d'Odoo
            if hasattr(self.env['bus.bus'], '_sendone'):
                self.env['bus.bus']._sendone(
                    manager.user_id.partner_id,
                    'notification',
                    {
                        'type': 'info' if stats['overdue_appointments'] == 0 else 'warning',
                        'title': '📊 Rapport atelier GPL',
                        'message': message,
                        'sticky': True,
                    }
                )
                return True
            else:
                _logger.warning("Système de notification bus non disponible")
                return False

        except Exception as e:
            _logger.error(f"Erreur notification manager {manager.name}: {e}")
            return False

    def _get_priority_alerts(self):
        """Générer les alertes prioritaires pour les managers"""
        alerts = []

        # Vérifier les retards critiques (plus de 3 jours)
        try:
            critical_overdue = self.env['gpl.vehicle'].search_count([
                ('appointment_date', '<', datetime.now().date() - timedelta(days=3)),
                ('next_service_type', '!=', False)
            ])

            if critical_overdue > 0:
                alerts.append(f"URGENT: {critical_overdue} RDV avec plus de 3 jours de retard")

        except Exception as e:
            _logger.error(f"Erreur calcul retards critiques: {e}")

        return " | ".join(alerts) if alerts else "Aucune alerte critique"


# Extension de la classe existante pour ajouter les nouvelles méthodes
class GplNotificationSystem(models.Model):
    _inherit = 'gpl.notification.system'

    @api.model
    def send_simple_daily_notifications(self):
        """Nouvelle méthode utilisant le système simplifié"""
        simple_system = self.env['gpl.notification.system']

        # Emails pour techniciens
        simple_system.send_daily_technician_emails()

        # Notifications pour managers
        simple_system.send_manager_notifications()


# Modèle pour les tâches cron
class GplCronJobs(models.Model):
    _name = 'gpl.cron.jobs'
    _description = 'Tâches automatisées GPL'

    @api.model
    def daily_notification_job(self):
        """Tâche quotidienne : emails techniciens + notifications managers"""
        try:
            notification_system = self.env['gpl.notification.system']

            # Emails pour techniciens (tous les jours à 7h)
            notification_system.send_daily_technician_emails()

            # Notifications internes pour managers (tous les jours à 8h)
            notification_system.send_manager_notifications()

        except Exception as e:
            _logger.error(f"Erreur job quotidien notifications: {e}")
