# coding: utf-8
{
    "name": "Ecuador - Payments Bank formats",
    "summary": """Export payments as Ecuadorian bank formats""",
    "category": "Accounting/Accounting",
    "description": """
        Export payments as most of Ecuadorian Bank Cash Management files.
    """,
    "version": "16.0.1.0.1",
    "depends": ["account_batch_payment", "l10n_ec"],
    "data": [
        "data/account_payment_method_data.xml",
        "views/account_journal_views.xml",
        "views/res_partner_views.xml",
    ]
}
