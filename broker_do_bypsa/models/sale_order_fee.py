from odoo import fields, models, api


class SaleOrderFee(models.Model):
    _inherit = 'sale.order.fee'

    amount_insured = fields.Float(
        string='Monto Asegurado',
    )
    value_depreciated = fields.Float(
        string='Valor Depreciado',
    )
