from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("api/products", views.list_products, name="api_products"),
    path("api/transactions", views.transactions, name="transactions"),
    path(
        "api/transactions/<int:transaction_id>/insert",
        views.insert_money,
        name="insert_money",
    ),
    path(
        "api/transactions/<int:transaction_id>/purchase",
        views.purchase_product,
        name="purchase_product",
    ),
    path(
        "api/transactions/<int:transaction_id>/finish",
        views.finish_transaction,
        name="finish_transaction",
    ),
    path("api/transactions/history", views.list_transactions, name="transaction_history"),
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("inventory/", views.admin_dashboard, name="inventory_dashboard"),
    path(
        "admin/transactions/",
        views.transaction_history_page,
        name="admin_transaction_history",
    ),
    path("inventory/products/add/", views.add_product, name="add_product"),
    path(
        "inventory/products/<str:product_id>/update/",
        views.update_product,
        name="update_product",
    ),
    path(
        "inventory/products/<str:product_id>/restock/",
        views.restock_product,
        name="restock_product",
    ),
    path(
        "inventory/products/<str:product_id>/delete/",
        views.delete_product,
        name="delete_product",
    ),
]
