from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GplVehicleOverride(models.Model):
    """Extension du modèle véhicule pour intégration avec les opérations"""
    _inherit = 'gpl.vehicle'


    # === CHAMPS CALCULÉS ===
    operation_count = fields.Integer(
        string='Nombre d\'opérations',
        compute='_compute_operation_count',
        help="Nombre total d'opérations effectuées sur ce véhicule"
    )

    installation_count = fields.Integer(
        string='Installations',
        compute='_compute_operation_count'
    )

    repair_count = fields.Integer(
        string='Réparations',
        compute='_compute_operation_count'
    )

    inspection_count = fields.Integer(
        string='Contrôles',
        compute='_compute_operation_count'
    )

    testing_count = fields.Integer(
        string='Tests réservoir',
        compute='_compute_operation_count'
    )

    @api.depends()  # Pas de dépendance pour éviter les recalculs constants
    def _compute_operation_count(self):
        """Calcule le nombre d'opérations pour chaque véhicule"""
        for vehicle in self:
            # Compteur installations
            installation_count = self.env['gpl.service.installation'].search_count([
                ('vehicle_id', '=', vehicle.id)
            ])

            # Compteur réparations
            repair_count = self.env['gpl.repair.order'].search_count([
                ('vehicle_id', '=', vehicle.id)
            ])

            # Compteur contrôles
            inspection_count = self.env['gpl.inspection'].search_count([
                ('vehicle_id', '=', vehicle.id)
            ])

            # Compteur tests réservoirs
            testing_count = self.env['gpl.reservoir.testing'].search_count([
                ('vehicle_id', '=', vehicle.id)
            ])

            # Attribution des valeurs
            vehicle.installation_count = installation_count
            vehicle.repair_count = repair_count
            vehicle.inspection_count = inspection_count
            vehicle.testing_count = testing_count
            vehicle.operation_count = installation_count + repair_count + inspection_count + testing_count

    # === ACTION SMART BUTTONS ===
    def action_view_installations(self):
        """Smart button pour voir les installations du véhicule"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Installations - %s') % self.license_plate,
            'res_model': 'gpl.service.installation',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_view_repairs(self):
        """Smart button pour voir les réparations du véhicule"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Réparations - %s') % self.license_plate,
            'res_model': 'gpl.repair.order',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_view_inspections(self):
        """Smart button pour voir les contrôles du véhicule"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrôles - %s') % self.license_plate,
            'res_model': 'gpl.inspection',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_view_testings(self):
        """Smart button pour voir les tests réservoir du véhicule"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tests Réservoir - %s') % self.license_plate,
            'res_model': 'gpl.reservoir.testing',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_start_service(self):
        """Surcharge pour créer automatiquement le document d'opération correspondant"""
        self.ensure_one()

        # Vérifier qu'un service est planifié
        if not self.next_service_type:
            raise UserError(_("Aucun type de service défini pour ce véhicule."))

        if not self.appointment_date:
            raise UserError(_("Aucun rendez-vous programmé pour ce véhicule."))

        # Appeler d'abord la méthode parente pour mettre à jour le statut
        result = super().action_start_service()

        # Créer le document d'opération correspondant
        operation_result = self._create_operation_document()

        # Retourner l'action pour ouvrir le document créé
        if operation_result:
            return operation_result

        return result

    def _create_operation_document(self):
        """Crée le document d'opération selon le type de service"""
        service_type = self.next_service_type

        # Données communes à tous les services
        common_data = self._prepare_common_service_data()

        if service_type == 'installation':
            return self._create_installation_document(common_data)
        elif service_type == 'repair':
            return self._create_repair_document(common_data)
        elif service_type == 'maintenance':
            return self._create_maintenance_document(common_data)
        elif service_type == 'inspection':
            return self._create_inspection_document(common_data)
        elif service_type == 'testing':
            return self._create_testing_document(common_data)
        else:
            raise UserError(_("Type de service '%s' non supporté.") % service_type)

    def _prepare_common_service_data(self):
        """Prépare les données communes à tous les services"""
        return {
            'vehicle_id': self.id,
            'client_id': self.client_id.id,
            'date_start': self.appointment_date or fields.Datetime.now(),
            'date_planned': self.appointment_date,
            'technician_ids': [(6, 0, self.assigned_technician_ids.ids)] if self.assigned_technician_ids else [],
            'notes': self.notes or '',
        }

    def _create_installation_document(self, common_data):
        """Crée un document d'installation GPL - VERSION CORRIGÉE"""
        installation_vals = {
            **common_data,
            'state': 'planned',  # Commencer en planifié
        }

        installation = self.env['gpl.service.installation'].create(installation_vals)

        installation.action_start()  # Ceci va créer la vente automatiquement


        return {
            'type': 'ir.actions.act_window',
            'name': _('Installation GPL - %s') % self.license_plate,
            'res_model': 'gpl.service.installation',
            'res_id': installation.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_vehicle_id': self.id,
            }
        }

    def _create_repair_document(self, common_data):
        """Crée un document de réparation GPL - VERSION CORRIGÉE"""
        repair_vals = {
            **common_data,
            'repair_type': 'repair',  # Type par défaut
            'priority': '0',  # Priorité normale
            'state': 'draft',
            'symptoms': self.notes or '',
            'date_scheduled': common_data['date_planned'],
        }

        repair = self.env['gpl.repair.order'].create(repair_vals)

        repair.action_start_repair()  # Ceci va créer la vente automatiquement

        return {
            'type': 'ir.actions.act_window',
            'name': _('Réparation GPL - %s') % self.license_plate,
            'res_model': 'gpl.repair.order',
            'res_id': repair.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_vehicle_id': self.id,
            }
        }

    def _create_maintenance_document(self, common_data):
        """Crée un document de maintenance - VERSION CORRIGÉE"""
        maintenance_vals = {
            **common_data,
            'repair_type': 'maintenance',
            'priority': '0',
            'state': 'draft',
            'symptoms': 'Maintenance préventive programmée',
            'date_scheduled': common_data['date_planned'],
        }

        maintenance = self.env['gpl.repair.order'].create(maintenance_vals)

        maintenance.action_start_repair()  # Ceci va créer la vente automatiquement

        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance GPL - %s') % self.license_plate,
            'res_model': 'gpl.repair.order',
            'res_id': maintenance.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_inspection_document(self, common_data):
        """Crée un document d'inspection GPL"""
        inspection_vals = {
            **common_data,
            'inspection_type': 'periodic',  # Type par défaut
            'state': 'draft',
        }

        inspection = self.env['gpl.inspection'].create(inspection_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrôle Technique - %s') % self.license_plate,
            'res_model': 'gpl.inspection',
            'res_id': inspection.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_testing_document(self, common_data):
        """Crée un document de test de réservoir"""
        if not self.reservoir_lot_id:
            raise UserError(_("Aucun réservoir associé à ce véhicule pour effectuer le test."))

        testing_vals = {
            **common_data,
            'reservoir_lot_id': self.reservoir_lot_id.id,
            'test_type': 'hydraulic',  # Type par défaut
            'state': 'draft',
        }

        testing = self.env['gpl.reservoir.testing'].create(testing_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Réépreuve Réservoir - %s') % self.license_plate,
            'res_model': 'gpl.reservoir.testing',
            'res_id': testing.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # === MÉTHODES UTILITAIRES ===

    @api.model
    def get_service_type_display(self):
        """Retourne les types de service disponibles pour affichage"""
        return [
            ('installation', 'Installation GPL'),
            ('repair', 'Réparation'),
            ('maintenance', 'Maintenance'),
            ('inspection', 'Contrôle Technique'),
            ('testing', 'Réépreuve Réservoir'),
        ]

    def action_view_related_operations(self):
        """Affiche toutes les opérations liées à ce véhicule"""
        self.ensure_one()

        # Rechercher tous les documents d'opération liés
        installations = self.env['gpl.service.installation'].search([('vehicle_id', '=', self.id)])
        repairs = self.env['gpl.repair.order'].search([('vehicle_id', '=', self.id)])
        inspections = self.env['gpl.inspection'].search([('vehicle_id', '=', self.id)])
        testings = self.env['gpl.reservoir.testing'].search([('vehicle_id', '=', self.id)])

        # Créer un contexte avec les IDs pour filtrage
        context = {
            'installation_ids': installations.ids,
            'repair_ids': repairs.ids,
            'inspection_ids': inspections.ids,
            'testing_ids': testings.ids,
            'default_vehicle_id': self.id,
        }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Opérations - %s') % self.license_plate,
            'res_model': 'gpl.vehicle.operations.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }


# === WIZARD POUR AFFICHER LES OPÉRATIONS LIÉES ===
class GplVehicleOperationsWizard(models.TransientModel):
    """Wizard pour afficher toutes les opérations d'un véhicule"""
    _name = 'gpl.vehicle.operations.wizard'
    _description = 'Opérations du véhicule GPL'

    vehicle_id = fields.Many2one('gpl.vehicle', 'Véhicule', required=True)

    # Compteurs
    installation_count = fields.Integer('Installations', compute='_compute_operation_counts')
    repair_count = fields.Integer('Réparations', compute='_compute_operation_counts')
    inspection_count = fields.Integer('Contrôles', compute='_compute_operation_counts')
    testing_count = fields.Integer('Tests réservoir', compute='_compute_operation_counts')

    @api.depends('vehicle_id')
    def _compute_operation_counts(self):
        for wizard in self:
            if wizard.vehicle_id:
                wizard.installation_count = self.env['gpl.service.installation'].search_count(
                    [('vehicle_id', '=', wizard.vehicle_id.id)])
                wizard.repair_count = self.env['gpl.repair.order'].search_count(
                    [('vehicle_id', '=', wizard.vehicle_id.id)])
                wizard.inspection_count = self.env['gpl.inspection'].search_count(
                    [('vehicle_id', '=', wizard.vehicle_id.id)])
                wizard.testing_count = self.env['gpl.reservoir.testing'].search_count(
                    [('vehicle_id', '=', wizard.vehicle_id.id)])
            else:
                wizard.installation_count = wizard.repair_count = wizard.inspection_count = wizard.testing_count = 0

    def action_view_installations(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Installations',
            'res_model': 'gpl.service.installation',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.vehicle_id.id)],
        }

    def action_view_repairs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Réparations',
            'res_model': 'gpl.repair.order',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.vehicle_id.id)],
        }

    def action_view_inspections(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contrôles',
            'res_model': 'gpl.inspection',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.vehicle_id.id)],
        }

    def action_view_testings(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tests réservoir',
            'res_model': 'gpl.reservoir.testing',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.vehicle_id.id)],
        }
