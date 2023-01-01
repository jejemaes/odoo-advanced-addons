
{
    'name': 'Point of Sale Require Customer',
    'version': '1.0',
    'category': 'Point Of Sale',
    'summary': 'Point of Sale Require Customer',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'views/pos_config_view.xml',
        'views/pos_order_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pos_customer_required/static/src/js/pos_customer_required.js',
        ]
    }
}
