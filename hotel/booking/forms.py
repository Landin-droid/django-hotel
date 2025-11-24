from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Booking, Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['first_name', 'last_name', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class BookingForm(forms.ModelForm):
    check_in_date = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}),
        label='Дата заезда'
    )
    check_out_date = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}),
        label='Дата выезда'
    )

    class Meta:
        model = Booking
        fields = ['room', 'check_in_date',
                  'check_out_date', 'needs_child_bed', 'notes']
        widgets = {
            'room':
                forms.Select(attrs={'class': 'form-select'}),
            'needs_child_bed':
                forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes':
                forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        check_in_date = cleaned_data.get('check_in_date')
        check_out_date = cleaned_data.get('check_out_date')
        room = cleaned_data.get('room')

        if check_in_date and check_out_date:
            if check_in_date < timezone.now().date():
                raise ValidationError('Дата заезда не может быть в прошлом')

            if check_out_date <= check_in_date:
                raise ValidationError(
                    'Дата выезда должна быть после даты заезда')

            # Проверка доступности номера
            if room and check_in_date and check_out_date:
                overlapping_bookings = Booking.objects.filter(
                    room=room,
                    status__in=['confirmed', 'checked_in'],
                    check_in_date__lt=check_out_date,
                    check_out_date__gt=check_in_date
                )
                if self.instance.pk:
                    overlapping_bookings = overlapping_bookings.exclude(
                        pk=self.instance.pk)

                if overlapping_bookings.exists():
                    raise ValidationError(
                        'Номер уже забронирован на выбранные даты')

        return cleaned_data
