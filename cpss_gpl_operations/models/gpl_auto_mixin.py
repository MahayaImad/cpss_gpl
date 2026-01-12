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
                #'lot_id': line.lot_id.id,
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
        """Valide un picking en assignant les lots aux move_lines"""
        for move in picking.move_ids:
            # Trouver le lot correspondant depuis les lignes originales
            lot_to_assign = None
            for line in self._get_order_lines():
                # Cas 1: Le produit de la ligne correspond directement au move
                if (line.product_id.id == move.product_id.id and
                    hasattr(line, 'lot_id') and line.lot_id):
                    lot_to_assign = line.lot_id
                    break

                # Cas 2: Le produit de la ligne est un kit GPL contenant le produit du move
                if (hasattr(line.product_id, 'is_gpl_kit') and line.product_id.is_gpl_kit and
                    hasattr(line, 'lot_id') and line.lot_id):
                    # Vérifier si le produit du move est un composant de ce kit
                    bom = self.env['mrp.bom'].search([
                        '|',
                        ('product_id', '=', line.product_id.id),
                        ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                        ('active', '=', True)
                    ], limit=1)

                    if bom:
                        # Vérifier si move.product_id est dans les composants du kit
                        if any(bom_line.product_id.id == move.product_id.id
                               for bom_line in bom.bom_line_ids):
                            lot_to_assign = line.lot_id
                            break

            # Assigner aux move_lines existants
            for move_line in move.move_line_ids:
                # Utiliser write() qui est plus robuste que l'assignation directe
                vals_to_update = {}

                try:
                    # Assigner qty_done
                    if hasattr(move_line, 'qty_done') and move_line.qty_done == 0:
                        vals_to_update['qty_done'] = move_line.product_uom_qty
                    elif not hasattr(move_line, 'qty_done'):
                        vals_to_update['qty_done'] = move_line.product_uom_qty

                    # Assigner le lot si trouvé et que le produit correspond
                    if lot_to_assign and move_line.product_id.id == move.product_id.id:
                        vals_to_update['lot_id'] = lot_to_assign.id

                    if vals_to_update:
                        move_line.write(vals_to_update)
                except Exception as e:
                    _logger.warning(f"Impossible d'assigner qty_done pour move_line {move_line.id}: {str(e)}")
                    continue

        # Valider le picking
        if hasattr(picking, 'button_validate'):
            picking.button_validate()
        else:
            picking.action_done()

    def _force_picking_validation(self, picking):
        """Force la validation d'un picking en créant les move_lines avec lots"""
        for move in picking.move_ids:
            if not move.move_line_ids:
                # Trouver le lot correspondant
                lot_to_assign = None
                for line in self._get_order_lines():
                    # Cas 1: Le produit de la ligne correspond directement au move
                    if (line.product_id.id == move.product_id.id and
                        hasattr(line, 'lot_id') and line.lot_id):
                        lot_to_assign = line.lot_id
                        break

                    # Cas 2: Le produit de la ligne est un kit GPL contenant le produit du move
                    if (hasattr(line.product_id, 'is_gpl_kit') and line.product_id.is_gpl_kit and
                        hasattr(line, 'lot_id') and line.lot_id):
                        # Vérifier si le produit du move est un composant de ce kit
                        bom = self.env['mrp.bom'].search([
                            '|',
                            ('product_id', '=', line.product_id.id),
                            ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                            ('active', '=', True)
                        ], limit=1)

                        if bom:
                            # Vérifier si move.product_id est dans les composants du kit
                            if any(bom_line.product_id.id == move.product_id.id
                                   for bom_line in bom.bom_line_ids):
                                lot_to_assign = line.lot_id
                                break

                # Créer le move_line
                move_line_vals = {
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'picking_id': picking.id,
                }

                # Dans Odoo 17, qty_done est le champ standard
                move_line_vals['qty_done'] = move.product_uom_qty

                # Ajouter le lot seulement si nécessaire
                if lot_to_assign:
                    move_line_vals['lot_id'] = lot_to_assign.id

                self.env['stock.move.line'].create(move_line_vals)
            else:
                # Assigner aux move_lines existants
                lot_to_assign = None
                for line in self._get_order_lines():
                    # Cas 1: Le produit de la ligne correspond directement au move
                    if (line.product_id.id == move.product_id.id and
                        hasattr(line, 'lot_id') and line.lot_id):
                        lot_to_assign = line.lot_id
                        break

                    # Cas 2: Le produit de la ligne est un kit GPL contenant le produit du move
                    if (hasattr(line.product_id, 'is_gpl_kit') and line.product_id.is_gpl_kit and
                        hasattr(line, 'lot_id') and line.lot_id):
                        # Vérifier si le produit du move est un composant de ce kit
                        bom = self.env['mrp.bom'].search([
                            '|',
                            ('product_id', '=', line.product_id.id),
                            ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                            ('active', '=', True)
                        ], limit=1)

                        if bom:
                            # Vérifier si move.product_id est dans les composants du kit
                            if any(bom_line.product_id.id == move.product_id.id
                                   for bom_line in bom.bom_line_ids):
                                lot_to_assign = line.lot_id
                                break

                for move_line in move.move_line_ids:
                    try:
                        # Utiliser write() pour être plus robuste
                        vals_to_update = {}

                        if hasattr(move_line, 'qty_done') and move_line.qty_done == 0:
                            vals_to_update['qty_done'] = move_line.product_uom_qty
                        elif not hasattr(move_line, 'qty_done'):
                            vals_to_update['qty_done'] = move_line.product_uom_qty

                        if lot_to_assign and not move_line.lot_id:
                            vals_to_update['lot_id'] = lot_to_assign.id

                        if vals_to_update:
                            move_line.write(vals_to_update)
                    except Exception as e:
                        _logger.warning(f"Impossible de mettre à jour move_line {move_line.id}: {str(e)}")
                        continue


        # Valider le picking
        if hasattr(picking, 'button_validate'):
            picking.button_validate()
        else:
            picking.action_done()

    def _process_automatic_invoice(self):
        """Traite automatiquement la facturation"""

        if not self.sale_order_id:
            return

        import logging
        _logger = logging.getLogger(__name__)

        try:
            # En mode simplifié, facturer directement depuis la commande de vente
            # Utiliser la méthode standard d'Odoo pour créer la facture
            if self.sale_order_id.invoice_status in ['to invoice', 'no']:
                # Méthode pour Odoo 17
                if hasattr(self.sale_order_id, '_create_invoices'):
                    invoice = self.sale_order_id._create_invoices()
                    _logger.info(f"Facture créée via _create_invoices: {invoice.name if invoice else 'Aucune'}")
                elif hasattr(self.sale_order_id, 'action_invoice_create'):
                    # Méthode pour versions antérieures
                    invoice_ids = self.sale_order_id.action_invoice_create()
                    invoice = self.env['account.move'].browse(invoice_ids) if invoice_ids else False
                    _logger.info(f"Facture créée via action_invoice_create: {invoice.name if invoice else 'Aucune'}")
                else:
                    # Fallback : création manuelle
                    _logger.info("Utilisation fallback création manuelle")
                    return self._create_manual_invoice()

                if invoice:
                    # Comptabiliser automatiquement
                    if hasattr(invoice, 'action_post'):
                        invoice.action_post()
                    elif hasattr(invoice, 'action_invoice_open'):
                        invoice.action_invoice_open()

                    self.auto_workflow_state = 'invoiced'
                    _logger.info(f"Facture postée: {invoice.name}")
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
