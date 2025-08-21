/** @odoo-module **/

console.log("[CPSS GPL] Widget Odoo - Version sans ID hardcodé");

setTimeout(function() {
    console.log("[CPSS GPL] Installation interception pour widget Odoo");

    document.addEventListener('click', function(e) {
        var url = window.location.href;

        if (url.includes('gpl.vehicle') && url.includes('calendar')) {
            var isEmptyCalendarArea = e.target.closest('.fc-view') ||
                                    e.target.classList.contains('fc-daygrid-day') ||
                                    e.target.classList.contains('fc-timegrid-slot') ||
                                    e.target.className.includes('fc-day') ||
                                    e.target.className.includes('fc-timegrid') ||
                                    e.target.className.includes('fc-daygrid');

            var isExistingEvent = e.target.closest('.fc-event') ||
                                e.target.classList.contains('fc-event');

            if (isEmptyCalendarArea && !isExistingEvent) {
                console.log("[CPSS GPL] ✅ Ouverture widget Odoo");

                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();

                setTimeout(function() {
                    openVehicleWizard(e);
                }, 50);

                return false;
            }
        }
    }, true);

    function openVehicleWizard(event) {
        console.log("[CPSS GPL] 🧙 Ouverture du wizard véhicule");

        // Extraire la date du clic
        var clickDate = extractDateFromClick(event);
        var isoDate = clickDate.toISOString();

        console.log("[CPSS GPL] Date extraite:", isoDate);

        // MÉTHODE 1: Appel AJAX pour créer et ouvrir le wizard
        createAndOpenWizard(isoDate);
    }

    function createAndOpenWizard(isoDate) {
        console.log("[CPSS GPL] Création du wizard via AJAX");

        // Créer le wizard via un appel AJAX
        fetch('/web/dataset/call_kw', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: {
                    model: 'vehicle.appointment.wizard',
                    method: 'create',
                    args: [{
                        appointment_date: isoDate
                    }],
                    kwargs: {}
                },
                id: Math.floor(Math.random() * 1000000)
            })
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.result) {
                var wizardId = data.result;
                console.log("[CPSS GPL] Wizard créé avec ID:", wizardId);

                // Ouvrir le wizard créé
                openWizardById(wizardId);
            } else {
                console.error("[CPSS GPL] Erreur création wizard:", data);
                // Fallback vers création directe de véhicule
                fallbackToVehicleCreation(isoDate);
            }
        })
        .catch(function(error) {
            console.error('[CPSS GPL] Erreur AJAX:', error);
            // Fallback vers création directe de véhicule
            fallbackToVehicleCreation(isoDate);
        });
    }

    function openWizardById(wizardId) {
        console.log("[CPSS GPL] Ouverture wizard ID:", wizardId);

        // Construire l'URL pour ouvrir le wizard spécifique
        var wizardUrl = '/web#model=vehicle.appointment.wizard&view_type=form&id=' + wizardId;

        console.log("[CPSS GPL] Redirection vers:", wizardUrl);
        window.location.href = wizardUrl;
    }

    function fallbackToVehicleCreation(isoDate) {
        console.log("[CPSS GPL] Fallback: Création directe de véhicule");

        // En cas d'échec, rediriger vers la création de véhicule directement
        var vehicleUrl = '/web#model=gpl.vehicle&view_type=form';
        vehicleUrl += '&context=%7B%22default_appointment_date%22%3A%22' + encodeURIComponent(isoDate) + '%22%2C%22default_next_service_type%22%3A%22installation%22%7D';

        console.log("[CPSS GPL] Fallback vers:", vehicleUrl);
        window.location.href = vehicleUrl;
    }

    function extractDateFromClick(event) {
        var target = event.target;
        var clickDate = new Date();

        // Essayer d'extraire la date des attributs DOM
        var dateAttr = target.getAttribute('data-date') ||
                      target.getAttribute('data-day') ||
                      target.closest('[data-date]')?.getAttribute('data-date') ||
                      target.closest('[data-day]')?.getAttribute('data-day');

        if (dateAttr) {
            try {
                var parsedDate = new Date(dateAttr);
                if (!isNaN(parsedDate.getTime())) {
                    clickDate = parsedDate;
                    console.log("[CPSS GPL] Date extraite des attributs:", clickDate);
                }
            } catch (e) {
                console.log("[CPSS GPL] Erreur parsing date attribut:", e);
            }
        }

        // Essayer d'extraire l'heure pour les vues horaires
        var timeSlot = target.closest('.fc-timegrid-slot');
        if (timeSlot) {
            var timeAttr = timeSlot.getAttribute('data-time');
            if (timeAttr) {
                try {
                    var timeComponents = timeAttr.split(':');
                    if (timeComponents.length >= 2) {
                        clickDate.setHours(parseInt(timeComponents[0]), parseInt(timeComponents[1]), 0, 0);
                        console.log("[CPSS GPL] Heure extraite:", clickDate);
                    }
                } catch (e) {
                    console.log("[CPSS GPL] Erreur parsing heure:", e);
                }
            }
        }

        // Si on est dans une vue mensuelle, essayer d'extraire le jour
        var dayCell = target.closest('.fc-daygrid-day');
        if (dayCell) {
            var dayAttr = dayCell.getAttribute('data-date');
            if (dayAttr) {
                try {
                    var dayDate = new Date(dayAttr);
                    if (!isNaN(dayDate.getTime())) {
                        // Garder l'heure actuelle mais changer le jour
                        var now = new Date();
                        clickDate = new Date(dayDate.getFullYear(), dayDate.getMonth(), dayDate.getDate(),
                                           now.getHours(), now.getMinutes(), 0, 0);
                        console.log("[CPSS GPL] Date jour extraite:", clickDate);
                    }
                } catch (e) {
                    console.log("[CPSS GPL] Erreur parsing jour:", e);
                }
            }
        }

        // Arrondir à la demi-heure la plus proche
        var minutes = clickDate.getMinutes();
        var roundedMinutes = minutes < 30 ? 0 : 30;
        clickDate.setMinutes(roundedMinutes, 0, 0);

        console.log("[CPSS GPL] Date finale:", clickDate);
        return clickDate;
    }

    console.log("[CPSS GPL] ✅ Widget Odoo configuré sans ID hardcodé!");

}, 2000);

console.log("[CPSS GPL] 🚀 Module widget Odoo chargé (version AJAX)!");
