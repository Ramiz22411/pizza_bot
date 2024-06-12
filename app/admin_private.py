from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_change_banner_image,
    orm_get_categories,
    orm_add_product,
    orm_get_products,
    orm_get_product,
    orm_delete_product,
    orm_update_product,
    orm_get_info_pages,
)

from filters.chat_types import ChatTypeFilter, IsAdmin
from kbds.inline import get_callback_btns
from kbds.reply import get_keybord

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(['private']), IsAdmin())

ADMIN_KB = get_keybord(
    'Add product',
    'Product range',
    'Add Banner/change',
    placeholder='Choose action',
    sizes=(2,),
)


@admin_router.message(Command("admin"))
async def add_product(message: types.Message):
    await message.answer("What do you want to do?", reply_markup=ADMIN_KB)


@admin_router.message(F.text == 'Product range')
async def admin_features(message: types.Message, session: AsyncSession):
    categories = await orm_get_categories(session)
    btns = {category.name: f'category_{category.id}' for category in categories}
    await message.answer('Choose category', reply_markup=get_callback_btns(btns=btns))


@admin_router.callback_query(F.data.startswith('category_'))
async def starring_at_product(callback: types.CallbackQuery, session: AsyncSession):
    category_id = callback.data.split('_')[-1]
    for product in await orm_get_products(session, int(category_id)):
        await callback.message.answer_photo(
            product.image,
            caption=f'<strong>{product.name}</strong>\n{product.description}\nPrice: {round(product.price, 2)}',
            reply_markup=get_callback_btns(
                btns={
                    'Delete': f'delete_{product.id}',
                    'Change': f'change_{product.id}',
                },
                sizes=(2,)
            ),
        )
        await callback.answer()
        await callback.message.answer('Good, there is list of products ⏫')


@admin_router.callback_query(F.data.startswith('delete_'))
async def delete_product_callback(callback: types.CallbackQuery, session: AsyncSession):
    product_id = callback.data.split('_')[-1]
    await orm_delete_product(session, int(product_id))

    await callback.answer('Product has deleted!')
    await callback.message.answer('Product has deleted!')


"""Tiny FSM for loading/changing Banners"""


class AddBanner(StatesGroup):
    image = State()


# Working with information bot pages and get state in FSM sending photo
@admin_router.message(StateFilter(None), F.text == 'Add Banner/change')
async def add_image2(message: types.message, state: FSMContext, session: AsyncSession):
    page_names = [page.name for page in await orm_get_info_pages(session)]
    await message.answer(f'Send photo banner.\nIn the description link for what page:\n{", ".join(page_names)}')
    await state.set_state(AddBanner.image)


# Add/Change img in table
# main, catalog, cart(for empty cart), about, payment, shipping
@admin_router.message(AddBanner.image, F.photo)
async def add_banner(message: types.Message, state: FSMContext, session: AsyncSession):
    image_id = message.photo[-1].file_id
    for_page = message.caption.strip()
    page_names = [page.name for page in await orm_get_info_pages(session)]
    if for_page not in page_names:
        await message.answer(f'Pls correct name of page, sample:\n{", ".join(page_names)}')
        return
    await orm_change_banner_image(session, for_page, image_id)
    await message.answer('Banner added/changed')
    await state.clear()


# Catch un correct input
@admin_router.message(AddBanner.image)
async def add_banner2(message: types.Message, state: FSMContext):
    await message.answer('Send photo banner or cancel')


""""""

"""FSM code for CRUD"""


class AddProduct(StatesGroup):
    name = State()
    description = State()
    category = State()
    price = State()
    image = State()

    product_for_change = None

    texts = {
        "AddProduct: name": 'Enter name of product again',
        "AddProduct: description": 'Enter description again',
        "AddProduct: category": 'Enter category again ⬆️',
        "AddProduct: price": 'Enter price again',
        "AddProduct: image": 'This state is last that for....',
    }


