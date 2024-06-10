# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_ats_subtotals_by_tax_supp_code(self, tax_support_code):
        '''
        Computes values needed for ATS parse, grouped by tax_support_code
        @param tax_support_code: string code corresponding to l10n_ec_code_taxsupport set in taxes.
        '''
        move = self
        amount_untaxed = 0.0
        # inicializamos en cero
        [l10n_ec_base_non_zero_iva, l10n_ec_amount_non_zero_iva, l10n_ec_base_zero_iva, l10n_ec_base_tax_free,
         l10n_ec_base_not_subject_to_vat, l10n_ec_base_ice, l10n_ec_amount_ice, l10n_ec_base_irbpnr] = [0.0 for x in range(8)]
        #We filter tax applied invoice lines only
        taxed_invoice_lines = move.invoice_line_ids.filtered(lambda line: line.tax_ids)
        #We filter these tax applied lines with the corresponding tax support code to get amount_untaxed from it
        for line in taxed_invoice_lines.filtered(lambda line: line.tax_ids[0].l10n_ec_code_taxsupport == tax_support_code):
            amount_untaxed += line.price_subtotal
        #Iter over tax lines that have the corresponding tax support code to compute amounts
        for tax_move_line in move.line_ids.filtered(lambda line: line.tax_line_id and line.tax_line_id.l10n_ec_code_taxsupport == tax_support_code):
            tax = tax_move_line.tax_line_id
            if tax.tax_group_id.l10n_ec_type in ['vat12', 'vat14', 'vat08']:
                l10n_ec_base_non_zero_iva += tax_move_line.tax_base_amount
                l10n_ec_amount_non_zero_iva += (tax_move_line.tax_tag_invert and -1 or 1) * tax_move_line.balance
            elif tax.tax_group_id.l10n_ec_type in ['zero_vat']:
                l10n_ec_base_zero_iva += tax_move_line.tax_base_amount
            elif tax.tax_group_id.l10n_ec_type == 'exempt_vat':
                l10n_ec_base_tax_free += tax_move_line.tax_base_amount
            elif tax.tax_group_id.l10n_ec_type == 'not_charged_vat':
                l10n_ec_base_not_subject_to_vat += tax_move_line.tax_base_amount
            elif tax.tax_group_id.l10n_ec_type == 'ice':
                l10n_ec_base_ice += tax_move_line.tax_base_amount
                l10n_ec_amount_ice += (tax_move_line.tax_tag_invert and -1 or 1) * tax_move_line.balance
            elif tax.tax_group_id.l10n_ec_type == 'irbpnr':
                l10n_ec_base_irbpnr += tax_move_line.tax_base_amount
            elif tax.tax_group_id.l10n_ec_type in move.env['account.tax.group']._fields['l10n_ec_type'].get_values(move.env):
                pass
            else:
                raise ValidationError('La factura numero ' + str(move.name) + \
                                      ' con ID ' + str(move.id) + \
                                      ' tiene un impuesto que no corresponde a ningun tipo ecuatoriano')
        vals = {
            'l10n_ec_base_non_zero_iva': l10n_ec_base_non_zero_iva,
            'l10n_ec_amount_non_zero_iva': l10n_ec_amount_non_zero_iva,
            'l10n_ec_base_zero_iva': l10n_ec_base_zero_iva,
            'l10n_ec_base_tax_free': l10n_ec_base_tax_free,
            'l10n_ec_base_not_subject_to_vat': l10n_ec_base_not_subject_to_vat,
            'l10n_ec_base_ice': l10n_ec_base_ice,
            'l10n_ec_amount_ice': l10n_ec_amount_ice,
            'l10n_ec_base_irbpnr': l10n_ec_base_irbpnr,
        }
        return vals