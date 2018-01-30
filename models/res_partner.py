# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import models, fields, api
import re

#Agrega el campo RFC al formulario de Clientes y Proveedores
class RFCClientes(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    is_a_user = fields.Boolean(string='Es un usuario?',default=False)
    rfc_cliente = fields.Char(string='RFC',size=13)
    colonia = fields.Char(string='Colonia')
    numero_int = fields.Char(string='Numero Int')
    numero_ext = fields.Char(string='Numero Exterior')
    nif = fields.Char(string='NIF EXTRA')
    cfdi = fields.Boolean(string='Activar CFDI')
    municipio = fields.Char(string='Municipio')
    company_type = fields.Selection([
            ('person','Persona Fisica'),
            ('company', 'Persona Moral'),
        ], index=True, default='person',
        track_visibility='onchange', copy=False)
    #Los Siguientes campos son relacionales extra que solo si estan configurados
    #Se cargan en la Factura de Venta al Seleccionar el cliente.
    #Por tanto no son obligatorios.
    metodo_pago_id = fields.Many2one('catalogos.metodo_pago', string='Metodo de pago')
    uso_cfdi_id = fields.Many2one('catalogos.uso_cfdi', string='Uso CFDI')

    @api.constrains('colonia')
    def validar_Municipio(self):
        if self.customer== True: 
            if self.cfdi == True:
                if self.municipio == False:
                        raise ValidationError("Error de Validacion : El cliente %s no tiene asignado ningun municipio, favor de asignarlo primera" % (self.name))

    @api.constrains('rfc_cliente','country_id')
    def validar_RFC(self):
        if self.customer== True: 
            if self.cfdi == True:
                if self.rfc_cliente == False:
                    if self.nif == False:
                        raise ValidationError("Error de Validacion : El cliente %s no tiene ningun RFC asignado, favor de asignarlo primero" % (self.name))
                else:
                    if self.is_company == True:
                        #Valida RFC en base al patron de una persona Moral
                        if len(self.rfc_cliente)!=12:
                            raise ValidationError("El RFC %s no tiene la logitud de 12 caracteres para personas Morales que establece el sat" % (self.rfc_cliente))
                        else:    
                            patron_rfc = re.compile(r'^([A-ZÑ\x26]{3}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                            if not patron_rfc.search(self.rfc_cliente):
                                msg = "Formato RFC de Persona Moral Incorrecto"
                                raise ValidationError(msg)
                    else:
                        #Valida el RFC en base al patron de una Persona Fisica
                        if len(self.rfc_cliente)!=13:
                            raise ValidationError("El RFC %s no tiene la logitud de 13 caracteres para personas Fisicas que establece el sat" % (self.rfc_cliente))
                        else: 
                            patron_rfc = re.compile(r'^([A-ZÑ\x26]{4}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                            if not patron_rfc.search(self.rfc_cliente):
                                msg = "Formato RFC de Persona Fisica Incorrecto"
                                raise ValidationError(msg)

    @api.constrains('nif')
    def validar_NIF(self):
        if self.customer== True: 
            if self.cfdi == True:
                if self.nif == False:
                    if self.rfc_cliente == False:
                        raise ValidationError("Error de Validacion : El cliente de origen extranjero %s no tiene el NIF registrado, favor de asignarlo primero" % (self.name))

    @api.constrains('colonia')
    def validar_Colonia(self):
        if self.customer== True: 
            if self.cfdi == True:
                if self.colonia == False:
                        raise ValidationError("Error de Validacion : El cliente %s no tiene asignada ninguna Colonia, favor de asignarlo primera" % (self.name))

    @api.constrains('email')
    def validar_Email(self):
        if self.customer== True: 
            if self.cfdi == True:
                if self.email == False:
                        raise ValidationError("Error de Validacion : El cliente %s no tiene asignado ningun Correo Electronico, favor de asignarlo primera" % (self.name))

    @api.constrains('city')
    def validar_Ciudad(self):
        if self.customer== True: 
            if self.cfdi == True:
                if self.city == False:
                        raise ValidationError("Error de Validacion : El cliente %s no tiene asignada ninguna Ciudad, favor de asignarlo primera" % (self.name))

    @api.constrains('zip')
    def validar_Codigo_Postal(self):
        if self.customer== True: 
            if self.cfdi == True:
                if self.zip == False:
                        raise ValidationError("Error de Validacion : El cliente %s no tiene asignada ningun Codigo Postal, favor de asignarlo primera" % (self.name))

    @api.constrains('country_id')
    def validar_Pais(self):
        if self.customer== True: 
            if self.cfdi == True:
                if self.country_id.name == False:
                        raise ValidationError("Error de Validacion : El cliente %s no tiene asignada ningun Pais, favor de asignarlo primera" % (self.name))
    
    @api.constrains('numero_ext')
    def validar_No_Exterior(self):
        if self.customer== True: 
            if self.cfdi == True:
                if self.numero_ext == False:
                        raise ValidationError("Error de Validacion : El cliente %s no tiene asignada ningun No Exterior, favor de asignarlo primera" % (self.name))

    @api.constrains('state_id')
    def validar_No_Exterior(self):
        if self.customer== True: 
            if self.cfdi == True:
                if self.state_id.name == False:
                        raise ValidationError("Error de Validacion : El cliente %s no tiene asignad ningun Estado, favor de asignarlo primero" % (self.name))