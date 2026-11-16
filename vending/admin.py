from django.contrib import admin

from .models import (
    Product,
    TransactionChange,
    TransactionInsertion,
    TransactionItem,
    VendingTransaction,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "product_id",
        "name",
        "category",
        "price_cents",
        "quantity",
        "is_active",
    )
    list_filter = ("category", "is_active")
    search_fields = ("product_id", "name", "category")


@admin.register(VendingTransaction)
class VendingTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "transaction_date",
        "transaction_time",
        "status",
        "total_inserted_cents",
        "total_purchase_cents",
        "change_returned_cents",
    )
    list_filter = ("status", "transaction_date")


@admin.register(TransactionInsertion)
class TransactionInsertionAdmin(admin.ModelAdmin):
    list_display = ("id", "transaction", "denomination_cents")
    list_filter = ("denomination_cents",)


@admin.register(TransactionItem)
class TransactionItemAdmin(admin.ModelAdmin):
    list_display = ("id", "transaction", "product", "quantity", "unit_price_cents")
    list_filter = ("product",)
    search_fields = ("product__product_id", "product__name")


@admin.register(TransactionChange)
class TransactionChangeAdmin(admin.ModelAdmin):
    list_display = ("id", "transaction", "denomination_cents")
    list_filter = ("denomination_cents",)
