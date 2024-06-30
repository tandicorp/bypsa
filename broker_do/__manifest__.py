# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Broker Do',
    'version': '1.0',
    'summary': u'Modulos de manejo de clientes para companias de brokers',
    'description': u'Modulos de manejo de clientes para companias de brokers',
    'category': 'sales',
    'author': 'Tandicorp',
    'website': '',
    'license': '',
    'depends': [
        'account_accountant',
        'hr',
        'mail',
        'crm_enterprise',
        'sale',
        'web',
        'l10n_ec',
        'report_xlsx',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/crm_stage_data.xml',
        'data/product_product_data.xml',
        'data/ir_config_parameter.xml',
        'data/res_partner_type_data.xml',
        'data/mail_templates.xml',
        'data/broker_business_data.xml',
        'data/ir_sequence_data.xml',
		'data/product_reversal_product_data.xml',
		'data/broker_branch_data.xml',
        'security/res_groups.xml',
        'data/ir_cron.xml',
        'data/sale_order_type_data.xml',
        'views/res_partner_views.xml',
        'views/broker_branch_views.xml',
        'views/crm_lead_views.xml',
        'views/broker_contract_views.xml',
        'views/broker_claim_notice_views.xml',
        'views/broker_commission_insurer_views.xml',
        'views/broker_movement_commission_view.xml',
        'views/sale_order_fee_views.xml',
        'views/broker_presettlement_views.xml',
        'views/agreements_insurer_views.xml',
        'views/coverage_template_views.xml',
        'views/broker_branch_insurer_views.xml',
        'views/broker_business_views.xml',
        'views/broker_movement_branch_views.xml',
        'views/account_move_view.xml',
        'views/res_config_settings_views.xml',
        'views/hr_employee_view.xml',
        'views/broker_quota_cross_views.xml',
        'wizard/wizard_load_fee_contract_view.xml',
        'wizard/commission_special_wizard.xml',
        'wizard/broker_presettlement_wizard.xml',
        'wizard/agreements_insurer_wizard.xml',
        'wizard/wizard_presettlement_view.xml',
        'wizard/wizard_notice_message_view.xml',
        'wizard/request_quotation_wizard.xml',
        'wizard/wizard_link_container_view.xml',
        'wizard/wizard_contract_object_view.xml',
        'reports/report_crm_lead_comparison.xml',
        'views/account_analytic_distribution_model_views.xml',
        'views/fee_payment_views.xml',
        'views/broker_contract_deductible_template_view.xml',
        'views/broker_movement_views.xml',
        'views/broker_movement_specialization_views.xml',
        'reports/reports.xml',
        'views/broker_menu_views.xml',
        'data/broker_movement_branch_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'broker_do/static/src/components/*/*.xml',
            'broker_do/static/src/components/*/*.js',
            'broker_do/static/src/components/*/*.scss',
            'broker_do/static/src/css/buttons.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'external_dependencies': {
        'python': [],
    }
}
