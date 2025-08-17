/**
 * GPL Reservoir Dashboard - Graphiques JavaScript
 * Rendu des graphiques avec Chart.js pour Odoo 17
 */

// === INITIALISATION DES GRAPHIQUES ===
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
});

// Réinitialiser les graphiques quand les données changent
$(document).on('change', 'input[name="fabricant_ids"], select[name="state_filter"], input[name="date_from"], input[name="date_to"]', function() {
    setTimeout(initializeCharts, 500); // Délai pour laisser Odoo mettre à jour les données
});

/**
 * Initialise tous les graphiques du dashboard
 */
function initializeCharts() {
    try {
        // Attendre que Chart.js soit disponible
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js non disponible, chargement depuis CDN...');
            loadChartJS().then(() => {
                renderAllCharts();
            });
        } else {
            renderAllCharts();
        }
    } catch (error) {
        console.error('Erreur lors de l\'initialisation des graphiques:', error);
    }
}

/**
 * Charge Chart.js depuis le CDN si nécessaire
 */
function loadChartJS() {
    return new Promise((resolve, reject) => {
        if (typeof Chart !== 'undefined') {
            resolve();
            return;
        }

        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js';
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

/**
 * Rend tous les graphiques
 */
function renderAllCharts() {
    renderStatusChart();
    renderFabricantChart();
    renderAgeChart();
}

/**
 * Graphique répartition par statut (Doughnut)
 */
function renderStatusChart() {
    const container = document.getElementById('chart_status');
    if (!container) return;

    // Récupérer les données depuis le champ caché
    const dataField = container.querySelector('input[name="chart_data_status"]');
    if (!dataField || !dataField.value) {
        container.innerHTML = '<p class="text-muted text-center">Aucune donnée disponible</p>';
        return;
    }

    try {
        // Parser les données Python (format: "{'valid': 5, 'expired': 2, ...}")
        const rawData = dataField.value.replace(/'/g, '"');
        const statusData = JSON.parse(rawData);

        // Préparer les données pour Chart.js
        const labels = [];
        const data = [];
        const backgroundColor = [];

        const statusConfig = {
            'valid': { label: 'Valides', color: '#28a745' },
            'expiring_soon': { label: 'Expirent bientôt', color: '#ffc107' },
            'expired': { label: 'Expirés', color: '#dc3545' },
            'test_required': { label: 'Test requis', color: '#fd7e14' },
            'too_old': { label: 'Trop anciens', color: '#6f42c1' }
        };

        Object.entries(statusData).forEach(([status, count]) => {
            if (count > 0) {
                const config = statusConfig[status] || { label: status, color: '#6c757d' };
                labels.push(`${config.label} (${count})`);
                data.push(count);
                backgroundColor.push(config.color);
            }
        });

        if (data.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">Aucun réservoir trouvé</p>';
            return;
        }

        // Créer le canvas
        container.innerHTML = '<canvas id="statusChart" width="400" height="300"></canvas>';
        const canvas = document.getElementById('statusChart');
        const ctx = canvas.getContext('2d');

        // Détruire le graphique existant s'il y en a un
        if (window.statusChartInstance) {
            window.statusChartInstance.destroy();
        }

        // Créer le graphique
        window.statusChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColor,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            fontSize: 12
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return `${context.label}: ${percentage}%`;
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            }
        });

    } catch (error) {
        console.error('Erreur lors du rendu du graphique statut:', error);
        container.innerHTML = '<p class="text-danger text-center">Erreur de rendu du graphique</p>';
    }
}

/**
 * Graphique répartition par fabricant (Bar horizontal)
 */
function renderFabricantChart() {
    const container = document.getElementById('chart_fabricant');
    if (!container) return;

    const dataField = container.querySelector('input[name="chart_data_fabricant"]');
    if (!dataField || !dataField.value) {
        container.innerHTML = '<p class="text-muted text-center">Aucune donnée disponible</p>';
        return;
    }

    try {
        const rawData = dataField.value.replace(/'/g, '"');
        const fabricantData = JSON.parse(rawData);

        const labels = Object.keys(fabricantData);
        const data = Object.values(fabricantData);

        if (data.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">Aucun fabricant trouvé</p>';
            return;
        }

        // Créer le canvas
        container.innerHTML = '<canvas id="fabricantChart" width="400" height="300"></canvas>';
        const canvas = document.getElementById('fabricantChart');
        const ctx = canvas.getContext('2d');

        // Détruire le graphique existant
        if (window.fabricantChartInstance) {
            window.fabricantChartInstance.destroy();
        }

        // Créer le graphique
        window.fabricantChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Nombre de réservoirs',
                    data: data,
                    backgroundColor: '#007bff',
                    borderColor: '#0056b3',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y', // Barres horizontales
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return `Fabricant: ${context[0].label}`;
                            },
                            label: function(context) {
                                return `${context.parsed.x} réservoir(s)`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        },
                        grid: {
                            color: '#e9ecef'
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        }
                    }
                },
                animation: {
                    duration: 1500,
                    easing: 'easeOutQuart'
                }
            }
        });

    } catch (error) {
        console.error('Erreur lors du rendu du graphique fabricant:', error);
        container.innerHTML = '<p class="text-danger text-center">Erreur de rendu du graphique</p>';
    }
}

