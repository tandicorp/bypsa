# -*- coding: utf-8 -*-

from odoo import fields, models, api, Command
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round, float_compare


class BrokerQuotaCross(models.Model):
    _name = 'broker.quota.cross'
    _description = 'Permite Realizar el cruce entre quotas'

    name = fields.Char(
        string="Nombre del Cruce"
    )
    client_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("posted", "Validado")
        ],
        string="Estado",
        required=True,
        default="draft"
    )
    cross_positive_ids = fields.One2many(
        "broker.quota.cross.positive",
        "quota_cross_id",
        string="Por Cobrar"
    )
    cross_negative_ids = fields.One2many(
        "broker.quota.cross.negative",
        "quota_cross_id",
        string="Por pagar"
    )
    reason_cross = fields.Selection(
        [
            ("revocation", "Anulación de seguro"),
            ("cancellation", "Cancelación de seguro"),
            ("rate_decrease", "Disminución de tasa"),
            ("value_decrease", "Disminución valor asegurado"),
            ("exclusion", "Exclusión"),
            ("early_payment", "Pronto pago"),
            ("withhold", "Retención"),
        ],
        string="Motivo del cruce",
        required=True,
    )
    comments = fields.Text(
        'Observaciones'
    )

    def action_search_quotas(self):
        contract_fee_obj = self.env['broker.contract.fee']
        contract_fee_ids = contract_fee_obj.search([
            ("contract_id.client_id", "=", self.client_id.id),
            ("status_fee", "!=", "paid")
        ])
        lines_positive, lines_negative = [], []
        if contract_fee_ids:
            for fee in contract_fee_ids.filtered(lambda fee: fee.balance_due_negative != 0):
                lines_negative.append({
                    "value": abs(fee.balance_due_negative),
                    "value_cross": abs(fee.balance_due_negative),
                    "contract_fee_id": fee.id
                })

            total_sum_negative = float_round(sum([x['value_cross'] for x in lines_negative]), 2)
            sum_negative = float_round(total_sum_negative, 2)
            remain_sum_negative = float_round(total_sum_negative, 2)
            for fee in contract_fee_ids.filtered(lambda fee: fee.balance_due != 0).sorted('provisional_payment_date'):
                sum_negative -= float_round(fee.balance_due, 2)
                if float_compare(sum_negative, 0, 2) > 0:
                    lines_positive.append({
                        "value": fee.balance_due,
                        "value_cross": fee.balance_due,
                        "contract_fee_id": fee.id
                    })
                    remain_sum_negative -= float_round(fee.balance_due, 2)
                elif float_compare(remain_sum_negative, 0, 2) > 0:
                    lines_positive.append({
                        "value": fee.balance_due,
                        "value_cross": remain_sum_negative,
                        "contract_fee_id": fee.id
                    })
                    remain_sum_negative -= remain_sum_negative
                else:
                    lines_positive.append({
                        "value": fee.balance_due,
                        "value_cross": 0,
                        "contract_fee_id": fee.id,
                        "check": False
                    })
        self.cross_negative_ids = [Command.clear()] + [Command.create(val) for val in lines_negative]
        self.cross_positive_ids = [Command.clear()] + [Command.create(val) for val in lines_positive]

    def action_validate(self):
        state = 'posted'
        positive = round(sum(self.cross_positive_ids.filtered(lambda pos: pos.check).mapped("value_cross")), 2)
        negative = round(sum(self.cross_negative_ids.filtered(lambda pos: pos.check).mapped("value_cross")), 2)
        if not positive == negative:
            raise ValidationError("El Valor total Cruzado debe ser el mismo en Por Pagar y Por cobrar")
        for this in self.cross_positive_ids:
            this.state = state
        for this in self.cross_negative_ids:
            this.state = state
        self.state = state
        # Ejecutar el compute
        contract_fee_ids = self.cross_positive_ids.mapped("contract_fee_id") + self.cross_negative_ids.mapped(
            "contract_fee_id")
        contract_fee_ids._compute_quotas_positive_negative()
        return True

    def action_return_draft(self):
        state = 'draft'
        for this in self.cross_positive_ids:
            this.state = state
        for this in self.cross_negative_ids:
            this.state = state
        self.state = state
        contract_fee_ids = self.cross_positive_ids.mapped("contract_fee_id") + self.cross_negative_ids.mapped(
            "contract_fee_id")
        contract_fee_ids._compute_quotas_positive_negative()
        return True


class BrokerQuotaCrossPositive(models.Model):
    _name = 'broker.quota.cross.positive'

    @api.depends("value_cross")
    def _compute_balance(self):
        for this in self:
            this.balance = this.value - this.value_cross

    quota_cross_id = fields.Many2one(
        "broker.quota.cross",
        string="Cruce"
    )
    check = fields.Boolean(
        string="Verificar",
        default=True
    )
    balance = fields.Float(
        string="Saldo",
        compute="_compute_balance"
    )
    value = fields.Float(
        string="Valor"
    )
    value_cross = fields.Float(
        string="Valor Cruzado"
    )
    contract_fee_id = fields.Many2one(
        "broker.contract.fee",
        ondelete='cascade',
        string="Cuota",
    )
    state = fields.Selection([
        ("draft", "Borrador"),
        ("posted", "Validado")
    ], string="Estado",
        required=True,
        default="draft"
    )

    @api.onchange("check")
    def _onchange_check(self):
        for this in self:
            if not this.check:
                this.value_cross = 0

    @api.onchange("value_cross")
    def _onchange_value_cross(self):
        for this in self:
            if this.value_cross > this.value or this.value_cross < 0:
                raise ValidationError("El valor de cruce debe ser menor o igual al valor o mayor a cero")


class BrokerQuotaCrossNegative(models.Model):
    _name = 'broker.quota.cross.negative'

    @api.depends("value_cross")
    def _compute_balance(self):
        for this in self:
            this.balance = this.value - this.value_cross

    quota_cross_id = fields.Many2one(
        "broker.quota.cross",
        string="Cruce"
    )
    check = fields.Boolean(
        string="Verificar",
        default=True
    )
    balance = fields.Float(
        string="Saldo",
        compute="_compute_balance"
    )
    value = fields.Float(
        string="Valor"
    )
    value_cross = fields.Float(
        string="Valor Cruzado"
    )
    contract_fee_id = fields.Many2one(
        "broker.contract.fee",
        ondelete='cascade',
        string="Cuota"
    )
    state = fields.Selection([
        ("draft", "Borrador"),
        ("posted", "Validado")
    ], string="Estado",
        required=True,
        default="draft"
    )

    @api.onchange("check")
    def _onchange_check(self):
        for this in self:
            if not this.check:
                this.value_cross = 0
