from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class GplAutoDocumentMixin(models.AbstractModel):
    """Mixin pour l'automatisation des documents en mode simplifié"""
    _name = 'gpl.auto.document.mixin'
    _description = 'Automatisation documents GPL'

    # === DOCUMENTS LIÉS ===
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Commande de vente',
        readonly=True,
        help="Commande générée automatiquement"
    )

    # === ÉTAT GLOBAL ===
    auto_workflow_state = fields.Selection([
        ('draft', 'Brouillon'),
        ('sale_created', 'Commande créée'),
        ('sale_confirmed', 'Commande confirmée'),
        ('delivered', 'Livré'),
        ('invoiced', 'Facturé'),
        ('done', 'Terminé'),
    ], string='État Workflow', default='draft', readonly=True)

    def _is_simplified_mode(self):
        """Vérifie si le mode simplifié est activé"""
        return self.env['ir.config_parameter'].sudo().get_param('cpss_gpl.simplified_mode', True)

    def _create_automatic_sale_order(self):
        """Crée automatiquement la commande de vente"""
        if self.sale_order_id or not self._get_order_lines():
            return

        # Préparation des données
        partner = self._get_partner()
        warehouse = self._get_warehouse()
        pricelist = self._get_pricelist()

        # Création de la commande
        sale_vals = {
            'partner_id': partner.id,
            'warehouse_id': warehouse.id,
            'pricelist_id': pricelist.id,
            'origin': self.name,
            'state': 'draft',
            'order_line': self._prepare_sale_order_lines(),
        }

        sale_order = self.env['sale.order'].create(sale_vals)
        self.sale_order_id = sale_order.id
        self.auto_workflow_state = 'sale_created'

        # Confirmation automatique
        sale_order.action_confirm()
        self.auto_workflow_state = 'sale_confirmed'

        # Traitement des livraisons en arrière-plan (ne pas attendre)
        self.env.cr.commit()  # Commit pour sauvegarder l'état

        # Programmer les traitements automatiques
        self._schedule_automatic_processing()

    def _schedule_automatic_processing(self):
        """Programme les traitements automatiques"""
        # Traiter immédiatement les livraisons
        self._process_automatic_delivery()

        # Créer la facture (basée sur la commande de vente, pas sur les livraisons)
        self._process_automatic_invoice()

    def _prepare_sale_order_lines(self):
        """Prépare les lignes de la commande de vente"""
        lines = []
        for line in self._get_order_lines():
            line_vals = {
                'product_id': line.product_id.id,
                'name': line.name or line.product_id.name,
                'product_uom_qty': line.quantity,
                'price_unit': line.price_unit,
                'product_uom': line.product_id.uom_id.id,
            }
            lines.append((0, 0, line_vals))
        return lines

    def _process_automatic_delivery(self):
        """Traite automatiquement la livraison - Version Odoo 17"""
        if not self.sale_order_id:
            return

        import logging
        _logger = logging.getLogger(__name__)

        # Rechercher les pickings de livraison
        pickings = self.sale_order_id.picking_ids.filtered(
            lambda p: p.state not in ['done', 'cancel'] and p.picking_type_code == 'outgoing'
        )

        for picking in pickings:
            try:
                # Confirmer le picking
                if picking.state == 'draft':
                    picking.action_confirm()

                # Vérifier la disponibilité
                if picking.state == 'confirmed':
                    picking.action_assign()

                # Validation automatique
                if picking.state == 'assigned':
                    # Méthode 1 : Si les move_lines existent déjà
                    self._validate_picking_with_move_lines(picking)

                elif picking.state in ['confirmed', 'waiting']:
                    # Méthode 2 : Pour produits non stockés ou services
                    self._force_picking_validation(picking)

                # Vérifier si la validation a réussi
                if picking.state != 'done':
                    _logger.warning(f"Picking {picking.name} n'a pas pu être validé automatiquement")

            except Exception as e:
                _logger.warning(f"Erreur lors de la validation du picking {picking.name}: {str(e)}")
                continue

        # Vérifier si tout est livré
        delivered_pickings = self.sale_order_id.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
        )
        if delivered_pickings and all(p.state == 'done' for p in delivered_pickings):
            self.auto_workflow_state = 'delivered'

    def _validate_picking_with_move_lines(self, picking):
        """Valide un picking via les move_lines existants"""
        for move_line in picking.move_line_ids:
            # Forcer la quantité fait égale à la quantité prévue
            if move_line.qty_done == 0:
                move_line.qty_done = move_line.product_uom_qty

        # Valider le picking
        picking.button_validate()

    def _force_picking_validation(self, picking):
        """Force la validation d'un picking en créant les move_lines nécessaires"""
        for move in picking.move_ids:
            # Créer des move_lines si elles n'existent pas
            if not move.move_line_ids:
                self.env['stock.move.line'].create({
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'qty_done': move.product_uom_qty,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'picking_id': picking.id,
                })
            else:
                # Mettre à jour les move_lines existants
                for move_line in move.move_line_ids:
                    if move_line.qty_done == 0:
                        move_line.qty_done = move_line.product_uom_qty

        # Valider le picking
        picking.button_validate()

    def _process_automatic_invoice(self):
        """Traite automatiquement la facturation"""
        if not self.sale_order_id:
            return

        try:
            # En mode simplifié, facturer directement depuis la commande de vente
            # Utiliser la méthode standard d'Odoo pour créer la facture
            if self.sale_order_id.invoice_status in ['to invoice', 'no']:
                # Créer la facture via l'action standard
                invoice_action = self.sale_order_id.action_create_invoice()

                if invoice_action and 'res_id' in invoice_action:
                    invoice = self.env['account.move'].browse(invoice_action['res_id'])
                elif invoice_action and 'domain' in invoice_action:
                    # Si plusieurs factures, prendre la dernière
                    invoices = self.env['account.move'].search(invoice_action['domain'])
                    invoice = invoices[-1] if invoices else False
                else:
                    # Fallback : chercher la facture liée à cette commande
                    invoice = self.sale_order_id.invoice_ids.filtered(lambda i: i.state == 'draft')[-1:]

                if invoice:
                    # Comptabiliser automatiquement
                    if invoice.state == 'draft':
                        invoice.action_post()

                    self.auto_workflow_state = 'invoiced'
                    return

            # Fallback si la méthode standard ne fonctionne pas
            self._create_manual_invoice()

        except Exception as e:
            # Log l'erreur et essayer la méthode manuelle
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Erreur lors de la création de la facture pour {self.sale_order_id.name}: {str(e)}")

            # Essayer la création manuelle
            self._create_manual_invoice()

    def _create_manual_invoice(self):
        """Création manuelle de la facture en cas d'échec de la méthode standard"""
        try:
            # Préparer les données de facture
            invoice_vals = self.sale_order_id._prepare_invoice()

            # Ajouter les lignes de facture
            invoice_lines = []
            for line in self.sale_order_id.order_line:
                if line.product_uom_qty > 0:  # Seulement les lignes avec quantité
                    line_vals = line._prepare_invoice_line()
                    invoice_lines.append((0, 0, line_vals))

            if invoice_lines:
                invoice_vals['invoice_line_ids'] = invoice_lines
                invoice = self.env['account.move'].create(invoice_vals)

                # Comptabiliser automatiquement
                if invoice.state == 'draft':
                    invoice.action_post()

                self.auto_workflow_state = 'invoiced'

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Erreur critique lors de la création manuelle de la facture: {str(e)}")

    def _get_partner(self):
        """Retourne le partenaire pour la commande"""
        # À implémenter dans les modèles héritiers
        raise NotImplementedError("_get_partner doit être implémenté dans le modèle héritier")

    def _get_order_lines(self):
        """Retourne les lignes pour la commande"""
        # À implémenter dans les modèles héritiers
        raise NotImplementedError("_get_order_lines doit être implémenté dans le modèle héritier")

    def _get_warehouse(self):
        """Retourne l'entrepôt par défaut"""
        # 1. Entrepôt configuré pour GPL
        warehouse_id = self.env['ir.config_parameter'].sudo().get_param('cpss_gpl.default_warehouse_id')
        if warehouse_id:
            try:
                warehouse = self.env['stock.warehouse'].browse(int(warehouse_id))
                if warehouse.exists():
                    return warehouse
            except (ValueError, TypeError):
                pass

        # 2. Entrepôt par défaut de la société
        return self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)

    def _get_pricelist(self):
        """Retourne la liste de prix par défaut"""
        # 1. Pricelist configurée pour GPL
        pricelist_id = self.env['ir.config_parameter'].sudo().get_param('cpss_gpl.default_pricelist_id')
        if pricelist_id:
            try:
                pricelist = self.env['product.pricelist'].browse(int(pricelist_id))
                if pricelist.exists():
                    return pricelist
            except (ValueError, TypeError):
                pass

        # 2. Pricelist du client si configurée
        partner = self._get_partner()
        if partner and partner.property_product_pricelist:
            return partner.property_product_pricelist

        # 3. Pricelist par défaut de la société
        return self.env['product.pricelist'].search([
            ('currency_id', '=', self.env.company.currency_id.id)
        ], limit=1)
