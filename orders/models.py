from django.db import models
from accounts.models import Account
from store.models import Product, Variation
from django.core.validators import MinValueValidator



class Payment(models.Model):
    PAYMENT_METHODS = (
        ('COD', 'Cash On Delivery'),
        ('UPI', 'UPI'),
        ('Card', 'Credit/Debit Card'),
        # Add more if needed
    )

    PAYMENT_STATUS = (
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
        ('Cancelled', 'Cancelled'),
    )
    DELIVERY_STATUS = (
        ('Pending', 'Pending'),
        ('Shipped', 'Shipped'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Returned', 'Returned'),
    )


    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Pending')
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Payment #{self.id} | {self.payment_method} | {self.status}'


class Order(models.Model):
    STATUS = (
        ('New', 'New'),
        ('Accepted', 'Accepted'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    order_number = models.CharField(max_length=20)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    email = models.EmailField(max_length=50)
    address_line_1 = models.CharField(max_length=50)
    address_line_2 = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    order_note = models.CharField(max_length=100, blank=True)
    order_total = models.FloatField()
    tax = models.FloatField()
    status = models.CharField(max_length=10, choices=STATUS, default='New')
    ip = models.CharField(blank=True, max_length=20)
    is_ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def full_address(self):
        return f'{self.address_line_1} {self.address_line_2}'

    def __str__(self):
        return self.first_name


class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variations = models.ManyToManyField(Variation, blank=True)
    quantity = models.IntegerField()
    product_price = models.FloatField()
    ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product.product_name
