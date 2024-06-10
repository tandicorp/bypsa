# -*- coding: utf-8 -*-
{
    'name': "Ecuador - Anexo Transaccional Simplificado (ATS)",

    'summary': """
        Anexo Transaccional Simplificado (ATS) """,

    'description': """
        Anexo Transaccional Simplificado (ATS)
    """,

    'author': "Tandicorp",
    'website': "https://www.tandicorp.com",

    'category': 'Accounting',
    'version': '1.0.1',

    'depends': [
        'l10n_ec_edi'
    ],
    'data': [
        'wizard/l10n_ec_ats_wizard_views.xml',
        'security/ir.model.access.csv',
    ],
}
