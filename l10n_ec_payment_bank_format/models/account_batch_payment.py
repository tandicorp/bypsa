# coding: utf-8
from odoo import fields, models, _
from odoo.exceptions import ValidationError

import base64
from . import util


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    def _validate_payment_for_ec_format(self, payment):
        #Validamos que el banco del partner tenga definido un tipo de cuenta de Ecuador.
        if not payment.partner_bank_id.l10n_ec_account_type:
            raise ValidationError(_("El contacto %s no tiene registrado el TIPO (Ahorros o Corriente) de cuenta bancaria") % payment.partner_id.name)
        if not payment.partner_id.vat:
            raise ValidationError(_(u"El contacto %s no tiene registrado un número de identificación") % payment.partner_id.name)

    def _validate_journal_for_ec_format(self):
        """
        Validamos que el diario del pago por lotes tenga configurado un formato de bancos
        """
        journal = self.journal_id
        error_msgs = []

        if not journal.l10n_ec_format_type:
            error_msgs.append(_("Por favor colocar un tipo de formato de bancos para el(los) diario(s): %(journal)s."))

        if error_msgs:
            raise ValidationError(
                '\n'.join(error_msgs) % {
                    "journal": journal.display_name,
                }
            )

    def _validate_bolivariano_journal_account(self):
        """
        Validamos que el diario tenga una cuenta de origen configurada
        """
        journal = self.journal_id
        error_msgs = []

        if not journal.bank_account_id:
            error_msgs.append(_(u"Por favor colocar un número de cuenta bancaria para el(los) diario(s): %(journal)s."))

        if error_msgs:
            raise ValidationError(
                '\n'.join(error_msgs) % {
                    "journal": journal.display_name,
                }
            )

    def _generate_pichincha_entry_detail(self, payment, sequence):
        """
        Metodo para generar las lineas del archivo con el formato del Banco del Pichincha
        """
        entry = []
        entry.append("PA")
        entry.append(str(sequence))  # Line sequence
        entry.append(payment.company_id.currency_id.name + "\t" + str(payment.amount).rjust(13, '0'))  # Currency Amount
        entry.append("CTA" + "\t" + payment.partner_bank_id.l10n_ec_account_type + "\t" +
                     str(payment.partner_bank_id.acc_number).rjust(11, '0'))  # Account type and number
        entry.append("C" if payment.partner_id.l10n_latam_identification_type_id.id == self.env.ref(
            'l10n_ec.ec_dni') else "P")  # Individual Name
        entry.append(payment.partner_id.vat)  # Partner VAT
        entry.append(payment.partner_id.name)

        return "\t".join(entry)

    def _generate_bolivariano_entry_detail(self, payment, sequence):
        """
        Metodo para generar las lineas del archivo con el formato del Banco del Bolivariano
        """
        entry = []
        sequence += 1
        company_bank_acount = self.journal_id.bank_account_id.acc_number
        entry.append(('BZDET' + str(sequence).zfill(6) + payment.partner_id.vat).ljust(29, ' '))#Line sequence with partner vat
        if payment.partner_id.l10n_latam_identification_type_id.id == self.env.ref('l10n_ec.ec_dni').id:
            identification_type_letter = 'C'
        elif payment.partner_id.l10n_latam_identification_type_id.id == self.env.ref('l10n_ec.ec_ruc').id:
            identification_type_letter = 'R'

        else:
            identification_type_letter = 'P'
        identification = identification_type_letter + payment.partner_id.vat
        entry.append((identification).ljust(15, ' '))
        entry.append((util.elimina_tildes('%s' % payment.partner_id.name)).ljust(60, ' '))
        if payment.partner_bank_id.bank_id.id == self.env.ref('l10n_ec.bank_12').id:
            transfer_code = 'CUE'
            bank_bic = '34'
        else:
            transfer_code = 'COB'
            bank_bic = str(payment.partner_bank_id.bank_id.bic)
        partner_account_type_code = '04' if payment.partner_bank_id.l10n_ec_account_type == 'AHO' else '03'
        entry.append((transfer_code + '001' + bank_bic + partner_account_type_code + str(payment.partner_bank_id.acc_number).ljust(20, ' '))) #acc type, acc number, bank bic
        entry.append(('1' + str(int(round(payment.amount * 100))).rjust(15, '0') + util.elimina_tildes(self.name)).ljust(76, ' ')) #amount with ref
        entry.append(('00000000000000000000000000000000000000000000000000000000000000000').ljust(195, ' ')) #filler string
        entry.append(('TER').ljust(34, ' ')) #third parties payment code
        entry.append(company_bank_acount + "RPA") #origin (company) bank acc number

        return "".join(entry)

    def _generate_ec_format_file(self):
        if self.journal_id.l10n_ec_format_type == 'pch':
            bank_detail_method_name = '_generate_pichincha_entry_detail'
        elif self.journal_id.l10n_ec_format_type == 'bol':
            self._validate_bolivariano_journal_account()
            bank_detail_method_name = '_generate_bolivariano_entry_detail'
        else:
            raise ValidationError(_("El formato de bancos configurado en el diario no está soportado: %s") % self.journal_id.l10n_ec_format_type)
        entries = []
        for batch_nr, payment in enumerate(self.payment_ids):
            self._validate_payment_for_ec_format(payment)
            bank_detail_method = getattr(self, bank_detail_method_name)
            entries.append(bank_detail_method(payment, batch_nr))

        return "\r\n".join(entries)

    def _get_methods_generating_files(self):
        res = super(AccountBatchPayment, self)._get_methods_generating_files()
        res.append("l10n_ec_format")
        return res

    def _generate_export_file(self):
        if self.payment_method_code == "l10n_ec_format":
            self._validate_journal_for_ec_format()
            data = self._generate_ec_format_file()
            date = fields.Datetime.today().strftime("%d/%m/%Y")  # EC date format
            return {
                "file": base64.encodebytes(data.encode()),
                "filename": "CASH MANAGEMENT-%s-%s.txt" % (self.journal_id.code, date),
            }
        else:
            return super(AccountBatchPayment, self)._generate_export_file()