@admin_router.callback_query(StateFilter(None), F.data.startswith('change_'))
async def change_product_callback(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    product_id = callback.data.split('_')[-1]
    product_for_change = await orm_get_product(session, int(product_id))

    AddProduct.product_for_change = product_for_change
    await callback.answer()
    await callback.message.answer('Enter new name of product', reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddProduct.name)


@admin_router.message(StateFilter(None), F.text == 'Add product')
async def add_product(message: types.Message, state: FSMContext):
    await message.answer("PLS enter the name of product for adding",
                         reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddProduct.name)


@admin_router.message(StateFilter('*'), Command("cancel"))
@admin_router.message(StateFilter('*'), F.text.casefould() == 'cancel')
async def cancel(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    if AddProduct.product_for_change:
        AddProduct.product_for_change = None

    await state.clear()
    await message.answer('Actions has canceled', reply_markup=ADMIN_KB)


@admin_router.message(StateFilter("*"), Command('back'))
@admin_router.message(StateFilter("*"), F.text.casefould() == 'back')
async def back(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state == AddProduct.name:
        await message.answer('Previous step not exist, pls write cancel')
        return
    previous = None
    for step in AddProduct.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(f"You returned back \n {AddProduct.texts[previous.state]}")
            return
        previous = step


@admin_router.message(AddProduct.name, F.text)
async def add_name(message: types.Message, state: FSMContext):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(name=AddProduct.product_for_change.name)
    else:
        if 4 >= len(message.text) >= 150:
            await message.answer("You enter uncorrect data")
            return

        await state.update_data(name=message.text)
    await message.answer("Enter description of product")
    await state.set_state(AddProduct.description)


@admin_router.message(AddProduct.name)
async def add_name2(message: types.Message, state: FSMContext):
    await message.answer("You enter uncorrect data")


@admin_router.message(AddProduct.description, F.text)
async def add_description(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == '.' and AddProduct.product_for_change:
        await state.update_data(description=AddProduct.product_for_change.description)
    else:
        if 4 >= len(message.text):
            await message.answer("You enter tiny description\n Enter again")
            return

        await state.update_data(description=message.text)

    categories = await orm_get_categories(session)
    btns = {category.name: str(category.id) for category in categories}
    await message.answer("Choose category", reply_markup=get_callback_btns(btns=btns))
    await state.set_state(AddProduct.category)


@admin_router.message(AddProduct.description)
async def add_description2(message: types.Message, state: FSMContext):
    await message.answer("You enter uncorrect data")


# Catch Callback Category
@admin_router.callback_query(AddProduct.category)
async def category_choice(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    if int(callback.data) in [category.id for category in await orm_get_categories(session)]:
        await callback.answer()
        await state.update_data(category=callback.data)
        await callback.message.answer('Now enter price of product')
        await state.set_state(AddProduct.price)
    else:
        await callback.message.answer('Choose category from buttons')
        await callback.answer()


@admin_router.message(AddProduct.category)
async def add_category2(message: types.Message, state: FSMContext):
    await message.answer("'Choose category from buttons'")


@admin_router.message(AddProduct.price, F.text)
async def add_price(message: types.Message, state: FSMContext):
    if message.text == '.' and AddProduct.product_for_change:
        await state.update_data(price=AddProduct.product_for_change.price)
    else:
        try:
            float(message.text)
        except ValueError:
            await message.answer("You enter uncorrect data price")
            return

        await state.update_data(price=message.text)
    await message.answer("Enter photo of product")
    await state.set_state(AddProduct.image)


@admin_router.message(AddProduct.price)
async def add_price2(message: types.Message, state: FSMContext):
    await message.answer("You enter uncorrect data price")


@admin_router.message(AddProduct.image, or_f(F.photo, F.text == '.'))
async def add_image(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text == '.' and AddProduct.product_for_change:
        await state.update_data(image=AddProduct.product_for_change.image)
    elif message.photo:
        await state.update_data(image=message.photo[-1].file_id)
    else:
        await message.answer("You enter uncorrect data photo")
        return
    data = await state.get_data()
    try:
        if AddProduct.product_for_change:
            await orm_update_product(session, AddProduct.product_for_change.id, data)
        else:
            await orm_add_product(session, data)
        await message.answer("Your product was add/change", reply_markup=ADMIN_KB)
        await state.clear()

    except Exception as e:
        await message.answer(f"Error: \n{str(e)}\n", reply_markup=ADMIN_KB)
        await state.clear()

    AddProduct.product_for_change = None


@admin_router.message(AddProduct.image)
async def add_photo2(message: types.Message, state: FSMContext):
    await message.answer("You enter uncorrect data photo")
