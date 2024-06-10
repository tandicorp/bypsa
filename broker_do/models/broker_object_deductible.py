# -*- coding: utf-8 -*-

from odoo import models, api, fields


class BrokerObjectDeductibleTemplate(models.Model):
    _name = "broker.object.deductible.template"
    _description = "Plantilla de deducibles"

    name = fields.Char(
        string="Plantilla de deducibles"
    )


class BrokerObjectDeductible(models.Model):
    _name = "broker.object.deductible"
    _description = "Deducibles"

    name = fields.Char(
        string="Texto del deducible"
    )
    object_id = fields.Many2one(
        'broker.movement.object',
        string="Contrato"
    )
    template_id = fields.Many2one(
        'broker.object.deductible.template',
        string="Plantilla de deducible"
    )

    @api.onchange('template_id')
    def onchange_template_id(self):
        if self.template_id:
            self.name = self.template_id.name
