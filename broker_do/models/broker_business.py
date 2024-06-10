# -*- coding: utf-8 -*-

from odoo import models, api, fields


class BrokerBusiness(models.Model):
    _name = "broker.business"
    _description = "Líneas de Negocio"

    name = fields.Char(
        string="Líneas de Negocio"
    )

    business_line_ids = fields.One2many(
        "broker.business.line",
        "business_id",
        string="Configuración de Notificación"
    )


class BrokerBusinessLine(models.Model):
    _name = "broker.business.line"
    _description = "Permite configurar las notificaciones"

    business_id = fields.Many2one(
        "broker.business",
        string="Línea de Negocio"
    )
    type = fields.Selection([
        ("notification_email", "Dias de Notificación"),
    ], string="Tipo"
    )
    value = fields.Integer(
        string="Valor"
    )
