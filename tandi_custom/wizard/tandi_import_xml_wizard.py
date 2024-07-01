# -*- coding: utf-8 -*-
from datetime import date

from odoo import fields, models, _, Command
from odoo.exceptions import ValidationError

import base64
import xml.etree.ElementTree as ET


class TandiImportXmlWizard(models.TransientModel):
    _name = 'tandi.import.xml.invoice'

    file = fields.Binary(
        string='File',
        required=True
    )
    filename = fields.Char(
        string='File name'
    )

    def action_import_xml(self):
        """
        Generates supplier invoice from loaded SRI XML
        """
        for record in self:
            data = base64.b64decode(record.file)
            invoice_info = self.read_xml(data)
            invoice = self.get_invoice_info(invoice_info)
            self.create_invoice_line(invoice, invoice_info)
            view = self.env.ref('account.view_move_form')
            ctxt = self.env.context.copy()

            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.move',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'current',
                'res_id': invoice.id,
                'context': ctxt
            }

    def read_xml(self, data):
        """
        Parses XML to util dictionary
        """
        root = ET.fromstring(data)
        invoice_info = {}
        detail_lst = []
        xml_auth_number = root.find('numeroAutorizacion').text
        last_supplier_invoice = self.env['account.move'].search([
            ('l10n_ec_authorization_number', '=', xml_auth_number)])
        # We first check if invoice already exists, to avoid duplicates
        if last_supplier_invoice:
            raise ValidationError(
                _("Invoice with authorization number: %s already exists!" % xml_auth_number)
            )
        # We only care about 'comprobante' XML tag, that's the one that has invoice information
        for child in root.findall('comprobante'):
            data_node_str = child.text.encode('utf-8').strip()
            vat = self.env.company.partner_id.vat
            tree_node = ET.fromstring(data_node_str)
            # 1. Validate buyer vat to avoid non company related invoices.
            for inv_info in tree_node.findall('infoFactura'):
                if not vat == inv_info.find('identificacionComprador').text:
                    raise ValidationError(
                        _("Error! Supplier invoice does not correspond to company")
                    )
                invoice_info.update({
                    'fechaEmision': inv_info.find('fechaEmision').text
                })
                # 2. Get invoice's SRI way to pay.
                for payments in inv_info.findall('pagos'):
                    for way_to_pay in payments.findall('pago'):
                        invoice_info.update({
                            'formaPago': way_to_pay.find('formaPago').text
                        })
                        break
            # 3. Get tax info from header, needed to fill Odoo's invoice header
            for info_tributaria in tree_node.findall('infoTributaria'):
                invoice_info.update({
                    'estab': info_tributaria.find('estab').text,
                    'ptoEmi': info_tributaria.find('ptoEmi').text,
                    'codDoc': info_tributaria.find('codDoc').text,
                    'secuencial': info_tributaria.find('secuencial').text,
                    'razonSocial': info_tributaria.find('razonSocial').text.upper(),
                    'identification_type': 'RUC',
                    'ruc': info_tributaria.find('ruc').text,
                    'dirMatriz': info_tributaria.find('dirMatriz').text,
                    'estado': root.find('estado').text,
                    'numeroAutorizacion': xml_auth_number,
                    'fechaAutorizacion': root.find('fechaAutorizacion').text,
                })
            # 4. Get XML invoice details, needed to fill Odoo's invoice details
            for details in tree_node.findall('detalles'):
                for line in details.findall('detalle'):
                    res = {
                        'descripcion': line.find('descripcion').text,
                        'cantidad': line.find('cantidad').text,
                        'precioUnitario': line.find('precioUnitario').text,
                        'precioTotalSinImpuesto': line.find('precioTotalSinImpuesto').text,
                    }
                    detail_lst.append(res)
            invoice_info.update({
                'detalles': detail_lst
            })

        return invoice_info

    def get_invoice_info(self, invoice_info):
        """
        Receives invoice dictionary and creates minimal objects to render invoice
        """
        partners = self.env['res.partner'].search([('vat', '=', invoice_info['ruc']),
                                                   ('l10n_latam_identification_type_id',
                                                    '=',
                                                    self.env.ref("l10n_ec.ec_ruc").id)
                                                   ],
                                                  limit=1)
        if partners:
            invoice_info.update({
                'partner_id': partners[0].id
            })
        else:
            self.create_partner(invoice_info)

        return self.create_invoice(invoice_info)

    def create_partner(self, invoice_info):
        """
        Method to create partner if it does not already exist
        """
        partner_obj = self.env['res.partner']
        partner_data = {
            'name': invoice_info['razonSocial'],
            'supplier_rank': 1,
            'vat': invoice_info['ruc'],
            'l10n_latam_identification_type_id': self.env.ref("l10n_ec.ec_ruc").id,
            'street': invoice_info['dirMatriz'],
            'country_id': self.env.ref('base.ec').id
        }
        partner = partner_obj.sudo().create(partner_data)
        invoice_info.update({'partner_id': partner.id})

    def create_invoice(self, invoice_info):
        """
        Method that receives invoice dict and creates supplier invoice object
        """
        partner = self.env['res.partner'].browse(invoice_info['partner_id'])
        day1, month1, year1 = str(invoice_info['fechaEmision']).split('/')
        date_start = date(int(year1), int(month1), int(day1))
        invoice_document_type = self.env.ref("l10n_ec.ec_dt_01")
        invoice_number = '%s-%s-%s' % (invoice_info['estab'],
                                       invoice_info['ptoEmi'],
                                       invoice_info['secuencial'])
        sri_payment_method = self.env['l10n_ec.sri.payment'].search([('code', '=', invoice_info['formaPago'])],
                                                                    limit=1)
        invoice_vals = {
            'partner_id': invoice_info['partner_id'],
            'move_type': 'in_invoice',
            'l10n_latam_document_type_id': invoice_document_type.id,
            'l10n_latam_document_number': invoice_number,
            'l10n_ec_sri_payment_id': sri_payment_method.id,
            'l10n_ec_authorization_number': invoice_info['numeroAutorizacion'],
            'name': '%s %s' % (invoice_document_type.doc_code_prefix, invoice_number),
            'invoice_date': date_start,
            'currency_id': partner.company_id.currency_id.id or self.env.ref('base.USD').id,
            'tandi_xml_imported': True
        }

        return self.env['account.move'].sudo().with_context(move_type='in_invoice').create(invoice_vals)

    def create_invoice_line(self, invoice, invoice_info):
        """
        Creates invoice lines from invoice dict info
        """
        provisional_prod = self.env.ref('tandi_custom.provisional_product_import')
        line_lst = []
        for line in invoice_info['detalles']:
            line_values = {
                'product_id': provisional_prod.id,
                'name': line['descripcion'],
                'quantity': float(line['cantidad']),
                'price_unit': line['precioUnitario'],
                'tax_ids': [],
            }
            contrib_line = Command.create(line_values)
            line_lst.append(contrib_line)
        if line_lst:
            invoice.write({
                'invoice_line_ids': line_lst
            })
