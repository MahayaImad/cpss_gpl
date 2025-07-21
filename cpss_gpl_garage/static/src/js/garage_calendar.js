/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * CPSS GPL Garage - Fonctionnalités JavaScript
 */

const GarageCalendarUtils = {
    /**
     * Formate l'affichage des événements du calendrier
     */
    formatCalendarEvent: function(event) {
        const serviceIcons = {
            'installation': '🔧',
            'repair': '🔨',
            'maintenance': '⚙️',
            'inspection': '✅',
            'testing': '🧪'
        };

        const icon = serviceIcons[event.next_service_type] || '📅';
        return `${icon} ${event.license_plate} - ${event.client_id}`;
    },

    /**
     * Applique les couleurs selon le type de service
     */
    getServiceColor: function(serviceType) {
        const colors = {
            'installation': '#28a745',
            'repair': '#dc3545',
            'maintenance': '#ffc107',
            'inspection': '#17a2b8',
            'testing': '#6f42c1'
        };
        return colors[serviceType] || '#6c757d';
    },

    /**
     * Notifie les actions de planning
     */
    showPlanningNotification: function(message, type = 'success') {
        if (typeof odoo !== 'undefined' && odoo.notification) {
            odoo.notification.add(message, {
                type: type,
                sticky: false,
                timeout: 3000
            });
        }
    },

    /**
     * Valide les créneaux horaires
     */
    validateTimeSlot: function(startDate, duration) {
        const start = new Date(startDate);
        const end = new Date(start.getTime() + (duration * 60 * 60 * 1000));

        // Vérifications business
        const startHour = start.getHours();
        const endHour = end.getHours();

        if (startHour < 8 || endHour > 18) {
            return {
                valid: false,
                message: 'Les créneaux doivent être entre 8h et 18h'
            };
        }

        if (start.getDay() === 0) { // Dimanche
            return {
                valid: false,
                message: 'Aucun rendez-vous le dimanche'
            };
        }

        return { valid: true };
    }
};

// Extension du widget calendrier
registry.category("fields").add("gpl_calendar_widget", {
    component: class extends Component {
        setup() {
            super.setup();
            this.garageUtils = GarageCalendarUtils;
        }

        onEventClick(info) {
            // Gestion des clics sur les événements
            console.log('Événement cliqué:', info.event);
        }

        onDateSelect(selectInfo) {
            // Gestion de la sélection de dates
            console.log('Date sélectionnée:', selectInfo);
        }
    }
});

// Fonctions utilitaires globales
window.GarageCalendarUtils = GarageCalendarUtils;

console.log('[CPSS GPL Garage] Module JavaScript chargé');
