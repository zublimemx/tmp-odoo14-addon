{
    "name": "Filtros de impuestos en facturas",
    "summary": "Filtros por impuesto en la lista de facturas, configurables.",
    "description": "Agrega 8 filtros por impuesto (al menos una / todas las líneas con "
    "IVA 16%, IVA 0%, IVA Exento e IEPS 8%) a la lista de facturas. Ver README.md.",
    "version": "14.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Zublime",
    "website": "https://zublime.com.mx",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "security/zub_invoice_tax_filter_security.xml",
        "views/zub_invoice_tax_filter_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}
