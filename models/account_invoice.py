# -*- coding: utf-8 -*-
import urllib2
import webbrowser
import hashlib
import json
import ctypes
import os
import base64
import requests
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re
from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

import odoo.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)


#Agrega al formulario los capos requeridos por el Sat
class localizacion_mexicana(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice']
    
    uuid = fields.Char(string="UUID")
    cfdi_relacionados = fields.Char(string='CFDI Relacionados')
    #Variables del receptor
    rfc_cliente_factura = fields.Char(string='RFC Receptor')

    def default_company_rfc(self):
        return self.env.user.company_id.company_registry

    def default_company_calle(self):
        return self.env.user.company_id.street

    def default_company_ciudad(self):
        return self.env.user.company_id.city

    def default_company_pais(self):
        return self.env.user.company_id.country_id.name

    def default_lugar_de_expedicion(self):
        codigo_postal_compania = self.env.user.company_id.zip
        id_codigo = self.env['catalogos.codigo_postal'].search([('c_codigopostal', '=',codigo_postal_compania)])
        if id_codigo.id != False:
            return id_codigo.id

    def default_company_estado(self):
        return self.env.user.company_id.state_id.name

    #Variables de la compañia
    compania_calle = fields.Char(string='Calle',readonly=True,default=default_company_calle)
    compania_ciudad = fields.Char(string='Ciudad',readonly=True,default=default_company_ciudad)
    compania_estado = fields.Char(string='Estado',readonly=True,default=default_company_estado)
    compania_pais = fields.Char(string='Pais',readonly=True,default=default_company_pais)
    no_parcialidad = fields.Char(string="Pagos Realizados",default="0")
    rfc_emisor = fields.Char(string='RFC Emisor',default= default_company_rfc)
    state = fields.Selection([
            ('draft','Draft'),
            ('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            ('timbrada', 'CFDI'),
            ('timbrado cancelado', 'CFDI Cancelado'),
            ('open', 'Open'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.", color="green")
    forma_pago_id = fields.Many2one('catalogos.forma_pago',string='Forma Pago')
    metodo_pago_id = fields.Many2one('catalogos.metodo_pago',string='Metodo de pago')
    codigo_postal_id = fields.Many2one('catalogos.codigo_postal',string='Lugar de Expedicion',default=default_lugar_de_expedicion)
    uso_cfdi_id = fields.Many2one('catalogos.uso_cfdi',string='Uso CFDI')
    fac_id = fields.Char()
    observaciones = fields.Text(string='Observaciones')
    tipo_de_relacion_id = fields.Many2one('catalogos.tipo_relacion',string='Tipo de Relacion')
    pdf ="Factura?Accion=descargaPDF&fac_id=";
    xml ="Factura?Accion=ObtenerXML&fac_id=";
    fac_timbrada = fields.Char('CFDI',default="Sin Timbrar",readonly=True)
    
    #Carga El RFC del Cliente Seleccionado
    @api.onchange('partner_id')
    def _onchange_rfc_emisor(self):
        if self.partner_id.rfc_cliente == False:
            if self.partner_id.nif != False:
                self.rfc_cliente_factura = self.partner_id.nif
        else:
            self.rfc_cliente_factura = self.partner_id.rfc_cliente
            if self.partner_id.metodo_pago_id.c_metodo_pago!= False:
                self.metodo_pago_id = self.partner_id.metodo_pago_id.id
            if self.partner_id.uso_cfdi_id.c_uso_cfdi!=False:
                self.uso_cfdi_id = self.partner_id.uso_cfdi_id.id

    @api.constrains('state')
    def limpiar_uuid_al_duplicar_factura(self):
        if self.state == 'draft':
            self.uuid = False

    @api.multi
    def timbrar_factura(self):

        self.url_parte = self.env['catalogos.configuracion'].search([('url', '!=', '')])
        usuario = self.url_parte.usuario
        contrasena=self.url_parte.contrasena
        string=str(contrasena.encode("utf-8"))
        #crea el algoritmo para encriptar la informacion
        algorithim=hashlib.md5()
        #encripta la informacion
        algorithim.update(string)
        #La decodifica en formato hexadecimal
        encrypted=algorithim.hexdigest()
        conceptos = []
        receptor = ""
        if self.partner_id.nif!= False:
            receptor = {
            "receptor_id": self.rfc_cliente_factura,
            "compania":self.partner_id.name.encode('utf-8'),
            "calle": self.partner_id.street.encode('utf-8'),
            "ciudad":self.partner_id.city.encode('utf-8'),
            "correo":self.partner_id.email.encode('utf-8'),
            "colonia":self.partner_id.colonia.encode('utf-8'),
            "codigopostal":self.partner_id.zip,
            "numero_ext":self.partner_id.numero_ext,
            "estado":self.partner_id.state_id.name.encode('utf-8'),
            "NIF": self.partner_id.nif.encode('utf-8')
        }
        else:
            receptor = {
            "receptor_id": self.rfc_cliente_factura,
            "compania":self.partner_id.name.encode('utf-8'),
            "calle": self.partner_id.street.encode('utf-8'),
            "ciudad":self.partner_id.city.encode('utf-8'),
            "correo":self.partner_id.email.encode('utf-8'),
            "colonia":self.partner_id.colonia.encode('utf-8'),
            "codigopostal":self.partner_id.zip,
            "numero_ext":self.partner_id.numero_ext,
            "estado":self.partner_id.state_id.name.encode('utf-8'),
        }


        

        descuento_acumulado = 0.0
        total_acumulado = 0.0
        importe_acumulado = 0.0
        impuesto_acumulado = 0.0


        mpuesto_retenido = 0.0

        for conceptos_record in self.invoice_line_ids:
        
            importe= conceptos_record.price_unit*conceptos_record.quantity
            importe_acumulado = importe_acumulado+importe
            impuestos = []
            descuento = importe*((conceptos_record.discount)/100)
            descuento_acumulado = descuento_acumulado+descuento
            subtotal = importe
            
            for impuestos_record in conceptos_record.invoice_line_tax_ids:

                iva = importe * (((impuestos_record.amount) / 100))
                impuesto_acumulado = impuesto_acumulado + iva
                total = subtotal + iva
                total_acumulado = total_acumulado + total

                #ImpuestosXConcepto
                impuestosxconcepto = {
                "traslado_base": str(importe),
                "con_importe_iva": str(iva),
                "descripcion_impuesto": str((impuestos_record.tipo_impuesto_id.descripcion.encode('utf-8'))),
                "tipo_tasaocuota": impuestos_record.tasa_o_cuota_id.valor_maximo,
                "tipo_factor": impuestos_record.tipo_factor_id.tipo_factor,
                "clave_impuesto": impuestos_record.tipo_impuesto_id.c_impuesto,
                }
                impuestos.append(impuestosxconcepto)

         # ConceptosXFactura
            concepto = {"con_cantidad": str(conceptos_record.quantity), "con_descripcion": str(conceptos_record.name.encode("utf-8")),
                    "con_unidad_clave": str(conceptos_record.product_id.clave_unidad_clave_catalogo_sat_id.c_claveunidad),
                    "con_valor_unitario": str(conceptos_record.price_unit), "con_descuento": str(descuento),
                    "con_subtotal": str(subtotal), "con_importe": str(importe),
                    "con_total": str(conceptos_record.price_subtotal), "tipo_cambio": self.currency_id.rate,
                    "con_has_impuesto":1,
                    "no_identificacion":str((conceptos_record.product_id.default_code).encode('utf-8')),
                    "con_clave_prod_serv": str(conceptos_record.product_id.clave_prod_catalogo_sat_id.c_claveprodserv),
                    "impuestosxconcepto": impuestos,
                    }
            conceptos.append(concepto)
        
        #Estructura JSON para timbrar la Factura
        url = str(self.url_parte.url)+"webresources/FacturacionWS/Facturar"
        print (str(self.currency_id.rate))
        if self.origin == False:
            self.origin = "sin pedido"

        if self.observaciones == False:
            self.observaciones = ""

        data = {
        "factura": { 
        "receptor_uso_cfdi": self.uso_cfdi_id.c_uso_cfdi,
        "user_odoo":usuario,
        "fac_no_orden": self.number,
        "odoo_contrasena": encrypted,
        "emisor_id" : str(self.rfc_emisor),
        "receptor": receptor,
        "fac_importe" : importe_acumulado,
        "fac_porcentaje_iva" : impuesto_acumulado,
        "fac_descuento" : descuento_acumulado,
        "fac_emisor_regimen_fiscal_key" : self.env.user.company_id.property_account_position_id.c_regimenfiscal,
        "fac_emisor_regimen_fiscal_descripcion": self.env.user.company_id.property_account_position_id.name,   
        "fecha_facturacion" : self.date_invoice,
        "fac_observaciones" : self.observaciones,
        "fac_forma_pago_key" : self.forma_pago_id.c_forma_pago,
        "fac_metodo_pago_key" : self.metodo_pago_id.c_metodo_pago,
        "fac_tipo_comprobante" : "I" ,
        "fac_moneda": self.currency_id.name,
        "fac_tipo_cambio": self.currency_id.rate,
        "fac_lugar_expedicion": self.codigo_postal_id.c_codigopostal,
        "conceptos" :
            conceptos
        
       }

    }
        
        headers = {
           'content-type': "application/json", 'Authorization':"Basic YWRtaW46YWRtaW4="
    }


        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        print data
        json_data = json.loads(response.text)
        #Valida que la factura haya sido timbrada Correctamente
        if json_data['result']['success']== 'true':
            self.state = 'timbrada'
            #En caso de recibir una respuesta positiva anexa el uuid al formulario de la factura timbrada
            self.uuid = json_data['result']['uuid']
            self.fac_id = json_data['result']['fac_id']
            self.fac_timbrada = "Timbrada"
            print self.fac_id
        else:
            raise ValidationError(json_data['result']['message'])

    
    @api.multi
    def timbrar_nota_de_credito(self):

        self.url_parte = self.env['catalogos.configuracion'].search([('url', '!=', '')])
        usuario = self.url_parte.usuario
        contrasena=self.url_parte.contrasena
        string=str(contrasena.encode("utf-8"))
        #crea el algoritmo para encriptar la informacion
        algorithim=hashlib.md5()
        #encripta la informacion
        algorithim.update(string)
        #La decodifica en formato hexadecimal
        encrypted=algorithim.hexdigest()
        conceptos = []
        receptor = ""
        if self.partner_id.nif!= False:
            receptor = {
            "receptor_id": self.rfc_cliente_factura,
            "compania":self.partner_id.name.encode('utf-8'),
            "calle": self.partner_id.street.encode('utf-8'),
            "ciudad":self.partner_id.city.encode('utf-8'),
            "correo":self.partner_id.email.encode('utf-8'),
            "colonia":self.partner_id.colonia.encode('utf-8'),
            "codigopostal":self.partner_id.zip,
            "numero_ext":self.partner_id.numero_ext,
            "estado":self.partner_id.state_id.name.encode('utf-8'),
            "NIF": self.partner_id.nif.encode('utf-8')
        }
        else:
            receptor = {
            "receptor_id": self.rfc_cliente_factura,
            "compania":self.partner_id.name.encode('utf-8'),
            "calle": self.partner_id.street.encode('utf-8'),
            "ciudad":self.partner_id.city.encode('utf-8'),
            "correo":self.partner_id.email.encode('utf-8'),
            "colonia":self.partner_id.colonia.encode('utf-8'),
            "codigopostal":self.partner_id.zip,
            "numero_ext":self.partner_id.numero_ext,
            "estado":self.partner_id.state_id.name.encode('utf-8'),
        }

        cfdi_relacionados = []
        cfdi_relacionado = {
           "uuid": self.cfdi_relacionados
        }
        cfdi_relacionados.append(cfdi_relacionado)

        descuento_acumulado = 0.0
        total_acumulado = 0.0
        importe_acumulado = 0.0
        impuesto_acumulado = 0.0


        mpuesto_retenido = 0.0

        for conceptos_record in self.invoice_line_ids:
        
            importe= conceptos_record.price_unit*conceptos_record.quantity
            importe_acumulado = importe_acumulado+importe
            impuestos = []
            descuento = importe*((conceptos_record.discount)/100)
            descuento_acumulado = descuento_acumulado+descuento
            subtotal = importe
            
            for impuestos_record in conceptos_record.invoice_line_tax_ids:

                iva = importe * (((impuestos_record.amount) / 100))
                impuesto_acumulado = impuesto_acumulado + iva
                total = subtotal + iva
                total_acumulado = total_acumulado + total

                #ImpuestosXConcepto
                impuestosxconcepto = {
                "traslado_base": str(importe),
                "con_importe_iva": str(iva),
                "descripcion_impuesto": str((impuestos_record.tipo_impuesto_id.descripcion.encode('utf-8'))),
                "tipo_tasaocuota": impuestos_record.tasa_o_cuota_id.valor_maximo,
                "tipo_factor": impuestos_record.tipo_factor_id.tipo_factor,
                "clave_impuesto": impuestos_record.tipo_impuesto_id.c_impuesto,
                }
                impuestos.append(impuestosxconcepto)

            print "Referencia Interna"
            print conceptos_record.product_id.default_code.encode('utf-8')
         # ConceptosXFactura
            concepto = {"con_cantidad": str(conceptos_record.quantity), "con_descripcion": str(conceptos_record.name.encode("utf-8")),
                    "con_unidad_clave": str(conceptos_record.product_id.clave_unidad_clave_catalogo_sat_id.c_claveunidad),
                    "con_valor_unitario": str(conceptos_record.price_unit), "con_descuento": str(descuento),
                    "con_subtotal": str(subtotal), "con_importe": str(importe),
                    "con_total": str(conceptos_record.price_subtotal), "tipo_cambio": self.currency_id.rate,
                    "con_has_impuesto":1,
                    "no_identificacion":str((conceptos_record.product_id.default_code).encode('utf-8')),
                    "con_clave_prod_serv": str(conceptos_record.product_id.clave_prod_catalogo_sat_id.c_claveprodserv),
                    "con_descripcion":"test Nota de Credito",
                    "impuestosxconcepto": impuestos,
                    }
            conceptos.append(concepto)
        
        #Estructura JSON para timbrar la Factura
        url = str(self.url_parte.url)+"webresources/FacturacionWS/Facturar"
        print (str(self.currency_id.rate))
        if self.origin == False:
            self.origin = "sin pedido"

        data = {
        "factura": { 
        "receptor_uso_cfdi": self.uso_cfdi_id.c_uso_cfdi,
        "user_odoo":usuario,
        "fac_no_orden": self.number,
        "odoo_contrasena": encrypted,
        "emisor_id" : str(self.rfc_emisor),
        "receptor": receptor,
        "fac_importe" : importe_acumulado,
        "fac_porcentaje_iva" : impuesto_acumulado,
        "fac_descuento" : descuento_acumulado,
        "fac_emisor_regimen_fiscal_key" : self.env.user.company_id.property_account_position_id.c_regimenfiscal,
        "fac_emisor_regimen_fiscal_descripcion": self.env.user.company_id.property_account_position_id.name,   
        "fecha_facturacion" : self.date_invoice,
        "fac_forma_pago_key" : self.forma_pago_id.c_forma_pago,
        "fac_metodo_pago_key" : self.metodo_pago_id.c_metodo_pago,
        "fac_tipo_comprobante" : "E" ,
        "cfdi_relacionados": cfdi_relacionados,
        "fac_tipo_relacion":self.tipo_de_relacion_id.c_tipo_relacion,
        "fac_moneda": self.currency_id.name,
        "fac_tipo_cambio": self.currency_id.rate,
        "fac_lugar_expedicion": self.codigo_postal_id.c_codigopostal,
        "conceptos" :
            conceptos
        
       }

    }
        
        headers = {
           'content-type': "application/json", 'Authorization':"Basic YWRtaW46YWRtaW4="
    }


        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        json_data = json.loads(response.text)
        #Valida que la factura haya sido timbrada Correctamente
        if json_data['result']['success']== 'true':
            self.state = 'timbrada'
            #En caso de recibir una respuesta positiva anexa el uuid al formulario de la factura timbrada
            self.uuid = json_data['result']['uuid']
            self.fac_id = json_data['result']['fac_id']
            self.fac_timbrada = "Timbrada"
        else:
            raise ValidationError(json_data['result']['message'])

    @api.multi
    def descargar_factura_pdf(self):

        url_parte = self.env['catalogos.configuracion'].search([('url', '!=', '')])
        url_descarga_pdf = url_parte.url+self.pdf+self.fac_id
        return {
            'type': 'ir.actions.act_url',
            'url': url_descarga_pdf,
            'target': 'new',
        }
        
    @api.multi
    def descargar_factura_xml(self):
        
        url_parte = self.env['catalogos.configuracion'].search([('url', '!=', '')])
        url_descarga_xml = url_parte.url+self.xml+self.fac_id
        return {
            'type': 'ir.actions.act_url',
            'url': url_descarga_xml,
            'target': 'new',
        }

    @api.multi
    def cancelar_factura_timbrada(self):
        url_parte = self.env['catalogos.configuracion'].search([('url', '!=', '')])
        url = str(url_parte.url)+"webresources/FacturacionWS/Cancelar"
        data = {
         "uuid": self.uuid
        }

        headers = {
           'content-type': "application/json", 'Authorization':"Basic YWRtaW46YWRtaW4="
    }

        response = requests.request("POST", url, data=json.dumps(data), headers=headers)
        json_data = json.loads(response.text)
        if json_data['result']['success'] == 'true':
            self.state = 'timbrado cancelado'
            self.fac_timbrada = "Timbre Cancelado"
        else:
            raise ValidationError(json_data['result']['message'])

        @api.multi
        def action_invoice_open(self):
            # lots of duplicate calls to action_invoice_open, so we remove those already open
            to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
            if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft']):
                raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
            to_open_invoices.action_date_assign()
            to_open_invoices.action_move_create()
            return to_open_invoices.invoice_validate()

    #Modifico  el metodo de Validacion Original para que el estado en que termina sea validate en vez de open
    @api.multi
    def invoice_validate(self):
        #Valida los campos
        self.validar_campos() 

        #Valida las lineas de Factura
        product_id = []
        for j in self.invoice_line_ids:
            product_id.append(j.product_id)
            #Valida que los impuestos asignados contengan sus correspondientes claves
            for taxs in j.invoice_line_tax_ids:
                if taxs.tipo_impuesto_id.descripcion == False:
                    raise ValidationError(
                        "FACT00001: El impuesto %s no  tiene asignada ninguna clave del Catalogo del Sat que lo identifique" % (taxs.name))
            #Valida que los productos asignados cuenten con las claves del sat asignadas
            for record_product in product_id:
                if record_product.clave_unidad_clave_catalogo_sat_id.nombre == False:
                    raise ValidationError("FACT002: Clave de unidad de medida del producto %s no asignada" % (record_product.name))
                else:
                    if record_product.clave_prod_catalogo_sat_id.descripcion == False:
                        raise ValidationError("FACT002: Clave de unidad de medida del producto %s no asignada" % (record_product.name))
                    else:
                        if record_product.default_code == False:
                            raise ValidationError("FACT002: El campo (referencia interna) del producto %s no  ha sido asignada la cual servira" 
                                " como No.Identificacion para la facturacion Electronica, usted puede asignarla dentro del modulo de inventarios en la seccion Informacion General" % (record_product.name))

        #Cambia el Estado de Borrador a Validado
        for invoice in self:
            #refuse to validate a vendor bill/refund if there already exists one with the same reference for the same partner,
            #because it's probably a double encoding of the same bill/refund
            if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
                if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference), ('company_id', '=', invoice.company_id.id), ('commercial_partner_id', '=', invoice.commercial_partner_id.id), ('id', '!=', invoice.id)]):
                    raise UserError(_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/refund."))
        #return self.write({'state': 'validate'})
        if self.type == "out_invoice":
            self.timbrar_factura()
        else:
            self.timbrar_nota_de_credito()

    @api.multi
    def action_invoice_open_2(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft']):
            raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        return to_open_invoices.invoice_validate_2()

    @api.multi
    def invoice_validate_2(self):
        for invoice in self:
            #refuse to validate a vendor bill/refund if there already exists one with the same reference for the same partner,
            #because it's probably a double encoding of the same bill/refund
            if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
                if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference), ('company_id', '=', invoice.company_id.id), ('commercial_partner_id', '=', invoice.commercial_partner_id.id), ('id', '!=', invoice.id)]):
                    raise UserError(_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/refund."))
        return self.write({'state': 'open'})

    @api.multi
    def validar_campos(self):
        if self.partner_id.country_id == False:
                raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: El ciente de origen extranjero %s no tiene el Pais registrado, favor de asignarlo primero" % (self.partner_id.name))

        if self.rfc_cliente_factura == False: 
                raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene ningun RFC asignado o un NIF(RFC Ventas en General), favor de asignarlo primero" % (self.partner_id.name))
        else:
            if len(self.rfc_cliente_factura) > 13:
                raise ValidationError("El RFC %s sobrepasa los 12 caracteres para personas Fisicas y 13 para personas morales que establece el sat" % (self.company_registry))
            if len(self.rfc_cliente_factura) < 12:
                raise ValidationError("El RFC %s tiene menos de los 12 caracteres para personas Fisicas y 13 para personas morales que establece el sat" % (self.company_registry))
            else:
                rule = re.compile(r'^([A-ZÑ\x26]{3,4}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                if not rule.search(self.rfc_cliente_factura):
                    msg = "Formato de RFC Invalido"
                    msg = msg + "El formato correcto es el siguiente:\n\n"
                    msg = msg + "-Apellido Paterno (del cual se van a utilizar las primeras 2 Letras). \n"
                    msg = msg + "-Apellido Materno (de este solo se utilizará la primera Letra).\n"
                    msg = msg + "-Nombre(s) (sin importar si tienes uno o dos nombres, solo se utilizarà la primera Letra del primer nombre).\n"
                    msg = msg + "-Fecha de Nacimiento (día, mes y año).\n"
                    msg = msg + "-Sexo (Masculino o Femenino).\n"
                    msg = msg + "-Entidad Federativa de nacimiento (Estado en el que fue registrado al nacer)."
                    raise ValidationError(msg)

        if self.env.user.company_id.property_account_position_id.c_regimenfiscal == False:
            raise ValidationError("La compania %s no tiene asignado ningun Regimen Fiscal, favor de asignarlo primero" % (self.name))   

        if self.partner_id.colonia == False:
            raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene asignada ninguna Colonia, favor de asignarlo primera" % (self.partner_id.name))

        if self.partner_id.email == False:
            raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene asignado ningun Correo Electronico, favor de asignarlo primera" % (self.name))

        if self.partner_id.city == False:
            raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene asignada ninguna Ciudad, favor de asignarlo primera" % (self.partner_id.name))

        if self.partner_id.zip == False:
            raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene asignada ningun Codigo Postal, favor de asignarlo primera" % (self.partner_id.name))

        if self.partner_id.country_id.name == False:
            raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene asignada ningun Pais, favor de asignarlo primera" % (self.partner_id.name))

        if self.partner_id.numero_ext == False:
            raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene asignada ningun No Exterior, favor de asignarlo primera" % (self.name))

        #Validacionciones Atributos de Factura
        if self.forma_pago_id.descripcion == False:
            raise ValidationError("FACT004 :  Hay campos en esta factura sin informacion requerida para Timbrar: La forma de pago no ha sido asignada")

        if self.metodo_pago_id.descripcion == False:
            raise ValidationError("FACT004 :  Hay campos en esta factura sin informacion requerida para Timbrar:El Metodo de Pago no ha sido asignada")

        if self.codigo_postal_id.c_estado == False:
            raise ValidationError("FACT004 :  Hay campos en esta factura sin informacion requerida para Timbrar: xpedicion no ha sido asignada")
        
        if self.uso_cfdi_id.descripcion == False:
            raise ValidationError("FACT004 :  Hay campos en esta factura sin informacion requerida para Timbrar: el Uso de CFDI no ha sido asignado")

        #Valida los datos Fiscales de la Compañia
        if self.env.user.company_id.company_registry == False:
            raise ValidationError("Error de Validacion : La compania %s no tiene ningun RFC asignado, favor de asignarlo primero" % (self.env.user.company_id.name))

        if self.partner_id.cfdi == False:
            raise ValidationError("FACT004 : Hay campos en el cliente %s sin informacion requerida para Timbrar: no tiene activado el campo CFDI que permite Facturar" % (self.partner_id.name))

    @api.multi
    def empezar_a_pagar(self):
        self.state='open'
        print self._name
    
    #Me obtiene el ultimo pago realizado en la factura
    @api.multi
    def Obtener_Valores_de_los_Pagos(self):
        pagos = []
        for fac_pagos in self.payment_ids:
            pagos.append(fac_pagos.amount)
            
        raise ValidationError('result %s' % pagos[0])
       


#Agrega los campos al formulario de los impuestos para asignar las claves de Sat
class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = 'account.tax'

    tipo_impuesto_id = fields.Many2one('catalogos.impuestos',string='Tipo de Impuesto')
    tipo_factor_id = fields.Many2one('catalogos.tipo_factor', string='Tipo Factor')
    tasa_o_cuota_id = fields.Many2one('catalogos.tasa_cuota',string='Tasa o cuota')
        
#"emisor_id" : "ACO560518KW7" ,
    #"receptor_id" : "IAMJ841217KMA" ,

    
