import re

from odoo import models, api, fields
from odoo.exceptions import UserError, ValidationError

import time
import base64
import io
import os
from jinja2 import Environment, FileSystemLoader
from lxml import etree
STD_FORMAT = '%Y-%m-%d'
tpIdProv = {
    'RUC': '01',
    'Cédula': '02',
    'Pasaporte': '03',
}
tpIdCliente = {
    'RUC': '04',
    'Cédula': '05',
    'Pasaporte': '06',
    'venta_consumidor_final': '07'
}


class AccountAts(dict):

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, item, value):
        if item in self.__dict__:
            dict.__setattr__(self, item, value)
        else:
            self.__setitem__(item, value)


class L10nEcAtsWizard(models.TransientModel):
    _name = 'l10n_ec.ats.wizard'
    _description = 'Anexo Transaccional Simplificado (ATS)'

    def _compute_establishment_selection(self):
        journals = self.env['account.journal'].search([('l10n_ec_entity', '!=', False)])
        entity_lst = []
        for journal in journals:
            if journal.l10n_ec_entity not in entity_lst:
                entity_lst.append(journal.l10n_ec_entity)
        return [(entity, entity) for entity in entity_lst] if entity_lst else []

    date_from = fields.Date(
        string="Desde",
    )
    date_to = fields.Date(
        string="Hasta"
    )
    file = fields.Binary(
        name="Archivo"
    )
    filename = fields.Char(
        string="Nombre del Archivo"
    )
    establishment_number = fields.Selection(
        _compute_establishment_selection,
        string="Establecimiento"
    )
    company_id = fields.Many2one(
        'res.company',
        string=u'Compañía',
        default=lambda self: self.env.user.company_id
    )
    no_validate = fields.Boolean(
        'Sin Validación?'
    )
    electronic_invoice = fields.Boolean(
        string="Añadir Facturas Electrónicas"
    )
    state = fields.Selection(
        (
            ('choose', 'Elegir'),
            ('export', 'Generado'),
            ('export_error', 'Error')
        ),
        string='Estado',
        default='choose'
    )

    def get_date_value(self, date, t='%Y'):
        return time.strftime(t, time.strptime(str(date), STD_FORMAT))

    def create_report(self):
        ats = AccountAts()
        for this in self:
            company = this.company_id
            if company.country_id.code != "EC":
                raise ValidationError("El reporte ATS solo está permitido para empresas ecuatorianas!")
            ats.IdInformante = company.vat
            ats.TipoIDInformante = 'R'
            date_from = this.date_from
            ats.razonSocial = company.l10n_ec_legal_name
            ats.Anio = this.get_date_value(date_from, '%Y')
            ats.Mes = this.get_date_value(date_from, '%m')
            ats.numEstabRuc = self.establishment_number
            #Electronic sales no longer reported
            ats.totalVentas = '0.00'
            ats.codigoOperativo = 'IVA'
            ats.compras = self.get_purchase()
            ats.ventas = self.get_sale()
            ats.codEstab = self.establishment_number
            ats.ventasEstab = self.get_sale_establishment()
            ats.ivaComp = '0.00'
            ats.anulados = self.read_cancelled()
            ats_rendered = self.render_xml(ats)
            ok, schema = self.validate_document(ats_rendered.encode())
            if not ok:
                raise UserError(schema.error_log)
            buf = io.BytesIO()
            buf.write(ats_rendered.encode())
            out = base64.b64encode(buf.getvalue())
            buf.close()
            buf_erro = io.BytesIO()
            for error in schema.error_log:
                buf_erro.write(error.message.encode())
            out_erro = base64.b64encode(buf_erro.getvalue())
            buf_erro.close()
            name = "ATS.XML"
            data2save = {
                'state': ok and 'export' or 'export_error',
                'file': out,
                'filename': name
            }
            if not ok:
                data2save.update({
                    'error_data': out_erro,
                    'fcname_errores': 'ERRORES.txt'
                })
            self.write(data2save)
            return {
                'context': self.env.context,
                'name': 'Reporte ATS',
                'res_model': 'l10n_ec.ats.wizard',
                'view_mode': ' form',
                'view_type': ' form',
                'res_id': self.id,
                'views': [(False, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    def _compute_vat_withhold_value(self, grouped_lines, percent):
        return sum(grouped_lines.filtered(lambda line: line.tax_ids[0].tax_group_id.l10n_ec_type == 'withhold_vat_purchase'
                                                       and abs(line.tax_ids[0].amount) == percent).mapped('l10n_ec_withhold_tax_amount'))

    def _get_vat_withhold_data(self, grouped_lines):
        valRetBien10 = self._compute_vat_withhold_value(grouped_lines, 10)
        valRetServ20 = self._compute_vat_withhold_value(grouped_lines, 20)
        valorRetBienes = self._compute_vat_withhold_value(grouped_lines, 30)
        valorRetServ50 = self._compute_vat_withhold_value(grouped_lines, 50)
        valorRetServicios = self._compute_vat_withhold_value(grouped_lines, 70)
        valorRetServ100 = self._compute_vat_withhold_value(grouped_lines, 100)

        return valRetBien10, valRetServ20, valorRetBienes, valorRetServ50, valorRetServicios, valorRetServ100

    def _get_profit_withhold_data(self, grouped_lines, purchase_amount_untaxed):
        profit_withhold_line = grouped_lines.filtered(lambda line: line.tax_ids[0].tax_group_id.l10n_ec_type == 'withhold_income_purchase')
        if profit_withhold_line:
            profit_wh_tax = profit_withhold_line.mapped('tax_ids')[0]
            codRetAir = profit_wh_tax.l10n_ec_code_ats
            baseImpAir = profit_withhold_line.balance
            porcentajeAir = round(abs(profit_wh_tax.amount),2)
            valRetAir = profit_withhold_line.l10n_ec_withhold_tax_amount
        else:
            codRetAir = '332'
            baseImpAir = purchase_amount_untaxed
            porcentajeAir = 0.00
            valRetAir = 0.00

        return codRetAir, baseImpAir, porcentajeAir, valRetAir

    def get_refund(self, move):
        if move.reversed_entry_id:
            reversed_auth_num = move.reversed_entry_id.l10n_ec_authorization_number if move.reversed_entry_id.l10n_ec_authorization_number else '9999999999'
            credit_note_vals = {
                    'docModificado': move.reversed_entry_id.l10n_latam_document_type_id.code,
                    'estabModificado': move.reversed_entry_id.sequence_prefix[-8:-5],
                    'ptoEmiModificado': move.reversed_entry_id.sequence_prefix[-4:-1],
                    'secModificado': str(move.reversed_entry_id.sequence_number).zfill(9),
                    'autModificado': reversed_auth_num,
                }
        else:
            error_msg = u"""Error al tratar de obtener los datos de la Nota de crédito: %s, con referencia %s. \n
                            El campo referencia factura debe contener el número de la factura (en formato XXX-XXX-XXXXXXXXX donde X en un valor numérico)
                            a la que esta afectando la Nota de crédito""" % (move.name, move.ref)
            try:
                regex = "\d{3}-\d{3}-\d{9}"
                reversed_doc_number = re.findall(regex, move.ref)
                if not reversed_doc_number:
                    raise ValidationError(error_msg)
                else:
                    reversed_doc_number = reversed_doc_number[0]
                credit_note_vals = {
                    'docModificado': '01',
                    'estabModificado': reversed_doc_number[0:3],
                    'ptoEmiModificado': reversed_doc_number[4:7],
                    'secModificado': reversed_doc_number[-9:],
                    'autModificado': '9999999999',
                }
            except Exception as e:
                raise ValidationError(error_msg)

        return credit_note_vals

    def get_purchase(self):
        """Data from account_move (Supplier Invoices, Credit Notes and Purchase Liquidations) """
        move_obj = self.env['account.move']
        purchases = move_obj.search(['|',
                                     ("move_type", 'in', ['in_invoice', 'in_refund']),
                                     ("journal_id.l10n_ec_is_purchase_liquidation", '=', True),
                                     ("invoice_date", '<=', self.date_to),
                                     ("invoice_date", '>=', self.date_from),
                                     ("state", '=', 'posted'),
                                     ("company_id", "=", self.env.company.id)
                                     ])
        lst_purchase = []
        for purchase in purchases:
            res_purchase = {}
            withhold = purchase.l10n_ec_withhold_ids[0] if purchase.l10n_ec_withhold_ids else False
            credit_note = True if purchase.move_type == 'in_refund' else False
            purchase_tax_lines = purchase.line_ids.filtered(lambda line: line.tax_line_id)
            l10n_ec_code_taxsupport_lst = purchase_tax_lines.tax_line_id.mapped('l10n_ec_code_taxsupport') if purchase_tax_lines else []
            for tax_supp_code in l10n_ec_code_taxsupport_lst:
                purchase_vat_subtotals = purchase._compute_ats_subtotals_by_tax_supp_code(tax_supp_code)
                res_purchase = {
                    'withhold': True if withhold else False,# Tech field to append or not withhold fields
                    'credit_note': credit_note,
                    'codSustento': tax_supp_code,
                    'tpIdProv': tpIdProv.get(purchase.partner_id.l10n_latam_identification_type_id.name, False) or '03',
                    'idProv': purchase.partner_id.vat,
                    'tipoComprobante': purchase.l10n_latam_document_type_id.code,
                    'parteRel': 'NO',
                    'fechaRegistro': self.format_date(purchase.invoice_date),
                    'establecimiento': purchase.sequence_prefix[-8:-5],
                    'puntoEmision': purchase.sequence_prefix[-4:-1],
                    'secuencial': str(purchase.sequence_number).zfill(9),
                    'fechaEmision': self.format_date(purchase.invoice_date),
                    'autorizacion': purchase.l10n_ec_authorization_number if purchase.l10n_ec_authorization_number else '9999999999',
                    'baseNoGraIva': '%.2f' % purchase_vat_subtotals['l10n_ec_base_not_subject_to_vat'],
                    'baseImponible': '%.2f' % purchase_vat_subtotals['l10n_ec_base_zero_iva'],
                    'baseImpGrav': '%.2f' % purchase_vat_subtotals['l10n_ec_base_non_zero_iva'],
                    'baseImpExe': '%.2f' % purchase_vat_subtotals['l10n_ec_base_tax_free'],
                    'total': '%.2f' % purchase.amount_total,
                    'montoIce': '%.2f' % purchase_vat_subtotals['l10n_ec_amount_ice'],
                    'montoIva': '%.2f' % purchase_vat_subtotals['l10n_ec_amount_non_zero_iva'],
                    'totbasesImpReemb': '%.2f' % 0.00,
                    'pagoExterior': {
                        'pagoLocExt': '01',
                        'paisEfecPago': 'NA',
                        'aplicConvDobTrib': 'NA',
                        'pagoExtSujRetNorLeg': 'NA'
                    },
                    'formaPago': purchase.l10n_ec_sri_payment_id.code
                }
                if withhold:
                    withhold_lines = withhold.l10n_ec_withhold_line_ids.filtered(lambda line: line.l10n_ec_code_taxsupport == tax_supp_code)
                    valRetBien10, valRetServ20, valorRetBienes, valorRetServ50, valorRetServicios, valorRetServ100 = self._get_vat_withhold_data(withhold_lines)
                    codRetAir, baseImpAir, porcentajeAir, valRetAir = self._get_profit_withhold_data(withhold_lines,
                                                                                                     purchase.amount_untaxed)
                    res_purchase.update({
                        'valRetBien10': '%.2f' % valRetBien10,
                        'valRetServ20': '%.2f' % valRetServ20,
                        'valorRetBienes': '%.2f' % valorRetBienes,
                        'valRetServ50': '%.2f' % valorRetServ50,
                        'valorRetServicios': '%.2f' % valorRetServicios,
                        'valorRetServ100': '%.2f' % valorRetServ100,
                        'codRetAir': codRetAir,
                        'baseImpAir': baseImpAir,
                        'porcentajeAir': porcentajeAir,
                        'valRetAir': valRetAir,
                        'estabRetencion1': withhold.journal_id.l10n_ec_entity,
                        'ptoEmiRetencion1': withhold.journal_id.l10n_ec_emission,
                        'secRetencion1': withhold.name.removeprefix(withhold.sequence_prefix),
                        'autRetencion1': withhold.l10n_ec_authorization_number,
                        'fechaEmiRet1': self.format_date(withhold.l10n_ec_withhold_date)
                    })
                else:
                    res_purchase.update({
                        'valRetBien10': '%.2f' % 0.00,
                        'valRetServ20': '%.2f' % 0.00,
                        'valorRetBienes': '%.2f' % 0.00,
                        'valRetServ50': '%.2f' % 0.00,
                        'valorRetServicios': '%.2f' % 0.00,
                        'valorRetServ100': '%.2f' % 0.00,
                        'baseImpAir': '%.2f' % purchase.amount_untaxed,
                        'codRetAir': '332',
                        'porcentajeAir': '0.00',
                        'valRetAir': '0.00'
                    })

                if credit_note:
                    res_purchase.update(self.get_refund(purchase))

            if res_purchase:
                lst_purchase.append(res_purchase)

        return lst_purchase

    def format_date(self, date):
        return date.strftime('%d/%m/%Y')

    def get_sale(self):
        '''
        At the moment electronic sales have not to be reported in ATS
        '''
        return []

    def get_sale_establishment(self):
        '''
        Filler data from every sale journal with
        '''
        journals = self.env['account.journal'].search([('l10n_ec_entity', '!=', False)])
        establishment_sales = []
        for journal in journals:
            establishment_sales.append({'codEstab': journal.l10n_ec_entity, 'ventasEstab': '%.2f' % 0.0})

        return establishment_sales

    def read_cancelled(self):
        '''
        Data from account_move with edi_state cancelled (Customer invoices, Customer credit notes, and Supplier withholdings)
        '''
        move_obj = self.env['account.move']
        invoices = move_obj.search(['|',
                                     ("move_type", 'in', ['out_invoice', 'out_refund']),
                                     ("journal_id.l10n_ec_is_purchase_liquidation", '=', True),
                                     ("invoice_date", '<=', self.date_to),
                                     ("invoice_date", '>=', self.date_from),
                                     ("state", '=', 'cancel'),
                                     ("edi_state", '=', 'cancelled'),
                                     ("company_id", "=", self.env.company.id)
                                    ])
        anulados = []
        for invoice in invoices:
            detalleanulados = {
                'tipoComprobante': invoice.l10n_latam_document_type_id.code,
                'establecimiento': invoice.sequence_prefix[-8:-5],
                'ptoEmision': invoice.sequence_prefix[-4:-1],
                'secuencialInicio': invoice.sequence_number,
                'secuencialFin': invoice.sequence_number,
                'autorizacion': invoice.l10n_ec_authorization_number or '9999999999'
            }
            anulados.append(detalleanulados)

        withhold_domain = [
            ('state', '=', 'cancel'),
            ('l10n_ec_withhold_date', '>=', self.date_from),
            ('l10n_ec_withhold_date', '<=', self.date_to),
            ('l10n_ec_withhold_type', '!=', False),
            ("state", '=', 'cancel'),
            ("edi_state", '=', 'cancelled'),
            ("company_id", "=", self.env.company.id)
        ]
        for withhold in move_obj.search(withhold_domain):
            detalleanulados = {
                'tipoComprobante': withhold.l10n_latam_document_type_id.code,
                'establecimiento': withhold.sequence_prefix[-8:-5],
                'ptoEmision': withhold.sequence_prefix[-4:-1],
                'secuencialInicio': withhold.sequence_number,
                'secuencialFin': withhold.sequence_number,
                'autorizacion': withhold.l10n_ec_authorization_number or '9999999999'
            }
            anulados.append(detalleanulados)

        return anulados

    def render_xml(self, ats):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        ats_tmpl = env.get_template('ats.xml')
        return ats_tmpl.render(ats)

    def validate_document(self, ats, error_log=False):
        file_path = os.path.join(os.path.dirname(__file__), 'XSD/ats.xsd')
        schema_file = open(file_path)
        xmlschema_doc = etree.parse(schema_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        root = etree.fromstring(ats)
        ok = True
        return ok, xmlschema