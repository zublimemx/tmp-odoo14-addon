from odoo import SUPERUSER_ID, api


def uninstall_hook(cr, registry):
    """Archiva los favoritos que usan los filtros del módulo.

    Sin sus campos, un favorito así (sobre todo si es el predeterminado) haría
    fallar la lista de facturas. Se archiva, no se borra: no se pierde nada.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    favorites = env["ir.filters"].search([
        ("model_id", "=", "account.move"),
        "|", ("domain", "like", "zub_any_"), ("domain", "like", "zub_all_"),
    ])
    favorites.write({"active": False, "is_default": False})
