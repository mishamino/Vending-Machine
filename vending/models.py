from django.db import models


class Product(models.Model):
    product_id = models.CharField(max_length=12, primary_key=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=80)
    price_cents = models.PositiveBigIntegerField()
    quantity = models.PositiveBigIntegerField()
    image = models.CharField(max_length=255)
    category_order = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category_order", "product_id"]

    def __str__(self):
        return "{} - {}".format(self.product_id, self.name)

    @property
    def price_display(self):
        return "{:.2f}".format(self.price_cents / 100)

    @property
    def price_whole_rupees(self):
        return self.price_cents // 100


class VendingTransaction(models.Model):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
    ]

    transaction_id = models.BigAutoField(primary_key=True)
    transaction_date = models.DateField()
    transaction_time = models.TimeField()
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    total_inserted_cents = models.PositiveBigIntegerField(default=0)
    total_purchase_cents = models.PositiveBigIntegerField(default=0)
    change_returned_cents = models.PositiveBigIntegerField(default=0)

    class Meta:
        ordering = ["-transaction_id"]

    def __str__(self):
        return "Transaction {}".format(self.transaction_id)

    @property
    def total_inserted_display(self):
        return "{:.2f}".format(self.total_inserted_cents / 100)

    @property
    def total_purchase_display(self):
        return "{:.2f}".format(self.total_purchase_cents / 100)

    @property
    def change_returned_display(self):
        return "{:.2f}".format(self.change_returned_cents / 100)


class TransactionInsertion(models.Model):
    transaction = models.ForeignKey(
        VendingTransaction,
        on_delete=models.CASCADE,
        related_name="insertions",
    )
    denomination_cents = models.PositiveBigIntegerField()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return "{} cents inserted".format(self.denomination_cents)


class TransactionItem(models.Model):
    transaction = models.ForeignKey(
        VendingTransaction,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        to_field="product_id",
        db_column="product_id",
        on_delete=models.PROTECT,
        related_name="sales",
    )
    quantity = models.PositiveBigIntegerField()
    unit_price_cents = models.PositiveBigIntegerField()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return "{} x {}".format(self.quantity, self.product)

    @property
    def unit_price_display(self):
        return "{:.2f}".format(self.unit_price_cents / 100)


class TransactionChange(models.Model):
    transaction = models.ForeignKey(
        VendingTransaction,
        on_delete=models.CASCADE,
        related_name="change_denominations",
    )
    denomination_cents = models.PositiveBigIntegerField()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return "{} cents returned".format(self.denomination_cents)
