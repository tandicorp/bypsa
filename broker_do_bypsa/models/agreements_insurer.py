from odoo import fields, models, api
from odoo.addons.broker_do.models.agreements_insurer import is_numeric_value


class AgreementsInsurer(models.Model):
    _inherit = "agreements.insurer"

    def get_amount_fee_depreciation(self, amount_insured):
        amount_fee = 0
        value_not_depreciated = self.agreements_line_ids.filtered(
            lambda line: line.is_amount_fee and line.is_limit and is_numeric_value(line.value)).mapped("value")
        if value_not_depreciated:
            amount_fee += sum([float(val) for val in value_not_depreciated])
        for dep in self.agreements_line_ids.filtered(lambda line: line.is_amount_fee and not line.is_limit):
            value = amount_insured * float(dep.rate)/100
            amount_fee += value
        return amount_fee
