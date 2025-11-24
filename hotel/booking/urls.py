from django.urls import path
from . import views

urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),

    # Комнаты
    path('rooms/', views.RoomListView.as_view(), name='room_list'),
    path('rooms/<int:pk>/', views.RoomDetailView.as_view(), name='room_detail'),
    path('rooms/availability/', views.room_availability,
         name='room_availability'),

    # Бронирования
    path('bookings/', views.BookingListView.as_view(), name='booking_list'),
    path('bookings/create/', views.BookingCreateView.as_view(),
         name='booking_create'),
    path('bookings/<int:pk>/', views.BookingDetailView.as_view(),
         name='booking_detail'),
    path('bookings/<int:pk>/update/',
         views.BookingUpdateView.as_view(), name='booking_update'),
    path('bookings/<int:pk>/cancel/',
         views.BookingCancelView.as_view(), name='booking_cancel'),
    path('bookings/<int:pk>/confirm/',
         views.confirm_booking, name='confirm_booking'),
    path('bookings/<int:pk>/check-in/',
         views.check_in_booking, name='check_in_booking'),
    path('bookings/<int:pk>/check-out/',
         views.check_out_booking, name='check_out_booking'),

    # Аутентификация - ДОБАВЛЯЕМ ЭТУ СТРОКУ
    path('accounts/logout/', views.custom_logout, name='logout'),
    
    # Регистрация и управление
    path('register/client/', views.client_register, name='client_register'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
]
