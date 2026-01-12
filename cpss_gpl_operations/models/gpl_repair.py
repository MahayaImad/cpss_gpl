from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class GplRepairOrder(models.Model):
    """
    Gestion simplifiée des réparations GPL
    """
    _name = 'gpl.repair.order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'gpl.auto.document.mixin']
    _description = 'Ordre de Réparation GPL'
    _order = 'priority desc, date_start desc'

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

    total_cost_ttc = fields.Float(
        string='Coût total TTC',
        compute='_compute_total_cost_ttc',
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

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Commande de vente',
        readonly=True,
        help="Commande générée automatiquement"
    )

    auto_workflow_state = fields.Selection([
        ('draft', 'Brouillon'),
        ('sale_created', 'Commande créée'),
        ('sale_confirmed', 'Commande confirmée'),
        ('delivered', 'Livré'),
        ('invoiced', 'Facturé'),
        ('done', 'Terminé'),
    ], string='État Workflow', default='draft', readonly=True)

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

    @api.depends('repair_line_ids.subtotal_ttc')
    def _compute_total_cost_ttc(self):
        for record in self:
            record.total_cost_ttc = sum(record.repair_line_ids.mapped('subtotal_ttc'))

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
            # Note: appointment_date and next_service_type are now computed from gpl.appointment

    def _ensure_sale_order_created(self):
        """S'assure qu'une commande de vente existe"""
        if self.sale_order_id:
            return

        if not self._get_order_lines():
            return

        try:
            self._create_automatic_sale_order()
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Erreur création commande pour {self.name}: {str(e)}")

    def _get_partner(self):
        """Retourne le client de la réparation"""
        return self.client_id

    def _get_order_lines(self):
        """Retourne les lignes de réparation avec quantité > 0"""
        return self.repair_line_ids.filtered(lambda l: l.quantity > 0)

    def action_done(self):
        """Termine la réparation"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("La réparation doit être en cours pour être terminée."))

        self.write({
            'state': 'done',
            'date_end': fields.Datetime.now()
        })

        if self._is_simplified_mode():
            self._ensure_sale_order_created()

        # Finaliser l'automatisation
        if self.state == 'done':
            if self.sale_order_id:
                try:
                    self._finalize_automatic_workflow()
                except Exception as e:
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning(f"Erreur finalisation workflow {self.name}: {str(e)}")

            self.auto_workflow_state = 'done'

        # Mettre à jour le statut du véhicule
        if self.vehicle_id:
            ready_status = self.env.ref('cpss_gpl_garage.vehicle_status_termine', raise_if_not_found=False)
            if ready_status:
                self.vehicle_id.status_id = ready_status

        self._update_vehicle_reservoir_links()

    def _finalize_automatic_workflow(self):
        """Finalise le workflow si possible"""
        if not self.sale_order_id:
            return

        so = self.sale_order_id

        # Vérifier si livré
        outgoing_pickings = so.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        if outgoing_pickings and all(p.state == 'done' for p in outgoing_pickings):
            if self.auto_workflow_state not in ['delivered', 'invoiced', 'done']:
                self.auto_workflow_state = 'delivered'

        # Vérifier si facturé
        posted_invoices = so.invoice_ids.filtered(lambda i: i.state == 'posted')
        if posted_invoices:
            if self.auto_workflow_state != 'done':
                self.auto_workflow_state = 'invoiced'

    def _update_vehicle_reservoir_links(self):
        """Met à jour les liens entre véhicule et réservoirs"""
        if not self.vehicle_id:
            return

        # Chercher les réservoirs dans les lignes
        reservoir_lines = self._get_order_lines().filtered(
            lambda l: hasattr(l, 'lot_id') and l.lot_id
                      and l.product_id.is_gpl_reservoir  # Assuming this field exists
                      and l.lot_id
        )

        for line in reservoir_lines:
            # Mettre à jour le réservoir : quel véhicule il équipe
            line.lot_id.write({
                'vehicle_id': self.vehicle_id.id,
                'state': 'installed',  # ← CHANGEMENT D'ÉTAT
                'installation_date': fields.Date.today()
            })

            # Mettre à jour le véhicule : quel réservoir il a
            if not self.vehicle_id.reservoir_lot_id:
                self.vehicle_id.reservoir_lot_id = line.lot_id.id

    def action_cancel(self):
        """Annule l'ordre de réparation"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Un ordre terminé ne peut pas être annulé."))
        self.state = 'cancel'

    # Ajouter cette méthode dans le modèle gpl.repair.order

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override pour forcer l'affichage de toutes les colonnes d'états dans kanban"""
        result = super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

        # Si groupé par state
        if groupby and len(groupby) > 0 and 'state' in groupby[0]:
            # Définir tous les états possibles dans l'ordre souhaité
            all_states = [
                ('draft', 'Brouillon'),
                ('planned', 'Planifié'),
                ('in_progress', 'En réparation'),
                ('done', 'Terminé'),
                ('cancel', 'Annulé'),
            ]

            # Extraire les états déjà présents dans les résultats
            existing_states = []
            for group in result:
                if group.get('state'):
                    existing_states.append(group['state'])

            # Ajouter les états manquants avec un count de 0
            for state_key, state_name in all_states:
                if state_key not in existing_states:
                    # Créer un groupe vide pour cet état
                    empty_group = {
                        'state': state_key,
                        'state_count': 0,
                        '__count': 0,  # AJOUT DU CHAMP __count REQUIS
                        '__domain': [('state', '=', state_key)] + domain,
                    }

                    # Ajouter les autres champs nécessaires selon le groupby
                    for field in fields:
                        if field not in empty_group and field != 'state':
                            if 'count' in field:
                                empty_group[field] = 0
                            elif field in ['estimated_cost', 'total_cost', 'amount_total']:
                                empty_group[field] = 0.0
                            else:
                                empty_group[field] = False

                    result.append(empty_group)

            # Trier les résultats dans l'ordre souhaité: draft > planned > in_progress > done > cancel
            def sort_key(group):
                state = group.get('state', '')
                order_map = {
                    'draft': 1,
                    'planned': 2,
                    'in_progress': 3,  # ou 'in_progress' selon votre modèle
                    'done': 4,
                    'cancel': 5
                }
                return order_map.get(state, 999)

            result.sort(key=sort_key)

        return result


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

    tax_rate = fields.Float(
        string='TVA (%)',
        compute='_compute_tax_rate',
        store=True,
        help="Taux de TVA pour cette ligne"
    )

    # Prix unitaire TTC
    price_unit_ttc = fields.Float(
        string='Prix unitaire TTC',
        compute='_compute_price_ttc',
        store=True
    )

    # Sous-total TTC
    subtotal_ttc = fields.Float(
        string='Sous-total TTC',
        compute='_compute_subtotal_ttc',
        store=True
    )

    @api.depends('price_unit', 'tax_rate')
    def _compute_price_ttc(self):
        for line in self:
            line.price_unit_ttc = line.price_unit * (1 + line.tax_rate / 100)

    @api.depends('subtotal', 'tax_rate')
    def _compute_subtotal_ttc(self):
        for line in self:
            line.subtotal_ttc = line.subtotal * (1 + line.tax_rate / 100)

    @api.depends('product_id', 'product_id.taxes_id')
    def _compute_tax_rate(self):
        for line in self:
            if line.product_id and line.product_id.taxes_id:
                # Prendre le premier taux de taxe du produit
                tax = line.product_id.taxes_id[0]
                line.tax_rate = tax.amount
            else:
                line.tax_rate = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Met à jour le tax_rate quand le produit change"""
        if self.product_id and self.product_id.taxes_id:
            self.tax_rate = self.product_id.taxes_id[0].amount
        else:
            self.tax_rate = 0.0

    # === NOUVEAU CHAMP LOT ===
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Série',
        domain="[('product_id', '=', product_id), ('product_qty', '>', 0)]",
        help="Lot spécifique pour les produits gérés par lot"
    )

    # Champ pour savoir si le produit est géré par lot
    product_tracking = fields.Selection(
        related='product_id.tracking',
        string='Suivi',
        readonly=True
    )

    name = fields.Text(
        string='Description',
        required=True
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
            self.price_unit = self.product_id.list_price
            self.name = self.product_id.name

            # FORCER quantité = 1 pour produits sériels
            if self.product_id.tracking == 'serial':
                self.quantity = 1.0

            self.lot_id = False

    @api.constrains('quantity', 'product_id', 'lot_id')
    def _check_serial_quantity(self):
        """Empêche quantité > 1 pour produits sériels"""
        for line in self:
            if (line.product_id.tracking == 'serial'
                and line.lot_id
                and line.quantity != 1):
                raise ValidationError(_(
                    "Les réservoirs sont gérés par numéro de série unique. "
                    "La quantité doit être 1. "
                    "Pour plusieurs réservoirs, créez une ligne par réservoir."
                ))

