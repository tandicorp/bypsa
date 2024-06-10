from odoo import models, api, fields


class BrokerMovementStakeholder(models.Model):
    _name = 'broker.movement.stakeholder'

    role = fields.Selection(
        [
            ('contractor', 'Contratante'),
            ('titular', 'Titular'),
            ('dependent', 'Dependiente'),
            ('insured', 'Asegurado'),
            ('beneficiary', 'Beneficiario'),
            ('payer', 'Pagador'),
            ('biller', 'Facturador')
        ],
        string='Rol'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Persona"
    )
    movement_id = fields.Many2one(
        'sale.order',
        string="Anexo"
    )
