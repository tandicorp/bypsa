# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command


class WizardContractContainer(models.TransientModel):
    _name = 'wizard.contract.object'

    contract_id = fields.Many2one(
        'broker.contract',
        string=u'Contrato'
    )
    movement_id = fields.Many2one(
        'sale.order',
        string=u'Movimiento'
    )
    movement_contract_object_ids = fields.Many2many(
        'broker.movement.object',
        'wizard_movement_contract_object_rel',
        'wizard_id',
        'contract_object_id',
        string=u'Items del movimiento',
    )
    contract_object_ids = fields.Many2many(
        'broker.movement.object',
        'wizard_contract_object_rel',
        'wizard_id',
        'object_id',
        domain="[('contract_id','=',contract_id),('id','not in', movement_contract_object_ids)]",
        string=u'Items del contrato',
    )

    def set_object_data(self):
        for object_id in self.contract_object_ids:
            object_id.copy({
                'contract_id': False,
                'movement_id': self.movement_id.id,
                'contract_object_id': object_id.id
            })
