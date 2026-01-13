# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """
    Migre les données de gpl_company_name et gpl_company_license
    depuis ir.config_parameter vers res.company
    """
    _logger.info("Migration des paramètres GPL vers res.company...")

    try:
        # Récupérer les paramètres existants
        cr.execute("""
            SELECT key, value
            FROM ir_config_parameter
            WHERE key IN ('cpss_gpl.company_name', 'cpss_gpl.company_license')
        """)
        params = dict(cr.fetchall())

        if not params:
            _logger.info("Aucun paramètre GPL à migrer")
            return

        company_name = params.get('cpss_gpl.company_name', '')
        company_license = params.get('cpss_gpl.company_license', '')

        if company_name or company_license:
            # Mettre à jour toutes les compagnies
            cr.execute("""
                UPDATE res_company
                SET gpl_company_name = %s,
                    gpl_company_license = %s
                WHERE gpl_company_name IS NULL
                   OR gpl_company_license IS NULL
            """, (company_name, company_license))

            _logger.info(
                f"Migration GPL terminée: {cr.rowcount} compagnie(s) mise(s) à jour - "
                f"Nom: {company_name}, Agrément: {company_license}"
            )

            # Supprimer les anciens paramètres
            cr.execute("""
                DELETE FROM ir_config_parameter
                WHERE key IN ('cpss_gpl.company_name', 'cpss_gpl.company_license')
            """)
            _logger.info("Anciens paramètres GPL supprimés")
        else:
            _logger.info("Aucune valeur GPL à migrer")

    except Exception as e:
        _logger.error(f"Erreur lors de la migration GPL: {str(e)}")
        # Ne pas bloquer l'installation en cas d'erreur
        pass
