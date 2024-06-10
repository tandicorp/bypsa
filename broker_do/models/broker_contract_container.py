# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command


class BrokerContractContainer(models.Model):
    _name = 'broker.contract.container'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        'Nombre',
        store=True,
        compute='_compute_name'
    )
    container_num = fields.Char(
        'Número de contrato'
    )
    branch_id = fields.Many2one(
        'broker.branch',
        'Ramo',
    )
    insurer_id = fields.Many2one(
        'res.partner',
        'Aseguradora'
    )
    client_id = fields.Many2one(
        'res.partner',
        'Cliente'
    )
    contract_ids = fields.One2many(
        'broker.contract',
        'container_id',
        string='Contratos',
    )

    @api.depends("branch_id", "container_num")
    def _compute_name(self):
        for this in self:
            branch_code = this.branch_id and this.branch_id.code or ""
            container_num = this.container_num or ''
            this.name = " - ".join([branch_code, container_num])
