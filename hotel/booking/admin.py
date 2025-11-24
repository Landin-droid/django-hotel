from django.utils.html import format_html
from django.contrib import admin
from .models import RoomType, Room, Price, Discount, Booking


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('category', 'capacity')
    list_filter = ('category', 'capacity')
    search_fields = ('category', 'description')


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('number', 'room_type', 'floor', 'is_available')
    list_filter = ('room_type', 'floor', 'is_available')
    search_fields = ('number',)
    list_editable = ('is_available',)


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ('room_type', 'day_of_week', 'price')
    list_filter = ('room_type', 'day_of_week')
    search_fields = ('room_type__category',)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_nights', 'discount_percent', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('is_active',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'client',
        'room_display',
        'check_in_date',
        'check_out_date',
        'nights_display',
        'needs_child_bed_display',
        'status_display',
        'total_price_display',
        'created_at'
    )
    list_filter = ('status', 'needs_child_bed',
                   'check_in_date', 'check_out_date')
    search_fields = ('client__first_name',
                     'client__last_name', 'room__number', 'id')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

    def room_display(self, obj):
        return f"{obj.room.number} ({obj.room.room_type})"
    room_display.short_description = 'Номер'

    def nights_display(self, obj):
        return f"{obj.nights} ночей"
    nights_display.short_description = 'Ночей'

    def needs_child_bed_display(self, obj):
        return "✅" if obj.needs_child_bed else "❌"
    needs_child_bed_display.short_description = 'Детская кровать'

    def status_display(self, obj):
        status_colors = {
            'pending': 'orange',
            'confirmed': 'blue',
            'checked_in': 'green',
            'checked_out': 'gray',
            'cancelled': 'red'
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Статус'

    def total_price_display(self, obj):
        return f"{obj.total_price}₽"
    total_price_display.short_description = 'Стоимость'
