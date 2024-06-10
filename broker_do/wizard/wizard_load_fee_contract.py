# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.tools.float_utils import float_round, float_compare, float_is_zero


class WizardContract(models.TransientModel):
    _name = 'wizard.load.fee.contract'

    payment_id = fields.Many2one(
        'fee.payment',
        string='Pago de cuotas'
    )
    contract_ids = fields.Many2many(
        'broker.contract',
        'wizard_contract_rel',
        'wizard_id',
        'contract_id',
        string='Contratos',
    )
    fee_order_ids = fields.Many2many(
        'broker.contract.fee',
        'wizard_fee_rel',
        'wizard_id',
        'fee_order_id',
        string='Cuotas de contratos',
    )

    def action_load_fee(self):
        self.fee_order_ids = [fields.Command.clear()]
        self.contract_ids = [fields.Command.set(self.env['broker.contract'].search(
            [('client_id', '=', self.payment_id.partner_id.id)]).ids)]
        commission_to_link = []
        if self.contract_ids:
            fee_order_ids = self.contract_ids.mapped('contract_fee_ids').filtered(
                lambda x: x.status_fee == 'no_payment')[:5].sorted(
                lambda x: x.provisional_payment_date)
            commission_not_paid = fee_order_ids
            for commission_id in commission_not_paid:
                commission_to_link.append(commission_id.id)
        return {
            'type': 'ir.actions.act_window',
            'context': {'default_payment_id': self.payment_id.id,
                        'default_contract_ids': [(6, 0, self.contract_ids.ids), ],
                        'default_fee_order_ids': [(6, 0, commission_to_link), ],
                        },
            'res_model': 'wizard.load.fee.contract',
            'view_mode': 'form',
            'target': 'new',
        }

    def import_data(self):
        decimal_places = self.env.company.currency_id.decimal_places
        payment_vals = []
        for fee_id in self.fee_order_ids.sorted(lambda x: x.provisional_payment_date):
            commission_amount_paid_due = fee_id.balance_due
            payment_vals.append({
                'fee_id': fee_id.id,
                'amount_paid': float_round(commission_amount_paid_due, decimal_places)
            })
        self.payment_id.sale_fee_payment_ids = [fields.Command.create(x) for x in payment_vals]
