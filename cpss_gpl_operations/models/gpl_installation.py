# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GplServiceInstallation(models.Model):
    """
    Version simplifiée du modèle gpl.service.installation
    Gère uniquement les informations essentielles pour l'installation GPL
    """
    _name = 'gpl.service.installation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Installation GPL Simplifiée'
    _order = 'date_service desc'

    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default='New',
        copy=False
    )

    vehicle_id = fields.Many2one(
        'gpl.vehicle',  # CORRIGÉ
        string='Véhicule',
        required=True,
        tracking=True,
        index=True
    )

    client_id = fields.Many2one(
        'res.partner',
        string='Client',
        related='vehicle_id.client_id',
        store=True,
        readonly=True
    )

    # Dates
    date_service = fields.Datetime(
        string='Date de début',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )
    date_planned = fields.Datetime(
        string='Date planifiée',
        tracking=True
    )
    date_end = fields.Datetime(
        string='Date de fin',
        tracking=True
    )

    # Techniciens
    technician_ids = fields.Many2many(
        'hr.employee',
        'gpl_installation_technician_rel',
        'installation_id',
        'employee_id',
        string='Techniciens'
    )

    vehicle_gpl_id = fields.Many2one(
        'gpl.vehicle',
        string='Véhicule GPL',
        related='vehicle_id',
        store=True
    )

    reservoir_lot_id = fields.Many2one(
        'stock.lot',
        string='Réservoir installé',
        domain=[('product_id.is_gpl_reservoir', '=', True)]
    )

    # Lien vers le réservoir via stock.lot
    reservoir_id = fields.Many2one(
        'stock.lot',
        string='Réservoir',
        related='reservoir_lot_id',
        store=True
    )

    # Produits utilisés (simplifié)
    installation_line_ids = fields.One2many(
        'gpl.installation.line',
        'installation_id',
        string='Produits utilisés'
    )

    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('planned', 'Planifié'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', tracking=True)

    # Montants
    total_amount = fields.Float(
        string='Montant total',
        compute='_compute_total_amount',
        store=True
    )

    # Notes
    notes = fields.Text(string='Notes internes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gpl.service.installation') or 'New'
        return super().create(vals_list)

    @api.depends('installation_line_ids.subtotal')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.installation_line_ids.mapped('subtotal'))

    def action_start(self):
        """Démarre l'installation"""
        self.ensure_one()
        if self.state not in ['draft', 'planned']:
            raise UserError(_("L'installation doit être en brouillon ou planifiée pour être démarrée."))

        self.write({
            'state': 'in_progress',
            'date_service': fields.Datetime.now()
        })

        # Mettre à jour le statut du véhicule
        if self.vehicle_id:
            in_progress_status = self.env.ref('cpss_gpl_garage.vehicle_status_en_cours', raise_if_not_found=False)
            if in_progress_status:
                self.vehicle_id.status_id = in_progress_status

    def action_done(self):
        """Termine l'installation"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("L'installation doit être en cours pour être terminée."))

        if not self.reservoir_lot_id:
            raise UserError(_("Veuillez sélectionner le réservoir installé avant de terminer."))

        self.write({
            'state': 'done',
            'date_end': fields.Datetime.now()
        })

        # Mettre à jour le véhicule
        if self.vehicle_id:
            completed_status = self.env.ref('cpss_gpl_garage.vehicle_status_termine', raise_if_not_found=False)
            if completed_status:
                self.vehicle_id.write({
                    'status_id': completed_status.id,
                    'reservoir_lot_id': self.reservoir_lot_id.id
                })

    def action_cancel(self):
        """Annule l'installation"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Une installation terminée ne peut pas être annulée."))

        self.state = 'cancel'

    def action_set_to_draft(self):
        """Remet l'installation en brouillon"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Une installation terminée ne peut pas être remise en brouillon."))
        self.state = 'draft'


class GplInstallationLine(models.Model):
    """Lignes de produits pour l'installation"""
    _name = 'gpl.installation.line'
    _description = 'Ligne de produits installation GPL'

    installation_id = fields.Many2one(
        'gpl.service.installation',
        string='Installation',
        required=True,
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        required=True
    )

    name = fields.Char(
        string='Description',
        related='product_id.name'
    )

    quantity = fields.Float(
        string='Quantité',
        default=1.0,
        required=True
    )

    price_unit = fields.Float(
        string='Prix unitaire',
        related='product_id.list_price'
    )

    subtotal = fields.Float(
        string='Sous-total',
        compute='_compute_subtotal',
        store=True
    )

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit
