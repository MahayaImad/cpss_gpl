from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GplBordereau(models.Model):
    _name = 'gpl.bordereau'
    _description = 'Bordereau d\'envoi contrôles GPL'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_creation desc'

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    date_creation = fields.Datetime(
        string='Date de création',
        default=fields.Datetime.now,
        required=True,
        readonly=True
    )

    date_envoi = fields.Date(
        string='Date d\'envoi',
        help="Date d'envoi à la direction de l'industrie"
    )

    inspection_ids = fields.One2many(
        'gpl.inspection',  # Modèle cible
        'bordereau_id',  # Champ dans le modèle cible qui pointe vers ce bordereau
        string='Contrôles'
    )

    inspection_count = fields.Integer(
        string='Nombre de contrôles',
        compute='_compute_inspection_count',
        store=True
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé'),
    ], string='État', default='draft', tracking=True)

    notes = fields.Text(string='Notes')

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
        required=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gpl.bordereau') or 'BOR-NEW'
        return super().create(vals_list)

    @api.depends('inspection_ids')
    def _compute_inspection_count(self):
        for record in self:
            record.inspection_count = len(record.inspection_ids)

    def action_send(self):
        """Marque le bordereau comme envoyé"""
        self.ensure_one()
        if not self.inspection_ids:
            raise UserError(_("Impossible d'envoyer un bordereau vide."))

        self.write({
            'state': 'sent',
            'date_envoi': fields.Date.today()
        })

    def action_print_bordereau(self):
        """Imprime le bordereau d'envoi"""
        self.ensure_one()
        return self.env.ref('cpss_gpl_reports.action_report_gpl_bordereau_envoi').report_action(self)

    def action_add_inspections(self):
        """Ouvre la liste des contrôles disponibles"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sélectionner des contrôles',
            'res_model': 'gpl.inspection',
            'view_mode': 'tree',
            'target': 'new',
            'domain': [('state', '=', 'done'), ('result', '=', 'pass'), ('bordereau_id', '=', False)],
            'context': {
                'bordereau_id_to_assign': self.id,
            },
            'view_id': self.env.ref('cpss_gpl_operations.view_gpl_inspection_bordereau_selection').id,
        }
