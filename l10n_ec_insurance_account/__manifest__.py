# -*- coding: utf-8 -*-
{
    'name': "Ecuador - Insurance Company Accounting",

    'summary': """
        Computes Ecuadorian Insurance Companies contributions automatically on invoicing.
        """,

    'description': """
        Computes Ecuadorian Insurance Companies contributions automatically on invoicing.
    """,

    'author': "Tandicorp",
    'website': "https://www.tandicorp.com",
    'category': 'Accounting',
    'version': '16.0.1.0.1',

    # any module necessary for this one to work correctly
    'depends': ['l10n_ec_edi'],

    # always loaded
    'data': [
        #Data
        "data/cron_send_edi_documents_email.xml",
        #Views
        "views/product_product.xml"
    ],

    'license': 'OPL-1'
}
