# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from ast import literal_eval


class ResPartnerType(models.Model):
    _name = 'res.partner.type'

    name = fields.Char(
        string="Nombre"
    )
    default_value = fields.Boolean(
        string="Por defecto"
    )
    internal_scope = fields.Boolean(
        string='Interno'
    )


class ResPartner(models.Model):
    _inherit = 'res.partner'

    full_lastname = fields.Char(
        'Apellidos'
    )
    business_group = fields.Boolean(
        string="¿Pertenece al grupo?"
    )
    withhold_emission = fields.Boolean(
        string="¿Se emite retención?"
    )
    full_name = fields.Char(
        'Nombres'
    )
    neighborhood = fields.Char(
        'Barrio/Sector'
    )
    shortname = fields.Char(
        'Nombre corto aseguradora'
    )
    claim_count = fields.Integer(
        "Siniestros",
        compute='_compute_claim_count'
    )
    contract_count = fields.Integer(
        u"Contratos",
        compute='_compute_contract_count'
    )
    partner_type_id = fields.Many2many(
        'res.partner.type',
        string="Tipo de Entidad",
        default=lambda self: self._default_partner_type()
    )
    zone_id = fields.Many2one(
        'res.zone',
        string='Zona'
    )
    contact_name = fields.Char(
        "Nombre de contacto"
    )
    contact_phone = fields.Char(
        "Número de contacto"
    )
    gender = fields.Selection(
        [
            ('male', 'Masculino'),
            ('female', 'Femenino'),
            ('other', 'Otros')
        ],
        string=u"Género"
    )
    birthdate = fields.Date(
        'Fecha de nacimiento'
    )
    establish_date = fields.Date(
        'Fecha de constitución'
    )
    contract_ids = fields.One2many(
        'broker.contract',
        'client_id',
        u"Contratos"
    )

    def _default_partner_type(self):
        default_id = self.env['res.partner.type'].search([('default_value', '=', True),
                                                          ('internal_scope', '=', True)
                                                          ], limit=1)
        if 'internal_scope' in self.env.context and not self.env.context.get('internal_scope'):
            default_id = self.env['res.partner.type'].search([('default_value', '=', True),
                                                              ('internal_scope', '=', False)
                                                              ], limit=1)
        if default_id:
            return [(4, [default_id.id])]

    @api.onchange('street', 'street2')
    def onchange_street(self):
        self.street = self.street and self.street.upper() or ''
        self.street2 = self.street2 and self.street2.upper() or ''

    @api.onchange('city')
    def onchange_city(self):
        self.city = self.city and self.city.upper() or ''

    @api.onchange('neighborhood')
    def onchange_neighborhood(self):
        self.neighborhood = self.neighborhood and self.neighborhood.upper() or ''

    @api.onchange('contact_name')
    def onchange_contact_name(self):
        self.contact_name = self.contact_name and self.contact_name.upper() or ''

    @api.onchange('name')
    def onchange_name(self):
        self.name = self.name and self.name.upper() or ''

    @api.onchange('full_name', 'full_lastname')
    def onchange_names(self):
        fields = ['full_lastname', 'full_name']
        self.full_name = self.full_name and self.full_name.upper() or ''
        self.full_lastname = self.full_lastname and self.full_lastname.upper() or ''
        onchange_data = [self[f] for f in fields if self[f]]
        self.name = ' '.join(onchange_data)

    def _compute_claim_count(self):
        for partner in self:
            partner.claim_count = self.env['broker.claim'].search_count(
                [('notice_claim_id.client_id', '=', partner.id)]
            )

    def _compute_contract_count(self):
        for partner in self:
            partner.contract_count = len(partner.contract_ids)

    def action_view_claim_client(self):
        self.ensure_one()
        action = self.env.ref('broker_do.crm_claim_notice_action_new').read()[0]
        if 'domain' in action:
            action['domain'] = literal_eval(str(action.get('domain') or []))
        action['domain'].append(('client_id', 'child_of', self.id))
        return action

    def action_view_contract(self):
        self.ensure_one()
        action = self.env.ref('broker_do.broker_contract_action').read()[0]
        action['domain'] = []
        if 'domain' in action:
            action['domain'] = literal_eval(str(action['domain'] or []))
        action['domain'].append(('client_id', 'child_of', self.id))
        return action


class ResZone(models.Model):
    _name = 'res.zone'

    name = fields.Char(
        string="Nombre"
    )
