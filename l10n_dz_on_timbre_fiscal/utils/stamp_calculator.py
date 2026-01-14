

class StampCalculator:
    def __init__(self, env):
        self.env = env

    def calculate(self, montant):
        res = {}
        montant_timbre = 0.0
        droit = 0.0

        # Ajustement par tranches de 100 DA
        tranche_arrondie = ((montant + 99) // 100) * 100  # arrondir vers le haut

        if montant <= 30_000:
            droit = tranche_arrondie * 0.01
        elif montant <= 100_000:
            droit = tranche_arrondie * 0.015
        else:
            droit = tranche_arrondie * 0.02

        # Minimum de 5 DA
        if montant > 300:
            montant_timbre = max(int(droit), 5)

        res['timbre'] = montant_timbre
        res['amount_timbre'] = montant + montant_timbre

        return res

    def GetStampAccount(self, move_type):
        if move_type in ('out_invoice', 'out_refund'):
            return self.env['ir.config_parameter'].sudo().get_param('l10n_dz_on_timbre_fiscal.stamp_sale_account_id')
        if move_type in ('in_invoice', 'in_refund'):
            return self.env['ir.config_parameter'].sudo().get_param('l10n_dz_on_timbre_fiscal.stamp_purchase_account_id')

        return False