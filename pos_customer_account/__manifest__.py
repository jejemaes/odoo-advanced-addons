
{
    'name': 'Point of Sale Customer Account',
    'version': '1.0',
    'category': 'Point Of Sale',
    'summary': 'Point of Sale Customer Account',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_payment_views.xml',
        'wizard/pos_payment_change_views.xml',
    ],
}
