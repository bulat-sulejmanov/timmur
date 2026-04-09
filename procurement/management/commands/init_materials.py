from django.core.management.base import BaseCommand
from procurement.models import Material


class Command(BaseCommand):
    help = 'Заполняет базу данных начальными материалами для нефтегазовой отрасли'

    def handle(self, *args, **kwargs):
        materials_data = [
            {
                'name': 'Буровой раствор (бентонитовый)',
                'quantity': 150.50,
                'unit': 'м³',
                'description': 'Буровой раствор для бурения нефтяных скважин, плотность 1.15-1.25 г/см³',
                'min_stock': 50.00,
                'location': 'Склад №1, сектор А'
            },
            {
                'name': 'Трубы НКТ (насосно-компрессорные)',
                'quantity': 2500.00,
                'unit': 'м',
                'description': 'Трубы НКТ 73х5.5 мм, группа прочности Д, сталь 45',
                'min_stock': 500.00,
                'location': 'Открытая площадка Б'
            },
            {
                'name': 'Обсадные трубы',
                'quantity': 800.00,
                'unit': 'м',
                'description': 'Обсадные трубы 168х8 мм, ГОСТ 632-80',
                'min_stock': 200.00,
                'location': 'Открытая площадка Б'
            },
            {
                'name': 'Цемент нефтяной (ПЦТ)',
                'quantity': 45.00,
                'unit': 'т',
                'description': 'Портландцемент тампонажный ГОСТ 1581-96, марка Д20',
                'min_stock': 20.00,
                'location': 'Склад №2, цементный отдел'
            },
            {
                'name': 'Долота буровые шарошечные',
                'quantity': 12.00,
                'unit': 'шт',
                'description': 'Долота 215,9 мм (8 1/2 дюйма), IADC 537',
                'min_stock': 5.00,
                'location': 'Склад №1, инструментальный отдел'
            },
            {
                'name': 'Бентонит утяжеленный',
                'quantity': 5.20,
                'unit': 'т',
                'description': 'Бентонит для приготовления буровых растворов (порошок)',
                'min_stock': 2.00,
                'location': 'Склад №1, сектор А'
            },
            {
                'name': 'Химреагенты (ингибиторы коррозии)',
                'quantity': 850.00,
                'unit': 'кг',
                'description': 'Ингибитор коррозии для заканчивания скважин, концентрат',
                'min_stock': 200.00,
                'location': 'Склад химреактивов'
            },
            {
                'name': 'Насосы штанговые',
                'quantity': 8.00,
                'unit': 'шт',
                'description': 'Насосы штанговые НШ-50-28-500 для добычи нефти',
                'min_stock': 3.00,
                'location': 'Склад оборудования'
            },
            {
                'name': 'Запорная арматура (задвижки)',
                'quantity': 24.00,
                'unit': 'шт',
                'description': 'Задвижки стальные 30с41нж Ду100 Ру16 для нефтепроводов',
                'min_stock': 10.00,
                'location': 'Склад №3, арматура'
            },
            {
                'name': 'Компрессоры для ГНКТ',
                'quantity': 3.00,
                'unit': 'шт',
                'description': 'Газонапорные компрессорные установки для поддержки пластового давления',
                'min_stock': 1.00,
                'location': 'Машинный двор'
            }
        ]

        created_count = 0
        for data in materials_data:
            material, created = Material.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Создан материал: {material.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'- Материал уже существует: {material.name}'))

        self.stdout.write(self.style.SUCCESS(f'\nИтого создано материалов: {created_count}'))