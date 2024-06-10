from odoo import fields, models, api


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    receive_commission = fields.Boolean(
        string="Recibe Comisiones?"
    )
