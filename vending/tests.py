import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import (
    Product,
    TransactionChange,
    TransactionInsertion,
    TransactionItem,
    VendingTransaction,
)


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class VendingMachineTests(TestCase):
    def setUp(self):
        Product.objects.create(
            product_id="04",
            name="Hello Panda",
            category="Snacks and chocolates",
            price_cents=4000,
            quantity=5,
            image="images/products/hello panda.png",
            category_order=1,
        )
        Product.objects.create(
            product_id="10",
            name="Astor",
            category="Snacks and chocolates",
            price_cents=1500,
            quantity=2,
            image="images/products/astor.png",
            category_order=1,
        )
        Product.objects.create(
            product_id="19",
            name="Coca-Cola",
            category="Other beverages",
            price_cents=6000,
            quantity=5,
            image="images/products/coca.png",
            category_order=2,
        )

    def post_json(self, url, data=None):
        return self.client.post(
            url,
            data=json.dumps(data or {}),
            content_type="application/json",
        )

    def start_with_money(self, denomination_cents):
        started = self.post_json("/api/transactions")
        transaction_id = started.json()["transaction_id"]
        inserted = self.post_json(
            "/api/transactions/{}/insert".format(transaction_id),
            {"denomination_cents": denomination_cents},
        )
        self.assertEqual(inserted.status_code, 200)
        return transaction_id

    def test_homepage_renders_products_and_machine_controls(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hello Panda")
        self.assertContains(response, "Soft drinks")
        self.assertContains(response, "Rs</span>100")
        self.assertContains(response, "name=\"csrfmiddlewaretoken\"")

    def test_transaction_collection_keeps_get_and_post_behavior(self):
        history = self.client.get("/api/transactions")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json(), [])

        created = self.post_json("/api/transactions")
        self.assertEqual(created.status_code, 200)
        self.assertTrue(
            VendingTransaction.objects.filter(
                transaction_id=created.json()["transaction_id"]
            ).exists()
        )

    def test_money_purchase_and_change_are_saved_by_denomination(self):
        transaction_id = self.start_with_money(10000)

        bought = self.post_json(
            "/api/transactions/{}/purchase".format(transaction_id),
            {"product_id": "04", "quantity": 1},
        )
        self.assertEqual(bought.status_code, 200)
        self.assertEqual(bought.json()["remaining_credit_cents"], 6000)
        self.assertEqual(bought.json()["stock_remaining"], 4)

        finished = self.post_json(
            "/api/transactions/{}/finish".format(transaction_id)
        )
        self.assertEqual(finished.status_code, 200)
        self.assertEqual(finished.json()["change_returned_cents"], 6000)
        self.assertEqual(finished.json()["change_denominations"], [5000, 1000])

        saved = VendingTransaction.objects.get(transaction_id=transaction_id)
        self.assertEqual(saved.status, VendingTransaction.STATUS_COMPLETED)
        self.assertEqual(saved.total_inserted_cents, 10000)
        self.assertEqual(saved.total_purchase_cents, 4000)
        self.assertEqual(saved.change_returned_cents, 6000)
        self.assertEqual(
            list(
                TransactionInsertion.objects.filter(
                    transaction=saved
                ).values_list("denomination_cents", flat=True)
            ),
            [10000],
        )
        self.assertEqual(
            list(
                TransactionChange.objects.filter(
                    transaction=saved
                ).values_list("denomination_cents", flat=True)
            ),
            [5000, 1000],
        )
        self.assertEqual(TransactionItem.objects.filter(transaction=saved).count(), 1)

    def test_multiple_purchases_keep_credit_and_record_each_item(self):
        transaction_id = self.start_with_money(20000)

        first = self.post_json(
            "/api/transactions/{}/purchase".format(transaction_id),
            {"product_id": "04", "quantity": 2},
        )
        self.assertEqual(first.json()["remaining_credit_cents"], 12000)
        second = self.post_json(
            "/api/transactions/{}/purchase".format(transaction_id),
            {"product_id": "10", "quantity": 1},
        )
        self.assertEqual(second.json()["remaining_credit_cents"], 10500)
        self.assertEqual(Product.objects.get(product_id="04").quantity, 3)
        self.assertEqual(Product.objects.get(product_id="10").quantity, 1)

        finished = self.post_json(
            "/api/transactions/{}/finish".format(transaction_id)
        )
        self.assertEqual(finished.json()["change_returned_cents"], 10500)
        self.assertEqual(finished.json()["change_denominations"], [10000, 500])
        self.assertEqual(
            TransactionItem.objects.filter(
                transaction_id=transaction_id
            ).count(),
            2,
        )

    def test_insufficient_credit_or_stock_does_not_create_sale(self):
        transaction_id = self.start_with_money(1000)
        too_expensive = self.post_json(
            "/api/transactions/{}/purchase".format(transaction_id),
            {"product_id": "04", "quantity": 1},
        )
        self.assertEqual(too_expensive.status_code, 400)
        self.assertIn("Insufficient credit", too_expensive.json()["error"])
        self.assertEqual(TransactionItem.objects.count(), 0)
        self.assertEqual(Product.objects.get(product_id="04").quantity, 5)

        enough_money = self.post_json(
            "/api/transactions/{}/insert".format(transaction_id),
            {"denomination_cents": 5000},
        )
        self.assertEqual(enough_money.status_code, 200)
        too_many = self.post_json(
            "/api/transactions/{}/purchase".format(transaction_id),
            {"product_id": "04", "quantity": 6},
        )
        self.assertEqual(too_many.status_code, 400)
        self.assertIn("Only 5", too_many.json()["error"])
        self.assertEqual(TransactionItem.objects.count(), 0)

        Product.objects.filter(product_id="04").update(quantity=0)
        sold_out = self.post_json(
            "/api/transactions/{}/purchase".format(transaction_id),
            {"product_id": "04", "quantity": 1},
        )
        self.assertEqual(sold_out.status_code, 400)
        self.assertEqual(sold_out.json()["error"], "SOLD OUT")
        self.assertEqual(TransactionItem.objects.count(), 0)

    def test_staff_can_open_history_and_view_completed_and_pending_transactions(self):
        transaction_id = self.start_with_money(10000)
        purchase = self.post_json(
            "/api/transactions/{}/purchase".format(transaction_id),
            {"product_id": "04", "quantity": 1},
        )
        self.assertEqual(purchase.status_code, 200)
        finished = self.post_json(
            "/api/transactions/{}/finish".format(transaction_id)
        )
        self.assertEqual(finished.status_code, 200)

        pending = self.post_json("/api/transactions")
        denied = self.client.get("/inventory/")
        self.assertEqual(denied.status_code, 302)

        User = get_user_model()
        user = User.objects.create_user(
            username="history-manager",
            password="history-manager-test-password",
            is_staff=True,
        )
        self.client.force_login(user)
        dashboard = self.client.get("/inventory/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "TRANSACTION HISTORY")
        self.assertContains(dashboard, "/admin/transactions/")

        history = self.client.get("/admin/transactions/")
        self.assertEqual(history.status_code, 200)
        self.assertContains(history, "All transactions")
        self.assertContains(dashboard, "Hello Panda")
        self.assertContains(history, "Hello Panda")
        self.assertContains(history, "Rs 100.00")
        self.assertContains(history, "Rs 40.00")
        self.assertContains(history, "#{}".format(transaction_id))
        self.assertContains(history, "#{}".format(pending.json()["transaction_id"]))
        self.assertContains(history, "Pending")

    def test_admin_inventory_requires_staff_and_restock_adds_stock(self):
        denied = self.client.get("/inventory/")
        self.assertEqual(denied.status_code, 302)

        User = get_user_model()
        user = User.objects.create_user(
            username="stock-manager",
            password="A-long-test-password-123",
            is_staff=True,
        )
        self.client.force_login(user)
        dashboard = self.client.get("/inventory/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Hello Panda")
        self.assertContains(dashboard, "Inventory management")
        response = self.client.post(
            "/inventory/products/04/restock/",
            {"quantity_to_add": "20"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Product.objects.get(product_id="04").quantity, 25)

    def test_django_admin_can_view_registered_product_model(self):
        User = get_user_model()
        user = User.objects.create_superuser(
            username="site-admin",
            email="admin@example.test",
            password="A-long-test-password-123",
        )
        self.client.force_login(user)
        response = self.client.get("/django-admin/vending/product/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hello Panda")

    def test_api_post_requires_csrf_token(self):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        denied = csrf_client.post(
            "/api/transactions",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)

        homepage = csrf_client.get("/")
        self.assertEqual(homepage.status_code, 200)
        token = csrf_client.cookies["csrftoken"].value
        allowed = csrf_client.post(
            "/api/transactions",
            data="{}",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(allowed.status_code, 200)

    def test_finished_transaction_cannot_be_completed_twice(self):
        transaction_id = self.start_with_money(10000)
        first = self.post_json("/api/transactions/{}/finish".format(transaction_id))
        second = self.post_json("/api/transactions/{}/finish".format(transaction_id))
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(
            TransactionChange.objects.filter(
                transaction_id=transaction_id
            ).count(),
            1,
        )
