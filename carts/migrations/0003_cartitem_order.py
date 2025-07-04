# Generated by Django 5.2.1 on 2025-07-03 10:39

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('carts', '0002_cartitem_price'),
        ('orders', '0002_payment_delivery_status_alter_payment_amount_paid_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='orders.order'),
        ),
    ]
