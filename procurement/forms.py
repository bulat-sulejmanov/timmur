# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Material, PurchaseRequest, Tender, TenderItem, Task, Supplier, Contract


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['last_name', 'first_name', 'middle_name', 'email', 'phone', 'birth_date', 'photo', 'position']
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PurchaseRequestForm(forms.ModelForm):
    # Виртуальное поле для отображения единицы измерения (только для чтения)
    unit_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'placeholder': 'Выберите номенклатуру'
        }),
        label='Единица измерения'
    )
    
    class Meta:
        model = PurchaseRequest
        fields = ['nomenclature', 'quantity', 'max_price', 'unit', 'plan_type', 'status', 'budget_article', 'description', 'attachment']
        widgets = {
            'nomenclature': forms.Select(attrs={'class': 'form-control', 'id': 'id_nomenclature'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit': forms.HiddenInput(),  # Скрытое поле, заполняется через JS
            'plan_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.HiddenInput(),  # Статус управляется логикой, а не пользователем
            'budget_article': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Делаем поле unit необязательным (заполняется через JS)
        self.fields['unit'].required = False
        
        # Если форма создана для редактирования существующего объекта
        if self.instance and self.instance.pk:
            if self.instance.nomenclature:
                self.fields['unit_display'].initial = self.instance.nomenclature.get_unit_display()
                # Устанавливаем начальное значение скрытого поля unit
                self.fields['unit'].initial = self.instance.nomenclature.unit
        else:
            # Для новой заявки задаем начальный статус 'draft'
            self.initial['status'] = 'draft'
    
    def clean(self):
        cleaned_data = super().clean()
        nomenclature = cleaned_data.get('nomenclature')
        unit = cleaned_data.get('unit')
        
        # Если номенклатура выбрана, но unit не заполнен - берем из номенклатуры
        if nomenclature and not unit:
            cleaned_data['unit'] = nomenclature.unit
            self.instance.unit = nomenclature.unit
        
        return cleaned_data
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError('Количество должно быть больше нуля')
        return quantity


class TenderForm(forms.ModelForm):
    class Meta:
        model = Tender
        # УДАЛЕНО: publication_type - конкурсы всегда открытые
        fields = ['name', 'contact_person', 'place_of_delivery', 
                  'min_step', 'is_trading', 'start_date', 'submission_deadline', 
                  'delivery_term', 'procurement_docs', 'price_request_doc', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.Select(attrs={'class': 'form-control'}),
            'place_of_delivery': forms.TextInput(attrs={'class': 'form-control'}),
            'min_step': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_trading': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'submission_deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'delivery_term': forms.TextInput(attrs={'class': 'form-control'}),
            'procurement_docs': forms.FileInput(attrs={'class': 'form-control'}),
            'price_request_doc': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class TenderItemForm(forms.ModelForm):
    class Meta:
        model = TenderItem
        fields = ['purchase_request', 'quantity', 'start_price', 'attachment']
        widgets = {
            'purchase_request': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'start_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }


# Formset для позиций конкурса
TenderItemFormSet = forms.inlineformset_factory(
    Tender, TenderItem, form=TenderItemForm,
    extra=1, can_delete=True, min_num=1, validate_min=True
)


class ApprovalForm(forms.Form):
    """Форма для согласования заявки"""
    comment = forms.CharField(
        label='Комментарий',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )


class SupplierForm(forms.ModelForm):
    """Форма для поставщика"""
    class Meta:
        model = Supplier
        fields = [
            'name', 'supplier_type', 'inn', 'kpp', 'ogrn',
            'legal_address', 'actual_address', 'phone', 'email', 'website',
            'bank_name', 'bank_bik', 'bank_account', 'corr_account',
            'contact_person', 'contact_phone', 'contact_email',
            'description', 'specialization', 'status',
            'registration_doc', 'license_doc'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название организации или ФИО'}),
            'supplier_type': forms.Select(attrs={'class': 'form-control'}),
            'inn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ИНН'}),
            'kpp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'КПП (для юр. лиц)'}),
            'ogrn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ОГРН или ОГРНИП'}),
            
            'legal_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Юридический адрес'}),
            'actual_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Фактический адрес'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Телефон'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Наименование банка'}),
            'bank_bik': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'БИК'}),
            'bank_account': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Расчетный счет'}),
            'corr_account': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Корр. счет'}),
            
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО контактного лица'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Телефон контактного лица'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email контактного лица'}),
            
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание поставщика'}),
            'specialization': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Специализация, категории товаров'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            
            'registration_doc': forms.FileInput(attrs={'class': 'form-control'}),
            'license_doc': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем поля необязательными, кроме названия и типа
        for field in self.fields:
            if field not in ['name', 'supplier_type']:
                self.fields[field].required = False
    
    def clean_inn(self):
        inn = self.cleaned_data.get('inn')
        if inn:
            # Проверка длины ИНН (10 для юр. лиц, 12 для ИП и физ. лиц)
            if len(inn) not in [10, 12]:
                raise forms.ValidationError('ИНН должен содержать 10 или 12 цифр')
            if not inn.isdigit():
                raise forms.ValidationError('ИНН должен содержать только цифры')
        return inn
    
    def clean_kpp(self):
        kpp = self.cleaned_data.get('kpp')
        supplier_type = self.cleaned_data.get('supplier_type')
        
        # КПП обязателен только для юридических лиц
        if supplier_type == 'company' and kpp:
            if len(kpp) != 9:
                raise forms.ValidationError('КПП должен содержать 9 цифр')
            if not kpp.isdigit():
                raise forms.ValidationError('КПП должен содержать только цифры')
        return kpp


