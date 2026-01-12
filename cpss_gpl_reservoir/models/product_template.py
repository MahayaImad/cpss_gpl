# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # === CHAMPS GPL ===
    is_gpl_reservoir = fields.Boolean(
        string="Réservoir GPL",
        default=False,
        help="Cocher si ce produit est un réservoir GPL"
    )

    is_gpl_component = fields.Boolean(
        string="Composant GPL",
        default=False,
        help="Cocher si ce produit est un composant GPL"
    )

    is_gpl_kit = fields.Boolean(
        string="Kit GPL",
        compute='_compute_is_gpl_kit',
        store=True,
        help="Calculé automatiquement si le produit contient des composants GPL"
    )

    # === FABRICANT ===
    gpl_fabricant_id = fields.Many2one(
        'gpl.reservoir.fabricant',
        string="Fabricant GPL",
        help="Fabricant du produit GPL"
    )

    # === SPÉCIFICATIONS RÉSERVOIR ===
    gpl_capacity = fields.Float(
        string="Capacité (L)",
        help="Capacité du réservoir en litres"
    )

    gpl_pressure = fields.Float(
        string="Pression (bar)",
        help="Pression de service en bars"
    )

    gpl_shape = fields.Selection([
        ('cylindrical', 'Cylindrique'),
        ('toroidal', 'Torique'),
        ('rectangular', 'Rectangulaire'),
        ('other', 'Autre')
    ], string="Forme", help="Forme du réservoir")

    # === COMPATIBILITÉ ===
    gpl_vehicle_brands = fields.Many2many(
        'fleet.vehicle.model.brand',
        'product_template_vehicle_brand_rel',
        'product_id',
        'brand_id',
        string="Marques compatibles",
        help="Marques de véhicules compatibles avec ce produit"
    )

    # === CHAMPS CALCULÉS ===
    gpl_lot_count = fields.Integer(
        string="Nombre de lots",
        compute='_compute_gpl_lot_count',
        help="Nombre de lots en stock pour ce produit GPL"
    )

    @api.depends('bom_ids', 'bom_ids.bom_line_ids', 'bom_ids.bom_line_ids.product_id')
    def _compute_is_gpl_kit(self):
        """Calcule automatiquement si le produit est un kit GPL"""
        for product in self:
            is_kit = False

            # Vérifier s'il y a des nomenclatures actives
            boms = product.bom_ids.filtered(lambda b: b.active)
            if boms:
                # Vérifier si au moins un composant est GPL
                for bom in boms:
                    gpl_components = bom.bom_line_ids.filtered(
                        lambda l: l.product_id.is_gpl_reservoir or l.product_id.is_gpl_component
                    )
                    if gpl_components:
                        is_kit = True
                        break

            product.is_gpl_kit = is_kit

    @api.depends('is_gpl_reservoir')
    def _compute_gpl_lot_count(self):
        """Calcule le nombre de lots GPL"""
        for product in self:
            if product.is_gpl_reservoir:
                lots = self.env['stock.lot'].search([
                    ('product_id', 'in', product.product_variant_ids.ids)
                ])
                product.gpl_lot_count = len(lots)
            else:
                product.gpl_lot_count = 0

    @api.onchange('is_gpl_reservoir')
    def _onchange_is_gpl_reservoir(self):
        """Configure automatiquement le produit pour GPL"""
        if self.is_gpl_reservoir:
            # Configuration automatique pour réservoirs
            self.detailed_type = 'product'
            self.tracking = 'serial'
            self.is_gpl_component = True

            # Catégorie par défaut
            gpl_category = self.env.ref('cpss_gpl_reservoir.product_category_gpl_reservoir', raise_if_not_found=False)
            if gpl_category:
                self.categ_id = gpl_category

    @api.onchange('is_gpl_component')
    def _onchange_is_gpl_component(self):
        """Configure automatiquement le produit pour composant GPL"""
        if self.is_gpl_component and not self.is_gpl_reservoir:
            # Catégorie par défaut
            gpl_category = self.env.ref('cpss_gpl_reservoir.product_category_gpl_component', raise_if_not_found=False)
            if gpl_category:
                self.categ_id = gpl_category

    @api.onchange('gpl_fabricant_id')
    def _onchange_gpl_fabricant_id(self):
        """Met à jour les informations selon le fabricant"""
        if self.gpl_fabricant_id:
            # Préfixer le nom si pas déjà fait
            if self.name and not self.name.startswith(f'[{self.gpl_fabricant_id.code}]'):
                self.name = f'[{self.gpl_fabricant_id.code}] {self.name}'

    @api.model_create_multi
    def create(self, vals_list):
        """Create method updated for Odoo 17"""
        products = super().create(vals_list)

        # Calculer is_gpl_kit après création
        products._compute_is_gpl_kit()

        return products

    def write(self, vals):
        """Write method with GPL specific logic"""
        result = super().write(vals)

        # Recalculer is_gpl_kit si nécessaire
        if any(key in vals for key in ['bom_ids', 'is_gpl_reservoir', 'is_gpl_component']):
            self._compute_is_gpl_kit()

        return result

    def action_view_gpl_lots(self):
        """Affiche les lots GPL de ce produit"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Lots GPL - %s') % self.name,
            'res_model': 'stock.lot',
            'view_mode': 'tree,form',
            'domain': [('product_id', 'in', self.product_variant_ids.ids)],
            'context': {
                'default_product_id': self.product_variant_ids[0].id if self.product_variant_ids else False,
                'search_default_product_id': self.product_variant_ids[0].id if self.product_variant_ids else False
            }
        }

    def action_create_bom(self):
        """Crée une nomenclature pour ce produit"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouvelle Nomenclature - %s') % self.name,
            'res_model': 'mrp.bom',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_product_tmpl_id': self.id,
                'default_type': 'normal'
            }
        }

    @api.model
    def get_gpl_products_stats(self):
        """Retourne les statistiques des produits GPL"""
        stats = {
            'reservoirs': self.search_count([('is_gpl_reservoir', '=', True)]),
            'components': self.search_count([('is_gpl_component', '=', True), ('is_gpl_reservoir', '=', False)]),
            'kits': self.search_count([('is_gpl_kit', '=', True)]),
            'total_gpl': self.search_count(['|', ('is_gpl_reservoir', '=', True), ('is_gpl_component', '=', True)])
        }

        return stats


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # def action_view_reservoir_lots(self):
    #     """Affiche les lots de réservoirs pour ce produit variant"""
    #     self.ensure_one()

    def action_view_gpl_lots(self):
        self.ensure_one()
        return self.product_tmpl_id.action_view_gpl_lots()

        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': _('Lots Réservoirs - %s') % self.name,
        #     'res_model': 'stock.lot',
        #     'view_mode': 'tree,form',
        #     'domain': [('product_id', '=', self.id)],
        #     'context': {
        #         'default_product_id': self.id,
        #         'search_default_product_id': self.id
        #     }
        # }
