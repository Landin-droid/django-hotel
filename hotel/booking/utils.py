from datetime import timedelta
from .models import Price, Discount


def get_room_price(room_type, date_obj):
    """Получить цену номера на конкретную дату"""
    day_of_week = date_obj.isoweekday()

    try:
        price_obj = Price.objects.get(
            room_type=room_type,
            day_of_week=day_of_week
        )
        return price_obj.price
    except Price.DoesNotExist:
        any_price = Price.objects.filter(room_type=room_type).first()
        if any_price:
            return any_price.price

        base_prices = {
            'standard': 2000,
            'comfort': 2500,
            'lux': 3000
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


def calculate_room_price_preview(
        room_type, check_in_date, check_out_date, needs_child_bed=False):
    """Предварительный расчет стоимости без сохранения"""
    total = 0
    base_total = 0
    current_date = check_in_date
    child_bed_price = 500

    daily_prices = []
    while current_date < check_out_date:
        day_price = get_room_price(room_type, current_date)
        base_total += day_price
        daily_prices.append({
            'date': current_date,
            'price': day_price
        })
        current_date += timedelta(days=1)

    total = base_total

    child_bed_total = 0
    if needs_child_bed:
        child_bed_total = len(daily_prices) * child_bed_price
        total += child_bed_total

    nights = (check_out_date - check_in_date).days
    discount = get_available_discount(nights)
    discount_amount = 0
    discount_percent = 0

    if discount:
        discount_percent = discount.discount_percent
        discount_amount = total * (discount_percent / 100)
        total -= discount_amount

    return {
        'total_price': total,
        'base_price': base_total,
        'child_bed_price': child_bed_total,
        'nights': nights,
        'discount_amount': discount_amount,
        'discount_percent': discount_percent,
        'has_discount': discount is not None,
        'discount_name': discount.name if discount else None
    }
