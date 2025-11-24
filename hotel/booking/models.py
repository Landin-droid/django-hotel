from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class RoomType(models.Model):
    CATEGORY_CHOICES = (
        ('standard', 'Стандарт'),
        ('comfort', 'Комфорт'),
        ('lux', 'Люкс'),
    )

    CAPACITY_CHOICES = (
        (1, '1-местный'),
        (2, '2-местный'),
        (3, '3-местный'),
    )

    category = models.CharField(
        max_length=10,
        choices=CATEGORY_CHOICES,
        verbose_name='Категория'
    )
    capacity = models.IntegerField(
        choices=CAPACITY_CHOICES,
        verbose_name='Вместимость'
    )
    has_child_bed = models.BooleanField(
        default=False,
        verbose_name='Возможность установки детской кровати'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )

    class Meta:
        verbose_name = 'Тип номера'
        verbose_name_plural = 'Типы номеров'
        unique_together = ['category', 'capacity', 'has_child_bed']

    def __str__(self):
        child_bed_info = " с детской кроватью" if self.has_child_bed else ""
        return f"{self.get_category_display()} {self.get_capacity_display()}{child_bed_info}"


class Room(models.Model):
    number = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Номер комнаты'
    )
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.PROTECT,
        related_name='rooms',
        verbose_name='Тип номера'
    )
    floor = models.IntegerField(
        verbose_name='Этаж'
    )
    is_available = models.BooleanField(
        default=True,
        verbose_name='Доступен для бронирования'
    )

    class Meta:
        verbose_name = 'Номер'
        verbose_name_plural = 'Номера'

    def __str__(self):
        status = "✅" if self.is_available else "❌"
        return f"Номер {self.number} ({self.room_type}) {status}"


class Price(models.Model):
    DAYS_OF_WEEK = (
        (1, 'Понедельник'),
        (2, 'Вторник'),
        (3, 'Среда'),
        (4, 'Четверг'),
        (5, 'Пятница'),
        (6, 'Суббота'),
        (7, 'Воскресенье'),
    )

    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        related_name='prices',
        verbose_name='Тип номера'
    )
    day_of_week = models.IntegerField(
        choices=DAYS_OF_WEEK,
        verbose_name='День недели'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена'
    )

    class Meta:
        verbose_name = 'Цена'
        verbose_name_plural = 'Цены'
        unique_together = ['room_type', 'day_of_week']

    def __str__(self):
        return f"{self.room_type} - {self.get_day_of_week_display()}: {self.price}₽"


class Discount(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name='Название скидки'
    )
    min_nights = models.IntegerField(
        verbose_name='Минимальное количество ночей'
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Процент скидки'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )

    class Meta:
        verbose_name = 'Скидка'
        verbose_name_plural = 'Скидки'

    def __str__(self):
        status = "✅" if self.is_active else "❌"
        return f"{self.name} ({self.discount_percent}%) {status}"


class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Ожидание'),
        ('confirmed', 'Подтверждено'),
        ('checked_in', 'Заселен'),
        ('checked_out', 'Выселен'),
        ('cancelled', 'Отменено'),
    )

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Клиент'
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='bookings',
        verbose_name='Номер'
    )
    check_in_date = models.DateField(verbose_name='Дата заезда')
    check_out_date = models.DateField(verbose_name='Дата выезда')
    actual_check_in = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Фактическое время заезда'
    )
    actual_check_out = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Фактическое время выезда'
    )
    needs_child_bed = models.BooleanField(
        default=False,
        verbose_name='Детская кровать'
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Общая стоимость'
    )
    discount_applied = models.ForeignKey(
        Discount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Примененная скидка'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-created_at']

    def __str__(self):
        return f"Бронирование #{self.id} - {self.client.username} ({self.get_status_display()})"

    @property
    def nights(self):
        """Количество ночей в бронировании"""
        return (self.check_out_date - self.check_in_date).days
