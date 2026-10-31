{
    "name": "Filtros de impuestos en facturas",
    "summary": "Filtros por impuesto en la lista de facturas, configurables.",
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
