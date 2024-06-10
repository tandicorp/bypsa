# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class BrokerContract(models.Model):
    _inherit = 'broker.contract'

    @api.onchange('date_start')
    def onchange_date_start(self):
        if self.date_start:
            self.date_end = self.date_start + relativedelta(months=12)
            type = self.env.ref("broker_do.policy_movement")
            for line in self.movement_ids.filtered(lambda x: x.type_id.id == type.id):
                line.date_start = self.date_start
                line.date_end = self.date_end
