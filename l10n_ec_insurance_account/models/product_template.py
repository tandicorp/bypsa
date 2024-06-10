# -*- coding: utf-8 -*-
from odoo import models, api, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_contribution = fields.Boolean(
        string="Ecuador Contribución",
        default=False
    )
    contrib_percent = fields.Float(
        string="Porcentaje de contribución"
    )
    contribution_product_ids = fields.Many2many(
        "product.template",
        "product_contribution_rel",
        "product_id",
        "contribution_id",
        string="Contribuciones",
        domain=[('is_contribution', '=', True)]
    )
