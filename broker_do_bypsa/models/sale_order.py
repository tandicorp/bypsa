# -*- coding: utf-8 -*-
from odoo import models, api, fields, Command
from odoo.exceptions import ValidationError
from odoo.tools import float_round, float_compare

_module = 'broker_do'
_branches_medical_assistance = ['broker_branch_medical_assistance', 'broker_branch_accident']
_branches_no_taxes = ['broker_branch_individual', 'broker_branch_collective'] + _branches_medical_assistance


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    table_emission_rights = fields.Selection(
        [
            ('0', 'DE 0.00 A 250.00'),
            ('1', 'DE 251.00 A 500.00'),
            ('2', 'DE 501.00 A 1000.00'),
            ('3', 'DE 1001.00 A 2000.00'),
            ('4', 'DE 2001.00 A 4000.00'),
            ('5', 'DE 4001.00 EN ADELANTE'),
            ('other', 'OTRO')
        ],
        string='Tabla de derechos de emisión',
    )

    @api.depends("amount_fee")
    def _compute_amount_taxes_insurance(self):
        super(SaleOrder, self)._compute_amount_taxes_insurance()
        for record in self:
            if record.amount_fee:
                if record.amount_fee <= 250:
                    record.table_emission_rights = '0'
                    record.amount_tax_emission_rights = 0.5
                elif 250 < record.amount_fee <= 500:
                    record.table_emission_rights = '1'
                    record.amount_tax_emission_rights = 1
                elif 500 < record.amount_fee <= 1000:
                    record.table_emission_rights = '2'
                    record.amount_tax_emission_rights = 3
                elif 1000 < record.amount_fee <= 2000:
                    record.table_emission_rights = '3'
                    record.amount_tax_emission_rights = 5
                elif 2000 < record.amount_fee <= 4000:
                    record.table_emission_rights = '4'
                    record.amount_tax_emission_rights = 7
                elif record.amount_fee > 4000:
                    record.table_emission_rights = '5'
                    record.amount_tax_emission_rights = 9

    @api.onchange('table_emission_rights')
    def onchange_amounts_emission_rights(self):
        if self.table_emission_rights == '0':
            self.amount_tax_emission_rights = 0.5
        elif self.table_emission_rights == '1':
            self.amount_tax_emission_rights = 1
        elif self.table_emission_rights == '2':
            self.amount_tax_emission_rights = 3
        elif self.table_emission_rights == '3':
            self.amount_tax_emission_rights = 5
        elif self.table_emission_rights == '4':
            self.amount_tax_emission_rights = 7
        elif self.table_emission_rights == '5':
            self.amount_tax_emission_rights = 9
        else:
            self.amount_tax_emission_rights = 0

    def action_calculate_fee(self):
        if self.is_manual_fee:
            super().action_calculate_fee()
        else:
            if not self.object_line_ids:
                raise ValidationError("Se debe agregar objetos Asegurados")
            if len(self.object_line_ids) != len(self.object_line_ids.mapped("agreement_id")):
                raise ValidationError("Los objetos asegurados deben tener un acuerdo ganador")
            super().action_calculate_fee()

    def assign_fee_amounts(self, residual_amount_due, residual_amount_fee, fee_vals, type_taxes=False,
                           list_amounts=False):
        if not self.is_manual_fee:
            list_fee_amount = self.get_list_amount_fee()
            balance_amount_due = self.amount_due  # CUOTA TOTAL
            balance_amount_fee = self.amount_fee  # PRIMA NETA
            fee_vals = super(SaleOrder, self).assign_fee_amounts(balance_amount_due, balance_amount_fee, fee_vals,
                                                                 type_taxes=type_taxes, list_amounts=list_fee_amount)
        else:
            fee_vals = super(SaleOrder, self).assign_fee_amounts(residual_amount_due, residual_amount_fee, fee_vals,
                                                                 type_taxes=type_taxes, list_amounts=list_amounts)
        return fee_vals

    def get_list_amount_fee(self):
        decimal_places = self.env.company.currency_id.decimal_places
        value_fee_total = 0
        list_amount_fee = []
        for fee in range(0, self.number_period):
            value_fee = 0
            for object in self.object_line_ids.filtered(lambda obj_line: obj_line.agreement_id):
                if not object.depreciation_id:
                    value_fee += object.agreement_id.amount_fee
                else:
                    value_insured, depreciation_value = object.depreciation_id.get_amount_insured_depreciation(
                        object.amount_insured,
                        fee + 1)
                    value_fee += object.agreement_id.get_amount_fee_depreciation(value_insured)
            value_fee = float_round(value_fee, decimal_places, rounding_method='HALF-DOWN')
            list_amount_fee.append({
                "period": fee,
                "value_fee": value_fee,
            })
            value_fee_total += float_round(value_fee, decimal_places, rounding_method='HALF-DOWN')
        self.amount_fee = value_fee_total
        self._compute_amounts_for_commission()
        return list_amount_fee

    def get_value_amounts(self, mount_fee, mount_due, index=False, list_fee_amount=False, type_taxes=False):
        decimal_places = self.env.company.currency_id.decimal_places
        if list_fee_amount:
            len_period = len(list_fee_amount)
            for fee in list_fee_amount:
                if fee["period"] == index:
                    mount_fee = fee["value_fee"]
                    mount_due = fee["value_fee"]
                    if type_taxes != 'first_fee':
                        balance_amount_due = float_round((self.amount_due - self.amount_fee) / len_period,
                                                         decimal_places, rounding_method='HALF-DOWN')
                        mount_due = fee["value_fee"] + balance_amount_due
                    return mount_fee, mount_due
        else:
            mount_fee, mount_due = mount_fee, mount_due
        return mount_fee, mount_due
