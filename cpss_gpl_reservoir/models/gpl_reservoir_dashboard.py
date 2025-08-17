# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import datetime
import json
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GplReservoirDashboard(models.TransientModel):
    _name = 'gpl.reservoir.dashboard'
    _description = 'Dashboard Réservoirs GPL'

    # === FILTRES ===
    date_from = fields.Date(
        string="Date de début",
        default='2020-01-01'
    )

    date_to = fields.Date(
        string="Date de fin",
        default=fields.Date.today
    )

    fabricant_ids = fields.Many2many(
        'gpl.reservoir.fabricant',
        string="Fabricants",
        help="Filtrer par fabricants"
    )

    state_filter = fields.Selection([
        ('all', 'Tous'),
        ('stock', 'En stock'),
        ('installed', 'Installés'),
        ('expired', 'Expirés'),
        ('test_required', 'Test requis')
    ], string="Filtrer par état", default='all')

    # === STATISTIQUES CALCULÉES ===
    total_reservoirs = fields.Integer(
        string="Total réservoirs",
        compute='_compute_statistics'
    )

    reservoirs_stock = fields.Integer(
        string="En stock",
        compute='_compute_statistics'
    )

    reservoirs_installed = fields.Integer(
        string="Installés",
        compute='_compute_statistics'
    )

    reservoirs_expired = fields.Integer(
        string="Expirés",
        compute='_compute_statistics'
    )

    reservoirs_expiring_soon = fields.Integer(
        string="Expirent bientôt",
        compute='_compute_statistics'
    )

    reservoirs_test_required = fields.Integer(
        string="Test requis",
        compute='_compute_statistics'
    )

    average_age = fields.Float(
        string="Âge moyen (années)",
        compute='_compute_statistics'
    )

    # === DONNÉES POUR GRAPHIQUES ===
    chart_data_status = fields.Text(
        string="Données graphique statut",
        compute='_compute_chart_data'
    )

    chart_data_fabricant = fields.Text(
        string="Données graphique fabricant",
        compute='_compute_chart_data'
    )

    chart_data_age = fields.Text(
        string="Données graphique âge",
        compute='_compute_chart_data'
    )

    @api.depends('date_from', 'date_to', 'fabricant_ids', 'state_filter')
    def _compute_statistics(self):
        """Calcule les statistiques des réservoirs"""
        for record in self:
            try:
                # Utiliser la méthode centralisée pour le domaine
                domain = record._build_reservoir_domain()
                reservoirs = self.env['stock.lot'].search(domain)

                # Calculer les statistiques
                record.total_reservoirs = len(reservoirs)
                record.reservoirs_stock = len(reservoirs.filtered(lambda r: r.state == 'stock'))
                record.reservoirs_installed = len(reservoirs.filtered(lambda r: r.state == 'installed'))
                record.reservoirs_expired = len(reservoirs.filtered(lambda r: r.reservoir_status == 'expired'))
                record.reservoirs_expiring_soon = len(
                    reservoirs.filtered(lambda r: r.reservoir_status == 'expiring_soon'))
                record.reservoirs_test_required = len(
                    reservoirs.filtered(lambda r: r.reservoir_status in ['expired', 'test_required']))

                # Âge moyen avec protection contre la division par zéro
                ages = reservoirs.filtered('manufacturing_date').mapped('age_years')
                record.average_age = sum(ages) / len(ages) if ages else 0.0

            except Exception as e:
                _logger.error(f"Erreur lors du calcul des statistiques: {e}")
                # Valeurs par défaut en cas d'erreur
                record.total_reservoirs = 0
                record.reservoirs_stock = 0
                record.reservoirs_installed = 0
                record.reservoirs_expired = 0
                record.reservoirs_expiring_soon = 0
                record.reservoirs_test_required = 0
                record.average_age = 0.0

    @api.depends('date_from', 'date_to', 'fabricant_ids', 'state_filter')
    def _compute_chart_data(self):
        """Prépare les données pour les graphiques avec format JSON valide"""
        for record in self:
            try:
                # Utiliser la méthode centralisée pour le domaine
                domain = record._build_reservoir_domain()
                reservoirs = self.env['stock.lot'].search(domain)

                # Préparer les données des graphiques
                record.chart_data_status = record._prepare_status_chart_data(reservoirs)
                record.chart_data_fabricant = record._prepare_fabricant_chart_data(reservoirs)
                record.chart_data_age = record._prepare_age_chart_data(reservoirs)

                _logger.info(f"Données graphiques calculées pour {len(reservoirs)} réservoirs")

            except Exception as e:
                _logger.error(f"Erreur lors du calcul des données graphiques: {e}")
                # Données par défaut en cas d'erreur
                record.chart_data_status = json.dumps({})
                record.chart_data_fabricant = json.dumps({})
                record.chart_data_age = json.dumps({})

    def _prepare_status_chart_data(self, reservoirs):
        """Prépare les données pour le graphique de statut"""
        try:
            status_data = {}

            # Compter par statut avec protection contre les erreurs
            for status in ['valid', 'expiring_soon', 'expired', 'test_required', 'too_old']:
                try:
                    count = len(
                        reservoirs.filtered(lambda r: hasattr(r, 'reservoir_status') and r.reservoir_status == status))
                    status_data[status] = count
                except Exception as e:
                    _logger.warning(f"Erreur lors du comptage du statut {status}: {e}")
                    status_data[status] = 0

            return json.dumps(status_data)

        except Exception as e:
            _logger.error(f"Erreur lors de la préparation des données de statut: {e}")
            return json.dumps({})

    def _prepare_fabricant_chart_data(self, reservoirs):
        """Prépare les données pour le graphique par fabricant"""
        try:
            fabricant_data = {}

            # Compter par fabricant
            fabricants = reservoirs.mapped('fabricant_id').filtered(lambda f: f.exists())

            for fabricant in fabricants:
                try:
                    count = len(reservoirs.filtered(lambda r: r.fabricant_id == fabricant))
                    # Utiliser le code du fabricant si disponible, sinon le nom
                    key = fabricant.code if hasattr(fabricant, 'code') and fabricant.code else fabricant.name
                    if key:  # S'assurer que la clé n'est pas vide
                        fabricant_data[key] = count
                except Exception as e:
                    _logger.warning(f"Erreur lors du comptage du fabricant {fabricant.name}: {e}")

            # Ajouter les réservoirs sans fabricant
            no_fabricant_count = len(reservoirs.filtered(lambda r: not r.fabricant_id))
            if no_fabricant_count > 0:
                fabricant_data['Non défini'] = no_fabricant_count

            return json.dumps(fabricant_data)

        except Exception as e:
            _logger.error(f"Erreur lors de la préparation des données de fabricant: {e}")
            return json.dumps({})

    def _prepare_age_chart_data(self, reservoirs):
        """Prépare les données pour le graphique par âge"""
        try:
            age_ranges = {
                '0-2 ans': 0,
                '3-5 ans': 0,
                '6-10 ans': 0,
                '11-15 ans': 0,
                '15+ ans': 0
            }

            # Compter par tranche d'âge
            reservoirs_with_date = reservoirs.filtered('manufacturing_date')

            for reservoir in reservoirs_with_date:
                try:
                    age = getattr(reservoir, 'age_years', 0)
                    if age <= 2:
                        age_ranges['0-2 ans'] += 1
                    elif age <= 5:
                        age_ranges['3-5 ans'] += 1
                    elif age <= 10:
                        age_ranges['6-10 ans'] += 1
                    elif age <= 15:
                        age_ranges['11-15 ans'] += 1
                    else:
                        age_ranges['15+ ans'] += 1
                except Exception as e:
                    _logger.warning(f"Erreur lors du calcul de l'âge du réservoir {reservoir.name}: {e}")

            return json.dumps(age_ranges)

        except Exception as e:
            _logger.error(f"Erreur lors de la préparation des données d'âge: {e}")
            return json.dumps({})

    def _build_reservoir_domain(self):
        """Construit le domaine de recherche selon les filtres actifs"""
        domain = [('is_gpl_reservoir', '=', True)]

        # Filtre par fabricants
        if self.fabricant_ids:
            valid_fabricants = self.fabricant_ids.filtered(lambda f: f.exists())
            if valid_fabricants:
                domain.append(('fabricant_id', 'in', valid_fabricants.ids))

        # Filtre par état - CORRECTION : appliquer les filtres de manière cohérente
        if self.state_filter and self.state_filter != 'all':
            if self.state_filter == 'expired':
                domain.append(('reservoir_status', '=', 'expired'))
            elif self.state_filter == 'test_required':
                domain.append(('reservoir_status', 'in', ['expired', 'test_required']))
            else:
                domain.append(('state', '=', self.state_filter))

        # Filtres de dates
        if self.date_from:
            domain.append(('create_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('create_date', '<=', self.date_to))

        return domain

    def action_view_reservoirs(self):
        """Affiche la liste des réservoirs selon les filtres"""
        self.ensure_one()

        domain = self._build_reservoir_domain()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Réservoirs GPL'),
            'res_model': 'stock.lot',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'search_default_is_gpl_reservoir': 1,
                'create': False
            },
            'target': 'current'
        }

    def action_view_expired(self):
        """Affiche les réservoirs expirés"""
        self.ensure_one()

        domain = [
            ('is_gpl_reservoir', '=', True),
            ('reservoir_status', '=', 'expired')
        ]

        if self.fabricant_ids:
            valid_fabricants = self.fabricant_ids.filtered(lambda f: f.exists())
            if valid_fabricants:
                domain.append(('fabricant_id', 'in', valid_fabricants.ids))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Réservoirs Expirés'),
            'res_model': 'stock.lot',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'search_default_is_gpl_reservoir': 1,
                'create': False
            }
        }

    def action_view_expiring_soon(self):
        """Affiche les réservoirs expirant bientôt"""
        self.ensure_one()

        domain = [
            ('is_gpl_reservoir', '=', True),
            ('reservoir_status', '=', 'expiring_soon')
        ]

        if self.fabricant_ids:
            valid_fabricants = self.fabricant_ids.filtered(lambda f: f.exists())
            if valid_fabricants:
                domain.append(('fabricant_id', 'in', valid_fabricants.ids))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Réservoirs Expirant Bientôt'),
            'res_model': 'stock.lot',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'search_default_is_gpl_reservoir': 1,
                'create': False
            }
        }

    def action_refresh_dashboard(self):
        """Actualise le dashboard"""
        self.ensure_one()

        try:
            # Forcer le recalcul des statistiques
            self._compute_statistics()
            self._compute_chart_data()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Dashboard actualisé'),
                    'message': _('Les données ont été mises à jour avec succès.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Erreur lors de l'actualisation du dashboard: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erreur'),
                    'message': _('Erreur lors de l\'actualisation du dashboard.'),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_generate_report(self):
        """Génère le rapport en appliquant les filtres du dashboard - VERSION CORRIGÉE"""
        self.ensure_one()

        try:
            # Construire le domaine et récupérer les réservoirs AVEC filtres
            domain = self._build_reservoir_domain()
            reservoirs = self.env['stock.lot'].search(domain)

            # Préparer les informations de filtrage pour le rapport
            filter_info = self._prepare_filter_context()

            # Debug pour vérifier le filtrage
            _logger.info(f"DEBUG Dashboard: {len(reservoirs)} réservoirs trouvés avec les filtres:")
            _logger.info(f"  - Fabricants: {self.fabricant_ids.mapped('name') if self.fabricant_ids else 'Tous'}")
            _logger.info(f"  - État: {self.state_filter}")
            _logger.info(f"  - Date début: {self.date_from}")
            _logger.info(f"  - Date fin: {self.date_to}")

            if not reservoirs:
                raise UserError(_("Aucun réservoir ne correspond aux filtres sélectionnés."))

            # Préparer le contexte pour le rapport
            report_context = {
                'dashboard_filters': filter_info,
                'filter_count': len(reservoirs),
                'generation_date': fields.Datetime.now(),
                'generated_by': self.env.user.name
            }

            # Générer le rapport avec le contexte
            return self.env.ref('cpss_gpl_reservoir.report_reservoir_dashboard').with_context(
                report_context
            ).report_action(reservoirs)

        except UserError:
            raise
        except Exception as e:
            _logger.error(f"Erreur lors de la génération du rapport: {e}")
            raise UserError(_("Erreur lors de la génération du rapport."))

    def action_generate_report_filtered(self):
        """Version alternative - redirige vers la méthode principale"""
        return self.action_generate_report()

    def _prepare_filter_context(self):
        """Prépare les informations des filtres pour le rapport"""
        filter_info = {}

        # Fabricants
        if self.fabricant_ids:
            filter_info['fabricants'] = self.fabricant_ids.mapped('name')

        # État
        if self.state_filter and self.state_filter != 'all':
            state_labels = {
                'stock': 'En stock',
                'installed': 'Installés',
                'expired': 'Expirés',
                'test_required': 'Test requis'
            }
            filter_info['state'] = state_labels.get(self.state_filter, self.state_filter)

        # Dates
        if self.date_from:
            filter_info['date_from'] = self.date_from.strftime('%d/%m/%Y')
        if self.date_to:
            filter_info['date_to'] = self.date_to.strftime('%d/%m/%Y')

        return filter_info

    @api.model
    def get_dashboard_data(self):
        """Retourne les données du dashboard pour JavaScript"""
        try:
            reservoirs = self.env['stock.lot'].search([('is_gpl_reservoir', '=', True)])

            return {
                'total': len(reservoirs),
                'by_status': {
                    'valid': len(reservoirs.filtered(
                        lambda r: hasattr(r, 'reservoir_status') and r.reservoir_status == 'valid')),
                    'expiring_soon': len(reservoirs.filtered(
                        lambda r: hasattr(r, 'reservoir_status') and r.reservoir_status == 'expiring_soon')),
                    'expired': len(reservoirs.filtered(
                        lambda r: hasattr(r, 'reservoir_status') and r.reservoir_status == 'expired')),
                    'test_required': len(reservoirs.filtered(
                        lambda r: hasattr(r, 'reservoir_status') and r.reservoir_status == 'test_required')),
                    'too_old': len(reservoirs.filtered(
                        lambda r: hasattr(r, 'reservoir_status') and r.reservoir_status == 'too_old'))
                },
                'by_state': {
                    'stock': len(reservoirs.filtered(lambda r: r.state == 'stock')),
                    'installed': len(reservoirs.filtered(lambda r: r.state == 'installed')),
                    'expired': len(reservoirs.filtered(lambda r: r.state == 'expired')),
                    'scrapped': len(reservoirs.filtered(lambda r: r.state == 'scrapped'))
                },
                'alerts': self._get_alerts(reservoirs)
            }
        except Exception as e:
            _logger.error(f"Erreur lors de la récupération des données dashboard: {e}")
            return {
                'total': 0,
                'by_status': {},
                'by_state': {},
                'alerts': []
            }

    def _get_alerts(self, reservoirs):
        """Génère les alertes pour le dashboard"""
        alerts = []

        try:
            expired_count = len(
                reservoirs.filtered(lambda r: hasattr(r, 'reservoir_status') and r.reservoir_status == 'expired'))
            if expired_count > 0:
                alerts.append({
                    'type': 'danger',
                    'message': f'{expired_count} réservoir(s) expiré(s)',
                    'action': 'action_view_expired'
                })

            expiring_count = len(
                reservoirs.filtered(lambda r: hasattr(r, 'reservoir_status') and r.reservoir_status == 'expiring_soon'))
            if expiring_count > 0:
                alerts.append({
                    'type': 'warning',
                    'message': f'{expiring_count} réservoir(s) expirent bientôt',
                    'action': 'action_view_expiring_soon'
                })

            old_count = len(
                reservoirs.filtered(lambda r: hasattr(r, 'reservoir_status') and r.reservoir_status == 'too_old'))
            if old_count > 0:
                alerts.append({
                    'type': 'info',
                    'message': f'{old_count} réservoir(s) trop ancien(s)',
                    'action': 'action_view_too_old'
                })

        except Exception as e:
            _logger.warning(f"Erreur lors de la génération des alertes: {e}")

        return alerts

    def action_export_chart_data(self):
        """Exporte les données des graphiques vers Excel"""
        self.ensure_one()

        try:
            reservoirs = self.env['stock.lot'].search(self._build_reservoir_domain())

            if not reservoirs:
                raise UserError(_("Aucun réservoir à exporter."))

            # Utiliser le rapport Excel si disponible
            if self.env.ref('cpss_gpl_reports.action_report_gpl_reservoir_xlsx', False):
                return self.env.ref('cpss_gpl_reports.action_report_gpl_reservoir_xlsx').report_action(reservoirs)
            else:
                raise UserError(_("Le module de rapport Excel n'est pas installé."))

        except UserError:
            raise
        except Exception as e:
            _logger.error(f"Erreur lors de l'export: {e}")
            raise UserError(_("Erreur lors de l'export des données."))
