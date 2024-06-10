# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        # EXTENDS account, creates journals for purchase liquidation, sale withholds, purchase withhold
        res = super(AccountChartTemplate, self).generate_journals(acc_template_ref, company,
                                                                  journals_dict=journals_dict)
        self._broker_configure_order_journals(company)
        return res

    def _broker_configure_order_journals(self, company):
        new_journals_values = [
            {
                'name': "Banco / Transferencias",
                'code': 'BBTCO',
                'type': 'general',
            },
            {
                'name': "Efectivo / Cheque",
                'code': 'BECCO',
                'type': 'general',
            },
            {
                'name': "Cobros en aseguradora",
                'code': 'BCACO',
                'type': 'general',
            },
        ]
        for new_values in new_journals_values:
            journal = self.env['account.journal'].search([
                ('code', '=', new_values['code']),
                ('company_id', '=', company.id)])
            if not journal:
                self.env['account.journal'].create({
                    **new_values,
                    'company_id': company.id,
                    'show_on_dashboard': True,
                })

    # def _load(self, company):
    #     # EXTENDS account to setup withhold taxes in company configuration
    #     res = super()._load(company)
    #     self._l10n_ec_configure_ecuadorian_withhold_taxpayer_type(company)
    #     return res
    #
    # def _l10n_ec_configure_ecuadorian_withhold_taxpayer_type(self, companies):
    #     # Set proper profit withhold tax on RIMPE on taxpayer type
    #     for company in companies.filtered(lambda r: r.account_fiscal_country_id.code == 'EC'):
    #         tax_rimpe_entrepreneur = self.env['account.tax'].search([
    #             ('l10n_ec_code_base', '=', '343'),
    #             ('company_id', '=', company.id)
    #         ], limit=1)
    #         tax_rimpe_popular_business = self.env['account.tax'].search([
    #             ('l10n_ec_code_base', '=', '332'),
    #             ('company_id', '=', company.id)
    #         ], limit=1)
    #         if tax_rimpe_entrepreneur:
    #             rimpe_entrepreneur = self.env.ref('l10n_ec_edi.l10n_ec_taxpayer_type_13')  # RIMPE Regime Entrepreneur
    #             rimpe_entrepreneur.with_company(company).profit_withhold_tax_id = tax_rimpe_entrepreneur.id
    #         if tax_rimpe_popular_business:
    #             rimpe_popular_business = self.env.ref(
    #                 'l10n_ec_edi.l10n_ec_taxpayer_type_15')  # RIMPE Regime Popular Business
    #             rimpe_popular_business.with_company(company).profit_withhold_tax_id = tax_rimpe_popular_business.id
