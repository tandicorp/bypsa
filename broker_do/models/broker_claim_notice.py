# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from random import randint


class BrokerClaimNotice(models.Model):
    _name = 'broker.claim.notice'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin', 'format.address.mixin']

    name = fields.Char(
        'Nombre'
    )
    client_id = fields.Many2one(
        'res.partner',
        'Cliente'
    )
    date_notification = fields.Date(
        'Fecha de notificación',
        default=lambda self: fields.Date.today()
    )
    date_claim = fields.Date(
        'Fecha de siniestro',
        default=lambda self: fields.Date.today()
    )
    description = fields.Text(
        'Descripción'
    )
    contract_id = fields.Many2one(
        'broker.contract',
        string=u'Contrato'
    )
    claim_ids = fields.One2many(
        'broker.claim',
        'notice_claim_id',
        string="Siniestros"
    )
    deductible_id = fields.Many2one(
        "broker.object.deductible",
        string="Deducible",
    )
    object_id = fields.Many2one(
        "broker.movement.object",
        string="Objeto Asegurado",
    )

    def create_new_claim(self):
        broker_claim = self.env['broker.claim'].create({
            'notice_claim_id': self.id,
            'contract_id': self.contract_id.id,
            'client_id': self.client_id.id,
            'object_id': self.object_id.id,
            'deductible_id': self.deductible_id.id,
            'date_notification': self.date_notification,
            'date_claim': self.date_claim,
            'is_group': True,
        })
        template = self.env.ref('broker_do.crm_claim_form')
        return {
            'name': 'Siniestro',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'res_id': broker_claim.id,
            'res_model': 'broker.claim',
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'self',
        }

    def generate_claim(self):
        template = self.env.ref('broker_do.wizard_notice_message_form')
        if not self.claim_ids:
            return self.create_new_claim()
        else:
            return {
                'name': 'Siniestro',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'context': {'claim_notice_id': self.id, 'new_claim_creation_warning': True},
                'res_model': 'wizard.notice.message',
                'views': [(template.id, 'form')],
                'view_id': template.id,
                'target': 'new',
            }

    def action_view_claim(self):
        self.ensure_one()
        template_form = self.env.ref('broker_do.crm_claim_form')
        template_tree = self.env.ref('broker_do.crm_claim_tree')
        if not self.claim_ids:
            raise ValidationError("No existe un siniestro Asociado")
        return {
            'name': 'Siniestro',
            'type': 'ir.actions.act_window',
            'view_type': 'tree,form',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.claim_ids.ids)],
            'res_model': 'broker.claim',
            'views': [(template_tree.id, 'tree'), (template_form.id, 'form')],
            'view_id': template_tree.id,
            'target': 'self',
        }

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env.ref("broker_do.sequence_notice_claim")
        partner_obj = self.env['res.partner']
        contract_obj = self.env['broker.contract']
        for values in vals_list:
            contract = contract_obj.browse(values.get('contract_id'))
            partner = partner_obj.browse(values.get('client_id'))
            values['name'] = sequence.next_by_id().format(contract=contract.name, name=partner.name)
        return super(BrokerClaimNotice, self).create(vals_list)

    @api.onchange('client_id')
    def _onchange_client(self):
        self.contract_id = False
        self.object_id = False
        self.deductible_id = False

    @api.onchange("contract_id")
    def _get_domain_object(self):
        res = []
        if self.contract_id:
            objects = self.contract_id.contract_object_ids
            res = [('id', 'in', objects.ids)]
        self.object_id = False
        self.deductible_id = False
        return {"domain": {'object_id': res}}

    @api.onchange("object_id")
    def _get_domain_deductible(self):
        res = []
        if self.object_id:
            deductible = self.object_id.deductible_ids
            res = [('id', 'in', deductible.ids)]
        self.deductible_id = False
        return {"domain": {'deductible_id': res}}


