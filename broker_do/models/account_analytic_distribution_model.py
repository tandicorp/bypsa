# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountAnalyticDistributionModel(models.Model):
    _inherit = 'account.analytic.distribution.model'

    work_location_id = fields.Many2one(
        'hr.work.location',
        string='Centro de trabajo',
        ondelete='cascade',
        help="Seleccione un centro de trabajo en el cual se usará la cuenta analítica especificada en las analíticas por defecto",
    )
    business_id = fields.Many2one(
        'broker.business',
        string=u'Línea de negocio',
        ondelete='cascade',
        help="Seleccione una línea de negocio en el cual se usará la cuenta analítica especificada en las analíticas por defecto",
    )

    def _create_domain(self, fname, value):
        return super()._create_domain(fname, value)
