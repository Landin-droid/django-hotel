from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView
)

from django.contrib.auth import logout
from django.urls import reverse_lazy
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages
from datetime import timedelta

from .models import Room, Booking, Price, Discount
from .forms import BookingForm, ClientRegistrationForm, RoomSearchForm
from .utils import get_room_price, get_available_discount

# Вспомогательные функции


def custom_logout(request):
    """
    Простой кастомный выход из системы
    Работает с GET запросами и сразу перенаправляет
    """
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.success(
            request, f'Вы успешно вышли из системы. До свидания, {username}!')
    return redirect('home')


def is_admin(user):
    return user.user_type == 'admin'


def is_staff(user):
    return user.user_type in ['admin', 'staff']


def calculate_total_price(
        room_type, check_in_date, check_out_date, needs_child_bed=False
):
    """Расчет общей стоимости бронирования с использованием цен из базы"""
    total_price = 0
    current_date = check_in_date

    # Базовая стоимость детской кровати
    child_bed_price = 500  # руб/ночь

    # Перебираем все дни бронирования
    while current_date < check_out_date:
        # Используем функцию из utils для получения цены
        day_price = get_room_price(room_type, current_date)
        total_price += day_price

        if needs_child_bed:
            total_price += child_bed_price

        current_date += timedelta(days=1)

    # Применение скидок за длительное проживание
    nights = (check_out_date - check_in_date).days
    discount = get_available_discount(nights)  # Используем функцию из utils

    if discount:
        discount_amount = total_price * (discount.discount_percent / 100)
        total_price -= discount_amount
        return total_price, discount

    return total_price, None

# View-классы для комнат


