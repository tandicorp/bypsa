# -*- coding: utf-8 -*-
from odoo import api, fields, models

class AccountInvoice(models.Model):
    _inherit = 'account.move'

    policy = fields.Char(
        'Contrato',
    )

    def _reverse_moves(self, default_values_list=None, cancel=False):
        reverse_moves = super(AccountInvoice, self)._reverse_moves(default_values_list, cancel)
        for move in reverse_moves:
            for invoice_line in move.invoice_line_ids:
                branch_id = self.env['broker.branch'].search([
                    ('product_id', '=', invoice_line.product_id.id)
                ])
                invoice_line.write({
                    'product_id': branch_id.product_reversal_id.id or invoice_line.product_id.id,
                    'quantity': 1,
                    'price_unit': invoice_line.price_unit,
                })
        return reverse_moves

    def action_load_commission(self):
        self.ensure_one()
        template = self.env.ref('broker_do.broker_presettlement_wizard_form')
        return {
            'name': 'Escoja su archivo',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'broker.presettlement.wizard',
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'new',
        }

    def action_load_presettlement(self):
        self.ensure_one()
        template = self.env.ref('broker_do.wizard_presettlement_form')
        return {
            'name': 'Preliquidaciones',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.presettlement',
            'context': {
                'default_invoice_id': self.id,
                'default_move_type': self.move_type,
                'default_presettlement_ids': [fields.Command.set(self.env['broker.presettlement'].search([
                    ('insurer_id', '=', self.partner_id.id), ('status', '=', 'validated')]).ids)]
            },
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'new',
        }