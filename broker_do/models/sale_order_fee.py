# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round, float_compare


class SaleOrderFee(models.Model):
    _name = 'sale.order.fee'
    _description = 'Comisiones de Anexos'

    name = fields.Char(
        string='Nombre',
        store=True,
        compute='_compute_name'
    )
    period_id = fields.Many2one(
        "broker.contract.period",
        string="Periodo"
    )
    period_date_from = fields.Date(
        string="Desde",
        related="period_id.date_from"
    )
    period_date_to = fields.Date(
        string="Hasta",
        related="period_id.date_to"
    )
    contract_id = fields.Many2one(
        'broker.contract',
        string=u'No. de contrato',
        compute='_compute_contract_id'
    )
    partner_contract_id = fields.Many2one(
        'res.partner',
        string=u'Cliente',
        compute='_compute_contract_id',
    )
    movement_id = fields.Many2one(
        'sale.order',
        string='Movimento de contrato',
        ondelete='cascade',
    )
    provisional_payment_date = fields.Date(
        string='Fecha prevista de pago'
    )
    invoice_number = fields.Char(
        string=u'Número de factura'
    )
    sequence = fields.Integer(
        string="No. de cuota"
    )
    amount_insurance_fee = fields.Float(
        string='Prima'
    )
    amount_insurance_due = fields.Float(
        string='Cuota del seguro'
    )
    payment_ids = fields.Many2many(
        'fee.payment',
        'fee_payment_rel',
        'fee_id',
        'payment_id',
        string='Pagos de cuotas',
    )
    status_fee = fields.Selection(
        [
            ('no_payment', 'Por pagar'),
            ('partial_payment', 'Parcialmente pagada'),
            ('paid', 'Pagada'),
        ],
        u'Estado',
        default='no_payment'
    )
    contract_fee_id = fields.Many2one(
        "broker.contract.fee",
        string="Cuotas Contrato"
    )
    commission_ids = fields.One2many(
        'sale.order.line',
        'fee_id',
        string="Comisiones"
    )

    def _compute_contract_id(self):
        for record in self:
            record.contract_id = record.movement_id.contract_id.id
            record.partner_contract_id = record.movement_id.contract_id.client_id.id

    @api.depends('sequence')
    def _compute_name(self):
        for record in self:
            record.name = '[' + record.contract_id.name + ']' + ' ' + ' - '.join(
                [record.movement_id.name or '', str(record.sequence)])

    def action_receive_commission(self):
        return True

    def action_pay_fee(self):
        self.status_fee = 'paid'

    def action_partially_pay_fee(self):
        self.status_fee = 'partial_payment'

    def action_no_pay_fee(self):
        self.status_fee = 'no_payment'


