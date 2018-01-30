# -*- coding: utf-8 -*-
import re
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import api, fields, models

class OrderSale(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """

        if self.partner_id.rfc_cliente == False:
            if self.partner_id.country_id.code == 'MX':
                raise ValidationError("Error de Validacion : El cliente %s no tiene ningun RFC asignado, favor de asignarlo primero" % (self.name))
        else:
            if self.partner_id.is_company == True:
                #Valida RFC en base al patron de una persona Moral
                if len(self.partner_id.rfc_cliente)!=12:
                    raise ValidationError("El RFC %s no tiene la logitud de 12 caracteres para personas Morales que establece el sat" % (self.partner_id.rfc_cliente))
                else:    
                    patron_rfc = re.compile(r'^([A-ZÑ\x26]{3}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                    if not patron_rfc.search(self.partner_id.rfc_cliente):
                        msg = "Formato RFC de Persona Moral Incorrecto"
                        raise ValidationError(msg)
            else:
                #Valida el RFC en base al patron de una Persona Fisica
                if len(self.partner_id.rfc_cliente)!=13:
                    raise ValidationError("El RFC %s no tiene la logitud de 13 caracteres para personas Fisicas que establece el sat" % (self.partner_id.rfc_cliente))
                else:
                    patron_rfc = re.compile(r'^([A-ZÑ\x26]{4}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                    if not patron_rfc.search(self.partner_id.rfc_cliente):
                        msg = "Formato RFC de Persona Fisica Incorrecto"
                        raise ValidationError(msg)
        
        if self.partner_id.uso_cfdi_id.descripcion==False:
            self.partner_id.uso_cfdi_id = ""

        if self.partner_id.metodo_pago_id.descripcion==False:
            self.partner_id.metodo_pago_id = ""


        if self.env.user.company_id.company_registry == False:
            raise ValidationError('La compañia No tiene asignado ningun RFC')

        if self.env.user.company_id.street == False:
            raise ValidationError('La compañia no tiene asignada ninguna direccion')

        if self.env.user.company_id.city == False:
            raise ValidationError('La compañia no tiene asignada ninguna ciudad')

        if self.env.user.company_id.country_id.name == False:
            raise ValidationError('La compañia no tiene asignado ningun nombre')

        codigo_search = self.env['catalogos.codigo_postal'].search([('c_codigopostal', '=',self.env.user.company_id.zip)])
        if codigo_search.id== False:
            raise ValidationError("Compruebe el Codigo Postal colocado en la configuracion de la compania ya que no se encuentra en el catalogo del sat")

        if self.env.user.company_id.state_id.name == False:
            raise ValidationError("La Compañia no tiene asignado ningun Estado")

        self.ensure_one()
        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(('Please define an accounting sale journal for this company.'))
        invoice_vals = {
            'name': self.client_order_ref or '',
            'origin': self.name,
            'type': 'out_invoice',
            'account_id': self.partner_invoice_id.property_account_receivable_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'journal_id': journal_id,
            'currency_id': self.pricelist_id.currency_id.id,
            'comment': self.note,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id and self.user_id.id,
            'team_id': self.team_id.id,
            'codigo_postal_id': codigo_search.id,
            "metodo_pago_id" : self.partner_id.metodo_pago_id.id,
            "uso_cfdi_id" : self.partner_id.uso_cfdi_id.id,
            'compania_estado': self.env.user.company_id.state_id.name,
            'rfc_cliente_factura': (self.partner_id.rfc_cliente).encode('utf-8'),
            'rfc_emisor': (self.env.user.company_id.company_registry).encode('utf-8'),
            'compania_calle': (self.env.user.company_id.street).encode('utf-8'),
            'compania_ciudad': (self.env.user.company_id.city).encode('utf-8'),
            'compania_pais': (self.env.user.company_id.country_id.name).encode('utf-8')
        }
        return invoice_vals
