# -*- coding: utf-8 -*-
{
    'name': "sft_facturacion",

    'summary': """
        Modulo de timbrado de CFDI 3.3 hacia Sft-Facturacion""",
	'license': 'OPL-1',
    'description': """
        El modulo esta integrado al portal de Sft-Facturacion, heredando toda la funcionalidad tanto en el portal en linea, como en el modulo dentro de Odoo.
    """,

    'author': "Softhink",
    'website': "http://www.sft.com.mx",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['sale','point_of_sale','catalogos','stock','account','account_accountant'],
    #'depends': ['account','account_accountant'],
    # always loaded
    'data': [
        #'security/ir.model.access.csv',
        'views/views_account_invoice.xml',
        'views/views_product_template.xml',
        'views/views_res_partner.xml',
        'views/views_res_company.xml',
        'views/views_sft_ayuda_error_factura.xml',
        'views/views_account_payment.xml',
        'views/views_wizard_account_invoice_refund.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
       
    ],
	"images":['static/description/Integracion4.jpg'],
}
