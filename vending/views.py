import json
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import ProductForm, RestockForm
from .models import (
    Product,
    TransactionChange,
    TransactionInsertion,
    TransactionItem,
    VendingTransaction,
)


INSERT_DENOMINATIONS = [
    100,
    500,
    1000,
    2000,
    2500,
    5000,
    10000,
    20000,
    50000,
    100000,
    200000,
]
CHANGE_DENOMINATIONS = sorted(INSERT_DENOMINATIONS, reverse=True)


def error_response(message, status=400):
    return JsonResponse({"error": message}, status=status)


def read_json(request):
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


@require_GET
def home(request):
    products = list(Product.objects.filter(is_active=True))
    cake_products = [
        product
        for product in products
        if any(
            word in product.category.casefold()
            for word in ("cake", "snack", "chocolate")
        )
    ]
    drink_products = [
        product for product in products if product not in cake_products
    ]
    categories = [
        {"name": "Cakes", "products": cake_products},
        {"name": "Soft drinks", "products": drink_products},
    ]
    categories = [category for category in categories if category["products"]]
    return render(
        request,
        "machine/index.html",
        {
            "categories": categories,
            "products_data": [
                {
                    "product_id": product.product_id,
                    "name": product.name,
                    "category": product.category,
                    "price_cents": product.price_cents,
                    "quantity": product.quantity,
                    "image": product.image,
                }
                for product in products
            ],
            "denominations": INSERT_DENOMINATIONS,
            "denomination_buttons": [
                (value, value // 100) for value in INSERT_DENOMINATIONS
            ],
            "keypad_keys": [
                "1", "2", "3", "4", "5", "6",
                "7", "8", "9", "clear", "0", "confirm",
            ],
        },
    )


@require_GET
def list_products(request):
    products = Product.objects.filter(is_active=True)
    return JsonResponse(
        [
            {
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "price_cents": product.price_cents,
                "quantity": product.quantity,
                "image": product.image,
            }
            for product in products
        ],
        safe=False,
    )


@require_POST
def start_transaction(request):
    local_now = timezone.localtime()
    new_transaction = VendingTransaction.objects.create(
        transaction_date=timezone.localdate(),
        transaction_time=local_now.replace(tzinfo=None, microsecond=0).time(),
    )
    return JsonResponse(
        {"transaction_id": new_transaction.transaction_id, "credit_cents": 0}
    )


@require_POST
def insert_money(request, transaction_id):
    data = read_json(request)
    if data is None:
        return error_response("Send a valid money denomination.")
    denomination = data.get("denomination_cents")
    if type(denomination) is not int or denomination not in INSERT_DENOMINATIONS:
        return error_response("That money denomination is not accepted.")

    with transaction.atomic():
        current_transaction = VendingTransaction.objects.select_for_update().filter(
            transaction_id=transaction_id
        ).first()
        if current_transaction is None:
            return error_response("Transaction not found.", 404)
        if current_transaction.status != VendingTransaction.STATUS_PENDING:
            return error_response("This transaction has already ended.")
        TransactionInsertion.objects.create(
            transaction=current_transaction,
            denomination_cents=denomination,
        )
        current_transaction.total_inserted_cents = F(
            "total_inserted_cents"
        ) + denomination
        current_transaction.save(update_fields=["total_inserted_cents"])
        current_transaction.refresh_from_db()

    credit = (
        current_transaction.total_inserted_cents
        - current_transaction.total_purchase_cents
    )
    return JsonResponse({"credit_cents": credit})


@require_POST
def purchase_product(request, transaction_id):
    data = read_json(request)
    if data is None:
        return error_response("Send a valid product code and quantity.")
    product_id = data.get("product_id")
    quantity = data.get("quantity")
    if not isinstance(product_id, str) or type(quantity) is not int or quantity < 1:
        return error_response("Enter a product code and a quantity of at least 1.")

    with transaction.atomic():
        current_transaction = VendingTransaction.objects.select_for_update().filter(
            transaction_id=transaction_id
        ).first()
        if current_transaction is None:
            return error_response("Transaction not found.", 404)
        if current_transaction.status != VendingTransaction.STATUS_PENDING:
            return error_response("This transaction has already ended.")

        product = Product.objects.select_for_update().filter(
            product_id=product_id,
            is_active=True,
        ).first()
        if product is None:
            return error_response("Product code not found.")
        if product.quantity == 0:
            return error_response("SOLD OUT")
        if quantity > product.quantity:
            return error_response(
                "Only {} {} available.".format(product.quantity, product.name)
            )

        total_cost = product.price_cents * quantity
        credit = (
            current_transaction.total_inserted_cents
            - current_transaction.total_purchase_cents
        )
        if total_cost > credit:
            return error_response(
                "Insufficient credit. Insert Rs {:.2f} more.".format(
                    (total_cost - credit) / 100
                )
            )

        Product.objects.filter(product_id=product_id).update(
            quantity=F("quantity") - quantity
        )
        TransactionItem.objects.create(
            transaction=current_transaction,
            product=product,
            quantity=quantity,
            unit_price_cents=product.price_cents,
        )
        current_transaction.total_purchase_cents = F(
            "total_purchase_cents"
        ) + total_cost
        current_transaction.save(update_fields=["total_purchase_cents"])
        current_transaction.refresh_from_db()
        product.refresh_from_db()

    return JsonResponse(
        {
            "product_name": product.name,
            "product_id": product_id,
            "quantity_purchased": quantity,
            "unit_price_cents": product.price_cents,
            "total_cost_cents": total_cost,
            "remaining_credit_cents": (
                current_transaction.total_inserted_cents
                - current_transaction.total_purchase_cents
            ),
            "stock_remaining": product.quantity,
        }
    )


@require_POST
def finish_transaction(request, transaction_id):
    with transaction.atomic():
        current_transaction = VendingTransaction.objects.select_for_update().filter(
            transaction_id=transaction_id
        ).first()
        if current_transaction is None:
            return error_response("Transaction not found.", 404)
        if current_transaction.status != VendingTransaction.STATUS_PENDING:
            return error_response("This transaction has already ended.")
        change_cents = (
            current_transaction.total_inserted_cents
            - current_transaction.total_purchase_cents
        )
        remaining_change = change_cents
        returned_denominations = []
        for denomination in CHANGE_DENOMINATIONS:
            while remaining_change >= denomination:
                returned_denominations.append(denomination)
                remaining_change -= denomination

        if remaining_change:
            return error_response("The machine cannot make the exact change.")

        TransactionChange.objects.bulk_create(
            [
                TransactionChange(
                    transaction=current_transaction,
                    denomination_cents=denomination,
                )
                for denomination in returned_denominations
            ]
        )
        current_transaction.change_returned_cents = change_cents
        current_transaction.status = VendingTransaction.STATUS_COMPLETED
        current_transaction.save(
            update_fields=["change_returned_cents", "status"]
        )

    return JsonResponse(
        {
            "transaction_id": current_transaction.transaction_id,
            "total_inserted_cents": current_transaction.total_inserted_cents,
            "total_purchase_cents": current_transaction.total_purchase_cents,
            "change_returned_cents": change_cents,
            "change_denominations": returned_denominations,
        }
    )


@require_GET
def list_transactions(request):
    completed = VendingTransaction.objects.filter(
        status=VendingTransaction.STATUS_COMPLETED
    ).prefetch_related("insertions", "items", "change_denominations")
    results = []
    for record in completed:
        results.append(
            {
                "transaction_id": record.transaction_id,
                "transaction_date": record.transaction_date.isoformat(),
                "transaction_time": record.transaction_time.isoformat(),
                "status": record.status,
                "total_inserted_cents": record.total_inserted_cents,
                "total_purchase_cents": record.total_purchase_cents,
                "change_returned_cents": record.change_returned_cents,
                "insertions": [
                    item.denomination_cents for item in record.insertions.all()
                ],
                "items": [
                    {
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "unit_price_cents": item.unit_price_cents,
                    }
                    for item in record.items.all()
                ],
                "change_denominations": [
                    item.denomination_cents
                    for item in record.change_denominations.all()
                ],
            }
        )
    return JsonResponse(results, safe=False)


@require_http_methods(["GET", "POST"])
def transactions(request):
    if request.method == "POST":
        return start_transaction(request)
    return list_transactions(request)


@staff_member_required(login_url="admin_login")
def admin_dashboard(request):
    return render(
        request,
        "vending/admin.html",
        {"products": Product.objects.all(), "product_form": ProductForm()},
    )


@staff_member_required(login_url="admin_login")
def transaction_history_page(request):
    transactions_page = Paginator(
        VendingTransaction.objects.prefetch_related(
            "items__product", "insertions", "change_denominations"
        ),
        20,
    ).get_page(request.GET.get("transactions_page"))
    return render(
        request,
        "vending/transaction_history.html",
        {"transactions_page": transactions_page},
    )


@staff_member_required(login_url="admin_login")
@require_POST
def add_product(request):
    form = ProductForm(request.POST)
    if not form.is_valid():
        error_text = "; ".join(
            str(error)
            for errors in form.errors.values()
            for error in errors
        )
        messages.error(request, error_text)
        return redirect("admin_dashboard")

    values = form.cleaned_data
    if Product.objects.filter(product_id=values["product_id"]).exists():
        messages.error(request, "That product ID already exists.")
        return redirect("admin_dashboard")

    category_order = Product.objects.filter(
        category=values["category"]
    ).values_list("category_order", flat=True).first()
    if category_order is None:
        category_order = (Product.objects.aggregate(Max("category_order"))[
            "category_order__max"
        ] or -1) + 1
    Product.objects.create(
        product_id=values["product_id"],
        name=values["name"],
        category=values["category"],
        price_cents=int(values["price"] * 100),
        quantity=values["quantity"],
        image=values["image"],
        category_order=category_order,
        is_active=True,
    )
    messages.success(request, "Product added to the vending machine.")
    return redirect("admin_dashboard")


@staff_member_required(login_url="admin_login")
@require_POST
def update_product(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    form = ProductForm(request.POST)
    if not form.is_valid():
        error_text = "; ".join(
            str(error)
            for errors in form.errors.values()
            for error in errors
        )
        messages.error(request, error_text)
        return redirect("admin_dashboard")

    values = form.cleaned_data
    if values["product_id"] != product_id:
        messages.error(request, "Product ID cannot be changed.")
        return redirect("admin_dashboard")

    if product.category == values["category"]:
        category_order = product.category_order
    else:
        category_order = Product.objects.filter(
            category=values["category"]
        ).values_list("category_order", flat=True).first()
        if category_order is None:
            category_order = (Product.objects.aggregate(Max("category_order"))[
                "category_order__max"
            ] or -1) + 1

    product.name = values["name"]
    product.category = values["category"]
    product.price_cents = int(values["price"] * 100)
    product.quantity = values["quantity"]
    product.image = values["image"]
    product.category_order = category_order
    product.is_active = values["is_active"]
    product.save()
    messages.success(request, "Product details saved.")
    return redirect("admin_dashboard")


@staff_member_required(login_url="admin_login")
@require_POST
def restock_product(request, product_id):
    form = RestockForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a whole number greater than 0 to restock.")
        return redirect("admin_dashboard")

    with transaction.atomic():
        product = get_object_or_404(
            Product.objects.select_for_update(),
            product_id=product_id,
        )
        if not product.is_active:
            messages.error(
                request,
                "Restore this discontinued product before restocking it.",
            )
        else:
            product.quantity = F("quantity") + form.cleaned_data["quantity_to_add"]
            product.save(update_fields=["quantity"])
            messages.success(
                request,
                "Stock increased by {} units.".format(
                    form.cleaned_data["quantity_to_add"]
                ),
            )
    return redirect("admin_dashboard")


@staff_member_required(login_url="admin_login")
@require_POST
def delete_product(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    if product.sales.exists():
        product.is_active = False
        product.save(update_fields=["is_active"])
        messages.success(
            request,
            "Product discontinued. Historical transaction records were preserved.",
        )
    else:
        product.delete()
        messages.success(request, "Product deleted.")
    return redirect("admin_dashboard")
