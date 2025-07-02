from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CategoryViewSet, RegisterAPIView, LoginView, LogoutAPIView


from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')
router.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('', include(router.urls)),
    # path('products/', ProductListView.as_view(), name='product-list'),
    # path('products/<int:id>/', ProductDetailView.as_view(), name='product-detail'),
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    # path('categories/', CategoryListView.as_view(), name='category-list'),


    
    # JWT login and refresh
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),     # login
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),    # refresh token
    path('logout/', LogoutAPIView.as_view(), name='logout'),
]