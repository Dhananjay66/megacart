from django.db import models
from store.models import Product, Variation
from accounts.models import Account
from orders.models import Order

# Create your models here.

class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True)
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.cart_id


class CartItem(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variations = models.ManyToManyField(Variation, blank=True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, null=True)
    quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 

    def sub_total(self):
        return (self.price if self.price else self.product.price) * self.quantity


    def __str__(self):
        return self.product.product_name