class RoomListView(ListView):
    model = Room
    template_name = 'booking/room_list.html'
    context_object_name = 'rooms'

    def get_queryset(self):
        queryset = Room.objects.filter(is_available=True)

        # Фильтрация по параметрам поиска
        form = RoomSearchForm(self.request.GET)
        if form.is_valid():
            capacity = form.cleaned_data.get('capacity')
            category = form.cleaned_data.get('category')
            needs_child_bed = form.cleaned_data.get('needs_child_bed')

            if capacity:
                queryset = queryset.filter(room_type__capacity=capacity)
            if category:
                queryset = queryset.filter(room_type__category=category)
            if needs_child_bed:
                queryset = queryset.filter(room_type__has_child_bed=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = RoomSearchForm(self.request.GET)
        return context


class RoomDetailView(DetailView):
    model = Room
    template_name = 'booking/room_detail.html'
    context_object_name = 'room'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking_form'] = BookingForm(initial={'room': self.object})
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = BookingForm(request.POST)

        if form.is_valid():
            booking = form.save(commit=False)
            booking.client = request.user
            booking.room = self.object

            # Расчет стоимости
            total_price, discount = calculate_total_price(
                self.object.room_type,
                booking.check_in_date,
                booking.check_out_date,
                booking.needs_child_bed
            )

            # Проверяем, использовались ли цены из базы
            try:
                # Пытаемся получить хотя бы одну цену для этого типа номера
                has_prices = Price.objects.filter(
                    room_type=self.object.room_type).exists()
                if not has_prices:
                    messages.warning(
                        request,
                        'Внимание: для данного типа номера не установлены цены. '
                        'Использована базовая стоимость.'
                    )
            except Exception:
                pass

            booking.total_price = total_price
            booking.discount_applied = discount
            booking.status = 'pending'
            booking.save()

            messages.success(
                request, 'Бронирование создано успешно! Ожидайте подтверждения.')
            return redirect('booking_detail', pk=booking.pk)

        context = self.get_context_data()
        context['booking_form'] = form
        return self.render_to_response(context)

# View-классы для бронирований


class BookingCreateView(LoginRequiredMixin, CreateView):
    model = Booking
    form_class = BookingForm
    template_name = 'booking/booking_create.html'

    def form_valid(self, form):
        form.instance.client = self.request.user
        room = form.cleaned_data['room']
        check_in_date = form.cleaned_data['check_in_date']
        check_out_date = form.cleaned_data['check_out_date']
        needs_child_bed = form.cleaned_data['needs_child_bed']

        # Расчет стоимости
        total_price, discount = calculate_total_price(
            room.room_type, check_in_date, check_out_date, needs_child_bed
        )

        form.instance.total_price = total_price
        form.instance.discount_applied = discount
        form.instance.status = 'pending'

        messages.success(
            self.request,
            'Бронирование создано успешно! Ожидайте подтверждения.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('booking_detail', kwargs={'pk': self.object.pk})


class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'booking/booking_list.html'
    context_object_name = 'bookings'

    def get_queryset(self):
        if self.request.user.user_type in ['admin', 'staff']:
            return Booking.objects.all().order_by('-created_at')
        else:
            return Booking.objects.filter(
                client=self.request.user).order_by('-created_at')


class BookingDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Booking
    template_name = 'booking/booking_detail.html'
    context_object_name = 'booking'

    def test_func(self):
        booking = self.get_object()
        return (self.request.user == booking.client or
                self.request.user.user_type in ['admin', 'staff'])


class BookingUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Booking
    form_class = BookingForm
    template_name = 'booking/booking_update.html'

    def test_func(self):
        return self.request.user.user_type in ['admin', 'staff']

    def form_valid(self, form):
        messages.success(self.request, 'Бронирование обновлено успешно!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('booking_detail', kwargs={'pk': self.object.pk})


class BookingCancelView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Booking
    fields = []
    template_name = 'booking/booking_cancel.html'

    def test_func(self):
        booking = self.get_object()
        return (self.request.user == booking.client or
                self.request.user.user_type in ['admin', 'staff'])

    def form_valid(self, form):
        form.instance.status = 'cancelled'
        messages.success(self.request, 'Бронирование отменено успешно!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('booking_detail', kwargs={'pk': self.object.pk})

# Функции для административных действий


@login_required
@user_passes_test(is_staff)
def confirm_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    booking.status = 'confirmed'
    booking.save()
    messages.success(request, 'Бронирование подтверждено!')
    return redirect('booking_detail', pk=pk)


@login_required
@user_passes_test(is_staff)
def check_in_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.status == 'confirmed':
        booking.status = 'checked_in'
        booking.actual_check_in = timezone.now()
        booking.save()
        messages.success(request, 'Клиент заселен!')
    else:
        messages.error(
            request,
            'Невозможно заселить клиента. Бронирование не подтверждено.')
    return redirect('booking_detail', pk=pk)


@login_required
@user_passes_test(is_staff)
def check_out_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.status == 'checked_in':
        booking.status = 'checked_out'
        booking.actual_check_out = timezone.now()
        booking.save()
        messages.success(request, 'Клиент выселен!')
    else:
        messages.error(
            request, 'Невозможно выселить клиента. Клиент не заселен.')
    return redirect('booking_detail', pk=pk)

# Функции для поиска и проверки доступности


def room_availability(request):
    """Проверка доступности номеров на определенные даты"""
    if request.method == 'GET':
        check_in = request.GET.get('check_in')
        check_out = request.GET.get('check_out')
        capacity = request.GET.get('capacity')
        category = request.GET.get('category')

        if not (check_in and check_out):
            return JsonResponse(
                {'error': 'Необходимо указать даты заезда и выезда'}
            )

        try:
            check_in_date = timezone.datetime.strptime(
                check_in, '%Y-%m-%d').date()
            check_out_date = timezone.datetime.strptime(
                check_out, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Неверный формат даты'})

        # Поиск доступных номеров
        available_rooms = Room.objects.filter(is_available=True)

        if capacity:
            available_rooms = available_rooms.filter(
                room_type__capacity=capacity)
        if category:
            available_rooms = available_rooms.filter(
                room_type__category=category)

        # Исключаем номера с пересекающимися бронированиями
        booked_rooms = Booking.objects.filter(
            status__in=['confirmed', 'checked_in'],
            check_in_date__lt=check_out_date,
            check_out_date__gt=check_in_date
        ).values_list('room_id', flat=True)

        available_rooms = available_rooms.exclude(id__in=booked_rooms)

        # Расчет стоимости для каждого номера
        rooms_data = []
        for room in available_rooms:
            total_price, discount = calculate_total_price(
                room.room_type, check_in_date, check_out_date)

            # Проверяем, есть ли цены в базе для этого типа номера
            has_custom_prices = Price.objects.filter(
                room_type=room.room_type).exists()

            rooms_data.append({
                'id': room.id,
                'number': room.number,
                'type': str(room.room_type),
                'floor': room.floor,
                'total_price': float(total_price),
                'discount': discount.name if discount else None,
                'has_custom_prices': has_custom_prices  # Для отладки
            })

        return JsonResponse({'available_rooms': rooms_data})

    return JsonResponse({'error': 'Метод не разрешен'})

# Регистрация клиента


def client_register(request):
    if request.method == 'POST':
        form = ClientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                'Регистрация прошла успешно!'
                'Теперь вы можете войти в систему.')
            return redirect('login')
    else:
        form = ClientRegistrationForm()

    return render(request, 'registration/client_register.html', {'form': form})

# Главная страница


def home(request):
    search_form = RoomSearchForm()
    return render(request, 'booking/home.html', {'search_form': search_form})

# Панель управления для администратора


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    today = timezone.now().date()

    # Статистика
    total_bookings = Booking.objects.count()
    active_bookings = Booking.objects.filter(
        status__in=['confirmed', 'checked_in']).count()
    today_check_ins = Booking.objects.filter(
        check_in_date=today, status='confirmed').count()
    today_check_outs = Booking.objects.filter(
        check_out_date=today, status='checked_in').count()

    # Последние бронирования
    recent_bookings = Booking.objects.all().order_by('-created_at')[:10]

    context = {
        'total_bookings': total_bookings,
        'active_bookings': active_bookings,
        'today_check_ins': today_check_ins,
        'today_check_outs': today_check_outs,
        'recent_bookings': recent_bookings,
    }

    return render(request, 'booking/admin_dashboard.html', context)