/**
 * Graphique répartition par âge (Bar)
 */
function renderAgeChart() {
    const container = document.getElementById('chart_age');
    if (!container) return;

    const dataField = container.querySelector('input[name="chart_data_age"]');
    if (!dataField || !dataField.value) {
        container.innerHTML = '<p class="text-muted text-center">Aucune donnée disponible</p>';
        return;
    }

    try {
        const rawData = dataField.value.replace(/'/g, '"');
        const ageData = JSON.parse(rawData);

        const labels = Object.keys(ageData);
        const data = Object.values(ageData);

        if (data.every(val => val === 0)) {
            container.innerHTML = '<p class="text-muted text-center">Aucune donnée d\'âge disponible</p>';
            return;
        }

        // Créer le canvas
        container.innerHTML = '<canvas id="ageChart" width="400" height="200"></canvas>';
        const canvas = document.getElementById('ageChart');
        const ctx = canvas.getContext('2d');

        // Détruire le graphique existant
        if (window.ageChartInstance) {
            window.ageChartInstance.destroy();
        }

        // Couleurs dégradées selon l'âge
        const backgroundColors = [
            '#28a745', // 0-2 ans - Vert
            '#20c997', // 3-5 ans - Vert clair
            '#ffc107', // 6-10 ans - Jaune
            '#fd7e14', // 11-15 ans - Orange
            '#dc3545'  // 15+ ans - Rouge
        ];

        // Créer le graphique
        window.ageChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Nombre de réservoirs',
                    data: data,
                    backgroundColor: backgroundColors.slice(0, data.length),
                    borderColor: backgroundColors.slice(0, data.length).map(color => color.replace('0.8', '1')),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return `Âge: ${context[0].label}`;
                            },
                            label: function(context) {
                                return `${context.parsed.y} réservoir(s)`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxRotation: 45
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        },
                        grid: {
                            color: '#e9ecef'
                        }
                    }
                },
                animation: {
                    duration: 2000,
                    easing: 'easeOutBounce'
                }
            }
        });

    } catch (error) {
        console.error('Erreur lors du rendu du graphique âge:', error);
        container.innerHTML = '<p class="text-danger text-center">Erreur de rendu du graphique</p>';
    }
}

/**
 * Fonction utilitaire pour actualiser tous les graphiques
 */
function refreshDashboardCharts() {
    console.log('Actualisation des graphiques du dashboard...');

    // Délai pour laisser le temps à Odoo de recalculer les données
    setTimeout(() => {
        renderAllCharts();
    }, 300);
}

/**
 * Export pour utilisation dans d'autres scripts
 */
window.GPLDashboardCharts = {
    initialize: initializeCharts,
    refresh: refreshDashboardCharts,
    renderStatus: renderStatusChart,
    renderFabricant: renderFabricantChart,
    renderAge: renderAgeChart
};

// === INTÉGRATION AVEC ODOO ===
// Hook pour les actions Odoo qui pourraient modifier les données
if (typeof odoo !== 'undefined' && odoo.define) {
    odoo.define('gpl_reservoir.dashboard_charts', function (require) {
        'use strict';

        var core = require('web.core');
        var FormController = require('web.FormController');

        // Étendre le contrôleur de formulaire pour actualiser les graphiques
        FormController.include({
            _onFieldChanged: function () {
                this._super.apply(this, arguments);

                // Si on est sur le dashboard des réservoirs
                if (this.modelName === 'gpl.reservoir.dashboard') {
                    refreshDashboardCharts();
                }
            }
        });

        return {
            initializeCharts: initializeCharts,
            refreshDashboardCharts: refreshDashboardCharts
        };
    });
}

console.log('GPL Dashboard Charts - Module JavaScript chargé');
