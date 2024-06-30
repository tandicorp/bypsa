from odoo import fields, models, api


class BrokerDepreciation(models.Model):
    _name = 'broker.depreciation'
    _description = 'Tabla de Depreciation'

    name = fields.Char(
        string="Nombre"
    )
    model_ids = fields.Many2many(
        "broker.depreciation.model",
        string="Modelos/Marcas"
    )
    rate = fields.Float(
        string="Tasa",
        required=True
    )
    depreciation_lines = fields.One2many(
        "broker.depreciation.line",
        "depreciation_id",
        string="Lineas de depreciación"
    )


class BrokerDepreciationLine(models.Model):
    _name = "broker.depreciation.line"
    _description = "Tabla de Depreciation Line"
    _order = "year asc"

    year = fields.Selection([
        ("1", "1er Año"),
        ("2", "2do Año"),
        ("3", "3er Año"),
        ("4", "4to Año"),
        ("5", "5to Año"),
        ("6", "6to Año"),
        ("future", "En adelante"),
    ], string="Año depreciación",
        required=True
    )
    action = fields.Selection([
        ("value_invoice", " Valor de la factura incluido IVA"),
        ("negative", "Valor año anterior menos"),
        ("equals", "Mismo valor"),
    ],
        string="Acción",
        required=True,
    )
    depreciation = fields.Float(
        string="Depreciación",
        required=True
    )
    depreciation_id = fields.Many2one(
        "broker.depreciation",
        string="Depreciación Cabecera"
    )


class BrokerDepreciationModel(models.Model):
    _name = 'broker.depreciation.model'

    name = fields.Char(
        string="Marca/Modelo"
    )