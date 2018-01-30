# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ErrorFactura(models.Model):
    _name = 'sft_ayuda.error.factura'

    clave = fields.Char("Clave")
    error = fields.Char("Error")
    solucion = fields.Text("Solucion")
    url = fields.Char("Link")
