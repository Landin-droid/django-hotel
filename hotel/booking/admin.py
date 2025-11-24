from django.contrib import admin
from .models import RoomType, Room, Price, Discount, Booking


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('category', 'capacity', 'has_child_bed')
    list_filter = ('category', 'capacity')


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('number', 'room_type', 'floor', 'is_available')
    list_filter = ('room_type', 'floor', 'is_available')
    search_fields = ('number',)


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ('room_type', 'day_of_week', 'price')
    list_filter = ('room_type', 'day_of_week')


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_nights', 'discount_percent', 'is_active')
    list_filter = ('is_active',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'room', 'check_in_date',
                    'check_out_date', 'status', 'total_price')
    list_filter = ('status', 'needs_child_bed')
    search_fields = ('client__username', 'room__number')
    readonly_fields = ('created_at', 'updated_at')
