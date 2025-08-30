from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class GplServiceInstallation(models.Model):
    """
    Version simplifiée du modèle gpl.service.installation
    Gère uniquement les informations essentielles pour l'installation GPL
    """
    _name = 'gpl.service.installation'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'gpl.auto.document.mixin']
    _description = 'Installation GPL Simplifiée'
    _order = 'date_start desc'

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
    date_start = fields.Datetime(
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

    reservoir_lot_ids = fields.Many2many(
        'stock.lot',
        string='Réservoirs installés',
        compute='_compute_reservoir_lots',
        store=True,
        help="Réservoirs sélectionnés dans les lignes d'installation"
    )

    reservoir_lot_id = fields.Many2one(
        'stock.lot',
        string='Réservoir principal',
        compute='_compute_reservoir_lots',
        store=True,
        help="Premier réservoir trouvé dans les lignes (pour compatibilité)"
    )

    reservoir_count = fields.Integer(
        string='Nombre de réservoirs',
        compute='_compute_reservoir_lots',
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

    total_amount_ttc = fields.Float(
        string='Montant total TTC',
        compute='_compute_total_amount_ttc',
        store=True
    )

    # Notes
    notes = fields.Text(string='Notes')

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

    @api.depends('installation_line_ids.lot_id', 'installation_line_ids.product_id')
    def _compute_reservoir_lots(self):
        """Calcule les réservoirs depuis les lignes"""
        for installation in self:
            # Trouver tous les réservoirs dans les lignes
            reservoir_lines = installation.installation_line_ids.filtered(
                lambda l: l.product_id.is_gpl_reservoir and l.lot_id
            )

            reservoir_lots = reservoir_lines.mapped('lot_id')

            installation.reservoir_lot_ids = [(6, 0, reservoir_lots.ids)]
            installation.reservoir_lot_id = reservoir_lots[0] if reservoir_lots else False
            installation.reservoir_count = len(reservoir_lots)

    @api.depends('installation_line_ids.subtotal_ttc')
    def _compute_total_amount_ttc(self):
        for record in self:
            record.total_amount_ttc = sum(record.installation_line_ids.mapped('subtotal_ttc'))

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

    def _get_partner(self):
        """Retourne le client de l'installation"""
        return self.client_id

    def _get_order_lines(self):
        """Retourne les lignes d'installation avec quantité > 0"""
        return self.installation_line_ids.filtered(lambda l: l.quantity > 0)

    def action_start(self):
        """Démarre l'installation"""
        self.ensure_one()
        if self.state not in ['draft', 'planned']:
            raise UserError(_("L'installation doit être en brouillon ou planifiée pour être démarrée."))

        self.write({
            'state': 'in_progress',
            'date_start': fields.Datetime.now()
        })

        # Mettre à jour le statut du véhicule
        if self.vehicle_id:
            in_progress_status = self.env.ref('cpss_gpl_garage.vehicle_status_en_cours', raise_if_not_found=False)
            if in_progress_status:
                self.vehicle_id.status_id = in_progress_status
            self.vehicle_id.appointment_date = self.date_start
            self.vehicle_id.next_service_type = 'installation'

    def _ensure_sale_order_created(self):
        """S'assure qu'une commande de vente existe - MÉTHODE SÉCURISÉE"""
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

    def action_done(self):
        """Termine l'installation"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("L'installation doit être en cours pour être terminée."))

        if not self.reservoir_lot_id:
            raise UserError(_("Veuillez sélectionner le réservoir à installer avant de terminer."))

        self.write({
            'state': 'done',
            'date_end': fields.Datetime.now()
        })

        if self._is_simplified_mode():
            self._ensure_sale_order_created()

        if self.state == 'done':
            if self.sale_order_id:
                try:
                    self._finalize_automatic_workflow()
                except Exception as e:
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning(f"Erreur finalisation workflow {self.name}: {str(e)}")

            # Dans tous les cas, marquer le workflow comme terminé
            self.auto_workflow_state = 'done'

        # Mettre à jour le véhicule
        if self.vehicle_id:
            completed_status = self.env.ref('cpss_gpl_garage.vehicle_status_termine', raise_if_not_found=False)
            if completed_status:
                self.vehicle_id.write({
                    'status_id': completed_status.id,
                    'reservoir_lot_id': self.reservoir_lot_id.id
                })

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

    # Ajouter cette méthode dans le modèle gpl.service.installation

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
                ('in_progress', 'En cours'),
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
                            elif field in ['total_amount', 'estimated_cost']:
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
                    'in_progress': 3,
                    'done': 4,
                    'cancel': 5
                }
                return order_map.get(state, 999)

            result.sort(key=sort_key)

        return result


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

    product_type = fields.Selection([
        ('product', 'Produit'),
        ('service', 'Service'),
    ], string='Type', compute='_compute_product_type', store=True)

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

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            self.price_unit = self.product_id.list_price

            # FORCER quantité = 1 pour produits sériels
            if self.product_id.tracking == 'serial':
                self.quantity = 1.0

            # Réinitialiser le lot si le produit change
            self.lot_id = False

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        """Met à jour la description avec le numéro de lot"""
        if self.lot_id and self.product_id:
            self.name = f"{self.product_id.name} - {self.lot_id.name}"

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

    @api.depends('product_id')
    def _compute_product_type(self):
        for line in self:
            if line.product_id:
                line.product_type = 'service' if line.product_id.type == 'service' else 'product'
            else:
                line.product_type = 'product'

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
