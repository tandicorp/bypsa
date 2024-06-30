# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.tools import float_round

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _description = 'Comisiones de Anexos'

    name = fields.Char(
        string='Nombre',
        store=True,
        compute='_compute_name'
    )
    contract_name = fields.Char(
        u'No. de contrato',
        compute='_compute_contract_name'
    )
    amount_fee = fields.Float(
        string="Prima Neta",
    )
    percentage_fee = fields.Float(
        string="% Prima Neta"
    )
    percentage_commission = fields.Float(
        string="% Comisión"
    )
    amount_subtotal = fields.Char(
        string=u'Valor de comisión',
    )
    fee_id = fields.Many2one(
        'sale.order.fee',
        string='Cuota que libera comisión'
    )
    status_commission = fields.Selection(
        [
            ('to_release', 'Por liberar'),
            ('to_receive', 'Por cobrar'),
            ('received', 'Cobrada'),
        ],
        u'Estado',
        default='to_release'
    )
    presettlement_line_ids = fields.One2many(
        'broker.presettlement.line',
        'commission_id',
        string='Líneas de preliquidación'
    )
    amount_invoiced = fields.Float(
        'Valor facturado',
        compute='_compute_amount_invoiced'
    )
    balance_commission = fields.Float(
        'Saldo de comisión',
        store=True,
        compute='_compute_amount_invoiced'
    )
    period_id = fields.Many2one(
        related='fee_id.period_id',
        string="Periodo"
    )

    @api.depends('order_id.contract_id.business_id', 'order_id.contract_id.user_id.work_location_id')
    def _compute_analytic_distribution(self):
        super(SaleOrderLine, self)._compute_analytic_distribution()
        for line in self:
            if not line.display_type:
                distribution = line.env['account.analytic.distribution.model']._get_distribution({
                    "business_id": line.order_id.contract_id.business_id.id,
                    "company_id": line.company_id.id,
                })
                distribution.update(line.env['account.analytic.distribution.model']._get_distribution({
                    "work_location_id": line.order_id.user_id.work_location_id.id,
                    "company_id": line.company_id.id,
                }))
                analytic_distribution = line.analytic_distribution and line.analytic_distribution.copy() or {}
                analytic_distribution.update(distribution)
                line.analytic_distribution = analytic_distribution or line.analytic_distribution

    def _compute_contract_name(self):
        for record in self:
            record.contract_name = record.order_id.contract_id.name

    @api.depends('invoice_lines', 'invoice_lines.price_subtotal', 'amount_subtotal', 'status_commission')
    def _compute_amount_invoiced(self):
        for record in self:
            record.amount_invoiced = sum(record.invoice_lines.mapped('price_subtotal'))
            record.balance_commission = record.price_subtotal - record.amount_invoiced

    @api.depends('sequence')
    def _compute_name(self):
        for record in self:
            if record.order_id.contract_id and record.order_id.contract_id.client_id:
                record.name = record.order_id.contract_id.client_id.name + '/ ' + ':'.join(
                    ['P.NETA', str(record.order_id.amount_fee) or '',
                     str(float_round((record.order_id.commission_percentage or 0) * 100, 2)) + '%'])

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        res = super(SaleOrderLine, self)._compute_amount()
        for line in self:
            line.update({
                'amount_subtotal': line.price_subtotal,
            })
        return res

    def action_receive_commission(self):
        self.status_commission = 'to_receive'

    def action_to_release_commission(self):
        self.status_commission = 'to_release'

    @api.onchange('percentage_commission')
    def _depends_percentage_commission(self):
        self.price_unit = self.amount_fee * self.percentage_commission
