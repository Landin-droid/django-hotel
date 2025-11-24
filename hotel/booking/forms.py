from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Booking, RoomType
from users.models import User


class BookingForm(forms.ModelForm):
    check_in_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Дата заезда'
    )
    check_out_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Дата выезда'
    )

    class Meta:
        model = Booking
        fields = ['room', 'check_in_date', 'check_out_date', 'needs_child_bed']

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
                if overlapping_bookings.exists():
                    raise ValidationError(
                        'Номер уже забронирован на выбранные даты')

        return cleaned_data


class ClientRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Пароль')
    password_confirm = forms.CharField(
        widget=forms.PasswordInput, label='Подтверждение пароля')

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise ValidationError('Пароли не совпадают')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.user_type = 'client'
        if commit:
            user.save()
        return user


class RoomSearchForm(forms.Form):
    check_in = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Дата заезда'
    )
    check_out = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Дата выезда'
    )
    capacity = forms.ChoiceField(
        choices=[('', 'Любая')] + list(RoomType.CAPACITY_CHOICES),
        required=False,
        label='Вместимость'
    )
    category = forms.ChoiceField(
        choices=[('', 'Любая')] + list(RoomType.CATEGORY_CHOICES),
        required=False,
        label='Категория'
    )
    needs_child_bed = forms.BooleanField(
        required=False,
        label='Детская кровать'
    )
