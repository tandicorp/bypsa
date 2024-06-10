# coding: utf-8
from odoo import api, fields, models

_FORMAT_TYPES = [('pch', 'Pichincha'),
                 #('int', 'Internacional'), #En un futuro
                 #('pac', u'Pacifico'), #En un futuro
                 ('bol', 'Bolivariano'),
                 #('cash', 'Cash Management') #En un futuro
                 ]


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _default_outbound_payment_methods(self):
        res = super()._default_outbound_payment_methods()
        if self._is_payment_method_available("l10n_ec_format"):
            res |= self.env.ref('l10n_ec_payment_bank_format.account_payment_method_ec_format')
        return res

    l10n_ec_format_type = fields.Selection(
        _FORMAT_TYPES,
        string="Tipos de formato de bancos"
    )

