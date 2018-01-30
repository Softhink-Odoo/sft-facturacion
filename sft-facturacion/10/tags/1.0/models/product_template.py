from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import models, fields, api

#Agrega el campo para seleccionar la clave de productos segun el catalogo del sat
class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    clave_prod_catalogo_sat_id = fields.Many2one('catalogos.clave_prod_serv',string='Productos y Servicios', help='Clave Producto y Servicios segun el catalogo del sat')
    clave_unidad_clave_catalogo_sat_id = fields.Many2one('catalogos.clave_unidad',string='Clave Unidad', help='Unidad de medida utilizada segun el catalogo del sat')
    

    @api.constrains('clave_prod_catalogo_sat_id')
    def validar_clave_prod_catalogo_sat_id(self):
        if self.clave_prod_catalogo_sat_id.descripcion == False:
            raise ValidationError('No ha asignado ninguna clave de productos y servicios del catalogo del sat')

    @api.constrains('clave_unidad_clave_catalogo_sat_id')
    def validar_clave_unidad_clave_catalogo_sat_id(self):
        if self.clave_unidad_clave_catalogo_sat_id.nombre == False:
            raise ValidationError('No ha asignado ninguna clave para la unidad de medida de este producto segun el catalogo del sat')


#class ProductTemplate(models.Model):
 #   _name = 'product.template'
  #  _inherit = 'product.product'
