from odoo import models, api, fields

_TYPES = [
    ("char", "Texto"),
    ("html", "Html"),
    ("float", "Decimal"),
    ("integer", "Entero"),
    ("date", "Fecha"),
    ("selection", "Selección"),
]


class BrokerMovementBranch(models.Model):
    _name = 'broker.movement.branch'
    _description = 'Formatos por cada ramo y movimiento'

    @api.depends("branch_id", "type_id")
    def _compute_name(self):
        for this in self:
            branch_name = this.branch_id.name if this.branch_id else ""
            type_name = this.type_id.name if this.type_id else ""
            this.name = "{} - {}".format(type_name, branch_name)

    name = fields.Char(
        string='Nombre',
        store=True,
        compute='_compute_name'
    )
    type_id = fields.Many2one(
        "sale.order.type",
        string='Tipo de Anexo',
        required=True
    )
    branch_id = fields.Many2one(
        'broker.branch',
        string='Ramo',
        required=True
    )
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Rating Email Template',
        domain=[('model', '=', 'sale.order')]
    )
    body_html = fields.Html(
        string="Contenido",
        related="mail_template_id.body_html",
        readonly=0
    )
    model_id = fields.Many2one(
        related="mail_template_id.model_id",
    )
    model = fields.Char(
        related="mail_template_id.model",
    )
    document_line_ids = fields.One2many(
        "broker.movement.document",
        "movement_branch_id",
        string="Documentación"
    )
    object_line_ids = fields.One2many(
        "broker.movement.branch.object",
        "movement_branch_id",
        string="Definición Objetos Asegurado",
        domain=lambda self: [('object_type', '=', 'normal')]

    )
    blanket_line_ids = fields.One2many(
        "broker.movement.branch.object",
        "movement_branch_id",
        string="Definición Objetos Agrupados",
        domain=lambda self: [('object_type', '=', 'blanket')]
    )


class BrokerMovementBranchObject(models.Model):
    _name = 'broker.movement.branch.object'

    name = fields.Char(
        string="Nombre",
        required=True
    )
    object_type = fields.Selection([
        ("blanket", "Agrupado"),
        ("normal", "Normal"),
    ], string="Tipo Objeto",
        default="normal"
    )
    type = fields.Selection(
        _TYPES,
        string="Tipo",
        required=True,
        default="char"
    )
    value = fields.Text(
        string="Valores por defecto",
        help="Usado para el listado de los campos de tipo Selection"
    )
    movement_branch_id = fields.Many2one(
        "broker.movement.branch",
        string="Ramo"
    )
    add_value = fields.Boolean(
        string="Suma al Valor?",
        default=False,
    )


class BrokerMovementDocument(models.Model):
    _name = 'broker.movement.document'

    name = fields.Char(
        string="Nombre"
    )
    required = fields.Boolean(
        string=u"¿Requerido?",
        default=False
    )
    movement_branch_id = fields.Many2one(
        "broker.movement.branch",
        string="Ramo"
    )
