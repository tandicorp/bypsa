from odoo import models, api, fields


class CoverageGroup(models.Model):
    _name = 'coverage.group'

    name = fields.Char(
        string='Nombre',
        required=True
    )
    code = fields.Char(
        string='Código',
        required=True
    )
