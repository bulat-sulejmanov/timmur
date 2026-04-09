# models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from datetime import datetime


class User(AbstractUser):
    middle_name = models.CharField('Отчество', max_length=100, blank=True)
    phone = models.CharField('Номер телефона', max_length=20, blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    photo = models.ImageField('Фото', upload_to='profile_photos/', blank=True, null=True)
    position = models.CharField('Должность', max_length=200, blank=True)
    is_manager = models.BooleanField('Руководитель', default=False)
    is_supply_employee = models.BooleanField('Сотрудник снабжения', default=False)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def get_full_name(self):
        full_name = f"{self.last_name} {self.first_name}"
        if self.middle_name:
            full_name += f" {self.middle_name}"
        return full_name.strip()

    def __str__(self):
        return self.get_full_name()


class Material(models.Model):
    """Справочник номенклатуры (без складского учёта)"""
    UNIT_CHOICES = [
        ('шт', 'штук'),
        ('т', 'тонн'),
        ('кг', 'килограммов'),
        ('м', 'метров'),
        ('м³', 'кубических метров'),
        ('л', 'литров'),
    ]

    name = models.CharField('Наименование материала', max_length=200)
    unit = models.CharField('Единица измерения', max_length=10, choices=UNIT_CHOICES)
    description = models.TextField('Описание', blank=True)

    class Meta:
        verbose_name = 'Номенклатура'
        verbose_name_plural = 'Номенклатура'
        ordering = ['name']

    def __str__(self):
        return f"{self.name}"


class Supplier(models.Model):
    """Модель поставщика"""
    STATUS_CHOICES = [
        ('active', 'Активный'),
        ('inactive', 'Неактивный'),
        ('blocked', 'Заблокирован'),
        ('new', 'Новый'),
    ]
    
    SUPPLIER_TYPE_CHOICES = [
        ('company', 'Юридическое лицо'),
        ('individual', 'Индивидуальный предприниматель'),
        ('person', 'Физическое лицо'),
    ]
    
    name = models.CharField('Название/ФИО', max_length=300)
    supplier_type = models.CharField('Тип поставщика', max_length=20, choices=SUPPLIER_TYPE_CHOICES, default='company')
    inn = models.CharField('ИНН', max_length=12, blank=True)
    kpp = models.CharField('КПП', max_length=9, blank=True)
    ogrn = models.CharField('ОГРН/ОГРНИП', max_length=15, blank=True)
    
    # Контактная информация
    legal_address = models.TextField('Юридический адрес', blank=True)
    actual_address = models.TextField('Фактический адрес', blank=True)
    phone = models.CharField('Телефон', max_length=50, blank=True)
    email = models.EmailField('Email', blank=True)
    website = models.URLField('Сайт', blank=True)
    
    # Банковские реквизиты
    bank_name = models.CharField('Наименование банка', max_length=200, blank=True)
    bank_bik = models.CharField('БИК банка', max_length=9, blank=True)
    bank_account = models.CharField('Расчетный счет', max_length=20, blank=True)
    corr_account = models.CharField('Корреспондентский счет', max_length=20, blank=True)
    
    # Контактное лицо
    contact_person = models.CharField('Контактное лицо', max_length=200, blank=True)
    contact_phone = models.CharField('Телефон контактного лица', max_length=50, blank=True)
    contact_email = models.EmailField('Email контактного лица', blank=True)
    
    # Дополнительная информация
    description = models.TextField('Описание', blank=True)
    specialization = models.TextField('Специализация/Категории товаров', blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Документы
    registration_doc = models.FileField('Регистрационные документы', upload_to='supplier_docs/registration/%Y/%m/', blank=True, null=True)
    license_doc = models.FileField('Лицензии и сертификаты', upload_to='supplier_docs/licenses/%Y/%m/', blank=True, null=True)
    
    # Служебные поля
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='Кем создан', null=True, blank=True, related_name='created_suppliers')
    
    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_status_display_color(self):
        """Возвращает цвет для статуса"""
        colors = {
            'active': 'success',
            'inactive': 'secondary',
            'blocked': 'danger',
            'new': 'warning',
        }
        return colors.get(self.status, 'secondary')
    
    @property
    def short_name(self):
        """Краткое название (первые 50 символов)"""
        return self.name[:50] + '...' if len(self.name) > 50 else self.name


class PurchaseRequest(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('planned', 'Запланирована'),
        ('pending', 'На согласовании'),
        ('approved', 'Согласована'),
        ('rejected', 'Отклонена'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнена'),
        ('cancelled', 'Отменена'),
    ]
    
    current_year = datetime.now().year
    PLAN_CHOICES = [
        (f'plan_{current_year}', f'План закупок на {current_year} год'),
        (f'plan_{current_year+1}', f'План закупок на {current_year+1} год'),
        (f'plan_{current_year+2}', f'План закупок на {current_year+2} год'),
        (f'plan_{current_year+3}', f'План закупок на {current_year+3} год'),
        (f'plan_{current_year+4}', f'План закупок на {current_year+4} год'),
        (f'plan_{current_year+5}', f'План закупок на {current_year+5} год'),
    ]
    
    BUDGET_ARTICLE_CHOICES = [
        ('capex', 'CAPEX (Капитальные затраты)'),
        ('opex', 'OPEX (Операционные затраты)'),
        ('repair', 'Ремонтные работы'),
        ('safety', 'Охрана труда и ТБ'),
        ('other', 'Прочее'),
    ]

    requester = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Заявитель', related_name='purchase_requests')
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                 verbose_name='Согласующий', related_name='requests_to_approve')
    nomenclature = models.ForeignKey(Material, on_delete=models.CASCADE, verbose_name='Номенклатура')
    quantity = models.DecimalField('Количество', max_digits=15, decimal_places=2)
    max_price = models.DecimalField('Максимальная цена', max_digits=15, decimal_places=2, null=True, blank=True)
    unit = models.CharField('Единица измерения', max_length=10, choices=Material.UNIT_CHOICES)
    plan_type = models.CharField('План', max_length=20, choices=PLAN_CHOICES)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')
    budget_article = models.CharField('Статья бюджета', max_length=20, choices=BUDGET_ARTICLE_CHOICES, default='opex')
    price = models.DecimalField('Цена', max_digits=15, decimal_places=2, null=True, blank=True)
    description = models.TextField('Описание', blank=True)
    attachment = models.FileField('Файлы', upload_to='purchase_files/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    rejection_reason = models.TextField('Причина отклонения/доработки', blank=True)

    class Meta:
        verbose_name = 'Заявка на закупку'
        verbose_name_plural = 'Заявки на закупку'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заявка №{self.id}"

    def sent_to_approval(self, approver_user):
        """Отправка на согласование"""
        if self.status in ['draft', 'planned', 'rejected']:
            self.status = 'pending'
            self.approver = approver_user
            self.save()
            return True
        return False
    
    def approve(self):
        """Согласование заявки"""
        if self.status == 'pending':
            self.status = 'approved'
            self.save()
            return True
        return False
    
    def reject(self, reason=''):
        """Отклонение заявки"""
        if self.status == 'pending':
            self.status = 'rejected'
            self.rejection_reason = reason
            self.save()
            return True
        return False
    
    def request_revision(self, reason=''):
        """Отправка на доработку"""
        if self.status == 'pending':
            self.status = 'draft'
            self.rejection_reason = reason
            self.approver = None
            self.save()
            return True
        return False
    
    def is_editable_by_requester(self):
        """Может ли заявитель редактировать"""
        return self.status in ['draft', 'planned', 'rejected']
    
    def can_be_approved(self):
        """Может ли быть согласована"""
        return self.status == 'pending'


class PlanApprover(models.Model):
    """Согласующие по плану закупок"""
    plan_type = models.CharField('План', max_length=20)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Согласующий', related_name='plan_approvals')
    position = models.CharField('Должность', max_length=200, blank=True)
    
    class Meta:
        verbose_name = 'Согласующий по плану'
        verbose_name_plural = 'Согласующие по планам'
        unique_together = ['plan_type', 'user']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.plan_type}"


class PlanApprovalHistory(models.Model):
    """История согласования плана"""
    DECISION_CHOICES = [
        ('approved', 'Согласовано'),
        ('rejected', 'Отклонено'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'На согласовании'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
    ]
    
    plan_type = models.CharField('План', max_length=20)
    approver = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Согласующий')
    start_date = models.DateTimeField('Дата начала', auto_now_add=True)
    end_date = models.DateTimeField('Дата завершения', null=True, blank=True)
    decision = models.CharField('Решение', max_length=20, choices=DECISION_CHOICES, blank=True)
    document = models.FileField('Документ', upload_to='approval_docs/%Y/%m/', blank=True, null=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    class Meta:
        verbose_name = 'Запись согласования'
        verbose_name_plural = 'История согласования'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.plan_type} - {self.approver.get_full_name()} - {self.get_decision_display()}"


class Tender(models.Model):
    """Модель конкурса (тендера) - всегда открытый"""
    STATUS_CHOICES = [
        ('preparation', 'Подготовка'),
        ('active', 'Активный'),
        ('closed', 'Закрыт'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]
    
    TRADING_CHOICES = [
        (True, 'Да'),
        (False, 'Нет'),
    ]
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    name = models.CharField('Название конкурса', max_length=300)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='preparation')
    contact_person = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='Контактное лицо', null=True, blank=True)
    
    place_of_delivery = models.CharField('Место поставки', max_length=300, blank=True)
    min_step = models.DecimalField('Минимальный шаг', max_digits=15, decimal_places=2, null=True, blank=True)
    is_trading = models.BooleanField('Проводить торги', choices=TRADING_CHOICES, default=True)
    
    start_date = models.DateTimeField('Дата и время начала конкурса')
    submission_deadline = models.DateTimeField('Срок подачи предложений')
    delivery_term = models.CharField('Срок поставки', max_length=200, blank=True)
    
    procurement_docs = models.FileField('Закупочная документация', upload_to='tender_docs/procurement/%Y/%m/', blank=True, null=True)
    price_request_doc = models.FileField('Запрос КП', upload_to='tender_docs/price_request/%Y/%m/', blank=True, null=True)
    
    description = models.TextField('Описание', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Создатель', related_name='created_tenders', null=True)
    
    # Новые поля для отслеживания отправки задач
    tasks_sent = models.BooleanField('Задачи отправлены', default=False)
    tasks_removed = models.BooleanField('Задачи удалены', default=False)
    
    class Meta:
        verbose_name = 'Конкурс'
        verbose_name_plural = 'Конкурсы'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Конкурс: {self.name}"
    
    @property
    def total_price(self):
        """Вычисляет общую цену из всех позиций конкурса"""
        total = sum(item.start_price or 0 for item in self.items.all())
        return total if total > 0 else None
    
    def is_active_for_proposals(self):
        """Проверяет, активен ли конкурс для подачи предложений"""
        from django.utils import timezone
        now = timezone.now()
        return self.status == 'active' and now < self.submission_deadline
    
    def send_tasks_to_users(self):
        """Отправляет задачи всем пользователям при старте конкурса"""
        if self.tasks_sent:
            return False
            
        from django.utils import timezone
        now = timezone.now()
        
        if now >= self.start_date and self.status == 'active':
            # Отправляем задачи только менеджерам, персоналу и сотрудникам снабжения
            all_users = User.objects.filter(
                models.Q(is_manager=True) | models.Q(is_staff=True) | models.Q(is_supply_employee=True)
            )
            
            for user in all_users:
                Task.objects.get_or_create(
                    title=f'Участие в конкурсе: {self.name}',
                    description=f'Конкурс открыт для участия.\n\n'
                               f'Название: {self.name}\n'
                               f'Срок подачи: {self.submission_deadline.strftime("%d.%m.%Y %H:%M")}\n'
                               f'Место поставки: {self.place_of_delivery or "Не указано"}\n\n'
                               f'Успейте подать заявку до окончания срока!',
                    executor=user,
                    defaults={
                        'created_by': self.created_by or user,
                        'state': 'active',
                        'task_type': 'general',
                        'start_date': self.start_date,
                        'end_date': self.submission_deadline
                    }
                )
            
            self.tasks_sent = True
            self.save(update_fields=['tasks_sent'])
            return True
        return False
    
    def remove_tasks_from_users(self):
        """Удаляет задачи у всех пользователей по окончании срока подачи"""
        if self.tasks_removed:
            return False
            
        from django.utils import timezone
        now = timezone.now()
        
        if now >= self.submission_deadline:
            Task.objects.filter(
                title=f'Участие в конкурсе: {self.name}',
                task_type='general'
            ).delete()
            
            self.tasks_removed = True
            self.status = 'closed'
            self.save(update_fields=['tasks_removed', 'status'])
            return True
        return False
    
    def check_and_update_status(self):
        """Проверяет и обновляет статус конкурса"""
        from django.utils import timezone
        now = timezone.now()
        
        # Если конкурс в подготовке и наступило время начала - активируем
        if self.status == 'preparation' and now >= self.start_date:
            self.status = 'active'
            self.save(update_fields=['status'])
            self.send_tasks_to_users()
            return True
            
        # Если конкурс активен и прошел срок подачи - закрываем
        if self.status == 'active' and now >= self.submission_deadline:
            self.remove_tasks_from_users()
            return True
            
        return False


class TenderItem(models.Model):
    """Позиции конкурса"""
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, verbose_name='Конкурс', related_name='items')
    purchase_request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, verbose_name='Заявка на закупку')
    quantity = models.DecimalField('Количество', max_digits=15, decimal_places=2)
    start_price = models.DecimalField('Начальная цена', max_digits=15, decimal_places=2)
    attachment = models.FileField('Приложение', upload_to='tender_items/%Y/%m/', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Позиция конкурса'
        verbose_name_plural = 'Позиции конкурса'
    
    def __str__(self):
        return f"{self.tender.name} - {self.purchase_request.nomenclature}"


class TenderProposal(models.Model):
    """Предложение пользователя по конкурсу"""
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, verbose_name='Конкурс', related_name='proposals')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь', related_name='tender_proposals')
    proposal_date = models.DateTimeField('Дата подачи', auto_now_add=True)
    validity_date = models.DateField('Действительно до', help_text='Дата окончания действия КП')
    attachment = models.FileField('Коммерческое предложение', upload_to='tender_proposals/%Y/%m/', blank=True, null=True)
    notes = models.TextField('Примечания', blank=True)
    is_active = models.BooleanField('Активно', default=True)
    
    class Meta:
        verbose_name = 'Предложение по конкурсу'
        verbose_name_plural = 'Предложения по конкурсам'
        unique_together = ['tender', 'user']
        ordering = ['-proposal_date']
    
    def __str__(self):
        return f"Предложение {self.user.get_full_name()} по {self.tender.name}"
    
    @property
    def total_amount(self):
        """Общая сумма предложения"""
        return sum(item.proposed_price * item.quantity for item in self.items.all())


