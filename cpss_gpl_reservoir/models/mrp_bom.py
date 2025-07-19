# -*- coding: utf-8 -*-

from odoo import models, api, fields


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    is_gpl_kit = fields.Boolean(
        string="Est un kit GPL",
        related='product_tmpl_id.is_gpl_kit',
        store=True,
        readonly=True
    )

    # === CHAMPS CALCULÉS GPL ===
    contains_gpl_reservoir = fields.Boolean(
        string="Contient un réservoir GPL",
        compute='_compute_gpl_components',
        store=True,
        help="Indique si cette nomenclature contient au moins un réservoir GPL"
    )

    contains_gpl_components = fields.Boolean(
        string="Contient des composants GPL",
        compute='_compute_gpl_components',
        store=True,
        help="Indique si cette nomenclature contient des composants GPL"
    )

    gpl_fabricant_id = fields.Many2one(
        'gpl.reservoir.fabricant',
        string="Fabricant GPL du produit",
        related='product_tmpl_id.gpl_fabricant_id',
        store=True,
        readonly=True
    )

    @api.depends('bom_line_ids.product_id.product_tmpl_id.is_gpl_reservoir',
                 'bom_line_ids.product_id.product_tmpl_id.is_gpl_component')
    def _compute_gpl_components(self):
        """Calcule si la nomenclature contient des composants GPL"""
        for bom in self:
            # Vérifier les réservoirs GPL
            bom.contains_gpl_reservoir = any(
                line.product_id.product_tmpl_id.is_gpl_reservoir
                for line in bom.bom_line_ids
            )

            # Vérifier les composants GPL (si ce champ existe)
            bom.contains_gpl_components = any(
                getattr(line.product_id.product_tmpl_id, 'is_gpl_component', False)
                for line in bom.bom_line_ids
            )

    @api.model_create_multi
    def create(self, vals_list):
        """Create method updated for Odoo 17 compatibility"""
        boms = super().create(vals_list)

        # Recalculer is_gpl_kit pour les produits concernés
        products = boms.mapped('product_tmpl_id')
        products._compute_is_gpl_kit()

        return boms

    def write(self, vals):
        """Write method with GPL kit recalculation"""
        result = super().write(vals)

        # Recalculer is_gpl_kit si nécessaire
        if any(key in vals for key in ['bom_line_ids', 'product_tmpl_id', 'active']):
            products = self.mapped('product_tmpl_id')
            products._compute_is_gpl_kit()

        return result

    def unlink(self):
        """Unlink method with GPL kit recalculation"""
        products = self.mapped('product_tmpl_id')
        result = super().unlink()

        # Recalculer is_gpl_kit après suppression
        products._compute_is_gpl_kit()

        return result


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    # === CHAMPS RELATED GPL ===
    is_gpl_reservoir = fields.Boolean(
        string="Est un réservoir GPL",
        related='product_id.product_tmpl_id.is_gpl_reservoir',
        store=True,
        readonly=True
    )

    is_gpl_component = fields.Boolean(
        string="Est un composant GPL",
        related='product_id.product_tmpl_id.is_gpl_component',
        store=True,
        readonly=True
    )

    gpl_fabricant_id = fields.Many2one(
        'gpl.reservoir.fabricant',
        string="Fabricant GPL",
        related='product_id.product_tmpl_id.gpl_fabricant_id',
        store=True,
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Create method updated for Odoo 17 compatibility"""
        lines = super().create(vals_list)

        # Recalculer is_gpl_kit pour les produits concernés
        products = lines.mapped('bom_id.product_tmpl_id')
        products._compute_is_gpl_kit()

        return lines

    def write(self, vals):
        """Write method with GPL kit recalculation"""
        result = super().write(vals)

        # Recalculer is_gpl_kit si nécessaire
        if any(key in vals for key in ['product_id', 'product_qty']):
            products = self.mapped('bom_id.product_tmpl_id')
            products._compute_is_gpl_kit()

        return result

    def unlink(self):
        """Unlink method with GPL kit recalculation"""
        products = self.mapped('bom_id.product_tmpl_id')
        result = super().unlink()

        # Recalculer is_gpl_kit après suppression
        products._compute_is_gpl_kit()

        return result
