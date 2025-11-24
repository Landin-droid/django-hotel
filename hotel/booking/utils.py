from datetime import timedelta
from django.utils import timezone
from .models import Price, Discount


def get_room_price(room_type, date_obj):
    """Получить цену номера на конкретную дату"""
    day_of_week = date_obj.isoweekday()

    try:
        # Пытаемся найти цену для конкретного типа номера и дня недели
        price_obj = Price.objects.get(
            room_type=room_type,
            day_of_week=day_of_week
        )
        return price_obj.price
    except Price.DoesNotExist:
        # Если цена не найдена, ищем любую цену для этого типа номера
        any_price = Price.objects.filter(room_type=room_type).first()
        if any_price:
            return any_price.price

        # Если вообще нет цен для этого типа номера, используем логику по категории
        base_prices = {
            'standard': 2000,
            'comfort': 3000,
            'lux': 5000
        }
        return base_prices.get(room_type.category, 2000)


def get_available_discount(nights):
    """Получить доступную скидку для количества ночей"""
    return Discount.objects.filter(
        min_nights__lte=nights,
        is_active=True
    ).order_by('-min_nights').first()


def is_room_available(room, check_in, check_out):
    """Проверить доступность номера на указанные даты"""
    from .models import Booking

    overlapping_bookings = Booking.objects.filter(
        room=room,
        status__in=['confirmed', 'checked_in'],
        check_in_date__lt=check_out,
        check_out_date__gt=check_in
    )
    return not overlapping_bookings.exists()


def get_booking_stats():
    """Получить статистику по бронированиям"""
    from .models import Booking

    today = timezone.now().date()
    stats = {
        'total':
            Booking.objects.count(),
        'pending':
            Booking.objects.filter(status='pending').count(),
        'confirmed':
            Booking.objects.filter(status='confirmed').count(),
        'checked_in':
            Booking.objects.filter(status='checked_in').count(),
        'today_checkins':
            Booking.objects.filter(check_in_date=today).count(),
        'today_checkouts':
            Booking.objects.filter(check_out_date=today).count(),
    }
    return stats


def calculate_room_price_preview(room_type, check_in_date, check_out_date, needs_child_bed=False):
    """Предварительный расчет стоимости без сохранения"""

    total = 0
    current_date = check_in_date
    child_bed_price = 500

    while current_date < check_out_date:
        total += get_room_price(room_type, current_date)
        if needs_child_bed:
            total += child_bed_price
        current_date += timedelta(days=1)

    nights = (check_out_date - check_in_date).days
    discount = get_available_discount(nights)

    if discount:
        total -= total * (discount.discount_percent / 100)

    return total
