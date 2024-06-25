# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bypsa Broker Do',
    'version': '1.0',
    'summary': u'Personalizacion de broker do para Bypsa',
    'description': u'Módulos de manejo de clientes para companias de brokers',
    'category': 'sales',
    'author': 'Tandicorp',
    'website': '',
    'license': '',
    'depends': [
        'broker_do',
    ],
    'data': [
        'data/broker_movement_branch_data.xml',
        'views/broker_movement_views.xml',
        'views/broker_contract_views.xml',
    ],
    'assets': {
    },
    'installable': True,
    'auto_install': False,
    'external_dependencies': {
        'python': [],
    }
}
