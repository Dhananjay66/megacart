from django import forms
from .models import Variation
from .models import Product, ReviewRating
from django.forms import inlineformset_factory

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['product_name', 'slug', 'description', 'price', 'images', 'stock', 'is_available', 'category']


class ReviewForm(forms.ModelForm):
    class Meta:
        model = ReviewRating
        fields = ['subject', 'review', 'rating']


class VariationForm(forms.ModelForm):
    class Meta:
        model = Variation
        fields = ['variation_category', 'variation_value', 'is_active']

# Create the inline formset
VariationFormSet = inlineformset_factory(
    Product,
    Variation,
    form=VariationForm,
    extra=5,
    can_delete=True
)