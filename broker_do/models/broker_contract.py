# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError
from itertools import groupby
from dateutil.relativedelta import relativedelta
from datetime import datetime

_OPTIONS_PAYMENT = [
    ('monthly', 'Normal'),
    ('annully_comision', u'Plurianual'),
]
_FIELDS_PERIOD_CHANGE = ["period_type", "date_start", "date_end"]


class BrokerContract(models.Model):
    _name = 'broker.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection(
        [
            ('draft', 'Pendiente'),
            ('valid', 'Vigente'),
            ('not_valid', 'No vigente'),
        ],
        'Estado',
        default='draft',
        tracking=True
    )
    name = fields.Char(
        'Nombre',
        store=True,
        compute='_compute_name',
        tracking=True
    )
    contract_num = fields.Char(
        'Número de contrato',
        tracking=True
    )
    date_start = fields.Date(
        'Inicio de vigencia',
        tracking=True
    )
    date_end = fields.Date(
        'Fin de vigencia',
        tracking=True
    )
    day_number = fields.Integer(
        'No. de días',
        compute='_compute_day_number'
    )
    open_date_contract = fields.Boolean(
        u'Póliza abierta',
    )
    commission_percentage = fields.Float(
        u'Porcentaje de comisión',
        tracking=True
    )
    amount_accumulate_claim = fields.Float(
        u'Valor acumulado de siniestros'
    )
    is_grouper_policy = fields.Boolean(
        'Es póliza corporativa/agrupadora?'
    )
    amount_accumulate_due = fields.Float(
        u'Valor de contrato faltante',
        compute='_compute_amount_accumulate_due'
    )
    annex_num = fields.Char(
        string=u'Número de anexo',
        tracking=True
    )
    branch_id = fields.Many2one(
        'broker.branch',
        'Ramo',
        domain=lambda self: self._get_branch_id_domain(),
        tracking=True
    )
    insurer_id = fields.Many2one(
        'res.partner',
        'Aseguradora',
        tracking=True
    )
    client_id = fields.Many2one(
        'res.partner',
        'Cliente',
        tracking=True
    )
    claim_notice_ids = fields.One2many(
        'broker.claim.notice',
        'contract_id',
        string='Siniestros'
    )
    movement_ids = fields.One2many(
        "sale.order",
        "contract_id",
        string="Anexos"
    )
    commission_ids = fields.One2many(
        "sale.order.line",
        compute='_compute_commission_ids',
        string="Comisiones"
    )
    contract_fee_ids = fields.One2many(
        'broker.contract.fee',
        'contract_id',
        string='Cuotas del contrato',
    )
    stakeholder_ids = fields.One2many(
        'broker.movement.stakeholder',
        string='Actores',
        compute='_compute_stakeholder_ids',
    )
    business_id = fields.Many2one(
        "broker.business",
        string="Línea de negocio"
    )
    agreement_ids = fields.One2many(
        "agreements.insurer",
        "contract_id",
        string="Acuerdos aceptados"
    )
    contract_object_ids = fields.One2many(
        "broker.movement.object",
        'contract_id',
        string="Objetos asegurados",
    )
    user_id = fields.Many2one(
        string='Ejecutivo de ventas',
        comodel_name='res.users',
        copy=False,
        tracking=True,
        default=lambda self: self.env.user,
    )
    lead_id = fields.Many2one(
        "crm.lead",
        string="Oportunidades"
    )
    parent_contract_id = fields.Many2one(
        "broker.contract",
        string="Contrato inicial"
    )
    container_id = fields.Many2one(
        'broker.contract.container',
        name="Póliza maestra",
        tracking=True
    )
    version = fields.Integer(
        string=u"Número de renovación",
        default=1,
        tracking=True
    )
    in_renewal = fields.Boolean(
        string=u"¿En proceso de renovación?",
        default=False
    )
    commission_insurer_id = fields.Many2one(
        "broker.commission.insurer",
        string="Contrato de agenciamiento asociado"
    )
    num_insured_items = fields.Float(
        string="No. Items asegurados",
        tracking=True
    )
    period_type = fields.Selection(
        [
            ("1", "Mensual"),
            ("3", "Trimestral"),
            ("6", "Semestral"),
            ("12", "Anual"),
        ],
        string="Tipo de Periodo",
        required=True,
        default="1",
        tracking=True
    )
    period_ids = fields.One2many(
        "broker.contract.period",
        "contract_id",
        string="Periodos",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Calculo de periodos al crear una poliza"""
        res = super(BrokerContract, self).create(vals_list)
        for record in res:
            record.compute_type_period()
        return res

    def write(self, vals):
        """Calculo de periodos al borrador"""
        res = super(BrokerContract, self).write(vals)
        if [x for x in _FIELDS_PERIOD_CHANGE if x in vals]:
            for record in self:
                record.compute_type_period()
        return res

    def unlink(self):
        """Control para no eliminar polizas que no estan en borrador"""
        not_draft_contract_ids = self.filtered(lambda record: record.state != 'draft')
        if not_draft_contract_ids:
            raise ValidationError(
                u'No se puede eliminar contratos que no esten en estado borrador.\nLos contratos que no estan en '
                u'estado "Borrador" son: \n-\t{}'.format(
                    '\n\t- '.join(not_draft_contract_ids.mapped('name'))
                )
            )
        return super(BrokerContract, self).unlink()

    def compute_type_period(self):
        def distance_month(date_start, date_end):
            """Permite obtener los meses de distancia entre dos fechas"""
            fecha_inicial = datetime.strptime(date_start, "%Y-%m-%d")
            fecha_final = datetime.strptime(date_end, "%Y-%m-%d")
            range_month = (fecha_final.year - fecha_inicial.year) * 12 + fecha_final.month - fecha_inicial.month
            return range_month

        for record in self:
            record.period_ids.unlink()
            lines = []
            if record.date_start and record.date_end:
                date_from = self.date_start
                month = distance_month(str(record.date_start), str(record.date_end))
                range_end = int(month / int(record.period_type) + 1)
                for val in range(1, range_end):
                    name = date_from.strftime('%B').upper() + ' /' + str(date_from.year)
                    date_to = date_from + relativedelta(months=int(record.period_type), days=-1)
                    lines.append(Command.create({
                        "sequence": val,
                        "date_from": date_from,
                        "date_to": date_to,
                        "name": name,
                    }))
                    date_from = date_to + relativedelta(days=1)
            record.period_ids = lines

    def _compute_amount_accumulate_due(self):
        for record in self:
            record.amount_accumulate_due = sum(
                record.movement_ids.mapped('fee_line_ids').mapped('amount_insurance_due'))

    def _compute_commission_ids(self):
        for record in self:
            record.commission_ids = [Command.set(record.movement_ids.mapped('order_line').ids)]

    @api.depends('date_start', 'date_end')
    def _compute_day_number(self):
        for record in self:
            if record.date_end and record.date_start:
                record.day_number = (record.date_end - record.date_start).days
            else:
                record.day_number = 0

    def _onchange_contract_fee_ids(self):
        for record in self:
            if record.contract_fee_ids.filtered(lambda x: x.status_fee != 'no_payment'):
                raise ValidationError(
                    u"No se puede recomputar cuotas que ya han sido pagadas, por favor identifíquelas y cancele los "
                    u"pagos y cruces antes de proceder con el recálculo de las cuotas de cartera."
                )
            record = record._origin if record._origin else record
            contract_fee_ids_operations = [fields.Command.delete(fee_id.id) for fee_id in
                                           record.contract_fee_ids.filtered(lambda x: x.status_fee == 'no_payment')]
            fee_line_ids = record.movement_ids.mapped('fee_line_ids').filtered(lambda x: x.status_fee == 'no_payment')
            list_create = []
            if fee_line_ids:
                groups = {}
                fee_line_order = sorted(fee_line_ids, key=lambda x: x.period_id.id)
                for key, group in groupby(fee_line_order, key=lambda x: x.period_id.id):
                    groups[key] = list(group)
                cont = len(record.contract_fee_ids)
                for name_group, fee_lines in groups.items():
                    status_fee = [line.status_fee for line in fee_lines]
                    if len(list(set(status_fee))) > 1:
                        status = 'partial_payment'
                    else:
                        status = status_fee[0]
                    cont += 1
                    res = {
                        "sequence": cont,
                        "period_id": name_group,
                        "provisional_payment_date": fee_lines[0].provisional_payment_date,
                        "amount_insurance_due": sum(
                            [line.amount_insurance_due for line in fee_lines if line.amount_insurance_due >= 0.0]),
                        "amount_insurance_due_negative": sum(
                            [line.amount_insurance_due for line in fee_lines if line.amount_insurance_due < 0.0]),
                        "status_fee": status,
                        "fee_line_ids": [fields.Command.set([line.id for line in fee_lines])]
                    }
                    list_create.append(fields.Command.create(res))
            contract_fee_ids_operations.extend(list_create)
            record.contract_fee_ids = contract_fee_ids_operations
            record.contract_fee_ids._compute_quotas_positive_negative()

    def _compute_stakeholder_ids(self):
        for record in self:
            record.stakeholder_ids = [Command.set(record.movement_ids.mapped('stakeholder_ids').ids)]

    @api.depends("branch_id", "contract_num", "version")
    def _compute_name(self):
        for this in self:
            branch_code = this.branch_id and this.branch_id.code or ""
            contract_num = this.contract_num or ''
            this.name = " - ".join([branch_code, contract_num, str(this.version)])

    def _compute_object_ids(self):
        for record in self:
            type_exclude = self.env.ref("broker_do.exclusion_movement")
            moves_exclude = record.movement_ids.filtered(lambda mov: mov.type_id.id == type_exclude.id)
            objects_exclude = moves_exclude.mapped("object_line_ids.object_id")
            movements = record.movement_ids.filtered(lambda mov: not mov.type_id.id == type_exclude.id)
            objects = movements.mapped("object_line_ids")
            objects_final = [obj.id for obj in set(objects - objects_exclude)]
            record.contract_object_ids = [Command.set(objects_final)]

    def _get_branch_id_domain(self):
        res = [('id', '=', 0)]
        params = self.env.context.get('params', {})
        if self and self.insurer_id or (params.get('model') == 'broker.contract' and params.get('id')):
            contract_id = self or self.browse(params.get('id'))
            commission_id = self.env['broker.commission.insurer'].search([
                ('date_start', '<=', fields.Date.today()),
                ('date_end', '>=', fields.Date.today()),
                ('insurer_id', '=', contract_id.insurer_id.id),
            ])
            if commission_id:
                res = [('id', 'in', commission_id.commission_line_ids.mapped('branch_id').ids)]
        return res

    @api.onchange('insurer_id', 'branch_id')
    def onchange_insurance_company(self):
        res = {'domain': {'branch_id': [('id', 'in', 0)]},
               'value': {'branch_id': False}}
        if self.insurer_id:
            commission_id = self.env['broker.commission.insurer'].search([
                ('insurer_id', '=', self.insurer_id.id),
            ])
            if commission_id:
                self.commission_insurer_id = commission_id.id
                res['domain'] = {'branch_id': [('id', 'in', commission_id.commission_line_ids.mapped('branch_id').ids)]}
                res['value'] = {'branch_id': self.branch_id.id}
                perc_value = commission_id.commission_line_ids.filtered(lambda x: x.branch_id == self.branch_id).mapped(
                    'percentage_value')
                self.commission_percentage = perc_value and sum(perc_value) or self.commission_percentage or 0
            else:
                res['warning'] = {'title': 'Advertencia', 'message':
                    "No existe un contrato de agenciamiento asociado con la aseguradora {insurer}".format(
                        insurer=self.insurer_id.name)}
        return res

    @api.onchange('open_date_contract')
    def onchange_open_date_contract(self):
        if self.open_date_contract:
            self.period_type = '12'

    @api.onchange('date_start')
    def onchange_date_start(self):
        if self.date_start:
            self.date_end = self.date_start + relativedelta(months=12, days=-1)
            type = self.env.ref("broker_do.policy_movement")
            for line in self.movement_ids.filtered(lambda x: x.type_id.id == type.id):
                line.date_start = self.date_start
                line.date_end = self.date_end

    def _send_email_contract_expired(self):
        date = fields.Date.today()
        mail_template = self.env.ref('broker_do.mail_template_send_email_expired_contract')
        contract_obj = self.env['broker.contract'].sudo()
        contracts = contract_obj.search([('state', '=', 'valid'), ('date_end', '=', date)])
        for contract in contracts:
            mail_template.send_mail(contract.id)
            contract.state = 'not_valid'

    def action_view_leads(self):
        lead_obj = self.env['crm.lead'].sudo()
        for this in self:
            lead_renewal = lead_obj.search([('renewal_id', '=', this.id)])
            lead_ids = this.lead_id.ids + lead_renewal.ids
            action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_action_pipeline")
            action['domain'] = [('id', 'in', lead_ids)]
            action['context'] = {
                'active_test': False,
                'create': False
            }
            return action

    def create_renewal_contract(self):
        crm_lead_obj = self.env['crm.lead']
        mail_template_client = self.env.ref('broker_do.mail_template_send_email_client_renewal_contract')
        mail_template_insurer = self.env.ref('broker_do.mail_template_send_email_contract_insurer')
        list_lead = []
        for contract in self:
            mail_template_client.send_mail(contract.id)
            mail_template_insurer.send_mail(contract.id)
            res = {
                "name": "Renovación Contrato: %s - %s" % (contract.name, contract.client_id.name),
                "partner_id": contract.client_id.id,
                "stage_id": self.env.ref("broker_do.stage_lead5").id,
                "branch_id": contract.branch_id.id,
                "is_renewal": True,
                "renewal_id": contract.id,
                "type": "opportunity",
                "user_id": contract.user_id.id,
                "business_id": contract.business_id.id,
            }
            crm = crm_lead_obj.create(res)
            for object_id in contract.contract_object_ids:
                object_id.copy({
                    "lead_id": crm.id
                })
            list_lead.append(crm.id)
            contract.in_renewal = True
        return {
            'name': 'Oportunidad',
            'type': 'ir.actions.act_window',
            'view_type': 'kanban,tree,form',
            'view_mode': 'kanban,tree,form',
            'res_model': 'crm.lead',
            'domain': [('id', 'in', list_lead)],
            'target': 'self',
        }

    def get_period_from_date(self, date):
        self.ensure_one()
        if not self.period_ids:
            raise ValidationError("Error deben existir periodos asociados al contrato")
        period = self.period_ids.filtered(lambda period: period.date_from <= date <= period.date_to).sorted('date_from')
        if not period:
            raise ValidationError("Periodo no encontrado para la fecha: {date}".format(date=str(date)))
        return period[0].id

    def get_next_period(self, period_id):
        find_per = False
        for per_id in self.period_ids.sorted(key=lambda x: x.date_from):
            if per_id.id == period_id:
                find_per = True
                continue
            if find_per:
                return per_id
        raise ValidationError(u'Es el último periodo no existe siguiente')

    def get_previous_period(self, period_id):
        period_prev_per = False
        for per_id in self.period_ids.sorted(key=lambda x: x.date_from):
            if per_id.id == period_id and period_prev_per:
                return period_prev_per
            period_prev_per = per_id
        raise ValidationError(u'Es el primer periodo no existe anterior')

    def action_valid_contract(self):
        for record in self:
            record.state = 'valid'
            for movement_id in record.movement_ids:
                movement_id.action_confirm()

    def action_draft(self):
        for record in self:
            record.state = 'draft'

    def action_open_contract(self):
        template = self.env.ref('broker_do.broker_contract_form')
        return {
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'res_model': 'broker.contract',
            'view_mode': 'form',
            'views': [(template.id, 'form')],
        }

    def link_to_container(self):
        insurer_id = self.mapped('insurer_id')
        if len(insurer_id) > 1:
            raise ValidationError('No se pueden vincular a pólizas maestras, contratos con diferentes aseguradoras.')
        return {
            'name': 'Vincular con póliza maestra',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.link.container',
            'context': {'default_insurer_id': insurer_id.id, 'default_contract_ids': self.ids},
            'target': 'new',
        }


class BrokerContractFee(models.Model):
    _name = 'broker.contract.fee'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string="Nombre de la cuota",
        store=True,
        compute='_compute_name'
    )
    period_id = fields.Many2one(
        "broker.contract.period",
        ondelete='restrict',
        string="Periodo"
    )
    period_date_from = fields.Date(
        string="Desde",
        related="period_id.date_from"
    )
    period_date_to = fields.Date(
        string="Hasta",
        related="period_id.date_to"
    )
    invoice_number = fields.Char(
        string=u'Número de factura',
        store=True,
        compute='_compute_name'
    )
    sequence = fields.Integer(
        string="No. de cuota"
    )
    contract_id = fields.Many2one(
        'broker.contract',
        ondelete='cascade',
        name="Contrato"
    )
    partner_contract_id = fields.Many2one(
        'res.partner',
        related='contract_id.client_id',
        ondelete='restrict',
        store=True
    )
    branch_id = fields.Many2one(
        'broker.branch',
        related='contract_id.branch_id',
        ondelete='restrict',
        store=True
    )
    annex_num = fields.Char(
        related='contract_id.annex_num',
        store=True
    )
    status_due = fields.Selection(
        [
            ('outstanding', 'Por vencer'),
            ('overdue', 'Vencido'),
            ('paid', 'Pagado'),
        ],
        string='Estado de cuota',
        default='outstanding',
        store=True,
        compute='_compute_status_due'
    )
    amount_insurance_due = fields.Float(
        string='Cuota del seguro (+)'
    )
    amount_insurance_due_negative = fields.Float(
        string='Cuota del seguro (-)'
    )
    status_fee = fields.Selection(
        [
            ('no_payment', 'Por pagar'),
            ('partial_payment', 'Parcialmente pagada'),
            ('paid', 'Pagada'),
        ],
        string=u'Estado del pago de la cuota',
        store=True,
        default='no_payment',
        compute='_compute_status_payment'
    )
    balance_due = fields.Float(
        string='Saldo de cuota del seguro (+)',
        store=True,
        compute='_compute_status_payment'
    )
    balance_due_negative = fields.Float(
        string='Saldo de cuota del seguro (-)',
        store=True,
        compute='_compute_quotas_positive_negative'
    )
    partner_contract_id = fields.Many2one(
        'res.partner',
        related='contract_id.client_id',
        ondelete='restrict',
        store=True
    )
    fee_line_ids = fields.One2many(
        'sale.order.fee',
        'contract_fee_id',
        string='Cuotas del contrato',
    )
    payment_fee_line_ids = fields.One2many(
        'sale.order.fee.payment',
        'fee_id',
        string='Lineas de pago',
    )
    provisional_payment_date = fields.Date(
        string='Fecha de vencimiento'
    )
    payment_ids = fields.Many2many(
        'fee.payment',
        'payment_contract_fee_rel',
        'contract_fee_id',
        'payment_id',
        string='Cuotas por movimientos',
        ondelete='restrict',
    )
    positive_quota_cross_ids = fields.One2many(
        'broker.quota.cross.positive',
        "contract_fee_id",
        string="Cruces Positivos",
        domain=lambda self: [('state', '=', 'posted'), ('check', '=', True)],
    )
    negative_quota_cross_ids = fields.One2many(
        'broker.quota.cross.negative',
        "contract_fee_id",
        string="Cruces Negativos",
        domain=lambda self: [('state', '=', 'posted'), ('check', '=', True)],
    )

    @api.depends("positive_quota_cross_ids", "fee_line_ids")
    def _compute_quotas_positive_negative(self):
        for this in self:
            value = sum(this.positive_quota_cross_ids.mapped("value_cross"))
            this.balance_due = this.amount_insurance_due - value
            value = sum(this.negative_quota_cross_ids.mapped("value_cross"))
            this.balance_due_negative = this.amount_insurance_due_negative + value

    @api.depends('fee_line_ids.invoice_number', 'fee_line_ids.name')
    def _compute_name(self):
        for record in self:
            record.name = '[' + (record.contract_id.name or '') + '] - ' + (str(record.sequence) or '1')
            record.invoice_number = ','.join([x for x in record.fee_line_ids.mapped('invoice_number') if x])

    @api.depends('fee_line_ids.status_fee')
    def _compute_status_payment(self):
        for record in self:
            if record.fee_line_ids:
                status_fee = list(set(record.fee_line_ids.mapped('status_fee')))
                if len(status_fee) > 1:
                    status = 'partial_payment'
                else:
                    status = status_fee[0]
                record.status_fee = status
            record.balance_due = record.amount_insurance_due - sum(
                record.payment_fee_line_ids.filtered(lambda x: x.payment_id.status == 'paid').mapped('amount_paid'))

    @api.depends('provisional_payment_date')
    def _compute_status_due(self):
        for record in self:
            if not record.status_fee == 'paid':
                if record.provisional_payment_date < fields.Date.context_today(record):
                    record.status_due = 'overdue'
            else:
                record.status_due = 'paid'

    def action_pay_fee_line(self):
        return {
            'context': {
                'default_partner_id': self.contract_id.client_id.id,
                'default_name': 'Pago ' + self.name,
                'default_sale_fee_payment_ids': [fields.Command.create({'fee_id': self.id,
                                                                        'amount_paid': self.balance_due})]
            },
            'name': "Cuotas",
            'type': 'ir.actions.act_window',
            'res_model': 'fee.payment',
            'view_mode': 'form',
            'target': 'new'
        }

    def action_open_broker_fee(self):
        return {
            'name': "Cuotas",
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.fee',
            'view_mode': 'tree',
            'domain': [('id', 'in', self.fee_line_ids.ids)]
        }


class BrokerContractPeriod(models.Model):
    _name = 'broker.contract.period'

    name = fields.Char(
        string="Nombre"
    )
    sequence = fields.Integer(
        string="Nro Periodo"
    )
    date_from = fields.Date(
        string="Desde"
    )
    date_to = fields.Date(
        string="Hasta"
    )
    contract_id = fields.Many2one(
        "broker.contract",
        ondelete='cascade',
        string="Contrato Asociado"
    )
