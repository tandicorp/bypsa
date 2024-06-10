# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BrokerBranch(models.Model):
    _name = 'broker.branch'

    name = fields.Char(
        'Nombre'
    )
    code = fields.Char(
        u'Código'
    )
    code_super_cias = fields.Char(
        u'Código Super cías.'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto de venta de comisiones'
    )
    product_reversal_id = fields.Many2one(
        'product.product',
        string=u'Producto de nota de crédito de comisiones'
    )
    coverage_groups = fields.Many2many(
        'coverage.group',
        string="Grupos de Cobertura"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for this in vals_list:
            if 'name' in this:
                this['name'] = this['name'].upper()
        return super(BrokerBranch, self).create(vals_list)

    def write(self, vals):
        if 'name' in vals:
            vals['name'] = vals['name'].upper()
        return super(BrokerBranch, self).write(vals)
