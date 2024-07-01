# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError
from odoo.addons.broker_do.models.sale_order import _branches_no_taxes, _module


class WizardPresettlement(models.TransientModel):
    _name = 'wizard.presettlement'

    invoice_id = fields.Many2one(
        'account.move',
        string='Pago de cuotas'
    )
    move_type = fields.Selection([
        ("out_invoice", "Facturas Cliente"),
        ("out_refund", "Notas de Crédito Cliente"),
    ],
        string="Tipo de Factura"
    )
    type = fields.Selection(
        selection='_list_types',
        string="Tipo",
        default="both",
        required=True
    )
    presettlement_ids = fields.Many2many(
        'broker.presettlement',
        'wizard_presettlement_rel',
        'wizard_id',
        'presettlement_id',
        string='Preliquidaciones',
    )
    commission_ids = fields.Many2many(
        'sale.order.line',
        'wizard_commission_rel',
        'wizard_id',
        'sale_order_line_id',
        store=True,
        compute='_compute_commission_ids',
        inverse='_set_commission_ids',
        string='Comisiones',
    )
    branch = fields.Selection([
        ("life", "VIDA"),
        ("general", "GENERALES"),
    ], string="Ramo",
        default="general",
        required=True
    )

    @api.model
    def _list_types(self):
        context = self.env.context.copy()
        if context.get('default_move_type') == 'out_invoice':
            list_type = [("positive", "Positivas"),
                         ("both", "Ambas")]
        else:
            list_type = [("negative", "Negativas"),
                         ("both", "Ambas")]
        return list_type

    @api.depends('presettlement_ids', "type", "branch")
    def _compute_commission_ids(self):
        for wizard_id in self:
            branch_no_taxes = [self.env.ref(_module + '.' + branch).id for branch in
                               _branches_no_taxes]
            if self.branch == 'general':
                sol_ids = wizard_id.presettlement_ids.mapped('presettlement_line_ids.commission_id').filtered(
                    lambda
                        x: x.status_commission == 'to_receive' and x.order_id.contract_id.branch_id.id not in branch_no_taxes)
            else:
                sol_ids = wizard_id.presettlement_ids.mapped('presettlement_line_ids.commission_id').filtered(
                    lambda
                        x: x.status_commission == 'to_receive' and x.order_id.contract_id.branch_id.id in branch_no_taxes)
            if self.type == 'positive':
                sol_ids = sol_ids.filtered(lambda com: com.price_subtotal >= 0)
            elif self.type == 'negative':
                sol_ids = sol_ids.filtered(lambda com: com.price_subtotal < 0)
            wizard_id.commission_ids = [fields.Command.set(sol_ids.ids)]

    def _set_commission_ids(self):
        commission_ids = self.commission_ids
        self.commission_ids = commission_ids

    def import_data(self):
        invoice_line_vals = []
        value_total = sum(self.commission_ids.mapped("price_subtotal"))
        if self.move_type == 'out_invoice' and value_total < 0:
            raise ValidationError("Error el valor total de la factura debe ser mayor o igual a cero")
        if self.move_type == 'out_refund' and value_total >= 0:
            raise ValidationError("El valor total de las comisiones debe ser menor a cero")
        for commission_id in self.commission_ids:
            invoice_line_vals.append(
                Command.create(
                    commission_id._prepare_invoice_line(move_id=self.invoice_id.id,
                                                        quantity=commission_id.product_uom_qty,
                                                        price_unit=abs(commission_id.price_unit),
                                                        name=commission_id.name + ':PRELIQ:' + ','.join(
                                                            commission_id.presettlement_line_ids.mapped(
                                                                'presettlement_id').filtered(
                                                                lambda x: x.id in self.presettlement_ids.ids).mapped(
                                                                'name'))
                                                        )
                )
            )
            self.invoice_id.invoice_line_ids.unlink()
            self.invoice_id.invoice_line_ids = invoice_line_vals
