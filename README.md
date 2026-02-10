# 🛒 MegaCart - E-Commerce Platform (Django)

**MegaCart** is a full-featured, scalable e-commerce platform built using Django. It supports multi-role user management (admin, seller, customer), a dynamic product catalog, secure checkout, and a powerful admin dashboard.

---

## 🚀 Features

- 🧑‍💼 Multi-role support (Admin, Seller, Customer)
- 🛍️ Product Management with image uploads
- 🛒 Cart and Checkout system
- 💳 Payment Gateway integration (dummy/PayPal-ready)
- 📦 Order tracking and order history
- 🧾 Invoice & Email Notifications
- 🧑‍🔒 Secure Authentication with Email Verification
- 📂 Modular Codebase (accounts, carts, category, orders, store)
- 🔐 Password Reset, Account Activation
- 📊 Admin Dashboard with insights

---

## 🌍 Live Demo

> 🔗 **Live Demo**: [Click Here](https://megacart-5sqk.onrender.com)

---

## 📁 Project Structure

```
MegaCart/
├── accounts/        # User management and authentication
├── carts/           # Shopping cart logic
├── category/        # Product categorization
├── megacart/        # Main Django project settings (previously 'greatcart')
├── media/           # Uploaded files and product images
├── orders/          # Order placement and payment logic
├── store/           # Product listing, search, filters
├── templates/       # HTML templates (with modular includes)
├── static/          # CSS, JS, images, fonts
├── db.sqlite3       # SQLite3 database
└── manage.py        # Django management script
```

---

## ⚙️ Installation Guide

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Dhananjay66/megacart.git
   cd megacart
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

7. **Visit**
   ```
   http://127.0.0.1:8000/
   ```

---

## 🔐 Default Roles

| Role       | Description                     |
|------------|---------------------------------|
| Admin      | Has access to Django admin site |
| Seller     | Can add/manage products         |
| Customer   | Can place orders and view cart  |

---


## 🧪 Testing

Use Django's test framework:
```bash
python manage.py test
```

---

## 🤝 Contributing

We love contributions from the community!

- 🐞 Found a bug? [Open an issue](https://github.com/Dhananjay66/megacart/issues).
- 🚀 Want to add a new feature? Fork the repo and submit a PR.
- 📄 Make sure to update documentation if needed.
- ✅ Please test your code before submitting.

Thank you for making this project better! 💖

---

## 📧 Contact

For any query or collaboration:  
pratapdhananjay738@gmail.com