class BrokerClaim(models.Model):
    _name = 'broker.claim'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin', 'format.address.mixin']

    _DEFAULT_NAME = "Nuevo"

    @api.depends("line_ids", "child_claim_ids")
    def get_amount_paid(self):
        for this in self:
            if this.is_group:
                claim_ids = this.child_claim_ids
                value = sum(claim_ids.line_ids.filtered(lambda line: line.type == 'pay').mapped('value'))
                this.amount_paid = value
            else:
                this.amount_paid = sum(this.line_ids.filtered(lambda line: line.type == 'pay').mapped('value'))

    date_payment = fields.Date(
        'Fecha de pago',
        tracking=True
    )
    date_notification = fields.Date(
        'Fecha de notificación',
        tracking=True
    )
    date_claim = fields.Date(
        'Fecha de siniestro',
    )
    state = fields.Selection(
        [
            ('registered', 'Ingresado'),
            ('documented', 'Documentado'),
            ('insurer', 'En Aseguradora'),
            ('paid', 'Pagado'),
            ('rejected', 'Rechazado'),
        ],
        'Estado',
        default='registered',
        tracking=True
    )
    amount_paid = fields.Float(
        'Valor pagado total',
        compute="get_amount_paid",
        store=True,
        tracking=True
    )
    name = fields.Char(
        string='Nombre',
        required=True, copy=False, readonly=True,
        index='trigram',
        states={'draft': [('readonly', False)]},
        default=lambda self: self._DEFAULT_NAME,
        tracking=True
    )
    reject_note = fields.Text(
        string='Motivo de rechazo',
        tracking=True
    )
    claim_number = fields.Char(
        string=u'Número de reclamo',
        tracking=True
    )
    additional_info = fields.Text(
        string=u'Observaciones',
        tracking=True
    )
    notice_claim_id = fields.Many2one(
        'broker.claim.notice',
        u'Aviso de siniestro'
    )
    contract_id = fields.Many2one(
        'broker.contract',
        string='Contrato',
        required=True,
        tracking=True
    )
    branch_id = fields.Many2one(
        'broker.branch',
        related='contract_id.branch_id',
        store=True,
        string='Ramo'
    )
    insurer_id = fields.Many2one(
        'res.partner',
        related='contract_id.insurer_id',
        store=True,
        string='Aseguradora'
    )
    document_ids = fields.One2many(
        "broker.claim.document",
        "claim_id",
        string="Documentos"
    )
    line_ids = fields.One2many(
        "broker.claim.line",
        "claim_id",
        string="Bitácora"
    )
    tag_ids = fields.Many2many(
        'broker.claim.tag',
        'claim_tag_rel',
        'claim_id',
        'tag_id',
        string='Etiquetas'
    )
    deductible_id = fields.Many2one(
        "broker.object.deductible",
        string="Deducible",
        tracking=True
    )
    client_id = fields.Many2one(
        'res.partner',
        'Cliente',
        required=True,
        tracking=True
    )
    coverage_line_id = fields.Many2one(
        "agreements.insurer.line",
        string="Cobertura",
    )
    amount_insured = fields.Float(
        related="coverage_line_id.amount_insured",
        string="Valor Asegurado"
    )
    object_id = fields.Many2one(
        "broker.movement.object",
        string="Objeto Asegurado",
        tracking=True
    )
    is_group = fields.Boolean(
        string="Agrupador"
    )
    parent_claim_id = fields.Many2one(
        "broker.claim",
        string="Siniestro Principal"
    )
    child_claim_ids = fields.One2many(
        "broker.claim",
        "parent_claim_id",
        string="Coberturas"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            if vals.get('name', self._DEFAULT_NAME) == self._DEFAULT_NAME:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.today())
                vals['name'] = self.env['ir.sequence'].next_by_code('broker.claim', sequence_date=seq_date) or self._DEFAULT_NAME
        return super().create(vals_list)

    @api.onchange("contract_id", "object_id")
    def _get_domain_object(self):
        res = {"domain": {}}
        if self.contract_id:
            object_ids = self.contract_id.contract_object_ids.ids
            res['domain']['object_id'] = [('id', 'in', object_ids)]
            actual_object_id = self.object_id.id
            self.object_id = False if actual_object_id not in object_ids else actual_object_id
        else:
            self.object_id = False
            self.deductible_id = False
        if self.object_id:
            agree_accept = self.object_id.agreements_line_ids.filtered(lambda mov: mov.state == 'accept')
            if agree_accept:
                lines = agree_accept[0].agreement_id.mapped("agreements_line_ids").filtered(
                    lambda line: line.is_coverage)
                res['domain']['coverage_line_id'] = [('id', 'in', lines.ids)]
            actual_deductible_id = self.deductible_id.id
            self.deductible_id = False if actual_deductible_id not in self.object_id.deductible_ids.ids else actual_deductible_id
        return res

    @api.onchange('client_id')
    def _onchange_client(self):
        ctxt = self.env.context
        if not ctxt.get("default_contract_id"):
            self.contract_id = False

    def action_view_notice_claim(self):
        self.ensure_one()
        template = self.env.ref('broker_do.crm_claim_notice_form')
        if not self.notice_claim_id:
            raise ValidationError("No existe un aviso de siniestro Asociado")
        return {
            'name': 'Aviso de Siniestro',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.notice_claim_id.id,
            'res_model': 'broker.claim.notice',
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'self',
        }

    def action_insurer(self):
        for this in self:
            compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
            ctx = dict(
                default_model='broker.claim',
                default_res_id=this.id,
                default_partner_ids=this.contract_id.insurer_id.ids,
                default_composition_mode='comment',
                default_email_layout_xmlid='mail.mail_notification_light',
                mark_coupon_as_sent=True,
                force_email=True,
            )
            return {
                'name': 'Remitir Aseguradora',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }

    def action_paid(self):
        for this in self:
            this.state = 'paid'

    def action_documented(self):
        for this in self:
            this.state = 'documented'

    def action_rejected(self):
        template = self.env.ref('broker_do.wizard_notice_message_form')
        return {
            'name': 'Siniestro',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'context': {'claim_id': self.id, 'reject_message': True},
            'res_model': 'wizard.notice.message',
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'new',
        }


class BrokerClaimDocument(models.Model):
    _name = 'broker.claim.document'

    claim_id = fields.Many2one(
        'broker.claim',
        string="Siniestro"
    )
    file = fields.Binary(
        string="Archivo",
        attachment=True
    )
    filename = fields.Char(
        string="Nombre del Archivo"
    )
    state = fields.Selection([
        ("receipt", "Recibido"),
        ("insurer", "En Aseguradora"),
    ], default="receipt",
        string="Estado Documento"
    )
    invoice_number = fields.Char(
        string="Número de Factura"
    )


class BrokerClaimLine(models.Model):
    _name = "broker.claim.line"

    claim_id = fields.Many2one(
        'broker.claim',
        string="Siniestro"
    )
    type = fields.Selection([
        ("pay", "Pago"),
        ("scope", "Alcance"),
        ("adjustment", "Ajuste"),
    ], string="Tipo",
        default="pay",
        required=True
    )
    date = fields.Date(
        string="Fecha",
        default=lambda self: fields.Date.today()
    )
    value = fields.Float(
        string="Valor"
    )
    comment = fields.Text(
        string="Observación"
    )


class BrokerClaimTag(models.Model):
    _name = "broker.claim.tag"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(
        string='Etiqueta',
        required=True,
        translate=True
    )
    color = fields.Integer(
        string='Color',
        default=_get_default_color
    )

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
