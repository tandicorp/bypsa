# coding: utf-8
from odoo import api, fields, models


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    l10n_ec_account_type = fields.Selection(
        [('AHO', 'Ahorros'),('CTE', 'Corriente')],
        string='Tipo Cuenta',
        default='AHO')