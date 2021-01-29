from odoo import http
from odoo.http import request
from werkzeug.exceptions import NotFound
from odoo.osv import expression


class RestaraurantMenuController(http.Controller):

    @http.route('/restaurant/<model("restaurant.menu"):menu>', auth='public')
    def restaurant_menu_page(self, menu, **kwargs):
        """ Render the online menu with available products on selected categories """
        if menu.is_published:
            domain = ['&', ('available_in_pos', '=', True), '|', ('company_id', '=', menu.company_id.id), ('company_id', '=', False)]
            if menu.pos_category_ids:
                domain = expression.AND([domain, [('pos_categ_id', 'in', menu.pos_category_ids.ids)]])

            products = request.env['product.product'].sudo().search(domain)
            categories = products.mapped('pos_categ_id')

            product_category_map = {}
            for product in products:
                product_category_map.setdefault(product.pos_categ_id, request.env['product.product'].sudo())
                product_category_map[product.pos_categ_id] |= product

            return request.render('pos_restaurant_menu.pos_restaurant_online_menu', {
                'product_category_map': product_category_map,
                'menu': menu,
                'categories': categories.sorted(key=lambda r: r.sequence),
            })
        return NotFound()
