# Generated by Django 5.2.1 on 2025-07-01 06:52

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='delivery_status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Shipped', 'Shipped'), ('Out for Delivery', 'Out for Delivery'), ('Delivered', 'Delivered'), ('Returned', 'Returned')], default='Pending', max_length=20),
        ),
        migrations.AlterField(
            model_name='payment',
            name='amount_paid',
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='payment',
            name='payment_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(choices=[('COD', 'Cash On Delivery'), ('UPI', 'UPI'), ('Card', 'Credit/Debit Card')], max_length=50),
        ),
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Paid', 'Paid'), ('Failed', 'Failed'), ('Cancelled', 'Cancelled')], default='Pending', max_length=20),
        ),
    ]
