from decimal import Decimal
from pathlib import PurePosixPath

from django import forms


class ProductForm(forms.Form):
    product_id = forms.RegexField(
        regex=r"^\d{2}$",
        max_length=2,
        error_messages={"invalid": "Product ID must contain exactly two numbers."},
    )
    name = forms.CharField(max_length=100)
    category = forms.CharField(max_length=80)
    price = forms.DecimalField(
        min_value=Decimal("0"),
        max_digits=10,
        decimal_places=2,
        label="Price in Rupees",
    )
    image = forms.CharField(max_length=255)
    quantity = forms.IntegerField(min_value=0, label="Stock quantity")
    is_active = forms.BooleanField(required=False, initial=True)

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_category(self):
        return self.cleaned_data["category"].strip()

    def clean_image(self):
        image = self.cleaned_data["image"].strip().replace("\\", "/")
        image_path = PurePosixPath(image)
        if (
            not image
            or image_path.is_absolute()
            or ".." in image_path.parts
            or ":" in image
        ):
            raise forms.ValidationError(
                "Enter an image path relative to the static folder."
            )
        return image_path.as_posix()

    def clean_price(self):
        price = self.cleaned_data["price"]
        if not price.is_finite() or price != price.to_integral_value():
            raise forms.ValidationError(
                "Price must be a whole Rupee because the machine returns "
                "whole-Rupee denominations."
            )
        return price


class RestockForm(forms.Form):
    quantity_to_add = forms.IntegerField(min_value=1, label="Quantity to add")
