from odoo import http
from odoo.http import request
from werkzeug.exceptions import NotFound
from odoo.osv import expression


class RestaraurantController(http.Controller):

    @http.route('/restaurant/<model("restaurant.kitchen"):kitchen>/<model("pos.order"):order>/reprint', auth='user', type="http")
    def restautant_order_reprint(self, kitchen, order, **kwargs):
        """ Render the online menu with available products on selected categories """
        order = order.with_context(kitchen_id=kitchen.id)

        # increment print count
        counter = 1
        if order.print_count >= 0:
            counter = order.print_count + 1
        order.sudo().write({'print_count': counter})

        # render ticket
        return request.render('pos_restaurant_kitchen.pos_order_reprint_receipt', {
            'order': order.sudo(),
            'lines': kitchen.get_order_line(order),
            'kitchen': kitchen,
            'is_line_simple': lambda l: l.discount == 0 and l.qty == 1
        })
