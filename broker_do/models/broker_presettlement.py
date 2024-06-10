# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.tools import float_compare
from odoo.exceptions import ValidationError


class BrokerPreSettlement(models.Model):
    _name = 'broker.presettlement'

    name = fields.Char(
        string="Nombre",
        store=True,
        compute='_compute_name'
    )
    presettlement_num = fields.Char(
        string=u"Número de preliquidación"
    )
    date_end = fields.Date(
        'Fecha de corte',
        required=True
    )
    amount_presettlement = fields.Float(
        u'Valor de preliquidación',
        compute='_compute_amount_presettlement'
    )
    status = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('disagreement', 'Con novedades'),
            ('validated', 'Aprobado'),
        ],
        string="Estado",
        default="draft"
    )
    insurer_id = fields.Many2one(
        'res.partner',
        'Aseguradora',
        required=True
    )
    presettlement_line_ids = fields.One2many(
        'broker.presettlement.line',
        'presettlement_id',
        string=u"Líneas de preliquidación"
    )

    @api.depends('presettlement_num')
    def _compute_name(self):
        for record in self:
            record.name = 'PRELIQ ' + ' '.join([record.insurer_id.shortname or '',
                                                record.presettlement_num or ''])

    @api.depends('presettlement_line_ids')
    def _compute_amount_presettlement(self):
        for record in self:
            record.amount_presettlement = sum(record.presettlement_line_ids.mapped('amount_insurer'))

    def action_generate_presettlement(self):
        commission_ids = self.env['sale.order.line'].search([
            ('order_id.contract_id.insurer_id', '=', self.insurer_id.id),
            ('fee_id.provisional_payment_date', '<=', self.date_end),
            ('status_commission', '=', 'to_receive'),
            ('balance_commission', '!=', 0),
        ])
        self.presettlement_line_ids = [Command.clear()] + [Command.create({
            'number_fee': commission_id.sequence,
            'commission_id': commission_id.id,
            'amount_insurer': 0,
            'display_type': 'commission',
            'amount_original_commission': commission_id.price_subtotal,
            'amount_commission': commission_id.price_subtotal,
        }) for commission_id in commission_ids]

    def action_generate_preset_insurer(self):
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

    def action_reset_lines(self):
        self.presettlement_line_ids.unlink()

    def action_resolve_for_insurer(self):
        for line_id in self.presettlement_line_ids:
            if line_id.amount_insurer:
                line_id.commission_id.price_unit = line_id.amount_insurer
                line_id.amount_commission = line_id.amount_insurer

    def action_validate(self):
        # TODO: Poner filtrado y validaciones para el proceso de liquidaciones
        self.presettlement_line_ids.filtered(lambda x: float_compare(x.amount_difference, 0, 1) == 0).mapped(
            'commission_id').write({'status_commission': 'to_receive'})
        self.status = 'validated'

    def action_draft(self):
        # TODO: Poner filtrado y validaciones para el proceso de reverso de liquidaciones liquidaciones
        self.presettlement_line_ids.filtered(lambda x: float_compare(x.amount_difference, 0, 1) == 0).mapped(
            'commission_id').write({'status_commission': 'to_release'})
        self.status = 'draft'

    def action_create_commission(self):
        for line in self.presettlement_line_ids.filtered(lambda x: x.create_commission):
            line.action_create_commission()


class BrokerPreSettlementLine(models.Model):
    _name = 'broker.presettlement.line'
    _order = 'sequence'

    name = fields.Char(
        string="Nombre",
    )
    sequence = fields.Integer(
        u'Orden Líneas'
    )
    number_fee = fields.Integer(
        u'No. de cuota'
    )
    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
            ('commission', 'Comisiones')
        ],
        default=False
    )
    contract_num_excel = fields.Char(
        string="Número de contrato",
    )
    type_contract_excel = fields.Char(
        string="Tipo de movimiento",
    )
    fee_num_seq_excel = fields.Integer(
        string="Número de cuota",
    )
    presettlement_id = fields.Many2one(
        'broker.presettlement',
        'Preliquidación'
    )
    commission_id = fields.Many2one(
        'sale.order.line',
        string='Comision'
    )
    contract_id = fields.Many2one(
        'broker.contract',
        string='Contrato',
    )
    branch_id = fields.Many2one(
        'broker.branch',
        related="contract_id.branch_id",
        string='Ramo',
    )
    invoice_number = fields.Char(
        related="commission_id.fee_id.invoice_number",
        string='# Factura',
    )
    create_commission = fields.Boolean(
        string=u'¿Crear comisión?'
    )
    commission_to_adjust = fields.Boolean(
        string=u'Por ajustar'
    )
    amount_insurer = fields.Float(
        string=u'Valor aseguradora'
    )
    amount_original_commission = fields.Float(
        string=u'Valor de comisión esperada'
    )
    amount_commission = fields.Float(
        string=u'Valor de comisión ajustada'
    )
    amount_difference = fields.Float(
        string=u'Diferencia',
        store=True,
        compute='_compute_difference'
    )

    @api.depends('amount_insurer', 'amount_commission')
    def _compute_difference(self):
        for record in self:
            record.amount_difference = record.amount_insurer - record.amount_commission

    @api.onchange('amount_insurer', 'amount_commission')
    def _onchange_vals(self):
        self.amount_difference = self.amount_insurer - self.amount_commission

    def action_create_commission(self):
        contract_obj = self.env['broker.contract']
        message_info = []
        if self.commission_id:
            raise ValidationError(u'Se intenta crear la comisión para el contrato número {} que ya tiene comisión '
                                  u'con nombre {}.'.format(self.contract_id.name or self.contract_num_excel or '',
                                                           self.commission_id.name))
        contract = contract_obj.search([('contract_num', '=', self.contract_num_excel)], limit=1)
        if not contract:
            message = ("No existe el contrato {contract_num}, verifique la linea {line}, no se ha creado "
                       "la comisión").format(contract_num=self.contract_num_excel, line=str(self.sequence))
            message_info.append(message)
        movement = contract.movement_ids.filtered(lambda mov: mov.type_id.code == self.type_contract_excel)
        if not movement:
            message = ("No existe un movimiento de tipo {type} en el contrato numero {number},"
                       "verifique la linea {line}, no se ha creado la comisión").format(type=self.type_contract_excel,
                                                                                        number=self.contract_num_excel,
                                                                                        line=str(self.sequence))
            message_info.append(message)
        fee_id = movement.fee_line_ids.filtered(lambda x: x.sequence == 1)
        commission_percentage = self.amount_insurer / movement.amount_fee if movement.amount_fee > 0 else 0
        value_commission = fields.Command.create({
            'product_id': contract.branch_id.product_id.id,
            'product_uom_qty': 1,
            'amount_fee': movement.amount_fee,
            'price_unit': self.amount_insurer,
            'percentage_commission': commission_percentage,
            'percentage_fee': 1,
            'sequence': 1,
            'fee_id': fee_id.id if fee_id else None,
            'status_commission': "to_receive",
        })
        movement.write({
            "order_line": [fields.Command.clear()] + [value_commission],
            "commission_percentage": commission_percentage
        })
