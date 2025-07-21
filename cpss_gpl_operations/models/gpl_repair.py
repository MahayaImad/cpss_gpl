# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GplRepairOrder(models.Model):
    """
    Modèle simplifié pour les réparations GPL
    """
    _name = 'gpl.repair.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Ordre de Réparation GPL'
    _order = 'date_repair desc'

    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default='New',
        copy=False
    )

    # Client et véhicule
    vehicle_id = fields.Many2one(
        'gpl.vehicle',
        string='Véhicule',
        required=True,
        tracking=True
    )
    client_id = fields.Many2one(
        'res.partner',
        string='Client',
        related='vehicle_id.client_id',
        store=True,
        readonly=True
    )

    # Type de réparation
    repair_type = fields.Selection([
        ('reservoir', 'Réservoir'),
        ('injector', 'Injecteurs'),
        ('tube', 'Tuyauterie'),
        ('pressure', 'Système de pression'),
        ('electronic', 'Électronique'),
        ('control', 'Contrôle périodique'),
        ('other', 'Autre'),
    ], string='Type de réparation', required=True, default='other')

    # Dates
    date_repair = fields.Datetime(
        string='Date de réparation',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )
    date_end = fields.Datetime(
        string='Date de fin',
        tracking=True
    )

    # Technicien principal
    technician_id = fields.Many2one(
        'hr.employee',
        string='Technicien principal',
        domain=[('department_id.name', 'ilike', 'technique')]
    )

    # Diagnostic et solution
    diagnostic = fields.Text(
        string='Diagnostic',
        help="Description du problème identifié"
    )
    solution = fields.Text(
        string='Solution appliquée',
        help="Description de la réparation effectuée"
    )

    # Produits utilisés
    repair_line_ids = fields.One2many(
        'gpl.repair.line',
        'repair_id',
        string='Pièces utilisées'
    )

    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('scheduled', 'Planifié'),
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

    # Urgence
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Très urgent'),
    ], string='Priorité', default='0')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gpl.repair.order') or 'New'
        return super().create(vals_list)

    @api.depends('repair_line_ids.subtotal')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.repair_line_ids.mapped('subtotal'))

    @api.onchange('repair_type')
    def _onchange_repair_type(self):
        """Suggère un diagnostic selon le type"""
        if self.repair_type and not self.diagnostic:
            diagnostics = {
                'reservoir': "Inspection du réservoir GPL et accessoires",
                'injector': "Vérification des injecteurs et système d'alimentation",
                'tube': "Contrôle de l'état des tuyaux et raccords",
                'pressure': "Test d'étanchéité et contrôle de pression",
                'electronic': "Diagnostic du système électronique GPL",
                'control': "Contrôle périodique du système GPL",
                'other': "Diagnostic du système GPL"
            }
            self.diagnostic = diagnostics.get(self.repair_type, "")

    def action_schedule(self):
        """Planifie la réparation"""
        self.ensure_one()
        if not self.technician_id:
            raise UserError(_("Veuillez assigner un technicien."))

        self.state = 'scheduled'

    def action_start(self):
        """Démarre la réparation"""
        self.ensure_one()
        if self.state not in ['draft', 'scheduled']:
            raise UserError(_("La réparation doit être planifiée pour être démarrée."))

        self.write({
            'state': 'in_progress',
            'date_repair': fields.Datetime.now()
        })

        # Mettre à jour le statut du véhicule
        if self.vehicle_id:
            in_progress_status = self.env.ref('cpss_gpl_garage.vehicle_status_en_cours', raise_if_not_found=False)
            if in_progress_status:
                self.vehicle_id.status_id = in_progress_status

    def action_done(self):
        """Termine la réparation"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("La réparation doit être en cours pour être terminée."))

        if not self.solution:
            raise UserError(_("Veuillez décrire la solution appliquée."))

        self.write({
            'state': 'done',
            'date_end': fields.Datetime.now()
        })

        # Mettre à jour le véhicule
        if self.vehicle_id:
            completed_status = self.env.ref('cpss_gpl_garage.vehicle_status_termine', raise_if_not_found=False)
            if completed_status:
                self.vehicle_id.status_id = completed_status

    def action_cancel(self):
        """Annule la réparation"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Une réparation terminée ne peut pas être annulée."))

        self.state = 'cancel'


class GplRepairLine(models.Model):
    """Ligne de produits pour la réparation"""
    _name = 'gpl.repair.line'
    _description = 'Ligne de réparation GPL'

    repair_id = fields.Many2one(
        'gpl.repair.order',
        string='Réparation',
        required=True,
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Pièce',
        required=True,
        domain=[('gpl_category', 'in', ['piece', 'consommable'])]
    )

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

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.list_price
