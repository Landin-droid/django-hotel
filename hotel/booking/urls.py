from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),

    path('bookings/', views.BookingListView.as_view(), name='booking_list'),
    path('bookings/create/', views.BookingCreateView.as_view(),
         name='booking_create'),
    path('bookings/<int:pk>/', views.BookingDetailView.as_view(),
         name='booking_detail'),

    path('bookings/<int:pk>/cancel/',
         views.cancel_booking, name='booking_cancel'),
    path('bookings/<int:pk>/confirm/',
         views.confirm_booking, name='confirm_booking'),
    path('bookings/<int:pk>/check-in/',
         views.check_in_booking, name='check_in_booking'),
    path('bookings/<int:pk>/check-out/',
         views.check_out_booking, name='check_out_booking'),

    path('accounts/logout/', views.custom_logout, name='logout'),
    path('calculate-price/', views.calculate_price, name='calculate_price'),

]
