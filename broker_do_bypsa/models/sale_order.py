# -*- coding: utf-8 -*-
from odoo import models, api, fields, Command

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