class TenderProposalItem(models.Model):
    """Позиции предложения по конкурсу"""
    proposal = models.ForeignKey(TenderProposal, on_delete=models.CASCADE, verbose_name='Предложение', related_name='items')
    tender_item = models.ForeignKey(TenderItem, on_delete=models.CASCADE, verbose_name='Позиция конкурса')
    proposed_price = models.DecimalField('Предлагаемая цена', max_digits=15, decimal_places=2)
    
    class Meta:
        verbose_name = 'Позиция предложения'
        verbose_name_plural = 'Позиции предложения'
        unique_together = ['proposal', 'tender_item']
    
    def __str__(self):
        return f"{self.tender_item.purchase_request.nomenclature} - {self.proposed_price} ₽"
    
    @property
    def quantity(self):
        """Количество из позиции конкурса"""
        return self.tender_item.quantity


class Task(models.Model):
    """Модель задач пользователя"""
    STATE_CHOICES = [
        ('active', 'Активная'),
        ('pending', 'В ожидании'),
        ('in_progress', 'В работе'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]
    
    # Типы задач
    TASK_TYPE_CHOICES = [
        ('general', 'Общая'),
        ('approval', 'Согласование заявки'),
        ('review', 'Доработка заявки'),
        ('contract_approval', 'Согласование договора'),
    ]
    
    title = models.CharField('Название задачи', max_length=300)
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    start_date = models.DateTimeField('Дата начала', null=True, blank=True)
    end_date = models.DateTimeField('Дата завершения', null=True, blank=True)
    executor = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Исполнитель', related_name='tasks')
    state = models.CharField('Состояние', max_length=20, choices=STATE_CHOICES, default='active')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Постановщик', related_name='created_tasks')
    task_type = models.CharField('Тип задачи', max_length=20, choices=TASK_TYPE_CHOICES, default='general')
    related_request = models.ForeignKey(PurchaseRequest, on_delete=models.SET_NULL, 
                                        verbose_name='Связанная заявка', null=True, blank=True)
    related_contract = models.ForeignKey('Contract', on_delete=models.SET_NULL,
                                         verbose_name='Связанный договор', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_state_display()})"
    
    @property
    def is_active(self):
        return self.state in ['active', 'pending', 'in_progress']
    
    def get_tender_id(self):
        """Извлекает ID конкурса из заголовка задачи"""
        if self.title.startswith('Участие в конкурсе:'):
            # Пытаемся найти конкурс по названию
            tender_name = self.title.replace('Участие в конкурсе:', '').strip()
            try:
                tender = Tender.objects.filter(name=tender_name).first()
                return tender.id if tender else None
            except:
                return None
        return None


