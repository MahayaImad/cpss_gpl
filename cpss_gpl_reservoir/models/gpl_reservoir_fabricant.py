from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GplReservoirFabriquant(models.Model):
    _name = 'gpl.reservoir.fabricant'
    _description = 'Fabricant de Réservoirs GPL'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string="Nom du fabricant",
        required=True,
        tracking=True,
        help="Nom officiel du fabricant de réservoirs GPL"
    )

    code = fields.Char(
        string="Code fabricant",
        size=10,
        required=True,
        tracking=True,
        help="Code unique pour identifier le fabricant"
    )

    country_id = fields.Many2one(
        'res.country',
        string="Pays",
        tracking=True,
        help="Pays d'origine du fabricant"
    )

    website = fields.Char(
        string="Site web",
        help="Site web officiel du fabricant"
    )

    email = fields.Char(
        string="Email",
        help="Email de contact du fabricant"
    )

    phone = fields.Char(
        string="Téléphone",
        help="Numéro de téléphone du fabricant"
    )

    active = fields.Boolean(
        string="Actif",
        default=True,
        tracking=True,
        help="Décocher pour archiver le fabricant"
    )

    notes = fields.Text(
        string="Notes",
        help="Informations complémentaires sur le fabricant"
    )

    # === RELATIONS ===
    product_ids = fields.One2many(
        'product.template',
        'gpl_fabricant_id',
        string="Produits",
        help="Tous les produits de ce fabricant"
    )

    # === CHAMPS CALCULÉS ===
    reservoir_count = fields.Integer(
        string="Nombre de réservoirs",
        compute='_compute_counts',
        store=True,
        help="Nombre total de réservoirs de ce fabricant"
    )

    product_count = fields.Integer(
        string="Nombre de produits",
        compute='_compute_counts',
        store=True,
        help="Nombre de produits référencés pour ce fabricant"
    )

    # === CONTRAINTES ===
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Le code fabricant doit être unique !'),
        ('name_unique', 'UNIQUE(name)', 'Le nom du fabricant doit être unique !'),
    ]

    @api.constrains('code')
    def _check_code_format(self):
        """Vérifie le format du code fabricant"""
        for record in self:
            if record.code:
                if not record.code.isalnum():
                    raise ValidationError(_("Le code fabricant ne doit contenir que des lettres et des chiffres."))
                if len(record.code) < 2:
                    raise ValidationError(_("Le code fabricant doit contenir au moins 2 caractères."))

    @api.constrains('certification_date', 'certification_expiry')
    def _check_certification_dates(self):
        """Vérifie la cohérence des dates de certification"""
        for record in self:
            if record.certification_date and record.certification_expiry:
                if record.certification_date >= record.certification_expiry:
                    raise ValidationError(_("La date d'expiration doit être postérieure à la date de certification."))

    @api.depends('product_ids', 'product_ids.is_gpl_reservoir')
    def _compute_counts(self):
        """Calcule le nombre de réservoirs et produits par fabricant"""
        for record in self:
            # Nombre total de produits
            record.product_count = len(record.product_ids)

            # Nombre de réservoirs GPL seulement
            record.reservoir_count = len(record.product_ids.filtered('is_gpl_reservoir'))

    @api.model_create_multi
    def create(self, vals_list):
        """Create method updated for Odoo 17 compatibility"""
        for vals in vals_list:
            # Normaliser le code en majuscules
            if vals.get('code'):
                vals['code'] = vals['code'].upper()

        return super().create(vals_list)

    def write(self, vals):
        """Write method with code normalization"""
        if vals.get('code'):
            vals['code'] = vals['code'].upper()

        return super().write(vals)

    def name_get(self):
        """Personnalise l'affichage du nom"""
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            if record.country_id:
                name += f" ({record.country_id.code})"
            result.append((record.id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Recherche améliorée sur nom et code"""
        if args is None:
            args = []

        if name:
            # Ajouter domaine de recherche sur nom et code
            search_domain = [
                '|',
                ('name', operator, name),
                ('code', operator, name.upper())
            ]
            args += search_domain

        # Utiliser la recherche standard avec le domaine modifié
        return super().name_search(name='', args=args, operator=operator, limit=limit)

    def action_view_reservoirs(self):
        """Affiche les réservoirs de ce fabricant"""
        self.ensure_one()

        action = self.env.ref('cpss_gpl_reservoir.action_stock_lot_reservoir').read()[0]
        action['domain'] = [
            ('product_id.is_gpl_reservoir', '=', True),
            ('product_id.gpl_fabricant_id', '=', self.id)
        ]
        action['context'] = {
            'default_gpl_fabricant_id': self.id,
            'search_default_fabricant_id': self.id
        }
        return action

    def action_view_products(self):
        """Affiche les produits de ce fabricant"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Produits de %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('gpl_fabricant_id', '=', self.id)],
            'context': {
                'default_gpl_fabricant_id': self.id,
                'search_default_fabricant_id': self.id
            }
        }

    def toggle_active(self):
        """Bascule le statut actif/inactif"""
        for record in self:
            record.active = not record.active

    @api.model
    def get_fabricant_stats(self):
        """Retourne les statistiques des fabricants pour le dashboard"""
        stats = {}

        fabricants = self.search([('active', '=', True)])
        for fabricant in fabricants:
            stats[fabricant.code] = {
                'name': fabricant.name,
                'reservoir_count': fabricant.reservoir_count,
                'country': fabricant.country_id.name if fabricant.country_id else '',
                'certification_expiry': fabricant.certification_expiry
            }

        return stats
