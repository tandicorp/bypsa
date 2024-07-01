# -*- coding: utf-8 -*-
{
    'name': "Tandicorp Custom",

    'summary': """
        Personalizaciones de Tandicorp """,

    'description': """
        Incluye las personalizaciones de Tandicorp sobre la versión de Odoo 16
    """,

    'author': "Tandicorp",
    'website': "https://www.tandicorp.com",

    'category': 'Accounting',
    'version': '1.0.1',

    'depends': [
        'l10n_ec_edi'
    ],
    'data': [
        # Data
        'data/product_product_data.xml',
        # View
        'views/account_move_views.xml',
        # Wizard
        'wizard/tandi_import_xml_wizard.xml',
        # Security
        'security/ir.model.access.csv',
    ],
}
