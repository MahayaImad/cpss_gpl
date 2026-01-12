# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class StockLot(models.Model):
    _inherit = 'stock.lot'

    # === CHAMPS GPL RÉSERVOIR ===
    is_gpl_reservoir = fields.Boolean(
        related='product_id.is_gpl_reservoir',
        string="Est un réservoir GPL",
        store=True,
        readonly=True
    )

    # === INFORMATIONS FABRICATION ===
    manufacturing_date = fields.Date(
        string="Date de fabrication",
        help="Date de fabrication du réservoir"
    )

    certification_number = fields.Char(
        string="N° de certification",
        help="Numéro de certification du réservoir"
    )

    # === TESTS ET ÉPREUVES ===
    last_test_date = fields.Date(
        string="Dernière épreuve",
        help="Date de la dernière épreuve hydraulique"
    )

    next_test_date = fields.Date(
        string="Prochaine épreuve",
        compute='_compute_next_test_date',
        store=True,
        help="Date de la prochaine épreuve requise"
    )

    test_frequency_years = fields.Integer(
        string="Fréquence tests (années)",
        default=lambda self: int(
            self.env['ir.config_parameter'].sudo().get_param('cpss_gpl.reservoir_test_frequency', 5)),
        help="Fréquence des tests en années"
    )

    # === ÉTAT ET STATUT ===
    state = fields.Selection([
        ('stock', 'En stock'),
        ('installed', 'Installé'),
        ('scrapped', 'Mis au rebut')
    ], string="État", default='stock', tracking=True)

    reservoir_status = fields.Selection([
        ('valid', 'Valide'),
        ('expiring_soon', 'Expire bientôt'),
        ('expired', 'Expiré'),
        ('test_required', 'Test requis'),
        ('too_old', 'Trop ancien')
    ], string="Statut réservoir", compute='_compute_reservoir_status', store=True)

    installation_date = fields.Date(
        string="Date d'installation",
        help="Date d'installation sur le véhicule"
    )

    # === CARACTÉRISTIQUES TECHNIQUES ===
    capacity = fields.Float(
        related='product_id.gpl_capacity',
        string="Capacité (L)",
        readonly=True
    )

    pressure = fields.Float(
        related='product_id.gpl_pressure',
        string="Pression (bar)",
        readonly=True
    )

    fabricant_id = fields.Many2one(
        related='product_id.gpl_fabricant_id',
        string="Fabricant",
        readonly=True,
        store=True
    )

    # === CHAMPS CALCULÉS ===
    age_years = fields.Integer(
        string="Âge (années)",
        compute='_compute_age_years',
        help="Âge du réservoir en années",
        store = True
    )

    days_until_test = fields.Integer(
        string="Jours avant test",
        compute='_compute_days_until_test',
        help="Nombre de jours avant le prochain test"
    )

    is_test_overdue = fields.Boolean(
        string="Test en retard",
        compute='_compute_test_status',
        store=True,
        help="Le test est-il en retard ?"
    )

    max_age_years = fields.Integer(
        string="Âge maximum (années)",
        default=lambda self: int(self.env['ir.config_parameter'].sudo().get_param('cpss_gpl.reservoir_max_age', 15)),
        help="Âge maximum autorisé"
    )


    # # === CONTRAINTES ===
    # _sql_constraints = [
    #     ('certification_number_unique',
    #      'UNIQUE(certification_number)',
    #      'Le numéro de certification doit être unique !'),
    # ]

    @api.onchange('manufacturing_date')
    def _onchange_manufacturing_date(self):
        """Auto-populate last_test_date with manufacturing_date if not set"""
        if self.manufacturing_date and not self.last_test_date and self.is_gpl_reservoir:
            self.last_test_date = self.manufacturing_date

    @api.depends('fabricant_id')
    def _compute_fabricant_name(self):
        for lot in self:
            try:
                if lot.fabricant_id and hasattr(lot.fabricant_id, 'name'):
                    lot.fabricant_name = lot.fabricant_id.name
                else:
                    lot.fabricant_name = ""
            except:  lot.fabricant_name = ""

    @api.depends('manufacturing_date')
    def _compute_age_years(self):
        """Calcule l'âge du réservoir en années"""
        for lot in self:
            if lot.manufacturing_date:
                today = fields.Date.today()
                delta = today - lot.manufacturing_date
                lot.age_years = delta.days / 365.25
            else:
                lot.age_years = 0.0

    @api.depends('next_test_date')
    def _compute_days_until_test(self):
        """Calcule les jours restants avant le prochain test"""
        for lot in self:
            if lot.next_test_date:
                today = fields.Date.today()
                delta = lot.next_test_date - today
                lot.days_until_test = delta.days
            else:
                lot.days_until_test = 0

    @api.depends('next_test_date', 'age_years', 'max_age_years')
    def _compute_reservoir_status(self):
        """Calcule le statut du réservoir"""
        warning_days = int(self.env['ir.config_parameter'].sudo().get_param('cpss_gpl.notification_test_days', 30))

        for lot in self:
            if not lot.is_gpl_reservoir:
                lot.reservoir_status = 'valid'
                continue

            today = fields.Date.today()

            # Vérifier l'âge maximum
            if lot.age_years >= lot.max_age_years:
                lot.reservoir_status = 'too_old'
            # Vérifier si test expiré
            elif lot.next_test_date and lot.next_test_date < today:
                lot.reservoir_status = 'expired'
            # Vérifier si test requis bientôt
            elif lot.next_test_date and (lot.next_test_date - today).days <= warning_days:
                lot.reservoir_status = 'expiring_soon'
            else:
                lot.reservoir_status = 'valid'

    @api.depends('last_test_date', 'test_frequency_years')
    def _compute_next_test_date(self):
        """Calcule la date de la prochaine épreuve requise"""
        for lot in self:
            if lot.last_test_date and lot.test_frequency_years:
                # Ajouter la fréquence en années à la dernière date de test
                next_date = lot.last_test_date + timedelta(days=lot.test_frequency_years * 365)
                lot.next_test_date = next_date
            else:
                lot.next_test_date = False

    @api.depends('next_test_date')
    def _compute_test_status(self):
        """Calcule si le test est en retard"""
        today = fields.Date.today()
        for lot in self:
            lot.is_test_overdue = (
                lot.next_test_date and
                lot.next_test_date < today
            )

    @api.constrains('manufacturing_date')
    def _check_manufacturing_date(self):
        """Vérifie que la date de fabrication est cohérente"""
        for lot in self:
            if lot.manufacturing_date:
                if lot.manufacturing_date > fields.Date.today():
                    raise ValidationError(_("La date de fabrication ne peut pas être dans le futur."))

                # Vérifier que le réservoir n'est pas trop ancien
                if lot.age_years > lot.max_age_years:
                    raise ValidationError(
                        _("Ce réservoir est trop ancien (%.1f ans). L'âge maximum autorisé est de %d ans.")
                        % (lot.age_years, lot.max_age_years)
                    )

    @api.constrains('last_test_date', 'manufacturing_date')
    def _check_test_date(self):
        """Vérifie que la date de test est cohérente"""
        for lot in self:
            if lot.last_test_date and lot.manufacturing_date:
                if lot.last_test_date < lot.manufacturing_date:
                    raise ValidationError(_("La date de test ne peut pas être antérieure à la fabrication."))

    @api.model_create_multi
    def create(self, vals_list):
        """Create method updated for Odoo 17"""
        lots = super().create(vals_list)

        # Pour les nouveaux réservoirs, définir la dernière date de test
        for lot in lots.filtered('is_gpl_reservoir'):
            if lot.manufacturing_date and not lot.last_test_date:
                # Premier test = date de fabrication
                lot.last_test_date = lot.manufacturing_date

        return lots

    @api.onchange('manufacturing_date')
    def _onchange_manufacturing_date(self):
        """Auto-populate last_test_date with manufacturing_date if not set"""

        if self.manufacturing_date and not self.last_test_date and self.is_gpl_reservoir:
            self.last_test_date = self.manufacturing_date


    def action_schedule_test(self):
        """Programme un test pour ce réservoir"""
        self.ensure_one()

        if not self.is_gpl_reservoir:
            raise UserError(_("Cette action n'est disponible que pour les réservoirs GPL."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Programmer Test - %s') % self.name,
            'res_model': 'gpl.reservoir.testing',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reservoir_lot_id': self.id,
                'default_test_type': 'periodic'
            }
        }

    def action_mark_installed(self):
        """Marque le réservoir comme installé"""
        self.ensure_one()

        if self.state != 'stock':
            raise UserError(_("Seuls les réservoirs en stock peuvent être marqués comme installés."))

        self.write({
            'state': 'installed',
            'installation_date': fields.Date.today()
        })

    def action_mark_stock(self):
        """Remet le réservoir en stock"""
        self.ensure_one()

        self.write({
            'state': 'stock',
            'installation_date': False
        })

    def action_scrap_reservoir(self):
        """Met le réservoir au rebut"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Mettre au rebut - %s') % self.name,
            'res_model': 'stock.scrap',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.product_id.id,
                'default_lot_id': self.id,
                'default_scrap_qty': 1.0
            }
        }

    def name_get(self):
        """Personnalise l'affichage du nom"""
        result = []
        for lot in self:
            name = lot.name
            if lot.is_gpl_reservoir:
                if lot.fabricant_id:
                    name = f"[{lot.fabricant_id.code}] {name}"
                if lot.capacity:
                    name += f" ({lot.capacity}L)"
                if lot.reservoir_status:
                    status_labels = {
                        'valid': '✓',
                        'expiring_soon': '⚠',
                        'expired': '✗',
                        'test_required': '!',
                        'too_old': '⚠'
                    }
                    name += f" {status_labels.get(lot.reservoir_status, '')}"
            result.append((lot.id, name))
        return result

    @api.model
    def get_reservoir_dashboard_data(self):
        """Retourne les données pour le dashboard des réservoirs"""
        reservoirs = self.search([('is_gpl_reservoir', '=', True)])

        data = {
            'total': len(reservoirs),
            'by_status': {},
            'by_fabricant': {},
            'by_state': {},
            'expiring_soon': [],
            'expired': [],
            'alerts': []
        }

        # Statistiques par statut
        for status in ['valid', 'expiring_soon', 'expired', 'test_required', 'too_old']:
            count = reservoirs.filtered(lambda r: r.reservoir_status == status)
            data['by_status'][status] = len(count)

        # Statistiques par fabricant
        fabricants = reservoirs.mapped('fabricant_id')
        for fabricant in fabricants:
            fab_reservoirs = reservoirs.filtered(lambda r: r.fabricant_id == fabricant)
            data['by_fabricant'][fabricant.code] = len(fab_reservoirs)

        # Statistiques par état
        for state in ['stock', 'installed', 'scrapped']:
            count = reservoirs.filtered(lambda r: r.state == state)
            data['by_state'][state] = len(count)

        # Réservoirs expirant bientôt
        expiring = reservoirs.filtered(lambda r: r.reservoir_status == 'expiring_soon')
        for res in expiring:
            data['expiring_soon'].append({
                'id': res.id,
                'name': res.name,
                'days_until_test': res.days_until_test
            })

        # Réservoirs expirés
        expired = reservoirs.filtered(lambda r: r.reservoir_status == 'expired')
        for res in expired:
            data['expired'].append({
                'id': res.id,
                'name': res.name,
                'days_overdue': abs(res.days_until_test)
            })

        # Alertes générales
        if data['by_status']['expired'] > 0:
            data['alerts'].append({
                'type': 'error',
                'message': f"{data['by_status']['expired']} réservoir(s) expiré(s)"
            })

        if data['by_status']['expiring_soon'] > 0:
            data['alerts'].append({
                'type': 'warning',
                'message': f"{data['by_status']['expiring_soon']} réservoir(s) expirent bientôt"
            })

        return data

    @api.model
    def send_expiration_notifications(self):
        """Envoie les notifications d'expiration (à appeler par cron)"""
        notification_email = self.env['ir.config_parameter'].sudo().get_param('cpss_gpl.notification_email')
        if not notification_email:
            return

        warning_days = int(self.env['ir.config_parameter'].sudo().get_param('cpss_gpl.notification_test_days', 30))

        # Réservoirs expirant bientôt
        expiring = self.search([
            ('is_gpl_reservoir', '=', True),
            ('reservoir_status', '=', 'expiring_soon')
        ])

        # Réservoirs expirés
        expired = self.search([
            ('is_gpl_reservoir', '=', True),
            ('reservoir_status', '=', 'expired')
        ])

        if expiring or expired:
            # Composer le message
            message = "Alerte GPL - Réservoirs nécessitant attention:\n\n"

            if expired:
                message += "RÉSERVOIRS EXPIRÉS:\n"
                for res in expired:
                    message += f"- {res.name} ({res.fabricant_id.code if res.fabricant_id else ''})\n"
                    message += f"  Test expiré depuis {abs(res.days_until_test)} jours\n"
                    message += "\n"

            if expiring:
                message += "RÉSERVOIRS EXPIRANT BIENTÔT:\n"
                for res in expiring:
                    message += f"- {res.name} ({res.fabricant_id.code if res.fabricant_id else ''})\n"
                    message += f"  Test requis dans {res.days_until_test} jours\n"
                    message += "\n"

            # Envoyer l'email (implémentation simplifiée)
            mail_values = {
                'subject': 'GPL CPSS - Alerte Réservoirs',
                'body_html': message.replace('\n', '<br>'),
                'email_to': notification_email,
                'email_from': self.env.user.email or 'noreply@cedarpss.com'
            }

            self.env['mail.mail'].create(mail_values).send()

    @api.model
    def cron_check_reservoirs(self):
        """Fonction cron pour vérifier les réservoirs"""
        _logger.info("Vérification automatique des réservoirs GPL...")

        # Recalculer les statuts
        reservoirs = self.search([('is_gpl_reservoir', '=', True)])
        reservoirs._compute_reservoir_status()

        # Envoyer les notifications
        self.send_expiration_notifications()

        _logger.info(f"Vérification terminée pour {len(reservoirs)} réservoirs.")