class FeePayment(models.Model):
    _name = 'fee.payment'
    _description = 'Pagos de comisiones'

    name = fields.Char(
        string='Nombre del pago',
        required=True, copy=False, readonly=True,
        index='trigram',
        states={'draft': [('readonly', False)]},
        default=lambda self: 'Nuevo'
    )
    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        string='Cliente'
    )
    date_payment = fields.Date(
        required=True,
        default=fields.Date.today(),
        string='Fecha de pago'
    )
    status = fields.Selection(
        [('draft', 'Borrador'),
         ('paid', 'Pagado')],
        string='Estado',
        default='draft'
    )
    payment_ref = fields.Char(
        string="Referencia de pago"
    )
    comment = fields.Text(
        string="Comentarios"
    )
    sale_fee_payment_ids = fields.One2many(
        'sale.order.fee.payment',
        'payment_id',
        string='Cuota del contrato'
    )
    fee_order_ids = fields.Many2many(
        'sale.order.fee',
        'fee_payment_rel',
        'payment_id',
        'fee_id',
        string='Cuotas de movimientos',
    )
    contract_fee_ids = fields.Many2many(
        'broker.contract.fee',
        'payment_contract_fee_rel',
        'payment_id',
        'contract_fee_id',
        string='Cuotas de contratos',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            if vals.get('name', 'Nuevo') == "Nuevo":
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(vals['date_payment'])
                ) if 'date_payment' in vals else None
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fee.payment', sequence_date=seq_date) or "Nuevo"
        return super().create(vals_list)

    def action_pay_fee(self):
        for payment_line_id in self.sale_fee_payment_ids:
            payment_line_id.avoid_overpayment()
            amount_paid = float_round(payment_line_id.amount_paid, 2) + sum(
                payment_line_id.fee_id.payment_fee_line_ids.mapped('payment_id').filtered(
                    lambda x: x.status == 'paid').mapped('sale_fee_payment_ids').mapped('amount_paid'))
            for fee_line_id in payment_line_id.fee_id.mapped('fee_line_ids'):
                if float_compare(amount_paid, payment_line_id.fee_id.balance_due, 2) >= 0:
                    fee_line_id.action_pay_fee()
                    for commission_id in fee_line_id.commission_ids:
                        commission_id.action_receive_commission()
                else:
                    fee_line_id.action_partially_pay_fee()
            payment_line_id.fee_id.payment_ids = [fields.Command.link(self.id)]
        self.status = 'paid'

    def action_draft(self):
        commission_obj = self.env['sale.order.line']
        for payment_line_id in self.sale_fee_payment_ids:
            for fee_line_id in payment_line_id.fee_id.mapped('fee_line_ids'):
                if fee_line_id.payment_ids.filtered(lambda x: x.status == 'paid'):
                    fee_line_id.action_partially_pay_fee()
                else:
                    fee_line_id.action_no_pay_fee()
                commission_id = commission_obj.search([('fee_id', '=', fee_line_id.id)])
                commission_id.action_to_release_commission()
        self.status = 'draft'

    def action_load_fee(self):
        self.ensure_one()
        template = self.env.ref('broker_do.wizard_load_fee_contract_form')
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'context': {'default_payment_id': self.id,
                        'default_contract_ids': [(6, 0, self.env['broker.contract'].search([
                            ('client_id', '=', self.partner_id.id)
                        ]).ids), ],
                        },
            'res_model': 'wizard.load.fee.contract',
            'target': 'new',
        }


class SaleOrderFeePayment(models.Model):
    _name = 'sale.order.fee.payment'
    _description = 'Comisiones de Anexos'

    payment_id = fields.Many2one(
        'fee.payment',
        required=True,
        string='Pagos de cuota'
    )
    fee_id = fields.Many2one(
        'broker.contract.fee',
        required=True,
        ondelete='cascade',
        string='Cuota del contrato'
    )
    amount_paid = fields.Float(
        string='Valor del pago'
    )

    def avoid_overpayment(self):
        self.ensure_one()
        fee_id = self.fee_id
        raise_error = False
        payment_done = []
        balance_after_payment = float_round(fee_id.balance_due - self.amount_paid, 2)
        if float_compare(fee_id.balance_due, self.amount_paid, 2) < 0:
            raise_error = True
            for payment_line_id in fee_id.payment_fee_line_ids.filtered(lambda x: x.payment_id.status == 'paid'):
                payment_done.append(
                    payment_line_id.payment_id.name + ' / $' + str(float_round(payment_line_id.amount_paid, 2)))
        if raise_error:
            raise ValidationError("El valor máximo de pago de esta cuota es ${}. No se puede realizar el pago debido a "
                                  "que el saldo de la cuota es ${} y se está pagando en exceso por el valor de ${} "
                                  "esta cuota.\nLos datos de los pagos realizados son: "
                                  "\t\n-\t{}".format(float_round(fee_id.amount_insurance_due, 2),
                                                     float_round(fee_id.balance_due, 2),
                                                     abs(balance_after_payment),
                                                     '\t\n-\t'.join(payment_done)))