class TenderWinner(models.Model):
    """Победитель конкурса"""
    tender = models.OneToOneField(Tender, on_delete=models.CASCADE, verbose_name='Конкурс', related_name='winner')
    proposal = models.ForeignKey(TenderProposal, on_delete=models.CASCADE, verbose_name='Предложение победителя')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Победитель', related_name='won_tenders')
    selected_by = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='Выбран кем', 
                                    related_name='selected_winners', null=True, blank=True)
    selected_at = models.DateTimeField('Дата выбора', auto_now_add=True)
    notes = models.TextField('Примечания', blank=True)
    
    class Meta:
        verbose_name = 'Победитель конкурса'
        verbose_name_plural = 'Победители конкурсов'
        ordering = ['-selected_at']
    
    def __str__(self):
        return f"Победитель {self.tender.name}: {self.user.get_full_name()}"
    
    @property
    def total_amount(self):
        """Общая сумма выигранного предложения"""
        return self.proposal.total_amount


# ==================== НОВАЯ МОДЕЛЬ ДОГОВОРОВ ====================

class Contract(models.Model):
    """Модель договора"""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('pending', 'На согласовании'),
        ('approved', 'Согласован'),
        ('rejected', 'Отклонен'),
        ('active', 'Действующий'),
        ('completed', 'Выполнен'),
        ('terminated', 'Расторгнут'),
        ('cancelled', 'Отменен'),
    ]
    
    name = models.CharField('Название договора', max_length=300)
    contract_amount = models.DecimalField('Сумма договора', max_digits=15, decimal_places=2, default=0)
    contract_date = models.DateField('Дата договора')
    end_date = models.DateField('Дата окончания срока договора')
    
    # Ответственный
    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                    verbose_name='Ответственный', 
                                    related_name='responsible_contracts',
                                    null=True, blank=True)
    
    # Связи
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE,
                                  verbose_name='Компания/Поставщик',
                                  related_name='contracts')
    
    # Коммерческое предложение (файл)
    commercial_proposal = models.FileField('Коммерческое предложение', 
                                           upload_to='contracts/proposals/%Y/%m/', 
                                           blank=True, null=True)
    
    # Документ договора
    contract_document = models.FileField('Документ договора',
                                          upload_to='contracts/documents/%Y/%m/',
                                          blank=True, null=True)
    
    # Статус и комментарий
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')
    comment = models.TextField('Комментарий', blank=True)
    
    # Согласование
    approver = models.ForeignKey(User, on_delete=models.SET_NULL,
                                  verbose_name='Согласующий',
                                  related_name='contracts_to_approve',
                                  null=True, blank=True)
    
    # Служебные поля
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    verbose_name='Кем создан',
                                    related_name='created_contracts',
                                    null=True, blank=True)
    
    class Meta:
        verbose_name = 'Договор'
        verbose_name_plural = 'Договоры'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Договор: {self.name}"
    
    def get_status_display_color(self):
        """Возвращает цвет для статуса"""
        colors = {
            'draft': 'secondary',
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'active': 'primary',
            'completed': 'info',
            'terminated': 'dark',
            'cancelled': 'secondary',
        }
        return colors.get(self.status, 'secondary')
    
    def send_to_approval(self, approver_user):
        """Отправка договора на согласование"""
        if self.status in ['draft', 'rejected']:
            self.status = 'pending'
            self.approver = approver_user
            self.save()
            return True
        return False
    
    def approve(self):
        """Согласование договора"""
        if self.status == 'pending':
            self.status = 'active'
            self.save()
            return True
        return False
    
    def reject(self, reason=''):
        """Отклонение договора"""
        if self.status == 'pending':
            self.status = 'rejected'
            if reason:
                self.comment = reason
            self.save()
            return True
        return False
    
    def is_editable(self):
        """Может ли договор редактироваться"""
        return self.status in ['draft', 'rejected']
    
    def can_be_approved(self):
        """Может ли быть согласован"""
        return self.status == 'pending'