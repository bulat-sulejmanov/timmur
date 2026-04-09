# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, Material, PurchaseRequest, PlanApprover, PlanApprovalHistory, Tender, TenderItem, Task, TenderWinner, Supplier, Contract
from .forms import UserCreationForm, UserChangeForm


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    
    list_display = ['username', 'get_full_name', 'position', 'is_manager', 'is_supply_employee', 'email', 'phone']
    list_filter = ['is_manager', 'is_supply_employee', 'is_staff', 'is_active']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {
            'fields': ('last_name', 'first_name', 'middle_name', 'email', 'phone', 'birth_date', 'photo', 'position')
        }),
        ('Права доступа', {
            'fields': ('is_manager', 'is_supply_employee', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'is_manager', 'is_supply_employee'),
        }),
    )
    
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering = ['last_name', 'first_name']


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    """Справочник номенклатуры (без складского учёта)"""
    list_display = ['name', 'unit', 'description']
    list_filter = ['unit']
    search_fields = ['name', 'description']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Единица измерения', {
            'fields': ('unit',)
        }),
    )


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'requester', 'nomenclature_short', 'quantity', 'unit', 'plan_type', 
                    'status', 'status_colored', 'budget_article', 'max_price', 'approver_info', 'created_at']
    list_filter = ['status', 'plan_type', 'budget_article', 'created_at']
    search_fields = ['nomenclature__name', 'requester__last_name', 'requester__first_name', 'approver__last_name']
    list_editable = ['status']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('requester', 'nomenclature', 'description', 'approver')
        }),
        ('Количество и цена', {
            'fields': ('quantity', 'unit', 'max_price', 'price')
        }),
        ('Планирование и бюджет', {
            'fields': ('plan_type', 'budget_article')
        }),
        ('Статус и решение', {
            'fields': ('status', 'rejection_reason')
        }),
        ('Файлы', {
            'fields': ('attachment',)
        }),
    )
    
    def nomenclature_short(self, obj):
        """Исправлено: преобразуем объект в строку"""
        name = str(obj.nomenclature)
        return name[:50] + '...' if len(name) > 50 else name
    nomenclature_short.short_description = 'Номенклатура'
    
    def approver_info(self, obj):
        if obj.approver:
            return obj.approver.get_full_name()
        return '-'
    approver_info.short_description = 'Согласующий'
    
    def status_colored(self, obj):
        """Цветной статус"""
        colors = {
            'draft': '#6c757d',
            'planned': '#0d6efd',
            'pending': '#fd7e14',
            'approved': '#198754',
            'rejected': '#dc3545',
            'in_progress': '#0dcaf0',
            'completed': '#20c997',
            'cancelled': '#adb5bd',
        }
        status_labels = dict(obj.STATUS_CHOICES)
        color = colors.get(obj.status, '#000000')
        label = status_labels.get(obj.status, obj.status)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            label
        )
    status_colored.short_description = 'Статус (цвет)'


@admin.register(PlanApprover)
class PlanApproverAdmin(admin.ModelAdmin):
    list_display = ['plan_type', 'user', 'position']
    list_filter = ['plan_type']
    search_fields = ['user__last_name', 'user__first_name', 'position']


@admin.register(PlanApprovalHistory)
class PlanApprovalHistoryAdmin(admin.ModelAdmin):
    list_display = ['plan_type', 'approver', 'decision', 'status', 'start_date', 'end_date']
    list_filter = ['plan_type', 'status', 'decision']
    search_fields = ['plan_type', 'approver__last_name', 'approver__first_name']
    date_hierarchy = 'start_date'


class TenderItemInline(admin.TabularInline):
    model = TenderItem
    extra = 1


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'start_date', 'submission_deadline', 'contact_person', 'display_total_price', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description']
    date_hierarchy = 'created_at'
    inlines = [TenderItemInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'status')
        }),
        ('Контактная информация и место', {
            'fields': ('contact_person', 'place_of_delivery')
        }),
        ('Условия торгов', {
            'fields': ('is_trading', 'min_step')
        }),
        ('Сроки', {
            'fields': ('start_date', 'submission_deadline', 'delivery_term')
        }),
        ('Документы', {
            'fields': ('procurement_docs', 'price_request_doc')
        }),
    )
    
    def display_total_price(self, obj):
        """Отображает общую цену с форматированием"""
        price = obj.total_price
        if price:
            return f"{price:,.2f} ₽"
        return "-"
    display_total_price.short_description = 'Общая цена'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'executor', 'state', 'task_type', 'created_at', 'start_date', 'end_date']
    list_filter = ['state', 'task_type', 'created_at']
    search_fields = ['title', 'description', 'executor__last_name', 'executor__first_name']
    date_hierarchy = 'created_at'
    list_editable = ['state']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'state', 'task_type')
        }),
        ('Сроки', {
            'fields': ('start_date', 'end_date')
        }),
        ('Участники', {
            'fields': ('executor', 'created_by')
        }),
        ('Связи', {
            'fields': ('related_request', 'related_contract')
        }),
    )


