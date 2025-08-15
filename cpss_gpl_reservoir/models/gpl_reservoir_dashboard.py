# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import datetime
from odoo.exceptions import UserError


class GplReservoirDashboard(models.TransientModel):
    _name = 'gpl.reservoir.dashboard'
    _description = 'Dashboard Réservoirs GPL'

    # === FILTRES ===
    date_from = fields.Date(
        string="Date de début",
        default=fields.Date.today
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
            domain = [('is_gpl_reservoir', '=', True)]

            # Appliquer les filtres
            if record.fabricant_ids:
                domain.append(('fabricant_id', 'in', record.fabricant_ids.ids))

            if record.state_filter != 'all':
                if record.state_filter == 'expired':
                    domain.append(('reservoir_status', '=', 'expired'))
                elif record.state_filter == 'test_required':
                    domain.append(('reservoir_status', 'in', ['expired', 'test_required']))
                else:
                    domain.append(('state', '=', record.state_filter))

            reservoirs = self.env['stock.lot'].search(domain)

            # Calculer les statistiques
            record.total_reservoirs = len(reservoirs)
            record.reservoirs_stock = len(reservoirs.filtered(lambda r: r.state == 'stock'))
            record.reservoirs_installed = len(reservoirs.filtered(lambda r: r.state == 'installed'))
            record.reservoirs_expired = len(reservoirs.filtered(lambda r: r.reservoir_status == 'expired'))
            record.reservoirs_expiring_soon = len(reservoirs.filtered(lambda r: r.reservoir_status == 'expiring_soon'))
            record.reservoirs_test_required = len(
                reservoirs.filtered(lambda r: r.reservoir_status in ['expired', 'test_required']))

            # Âge moyen
            ages = reservoirs.filtered('manufacturing_date').mapped('age_years')
            record.average_age = sum(ages) / len(ages) if ages else 0.0

    @api.depends('date_from', 'date_to', 'fabricant_ids', 'state_filter')
    def _compute_chart_data(self):
        """Prépare les données pour les graphiques"""
        for record in self:
            domain = [('is_gpl_reservoir', '=', True)]

            # Appliquer les filtres
            if record.fabricant_ids:
                domain.append(('fabricant_id', 'in', record.fabricant_ids.ids))

            reservoirs = self.env['stock.lot'].search(domain)

            # Données par statut
            status_data = {}
            for status in ['valid', 'expiring_soon', 'expired', 'test_required', 'too_old']:
                count = len(reservoirs.filtered(lambda r: r.reservoir_status == status))
                status_data[status] = count

            record.chart_data_status = str(status_data)

            # Données par fabricant
            fabricant_data = {}
            for fabricant in reservoirs.mapped('fabricant_id'):
                count = len(reservoirs.filtered(lambda r: r.fabricant_id == fabricant))
                fabricant_data[fabricant.code] = count

            record.chart_data_fabricant = str(fabricant_data)

            # Données par âge
            age_ranges = {
                '0-2 ans': 0,
                '3-5 ans': 0,
                '6-10 ans': 0,
                '11-15 ans': 0,
                '15+ ans': 0
            }

            for reservoir in reservoirs.filtered('manufacturing_date'):
                age = reservoir.age_years
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

            record.chart_data_age = str(age_ranges)

    def action_view_reservoirs(self):
        """Affiche la liste des réservoirs selon les filtres"""
        self.ensure_one()

        domain = [('is_gpl_reservoir', '=', True)]

        # Appliquer les filtres avec protection contre les données corrompues
        if self.fabricant_ids:
            # Vérifier que les fabricants existent encore
            valid_fabricants = self.fabricant_ids.filtered(lambda f: f.exists())
            if valid_fabricants:
                domain.append(('fabricant_id', 'in', valid_fabricants.ids))

        if self.state_filter != 'all':
            if self.state_filter == 'expired':
                domain.append(('reservoir_status', '=', 'expired'))
            elif self.state_filter == 'test_required':
                domain.append(('reservoir_status', 'in', ['expired', 'test_required']))
            else:
                domain.append(('state', '=', self.state_filter))

        # Ajouter un filtre de date si spécifié
        if self.date_from:
            domain.append(('create_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('create_date', '<=', self.date_to))

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
            domain.append(('fabricant_id', 'in', self.fabricant_ids.ids))

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
            domain.append(('fabricant_id', 'in', self.fabricant_ids.ids))

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

        # Forcer le recalcul des statistiques
        self._compute_statistics()
        self._compute_chart_data()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    @api.model
    def get_dashboard_data(self):
        """Retourne les données du dashboard pour JavaScript"""
        reservoirs = self.env['stock.lot'].search([('is_gpl_reservoir', '=', True)])

        return {
            'total': len(reservoirs),
            'by_status': {
                'valid': len(reservoirs.filtered(lambda r: r.reservoir_status == 'valid')),
                'expiring_soon': len(reservoirs.filtered(lambda r: r.reservoir_status == 'expiring_soon')),
                'expired': len(reservoirs.filtered(lambda r: r.reservoir_status == 'expired')),
                'test_required': len(reservoirs.filtered(lambda r: r.reservoir_status == 'test_required')),
                'too_old': len(reservoirs.filtered(lambda r: r.reservoir_status == 'too_old'))
            },
            'by_state': {
                'stock': len(reservoirs.filtered(lambda r: r.state == 'stock')),
                'installed': len(reservoirs.filtered(lambda r: r.state == 'installed')),
                'expired': len(reservoirs.filtered(lambda r: r.state == 'expired')),
                'scrapped': len(reservoirs.filtered(lambda r: r.state == 'scrapped'))
            },
            'alerts': self._get_alerts(reservoirs)
        }

    def _get_alerts(self, reservoirs):
        """Génère les alertes pour le dashboard"""
        alerts = []

        expired_count = len(reservoirs.filtered(lambda r: r.reservoir_status == 'expired'))
        if expired_count > 0:
            alerts.append({
                'type': 'danger',
                'message': f'{expired_count} réservoir(s) expiré(s)',
                'action': 'action_view_expired'
            })

        expiring_count = len(reservoirs.filtered(lambda r: r.reservoir_status == 'expiring_soon'))
        if expiring_count > 0:
            alerts.append({
                'type': 'warning',
                'message': f'{expiring_count} réservoir(s) expirent bientôt',
                'action': 'action_view_expiring_soon'
            })

        old_count = len(reservoirs.filtered(lambda r: r.reservoir_status == 'too_old'))
        if old_count > 0:
            alerts.append({
                'type': 'info',
                'message': f'{old_count} réservoir(s) trop ancien(s)',
                'action': 'action_view_too_old'
            })

        return alerts

    def action_generate_report(self):

        self.ensure_one()

        # Récupérer tous les réservoirs GPL
        reservoirs = self.env['stock.lot'].search([('is_gpl_reservoir', '=', True)])

        print(f"DEBUG Dashboard: {len(reservoirs)} réservoirs trouvés")

        # Appeler le rapport directement sur les réservoirs
        # Plus de passage de data complexe !
        return self.env.ref('cpss_gpl_reservoir.report_reservoir_dashboard').report_action(reservoirs)

    def action_generate_report_filtered(self):
        """Version avec filtres du dashboard si nécessaire"""
        self.ensure_one()

        # Construire le domaine selon les filtres du dashboard
        domain = [('is_gpl_reservoir', '=', True)]

        # Ajouter les filtres si ils existent
        if hasattr(self, 'state_filter') and self.state_filter and self.state_filter != 'all':
            domain.append(('state', '=', self.state_filter))

        if hasattr(self, 'fabricant_filter') and self.fabricant_filter:
            domain.append(('fabricant_id', '=', self.fabricant_filter.id))

        # Récupérer les réservoirs filtrés
        reservoirs = self.env['stock.lot'].search(domain)

        print(f"DEBUG Dashboard (filtré): {len(reservoirs)} réservoirs trouvés")

        # Appeler le rapport sur les réservoirs filtrés
        return self.env.ref('cpss_gpl_reservoir.report_reservoir_dashboard').report_action(reservoirs)


