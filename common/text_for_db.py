from aiogram.utils.formatting import Bold, as_list, as_marked_section


categories = ['Food', 'Beverage']

description_for_info_pages = {
    "main": 'Welcome to the main page',
    'about': 'Pizzerias work time 24 hour 7 day for week',
    'payment': as_marked_section(
        Bold('Variant Payments:'),
        'by card in bot',
        'pay receipt by card or cash',
        'in establishment',
        marker='✅',
    ).as_html(),
    'shipping': as_list(
        as_marked_section(
            Bold('Variants of shipping/order:'),
            'by courier',
            'pick up',
            'eat in establishment',
            marker='✅',
        ),
        as_marked_section(Bold('it is forbidden:'), 'by post', 'pigeon', marker='❌ '),
        sep='\n-----------------------\n',
    ).as_html(),
    'catalog': 'Categories',
    'cart': 'Cart is empty!'
}
