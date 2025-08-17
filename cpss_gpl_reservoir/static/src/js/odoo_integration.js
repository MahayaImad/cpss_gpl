/**
 * GPL Reservoir Dashboard - Intégration Odoo 17
 * Version optimisée pour le framework Odoo
 */

odoo.define('cpss_gpl_reservoir.dashboard_charts', function (require) {
    'use strict';

    var FormController = require('web.FormController');
    var FormRenderer = require('web.FormRenderer');
    var core = require('web.core');
    var session = require('web.session');

    // === EXTENSION DU RENDERER POUR LES GRAPHIQUES ===
    var GPLDashboardRenderer = FormRenderer.extend({

        /**
         * Appelé après le rendu du formulaire
         */
        _renderView: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (self.state.model === 'gpl.reservoir.dashboard') {
                    self._initializeGPLCharts();
                }
            });
        },

        /**
         * Initialise les graphiques GPL
         */
        _initializeGPLCharts: function () {
            var self = this;

            // Attendre que le DOM soit stable
            setTimeout(function () {
                self._loadChartLibrary().then(function () {
                    self._renderAllCharts();
                });
            }, 500);
        },

        /**
         * Charge Chart.js si nécessaire
         */
        _loadChartLibrary: function () {
            return new Promise(function (resolve, reject) {
                if (typeof Chart !== 'undefined') {
                    resolve();
                    return;
                }

                var script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        },

        /**
         * Rend tous les graphiques
         */
        _renderAllCharts: function () {
            this._renderStatusChart();
            this._renderFabricantChart();
            this._renderAgeChart();
        },

        /**
         * Graphique des statuts (Doughnut)
         */
        _renderStatusChart: function () {
            var container = this.$('#chart_status')[0];
            if (!container) return;

            var dataField = this.$('input[name="chart_data_status"]')[0];
            if (!dataField || !dataField.value) {
                container.innerHTML = '<div class="chart-no-data">Aucune donnée de statut disponible</div>';
                return;
            }

            try {
                var rawData = dataField.value.replace(/'/g, '"');
                var statusData = JSON.parse(rawData);

                var chartData = this._prepareStatusData(statusData);

                if (chartData.labels.length === 0) {
                    container.innerHTML = '<div class="chart-no-data">Aucun réservoir trouvé</div>';
                    return;
                }

                this._createChart(container, 'statusChart', {
                    type: 'doughnut',
                    data: {
                        labels: chartData.labels,
                        datasets: [{
                            data: chartData.data,
                            backgroundColor: chartData.colors,
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: this._getStatusChartOptions()
                });

            } catch (error) {
                console.error('Erreur graphique statut:', error);
                container.innerHTML = '<div class="chart-error">Erreur de rendu du graphique</div>';
            }
        },

        /**
         * Graphique des fabricants (Bar horizontal)
         */
        _renderFabricantChart: function () {
            var container = this.$('#chart_fabricant')[0];
            if (!container) return;

            var dataField = this.$('input[name="chart_data_fabricant"]')[0];
            if (!dataField || !dataField.value) {
                container.innerHTML = '<div class="chart-no-data">Aucune donnée de fabricant disponible</div>';
                return;
            }

            try {
                var rawData = dataField.value.replace(/'/g, '"');
                var fabricantData = JSON.parse(rawData);

                var labels = Object.keys(fabricantData);
                var data = Object.values(fabricantData);

                if (data.length === 0) {
                    container.innerHTML = '<div class="chart-no-data">Aucun fabricant trouvé</div>';
                    return;
                }

                this._createChart(container, 'fabricantChart', {
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
                    options: this._getFabricantChartOptions()
                });

            } catch (error) {
                console.error('Erreur graphique fabricant:', error);
                container.innerHTML = '<div class="chart-error">Erreur de rendu du graphique</div>';
            }
        },

        /**
         * Graphique des âges (Bar)
         */
        _renderAgeChart: function () {
            var container = this.$('#chart_age')[0];
            if (!container) return;

            var dataField = this.$('input[name="chart_data_age"]')[0];
            if (!dataField || !dataField.value) {
                container.innerHTML = '<div class="chart-no-data">Aucune donnée d\'âge disponible</div>';
                return;
            }

            try {
                var rawData = dataField.value.replace(/'/g, '"');
                var ageData = JSON.parse(rawData);

                var labels = Object.keys(ageData);
                var data = Object.values(ageData);

                if (data.every(function(val) { return val === 0; })) {
                    container.innerHTML = '<div class="chart-no-data">Aucune donnée d\'âge disponible</div>';
                    return;
                }

                var backgroundColors = ['#28a745', '#20c997', '#ffc107', '#fd7e14', '#dc3545'];

                this._createChart(container, 'ageChart', {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Nombre de réservoirs',
                            data: data,
                            backgroundColor: backgroundColors.slice(0, data.length),
                            borderColor: backgroundColors.slice(0, data.length),
                            borderWidth: 1
                        }]
                    },
                    options: this._getAgeChartOptions()
                });

            } catch (error) {
                console.error('Erreur graphique âge:', error);
                container.innerHTML = '<div class="chart-error">Erreur de rendu du graphique</div>';
            }
        },

        /**
         * Crée un graphique Chart.js
         */
        _createChart: function (container, chartId, config) {
            // Nettoyer le container
            container.innerHTML = '<canvas id="' + chartId + '" width="400" height="300"></canvas>';

            var canvas = document.getElementById(chartId);
            var ctx = canvas.getContext('2d');

            // Détruire l'instance existante si elle existe
            if (window[chartId + 'Instance']) {
                window[chartId + 'Instance'].destroy();
            }

            // Créer le nouveau graphique
            window[chartId + 'Instance'] = new Chart(ctx, config);

            // Ajouter l'animation de fade-in
            container.classList.add('chart-fade-in');
        },

        /**
         * Prépare les données pour le graphique de statut
         */
        _prepareStatusData: function (statusData) {
            var labels = [];
            var data = [];
            var colors = [];

            var statusConfig = {
                'valid': { label: 'Valides', color: '#28a745' },
                'expiring_soon': { label: 'Expirent bientôt', color: '#ffc107' },
                'expired': { label: 'Expirés', color: '#dc3545' },
                'test_required': { label: 'Test requis', color: '#fd7e14' },
                'too_old': { label: 'Trop anciens', color: '#6f42c1' }
            };

            Object.keys(statusData).forEach(function (status) {
                var count = statusData[status];
                if (count > 0) {
                    var config = statusConfig[status] || { label: status, color: '#6c757d' };
                    labels.push(config.label + ' (' + count + ')');
                    data.push(count);
                    colors.push(config.color);
                }
            });

            return { labels: labels, data: data, colors: colors };
        },

        /**
         * Options pour le graphique de statut
         */
        _getStatusChartOptions: function () {
            return {
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
                                var total = context.dataset.data.reduce(function(a, b) { return a + b; }, 0);
                                var percentage = ((context.parsed / total) * 100).toFixed(1);
                                return context.label + ': ' + percentage + '%';
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            };
        },

        /**
         * Options pour le graphique de fabricant
         */
        _getFabricantChartOptions: function () {
            return {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return 'Fabricant: ' + context[0].label;
                            },
                            label: function(context) {
                                return context.parsed.x + ' réservoir(s)';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 },
                        grid: { color: '#e9ecef' }
                    },
                    y: { grid: { display: false } }
                },
                animation: {
                    duration: 1500,
                    easing: 'easeOutQuart'
                }
            };
        },

        /**
         * Options pour le graphique d'âge
         */
        _getAgeChartOptions: function () {
            return {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return 'Âge: ' + context[0].label;
                            },
                            label: function(context) {
                                return context.parsed.y + ' réservoir(s)';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { maxRotation: 45 }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 },
                        grid: { color: '#e9ecef' }
                    }
                },
                animation: {
                    duration: 2000,
                    easing: 'easeOutBounce'
                }
            };
        }
    });

    // === EXTENSION DU CONTROLLER ===
    var GPLDashboardController = FormController.extend({

        /**
         * Actualise les graphiques après changement de filtre
         */
        _onFieldChanged: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (self.modelName === 'gpl.reservoir.dashboard') {
                    // Délai pour laisser Odoo recalculer les données
                    setTimeout(function () {
                        if (self.renderer._renderAllCharts) {
                            self.renderer._renderAllCharts();
                        }
                    }, 300);
                }
            });
        },

        /**
         * Actualise après sauvegarde
         */
        _onSave: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (self.modelName === 'gpl.reservoir.dashboard') {
                    setTimeout(function () {
                        if (self.renderer._renderAllCharts) {
                            self.renderer._renderAllCharts();
                        }
                    }, 500);
                }
            });
        }
    });

    // === ENREGISTREMENT DES COMPOSANTS ===
    return {
        GPLDashboardRenderer: GPLDashboardRenderer,
        GPLDashboardController: GPLDashboardController
    };
});

// === FONCTION GLOBALE POUR DEBUG ===
window.debugGPLCharts = function() {
    console.log('=== DEBUG GPL CHARTS ===');
    console.log('Chart.js disponible:', typeof Chart !== 'undefined');
    console.log('Conteneurs graphiques:', {
        status: !!document.getElementById('chart_status'),
        fabricant: !!document.getElementById('chart_fabricant'),
        age: !!document.getElementById('chart_age')
    });
    console.log('Instances Chart.js:', {
        status: !!window.statusChartInstance,
        fabricant: !!window.fabricantChartInstance,
        age: !!window.ageChartInstance
    });
};
