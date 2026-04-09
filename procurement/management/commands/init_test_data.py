from datetime import timedelta
from decimal import Decimal
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from procurement.models import Contract, Material, PurchaseRequest, Supplier, Task, User


class Command(BaseCommand):
    help = 'Создает тестовые аккаунты по ролям и базовые тестовые данные без дублей.'

    def _ensure_user(self, username, password, role_flags, profile_defaults):
        defaults = {
            **profile_defaults,
            **role_flags,
            'is_active': True,
        }
        user, created = User.objects.get_or_create(username=username, defaults=defaults)

        updated_fields = []
        for field, value in role_flags.items():
            if getattr(user, field) != value:
                setattr(user, field, value)
                updated_fields.append(field)

        if not user.is_active:
            user.is_active = True
            updated_fields.append('is_active')

        if updated_fields:
            user.save(update_fields=updated_fields)

        if created:
            user.set_password(password)
            user.save(update_fields=['password'])

        return user, created

    @transaction.atomic
    def handle(self, *args, **kwargs):
        password = os.environ.get('TEST_USERS_PASSWORD', 'Test12345!')

        users_to_create = [
            {
                'username': 'admin_test',
                'role_flags': {
                    'is_superuser': True,
                    'is_staff': True,
                    'is_manager': False,
                    'is_supply_employee': False,
                },
                'profile': {
                    'first_name': 'Системный',
                    'last_name': 'Администратор',
                    'email': 'admin_test@example.com',
                    'position': 'Администратор системы',
                },
            },
            {
                'username': 'staff_test',
                'role_flags': {
                    'is_superuser': False,
                    'is_staff': True,
                    'is_manager': False,
                    'is_supply_employee': False,
                },
                'profile': {
                    'first_name': 'Офисный',
                    'last_name': 'Сотрудник',
                    'email': 'staff_test@example.com',
                    'position': 'Персонал',
                },
            },
            {
                'username': 'manager_test',
                'role_flags': {
                    'is_superuser': False,
                    'is_staff': False,
                    'is_manager': True,
                    'is_supply_employee': False,
                },
                'profile': {
                    'first_name': 'Руководитель',
                    'last_name': 'Тестовый',
                    'email': 'manager_test@example.com',
                    'position': 'Руководитель отдела',
                },
            },
            {
                'username': 'supply_test',
                'role_flags': {
                    'is_superuser': False,
                    'is_staff': False,
                    'is_manager': False,
                    'is_supply_employee': True,
                },
                'profile': {
                    'first_name': 'Снабжение',
                    'last_name': 'Тестовый',
                    'email': 'supply_test@example.com',
                    'position': 'Специалист снабжения',
                },
            },
            {
                'username': 'employee_test',
                'role_flags': {
                    'is_superuser': False,
                    'is_staff': False,
                    'is_manager': False,
                    'is_supply_employee': False,
                },
                'profile': {
                    'first_name': 'Пользователь',
                    'last_name': 'Тестовый',
                    'email': 'employee_test@example.com',
                    'position': 'Инициатор заявок',
                },
            },
        ]

        users = {}
        users_created_count = 0

        for item in users_to_create:
            user, created = self._ensure_user(
                username=item['username'],
                password=password,
                role_flags=item['role_flags'],
                profile_defaults=item['profile'],
            )
            users[item['username']] = user
            if created:
                users_created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Создан пользователь: {user.username}'))
            else:
                self.stdout.write(self.style.WARNING(f'Пользователь уже существует: {user.username}'))

        materials_data = [
            ('[TEST] Бентонитовый раствор', 'м³', 'Тестовый материал для демо-заявок'),
            ('[TEST] Труба НКТ 73', 'м', 'Тестовый материал для тендеров'),
            ('[TEST] Арматура запорная', 'шт', 'Тестовая номенклатура'),
        ]

        materials = {}
        materials_created_count = 0
        for name, unit, description in materials_data:
            material, created = Material.objects.get_or_create(
                name=name,
                defaults={
                    'unit': unit,
                    'description': description,
                },
            )
            materials[name] = material
            if created:
                materials_created_count += 1

        supplier, supplier_created = Supplier.objects.get_or_create(
            name='[TEST] ООО ТестПоставка',
            defaults={
                'supplier_type': 'company',
                'inn': '7700000001',
                'kpp': '770001001',
                'ogrn': '1027700000001',
                'phone': '+7 (900) 000-00-01',
                'email': 'supplier_test@example.com',
                'status': 'active',
                'contact_person': 'Иванов Иван',
                'created_by': users['manager_test'],
            },
        )

        current_plan_type = PurchaseRequest.PLAN_CHOICES[0][0]
        purchase_request, request_created = PurchaseRequest.objects.get_or_create(
            requester=users['employee_test'],
            nomenclature=materials['[TEST] Бентонитовый раствор'],
            description='[TEST] Демонстрационная заявка на закупку',
            defaults={
                'quantity': Decimal('25.00'),
                'max_price': Decimal('120000.00'),
                'unit': materials['[TEST] Бентонитовый раствор'].unit,
                'plan_type': current_plan_type,
                'status': 'pending',
                'budget_article': 'opex',
                'approver': users['manager_test'],
            },
        )

        task, task_created = Task.objects.get_or_create(
            title='[TEST] Согласование демо-заявки',
            executor=users['manager_test'],
            task_type='approval',
            related_request=purchase_request,
            defaults={
                'description': 'Проверьте и согласуйте тестовую заявку на закупку.',
                'state': 'active',
                'created_by': users['employee_test'],
            },
        )

        today = timezone.localdate()
        contract, contract_created = Contract.objects.get_or_create(
            name='[TEST] Рамочный договор на поставку материалов',
            supplier=supplier,
            defaults={
                'contract_amount': Decimal('500000.00'),
                'contract_date': today,
                'end_date': today + timedelta(days=365),
                'responsible': users['supply_test'],
                'status': 'pending',
                'comment': 'Тестовый договор для демонстрации workflow',
                'approver': users['staff_test'],
                'created_by': users['manager_test'],
            },
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Инициализация тестовых данных завершена.'))
        self.stdout.write(
            f'Пользователи: создано {users_created_count}, уже существовали {len(users_to_create) - users_created_count}'
        )
        self.stdout.write(
            f'Материалы: создано {materials_created_count}, уже существовали {len(materials_data) - materials_created_count}'
        )
        self.stdout.write(
            f"Поставщик: {'создан' if supplier_created else 'уже существует'}"
        )
        self.stdout.write(
            f"Заявка: {'создана' if request_created else 'уже существует'}"
        )
        self.stdout.write(
            f"Задача: {'создана' if task_created else 'уже существует'}"
        )
        self.stdout.write(
            f"Договор: {'создан' if contract_created else 'уже существует'}"
        )
        self.stdout.write('Тестовый пароль для новых аккаунтов: TEST_USERS_PASSWORD (по умолчанию Test12345!)')
