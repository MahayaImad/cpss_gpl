# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GplRepairOrder(models.Model):
    """
    Gestion simplifiée des réparations GPL
    """
    _name = 'gpl.repair.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Ordre de Réparation GPL'
    _order = 'priority desc, date_order desc'

    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default='New',
        copy=False
    )

    # Client et véhicule
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
    date_order = fields.Datetime(
        string='Date de création',
        default=fields.Datetime.now,
        required=True,
        readonly=True
    )

    date_scheduled = fields.Datetime(
        string='Date planifiée',
        tracking=True
    )

    date_start = fields.Datetime(
        string='Date de début',
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

    # Informations de réparation
    repair_type = fields.Selection([
        ('maintenance', 'Maintenance préventive'),
        ('repair', 'Réparation'),
        ('inspection', 'Inspection'),
        ('modification', 'Modification'),
        ('urgent', 'Intervention urgente'),
    ], string='Type de réparation', default='repair', required=True)

    priority = fields.Selection([
        ('0', 'Normale'),
        ('1', 'Urgente'),
        ('2', 'Très urgente'),
    ], string='Priorité', default='0')

    # Diagnostic
    symptoms = fields.Text(
        string='Symptômes décrits',
        help="Description des problèmes rapportés par le client"
    )

    diagnosis = fields.Text(
        string='Diagnostic technique',
        help="Diagnostic établi par le technicien"
    )

    solution = fields.Text(
        string='Solution appliquée',
        help="Description de la réparation effectuée"
    )

    # Techniciens
    technician_ids = fields.Many2many(
        'hr.employee',
        'gpl_repair_technician_rel',
        'repair_id',
        'employee_id',
        string='Techniciens'
    )

    # Lignes de réparation
    repair_line_ids = fields.One2many(
        'gpl.repair.line',
        'repair_id',
        string='Produits et services'
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
    amount_total = fields.Float(
        string='Montant total',
        compute='_compute_amount_total',
        store=True
    )

    # Réservoir si concerné
    reservoir_lot_id = fields.Many2one(
        'stock.lot',
        string='Réservoir concerné',
        domain=[('product_id.is_gpl_reservoir', '=', True)]
    )

    # Notes
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gpl.repair.order') or 'New'
        return super().create(vals_list)

    @api.depends('repair_line_ids.subtotal')
    def _compute_amount_total(self):
        for repair in self:
            repair.amount_total = sum(repair.repair_line_ids.mapped('subtotal'))

    def action_confirm(self):
        """Confirme l'ordre de réparation"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Seul un ordre en brouillon peut être confirmé."))
        self.state = 'planned'

    def action_start_repair(self):
        """Démarre la réparation"""
        self.ensure_one()
        if self.state not in ['draft', 'planned']:
            raise UserError(_("L'ordre doit être plannifié ou en brouillon pour démarrer la réparation."))

        self.write({
            'state': 'in_progress',
            'date_start': fields.Datetime.now()
        })

        # Mettre à jour le statut du véhicule
        if self.vehicle_id:
            repair_status = self.env.ref('cpss_gpl_garage.vehicle_status_en_cours', raise_if_not_found=False)
            if repair_status:
                self.vehicle_id.status_id = repair_status

    def action_done(self):
        """Termine la réparation"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("La réparation doit être en cours pour être terminée."))

        self.write({
            'state': 'done',
            'date_end': fields.Datetime.now()
        })

        # Mettre à jour le statut du véhicule
        if self.vehicle_id:
            ready_status = self.env.ref('cpss_gpl_garage.vehicle_status_termine', raise_if_not_found=False)
            if ready_status:
                self.vehicle_id.status_id = ready_status

    def action_cancel(self):
        """Annule l'ordre de réparation"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Un ordre terminé ne peut pas être annulé."))
        self.state = 'cancel'


class GplRepairLine(models.Model):
    """Lignes de produits/services pour la réparation"""
    _name = 'gpl.repair.line'
    _description = 'Ligne de réparation GPL'

    repair_id = fields.Many2one(
        'gpl.repair.order',
        string='Ordre de réparation',
        required=True,
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Produit/Service',
        required=True
    )

    name = fields.Text(
        string='Description',
        required=True
    )

    product_type = fields.Selection([
        ('product', 'Produit'),
        ('service', 'Service'),
    ], string='Type', compute='_compute_product_type', store=True)

    quantity = fields.Float(
        string='Quantité',
        default=1.0,
        required=True
    )

    price_unit = fields.Float(
        string='Prix unitaire',
        required=True
    )

    subtotal = fields.Float(
        string='Sous-total',
        compute='_compute_subtotal',
        store=True
    )

    @api.depends('product_id')
    def _compute_product_type(self):
        for line in self:
            if line.product_id:
                line.product_type = 'service' if line.product_id.type == 'service' else 'product'
            else:
                line.product_type = 'product'

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            self.price_unit = self.product_id.list_price


class GplRepairOrderMixin(models.Model):
    _name = 'gpl.repair.order'
    _inherit = ['gpl.repair.order', 'gpl.auto.document.mixin']

    def action_start_repair(self):
        """Démarrage réparation avec automatisation"""
        result = super().action_start_repair()

        if self._is_simplified_mode():
            self._create_automatic_sale_order()

        return result

    def _get_partner(self):
        """Retourne le client de la réparation"""
        return self.client_id

    def _get_order_lines(self):
        """Retourne les lignes de réparation"""
        return self.repair_line_ids.filtered(lambda l: l.quantity > 0)

    def action_done(self):
        """Finalisation avec mise à jour du workflow"""
        result = super().action_done()

        if self.auto_workflow_state == 'invoiced':
            self.auto_workflow_state = 'done'

        return result
