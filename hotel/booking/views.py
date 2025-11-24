from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView
)
from django.http import JsonResponse
from django.contrib.auth import logout
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from datetime import datetime

from .models import Room, Booking
from .forms import BookingForm, ClientForm
from .utils import (
    calculate_room_price_preview, get_available_discount
)


@login_required
def calculate_price(request):
    """AJAX endpoint для расчета стоимости бронирования"""
    if request.method == 'GET':
        room_id = request.GET.get('room_id')
        check_in = request.GET.get('check_in')
        check_out = request.GET.get('check_out')
        needs_child_bed = request.GET.get('needs_child_bed') == 'true'

        if not all([room_id, check_in, check_out]):
            return JsonResponse(
                {'error': 'Не все параметры указаны'},
                status=400
            )

        try:
            room = Room.objects.get(id=room_id)
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()

            # Валидация дат
            if check_out_date <= check_in_date:
                return JsonResponse(
                    {'error': 'Дата выезда должна быть после даты заезда'},
                    status=400)

            if check_in_date < timezone.now().date():
                return JsonResponse(
                    {'error': 'Дата заезда не может быть в прошлом'},
                    status=400
                )

            # Расчет стоимости
            price_data = calculate_room_price_preview(
                room.room_type,
                check_in_date,
                check_out_date,
                needs_child_bed
            )

            data = {
                'success': True,
                'total_price': float(price_data['total_price']),
                'nights': price_data['nights'],
                'discount_applied': price_data['has_discount'],
                'discount_info': (
                    f"{price_data['discount_name']} "
                    "(-{price_data['discount_percent']}%)"
                    if price_data['has_discount'] else None
                ),
                'discount_amount': float(price_data['discount_amount']),
                'price_per_night': (
                    float(price_data['total_price']) / price_data['nights']
                    if price_data['nights'] > 0 else 0
                ),
                'child_bed_price': float(price_data['child_bed_price']),
            }

            return JsonResponse(data)

        except Room.DoesNotExist:
            return JsonResponse({'error': 'Номер не найден'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'Неверный формат даты'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Ошибка расчета: {str(e)}'},
                                status=500)

    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


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
    return redirect('login')


@login_required
def admin_dashboard(request):
    """Главная панель управления"""
    today = timezone.now().date()

    # Статистика
    stats = {
        'total_bookings':
            Booking.objects.count(),
        'active_bookings':
            Booking.objects.filter(
                status__in=['confirmed', 'checked_in']).count(),
        'today_check_ins':
            Booking.objects.filter(
                check_in_date=today, status='confirmed').count(),
        'today_check_outs':
            Booking.objects.filter(
                check_out_date=today, status='checked_in').count(),
        'available_rooms':
            Room.objects.filter(
                is_available=True).count(),
    }

    # Ближайшие заезды
    upcoming_checkins = Booking.objects.filter(
        check_in_date__gte=today,
        status='confirmed'
    ).order_by('check_in_date')[:10]

    # Текущие гости
    current_guests = Booking.objects.filter(
        status='checked_in').order_by('check_in_date')

    # Последние бронирования
    recent_bookings = Booking.objects.all().order_by('-created_at')[:10]

    context = {
        'stats': stats,
        'upcoming_checkins': upcoming_checkins,
        'current_guests': current_guests,
        'recent_bookings': recent_bookings,
    }

    return render(request, 'booking/admin_dashboard.html', context)


def calculate_total_price(
        room_type, check_in_date, check_out_date, needs_child_bed=False):
    """Расчет общей стоимости бронирования с использованием цен из базы"""
    price_data = calculate_room_price_preview(
        room_type,
        check_in_date,
        check_out_date,
        needs_child_bed
    )
    discount = get_available_discount(price_data['nights'])

    return price_data['total_price'], discount


class BookingCreateView(LoginRequiredMixin, CreateView):
    """Создание нового бронирования"""
    model = Booking
    form_class = BookingForm
    template_name = 'booking/booking_create.html'
    success_url = reverse_lazy('booking_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client_form'] = ClientForm()
        context['booking_form'] = BookingForm()
        return context

    def post(self, request, *args, **kwargs):
        client_form = ClientForm(request.POST)
        booking_form = BookingForm(request.POST)

        if client_form.is_valid() and booking_form.is_valid():
            # Сохраняем клиента
            client = client_form.save()

            # Создаем бронирование
            booking = booking_form.save(commit=False)
            booking.client = client
            booking.created_by = request.user

            # Расчет стоимости
            price_data = calculate_room_price_preview(
                booking.room.room_type,
                booking.check_in_date,
                booking.check_out_date,
                booking.needs_child_bed
            )
            # Берем total_price из словаря
            booking.total_price = price_data['total_price']

            # Применяем скидку если есть
            if price_data['has_discount']:
                booking.discount_applied = get_available_discount(
                    price_data['nights'])

            booking.save()

            messages.success(request, 'Бронирование успешно создано!')
            return redirect('booking_list')

        # Если формы невалидны
        context = self.get_context_data()
        context['client_form'] = client_form
        context['booking_form'] = booking_form
        return self.render_to_response(context)


class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'booking/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 20

    def get_queryset(self):
        return Booking.objects.all().select_related(
            'client', 'room', 'created_by'
        )


class BookingDetailView(LoginRequiredMixin, DetailView):
    """Детали бронирования"""
    model = Booking
    template_name = 'booking/booking_detail.html'
    context_object_name = 'booking'


class BookingUpdateView(LoginRequiredMixin, UpdateView):
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


@login_required
def check_out_booking(request, pk):
    """Выселение гостя"""
    booking = get_object_or_404(Booking, pk=pk)
    if booking.status == 'checked_in':
        booking.status = 'checked_out'
        booking.actual_check_out = timezone.now()
        booking.save()
        messages.success(request, 'Гость выселен!')
    else:
        messages.error(
            request, 'Невозможно выселить гостя.')
    return redirect('booking_detail', pk=pk)


@login_required
def confirm_booking(request, pk):
    """Подтверждение бронирования"""
    booking = get_object_or_404(Booking, pk=pk)
    booking.status = 'confirmed'
    booking.save()
    messages.success(request, 'Бронирование подтверждено!')
    return redirect('booking_detail', pk=pk)


@login_required
def check_in_booking(request, pk):
    """Заселение гостя"""
    booking = get_object_or_404(Booking, pk=pk)
    if booking.status == 'confirmed':
        booking.status = 'checked_in'
        booking.actual_check_in = timezone.now()
        booking.save()
        messages.success(request, 'Гость заселен!')
    else:
        messages.error(request, 'Невозможно заселить гостя')
    return redirect('booking_detail', pk=pk)


@login_required
def cancel_booking(request, pk):
    """Отмена бронирования"""
    booking = get_object_or_404(Booking, pk=pk)
    booking.status = 'cancelled'
    booking.save()
    messages.success(request, 'Бронирование отменено!')
    return redirect('booking_detail', pk=pk)