@admin.register(TenderWinner)
class TenderWinnerAdmin(admin.ModelAdmin):
    list_display = ['tender', 'user', 'total_amount_display', 'selected_by', 'selected_at']
    list_filter = ['selected_at']
    search_fields = ['tender__name', 'user__last_name', 'user__first_name']
    date_hierarchy = 'selected_at'
    
    fieldsets = (
        ('Конкурс', {
            'fields': ('tender',)
        }),
        ('Победитель', {
            'fields': ('proposal', 'user')
        }),
        ('Дополнительно', {
            'fields': ('selected_by', 'notes')
        }),
    )
    
    readonly_fields = ['selected_at']
    
    def total_amount_display(self, obj):
        """Отображает общую сумму с форматированием"""
        amount = obj.total_amount
        if amount:
            return f"{amount:,.2f} ₽"
        return "-"
    total_amount_display.short_description = 'Общая сумма'


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'supplier_type', 'inn', 'phone', 'email', 'status_colored', 'created_at', 'status']
    list_filter = ['status', 'supplier_type', 'created_at']
    search_fields = ['name', 'inn', 'contact_person', 'email']
    date_hierarchy = 'created_at'
    list_editable = ['status']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'supplier_type', 'inn', 'kpp', 'ogrn', 'status')
        }),
        ('Адреса и контакты', {
            'fields': ('legal_address', 'actual_address', 'phone', 'email', 'website')
        }),
        ('Банковские реквизиты', {
            'fields': ('bank_name', 'bank_bik', 'bank_account', 'corr_account')
        }),
        ('Контактное лицо', {
            'fields': ('contact_person', 'contact_phone', 'contact_email')
        }),
        ('Дополнительно', {
            'fields': ('description', 'specialization')
        }),
        ('Документы', {
            'fields': ('registration_doc', 'license_doc')
        }),
    )
    
    def status_colored(self, obj):
        colors = {
            'active': '#198754',
            'new': '#ffc107',
            'inactive': '#6c757d',
            'blocked': '#dc3545',
        }
        status_labels = dict(obj.STATUS_CHOICES)
        color = colors.get(obj.status, '#000000')
        label = status_labels.get(obj.status, obj.status)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            label
        )
    status_colored.short_description = 'Статус'


# ==================== АДМИНКА ДОГОВОРОВ ====================

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['name', 'supplier', 'contract_amount_display', 'contract_date', 'end_date', 
                    'responsible', 'status_colored', 'status', 'created_at']
    list_filter = ['status', 'contract_date', 'created_at', 'supplier']
    search_fields = ['name', 'supplier__name', 'responsible__last_name', 'responsible__first_name']
    date_hierarchy = 'created_at'
    list_editable = ['status']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'contract_amount', 'contract_date', 'end_date')
        }),
        ('Участники', {
            'fields': ('responsible', 'approver', 'created_by')
        }),
        ('Связи', {
            'fields': ('supplier',)
        }),
        ('Документы', {
            'fields': ('commercial_proposal', 'contract_document')
        }),
        ('Статус и комментарий', {
            'fields': ('status', 'comment')
        }),
    )
    
    def contract_amount_display(self, obj):
        """Отображает сумму договора с форматированием"""
        return f"{obj.contract_amount:,.2f} ₽"
    contract_amount_display.short_description = 'Сумма'
    
    def status_colored(self, obj):
        """Цветной статус"""
        colors = {
            'draft': '#6c757d',
            'pending': '#fd7e14',
            'approved': '#0d6efd',
            'rejected': '#dc3545',
            'active': '#198754',
            'completed': '#20c997',
            'terminated': '#212529',
            'cancelled': '#adb5bd',
        }
        status_labels = dict(obj.STATUS_CHOICES)
        color = colors.get(obj.status, '#000000')
        label = status_labels.get(obj.status, obj.status)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            label
        )
    status_colored.short_description = 'Статус (цвет)'