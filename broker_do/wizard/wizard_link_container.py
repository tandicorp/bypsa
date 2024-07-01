# -*- coding: utf-8 -*-
from odoo import fields, models, api


class WizardLinkContainer(models.TransientModel):
    _name = 'wizard.link.container'

    client_id = fields.Many2one(
        'res.partner',
        string='Cliente'
    )
    insurer_id = fields.Many2one(
        'res.partner',
        string='Aseguradora'
    )
    branch_id = fields.Many2one(
        'broker.branch',
        string='Ramo'
    )
    contract_ids = fields.Many2many(
        'broker.contract',
        'link_container_contract_rel',
        'wizard_id',
        'contract_id',
        string=u'Contratos'
    )
    container_id = fields.Many2one(
        'broker.contract.container',
        string=u'Pólizas Maestras',
    )

    def set_container_data(self):
        self.contract_ids.write({'container_id': self.container_id.id})