# ==================== ФОРМЫ ДЛЯ ДОГОВОРОВ ====================

class ContractForm(forms.ModelForm):
    """Форма для создания/редактирования договора"""
    class Meta:
        model = Contract
        fields = ['name', 'contract_amount', 'contract_date', 'end_date', 'responsible', 
                  'status', 'comment', 'contract_document', 'supplier', 'commercial_proposal']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название договора'}),
            'contract_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'contract_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'responsible': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Комментарий к договору'}),
            'contract_document': forms.FileInput(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'commercial_proposal': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Фильтруем активных поставщиков
        self.fields['supplier'].queryset = Supplier.objects.filter(status__in=['active', 'new'])
        self.fields['responsible'].queryset = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
        
        # Статус только для чтения при редактировании (управляется через workflow)
        if self.instance and self.instance.pk:
            self.fields['status'].widget = forms.Select(attrs={'class': 'form-control', 'readonly': 'readonly'})
    
    def clean(self):
        cleaned_data = super().clean()
        contract_date = cleaned_data.get('contract_date')
        end_date = cleaned_data.get('end_date')
        
        if contract_date and end_date:
            if end_date < contract_date:
                raise forms.ValidationError('Дата окончания не может быть раньше даты договора')
        
        return cleaned_data
    
    def clean_contract_amount(self):
        amount = self.cleaned_data.get('contract_amount')
        if amount is not None and amount < 0:
            raise forms.ValidationError('Сумма договора не может быть отрицательной')
        return amount


class ContractApprovalForm(forms.Form):
    """Форма для согласования договора"""
    comment = forms.CharField(
        label='Комментарий',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )


# ==================== ФОРМА СОЗДАНИЯ ПОЛЬЗОВАТЕЛЯ ====================

class SupplyEmployeeCreationForm(forms.ModelForm):
    """Форма для создания сотрудника отдела снабжения менеджером"""
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    password_confirm = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    
    class Meta:
        model = User
        fields = ['username', 'last_name', 'first_name', 'middle_name', 'email', 'phone', 'position', 'birth_date']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Специалист отдела снабжения'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Пароли не совпадают')
        
        return password_confirm
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует')
        return username
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_supply_employee = True
        user.is_active = True
        
        if commit:
            user.save()
        
        return user