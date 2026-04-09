# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction, models
from django.db.models import Q, Sum, F
from django.utils import timezone
from decimal import Decimal
from datetime import datetime
from .forms import ProfileEditForm, PurchaseRequestForm, TenderForm, TenderItemFormSet, ApprovalForm, SupplierForm, ContractForm, ContractApprovalForm, SupplyEmployeeCreationForm
from .models import Material, PurchaseRequest, User, PlanApprover, PlanApprovalHistory, Tender, TenderItem, TenderProposal, TenderProposalItem, Task, TenderWinner, Supplier, Contract


class CustomLoginView(auth_views.LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True


class CustomLogoutView(auth_views.LogoutView):
    next_page = 'login'


@login_required
def profile_detail(request):
    user = request.user
    return render(request, 'profile/detail.html', {'user': user})


@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile_detail')
    else:
        form = ProfileEditForm(instance=request.user)
    
    return render(request, 'profile/edit.html', {'form': form})


@login_required
def dashboard(request):
    """Главная страница с диаграммами и статистикой"""
    user = request.user
    
    # Проверяем и обновляем статусы конкурсов
    check_tender_statuses()
    
    # === СТАТИСТИКА ЗАДАЧ ===
    completed_tasks_count = Task.objects.filter(
        executor=user,
        state='completed'
    ).count()
    
    pending_tasks_count = Task.objects.filter(
        executor=user,
        state__in=['active', 'pending', 'in_progress']
    ).count()
    
    # === СТАТИСТИКА ЗАЯВОК (для круговой диаграммы) ===
    planned_requests = PurchaseRequest.objects.filter(
        status='planned'
    ).count()
    
    approved_requests = PurchaseRequest.objects.filter(
        status='approved'
    ).count()
    
    # === СТАТИСТИКА ДОГОВОРОВ (для столбчатой диаграммы) ===
    draft_contracts = Contract.objects.filter(
        status='draft'
    ).count()
    
    pending_contracts = Contract.objects.filter(
        status='pending'
    ).count()
    
    active_contracts = Contract.objects.filter(
        status='active'
    ).count()
    
    completed_contracts = Contract.objects.filter(
        status='completed'
    ).count()
    
    context = {
        'completed_tasks_count': completed_tasks_count,
        'pending_tasks_count': pending_tasks_count,
        'planned_requests': planned_requests,
        'approved_requests': approved_requests,
        'draft_contracts': draft_contracts,
        'pending_contracts': pending_contracts,
        'active_contracts': active_contracts,
        'completed_contracts': completed_contracts,
    }
    
    return render(request, 'dashboard.html', context)


def check_tender_statuses():
    """Проверяет статусы всех конкурсов и отправляет/удаляет задачи при необходимости"""
    now = timezone.now()
    
    # Находим конкурсы в подготовке, которые должны начаться
    tenders_to_activate = Tender.objects.filter(
        status='preparation',
        start_date__lte=now,
        tasks_sent=False
    )
    
    for tender in tenders_to_activate:
        tender.check_and_update_status()
    
    # Находим активные конкурсы, у которых закончился срок подачи
    tenders_to_close = Tender.objects.filter(
        status='active',
        submission_deadline__lte=now,
        tasks_removed=False
    )
    
    for tender in tenders_to_close:
        tender.remove_tasks_from_users()


@login_required
def purchase_request_list(request):
    requests = PurchaseRequest.objects.all().select_related('requester', 'nomenclature', 'approver')
    
    available_approvers = User.objects.filter(
        Q(is_manager=True) | Q(is_staff=True) | Q(is_superuser=True)
    ).distinct().order_by('last_name', 'first_name')
    
    is_privileged = request.user.is_manager or request.user.is_staff or request.user.is_superuser
    
    if not is_privileged:
        available_approvers = available_approvers.exclude(id=request.user.id)
    
    status_counts = {
        'total': requests.count(),
        'pending': requests.filter(status='pending').count(),
        'approved': requests.filter(status='approved').count(),
        'draft': requests.filter(status='draft').count(),
        'rejected': requests.filter(status='rejected').count(),
    }
    
    context = {
        'requests': requests,
        'status_counts': status_counts,
        'available_approvers': available_approvers,
        'is_privileged_user': is_privileged,
    }
    return render(request, 'purchases/request_list.html', context)


@login_required
def create_purchase_request(request):
    if request.method == 'POST':
        form = PurchaseRequestForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            purchase_request = form.save(commit=False)
            purchase_request.requester = request.user
            purchase_request.status = form.cleaned_data.get('status', 'draft')
            purchase_request.save()
            
            messages.success(request, f'Заявка №{purchase_request.id} создана')
            return redirect('view_purchase_request', pk=purchase_request.pk)
        else:
            messages.error(request, f'Ошибка в форме: {form.errors}')
    else:
        form = PurchaseRequestForm(user=request.user)
    
    context = {
        'form': form,
        'is_new': True,
        'is_draft': True,
        'user_full_name': request.user.get_full_name(),
    }
    return render(request, 'purchases/request_form.html', context)


@login_required
def view_purchase_request(request, pk):
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk)
    
    is_requester = (request.user == purchase_request.requester)
    is_approver = (request.user == purchase_request.approver)
    can_edit = is_requester and purchase_request.is_editable_by_requester()
    
    is_draft = (purchase_request.status == 'draft')
    is_pending = (purchase_request.status == 'pending')
    
    if request.method == 'POST':
        if 'send_to_plan' in request.POST and is_requester and is_draft:
            purchase_request.status = 'planned'
            purchase_request.save()
            messages.success(request, 'Заявка отправлена в план')
            return redirect('view_purchase_request', pk=pk)
        
        if 'save_changes' in request.POST and can_edit:
            form = PurchaseRequestForm(request.POST, request.FILES, instance=purchase_request, user=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Изменения сохранены')
                return redirect('view_purchase_request', pk=pk)
            else:
                messages.error(request, 'Ошибка при сохранении')
    
    form = PurchaseRequestForm(instance=purchase_request, user=request.user)
    
    available_approvers = User.objects.filter(
        Q(is_manager=True) | Q(is_staff=True) | Q(is_superuser=True)
    ).exclude(id=request.user.id)
    
    context = {
        'request_obj': purchase_request,
        'form': form,
        'is_draft': is_draft,
        'is_pending': is_pending,
        'is_new': False,
        'can_edit': can_edit,
        'is_requester': is_requester,
        'is_approver': is_approver,
        'user_full_name': purchase_request.requester.get_full_name(),
        'available_approvers': available_approvers,
    }
    return render(request, 'purchases/request_form.html', context)


@login_required
def edit_purchase_request(request, pk):
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk)
    
    if request.user != purchase_request.requester:
        messages.error(request, 'Вы не можете редактировать чужую заявку')
        return redirect('view_purchase_request', pk=pk)
    
    if not purchase_request.is_editable_by_requester():
        messages.error(request, 'Редактирование недоступно для заявок в текущем статусе')
        return redirect('view_purchase_request', pk=pk)
    
    if request.method == 'POST':
        form = PurchaseRequestForm(request.POST, request.FILES, instance=purchase_request, user=request.user)
        if form.is_valid():
            instance = form.save(commit=False)
            
            if instance.rejection_reason:
                instance.rejection_reason = ''
                messages.info(request, 'Замечания сброшены. Теперь можно отправить на повторное согласование.')
            
            instance.save()
            
            messages.success(request, 'Заявка успешно обновлена')
            
            # УДАЛЯЕМ задачу на доработку после её выполнения
            Task.objects.filter(
                related_request=purchase_request,
                executor=request.user,
                task_type='review',
                state__in=['active', 'pending', 'in_progress']
            ).delete()
            
            return redirect('view_purchase_request', pk=pk)
    else:
        form = PurchaseRequestForm(instance=purchase_request, user=request.user)
    
    context = {
        'form': form,
        'request_obj': purchase_request,
        'is_new': False,
        'is_draft': purchase_request.status == 'draft',
        'user_full_name': request.user.get_full_name(),
        'is_edit_mode': True,
        'is_revision': bool(purchase_request.rejection_reason),
    }
    return render(request, 'purchases/request_edit.html', context)


@login_required
@transaction.atomic
def send_for_approval(request, pk):
    """Отправка заявки на согласование с созданием задачи"""
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk)
    
    if request.user != purchase_request.requester:
        messages.error(request, 'Вы не можете отправить чужую заявку на согласование')
        return redirect('purchase_request_list')
    
    if request.method == 'POST':
        approver_id = request.POST.get('approver')
        if not approver_id:
            messages.error(request, 'Необходимо выбрать согласующего')
            return redirect('purchase_request_list')
        
        try:
            approver = User.objects.get(pk=approver_id)
        except User.DoesNotExist:
            messages.error(request, 'Выбранный согласующий не найден')
            return redirect('purchase_request_list')
        
        if not (approver.is_manager or approver.is_staff or approver.is_superuser):
            messages.error(request, 'Выбранный пользователь не имеет прав для согласования заявок')
            return redirect('purchase_request_list')
        
        is_privileged = request.user.is_manager or request.user.is_staff or request.user.is_superuser
        if approver == request.user and not is_privileged:
            messages.error(request, 'Вы не можете отправить заявку на согласование самому себе')
            return redirect('purchase_request_list')
        
        # Удаляем старые активные задачи по этой заявке для этого исполнителя (если есть)
        Task.objects.filter(
            related_request=purchase_request,
            executor=approver,
            task_type='approval',
            state__in=['active', 'pending', 'in_progress']
        ).delete()
        
        if purchase_request.sent_to_approval(approver):
            Task.objects.create(
                title=f'Согласование заявки №{purchase_request.id}',
                description=f'Необходимо согласовать заявку на закупку: {purchase_request.nomenclature.name}\n'
                           f'Количество: {purchase_request.quantity} {purchase_request.get_unit_display()}\n'
                           f'Максимальная цена: {purchase_request.max_price or "не указана"}\n'
                           f'Заявитель: {purchase_request.requester.get_full_name()}',
                executor=approver,
                created_by=request.user,
                state='active',
                task_type='approval',
                related_request=purchase_request
            )
            
            messages.success(request, f'Заявка №{purchase_request.id} отправлена на согласование пользователю {approver.get_full_name()}')
        else:
            messages.error(request, 'Невозможно отправить заявку на согласование в текущем статусе')
    
    return redirect('purchase_request_list')


@login_required
@transaction.atomic
def approve_request_view(request, pk):
    """Согласование заявки - после выполнения задача УДАЛЯЕТСЯ"""
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk)
    
    if request.user != purchase_request.approver and not (request.user.is_manager or request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'У вас нет прав для согласования этой заявки')
        return redirect('purchase_request_list')
    
    if purchase_request.status != 'pending':
        messages.warning(request, 'Заявка уже обработана или находится в другом статусе')
        return redirect('view_purchase_request', pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            if purchase_request.approve():
                # УДАЛЯЕМ задачу согласования после выполнения
                Task.objects.filter(
                    related_request=purchase_request,
                    executor=request.user,
                    task_type='approval',
                    state__in=['active', 'pending', 'in_progress']
                ).delete()
                
                messages.success(request, f'Заявка №{purchase_request.id} успешно согласована')
                return redirect('my_tasks')
                
        elif action == 'reject':
            if not comment:
                messages.error(request, 'При отклонении необходимо указать причину')
                return redirect('approve_request', pk=pk)
                
            if purchase_request.reject(comment):
                # УДАЛЯЕМ задачу согласования после выполнения
                Task.objects.filter(
                    related_request=purchase_request,
                    executor=request.user,
                    task_type='approval',
                    state__in=['active', 'pending', 'in_progress']
                ).delete()
                
                messages.success(request, 'Заявка отклонена')
                return redirect('my_tasks')
                
        elif action == 'revision':
            if not comment:
                messages.error(request, 'При отправке на доработку необходимо указать причину')
                return redirect('approve_request', pk=pk)
                
            if purchase_request.request_revision(comment):
                # УДАЛЯЕМ задачу согласования
                Task.objects.filter(
                    related_request=purchase_request,
                    executor=request.user,
                    task_type='approval',
                    state__in=['active', 'pending', 'in_progress']
                ).delete()
                
                # Создаем задачу на доработку для заявителя (эта останется активной у заявителя)
                Task.objects.create(
                    title=f'Доработка заявки №{purchase_request.id}',
                    description=f'Необходимо доработать заявку.\nЗамечания: {comment}\n\nНоменклатура: {purchase_request.nomenclature.name}',
                    executor=purchase_request.requester,
                    created_by=request.user,
                    state='active',
                    task_type='review',
                    related_request=purchase_request
                )
                
                messages.success(request, 'Заявка отправлена на доработку заявителю')
                return redirect('my_tasks')
    
    context = {
        'request_obj': purchase_request,
    }
    return render(request, 'purchases/approve_request.html', context)


@login_required
def delete_purchase_request(request, pk):
    purchase_request = get_object_or_404(PurchaseRequest, pk=pk)
    
    if request.user != purchase_request.requester and not (request.user.is_manager or request.user.is_staff):
        messages.error(request, 'У вас нет прав для удаления этой заявки')
        return redirect('purchase_request_list')
    
    if request.method == 'POST':
        # При удалении заявки удаляем все связанные задачи
        Task.objects.filter(related_request=purchase_request).delete()
        purchase_request.delete()
        messages.success(request, f'Заявка №{pk} успешно удалена')
        return redirect('purchase_request_list')
    
    return redirect('purchase_request_list')


@login_required
def purchase_plans_list(request):
    plans_data = PurchaseRequest.objects.values('plan_type').annotate(
        count=models.Count('id'),
        last_date=models.Max('created_at')
    ).order_by('plan_type')
    
    plans = []
    for item in plans_data:
        plan_type = item['plan_type']
        plan_display = dict(PurchaseRequest.PLAN_CHOICES).get(plan_type, plan_type)
        year = plan_type.split('_')[-1] if '_' in plan_type else '-'
        
        requesters = PurchaseRequest.objects.filter(
            plan_type=plan_type
        ).select_related('requester').values_list(
            'requester__last_name', 
            'requester__first_name', 
            'requester__middle_name'
        ).distinct()
        
        responsible_list = []
        for last, first, middle in requesters:
            name = f"{last} {first}"
            if middle:
                name += f" {middle}"
            responsible_list.append(name)
        
        responsible = ', '.join(responsible_list) if responsible_list else 'Не указан'
        
        has_planned = PurchaseRequest.objects.filter(
            plan_type=plan_type, status='planned'
        ).exists()
        has_draft = PurchaseRequest.objects.filter(
            plan_type=plan_type, status='draft'
        ).exists()
        has_completed = PurchaseRequest.objects.filter(
            plan_type=plan_type, status='completed'
        ).exists()
        
        if has_draft:
            status = 'Формируется'
        elif has_planned and not has_completed:
            status = 'Запланирован'
        elif has_completed:
            status = 'Выполняется'
        else:
            status = 'Активен'
        
        plans.append({
            'id': plan_type,
            'name': plan_display,
            'year': year,
            'responsible': responsible,
            'status': status,
            'requests_count': item['count']
        })
    
    context = {
        'plans': plans,
        'total_plans': len(plans)
    }
    return render(request, 'purchases/plans_list.html', context)


@login_required
def purchase_plan_detail(request, plan_type):
    """
    Детальная страница плана закупок
    """
    plan_name = dict(PurchaseRequest.PLAN_CHOICES).get(plan_type, plan_type)
    
    plan_requests = PurchaseRequest.objects.filter(plan_type=plan_type).select_related(
        'requester', 'nomenclature', 'approver'
    )
    
    if not plan_requests.exists():
        messages.error(request, 'План не найден')
        return redirect('purchase_plans_list')
    
    # Разделяем на согласованные и не согласованные
    approved_requests = plan_requests.filter(status='approved').order_by('-created_at')
    not_approved_requests = plan_requests.exclude(status='approved').order_by('-created_at')
    
    # Статистика
    total_positions = plan_requests.count()
    approved_count = approved_requests.count()
    pending_count = not_approved_requests.count()
    
    # Определяем статус плана
    has_pending = plan_requests.filter(status='pending').exists()
    has_draft = plan_requests.filter(status='draft').exists()
    
    if has_draft:
        plan_status = 'Формируется'
    elif has_pending:
        plan_status = 'На согласовании'
    elif approved_count > 0:
        plan_status = 'Полностью согласован' if approved_count == total_positions else 'Частично согласован'
    else:
        plan_status = 'Активен'
    
    # Получаем ответственных (уникальные заявители)
    responsible_list = User.objects.filter(
        purchase_requests__plan_type=plan_type
    ).distinct()
    
    # Получаем согласующих по плану (если назначены)
    approvers = PlanApprover.objects.filter(plan_type=plan_type).select_related('user')
    
    # Получаем историю согласования плана
    approval_history = PlanApprovalHistory.objects.filter(plan_type=plan_type).select_related('approver').order_by('-start_date')
    
    context = {
        'plan_type': plan_type,
        'plan_name': plan_name,
        'plan_requests': plan_requests,
        'approved_requests': approved_requests,
        'not_approved_requests': not_approved_requests,
        'total_positions': total_positions,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'plan_status': plan_status,
        'responsible_list': responsible_list,
        'approvers': approvers,
        'approval_history': approval_history,
    }
    
    return render(request, 'purchases/plan_detail.html', context)


@login_required
def tender_list(request):
    # Проверяем статусы конкурсов перед отображением
    check_tender_statuses()
    
    tenders = Tender.objects.all().select_related('contact_person').order_by('-created_at')
    
    # === ПОИСК ПО ДАТЕ НАЧАЛА ===
    start_date = request.GET.get('start_date')
    
    if start_date:
        try:
            from datetime import datetime
            # Парсим дату из строки
            search_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
            # Фильтруем конкурсы по дате начала (точное совпадение)
            tenders = tenders.filter(
                start_date__date=search_date
            )
        except ValueError:
            pass
    
    context = {
        'tenders': tenders,
        'total_tenders': tenders.count(),
        'start_date': start_date or '',
    }
    return render(request, 'purchases/tender_list.html', context)


@login_required
@transaction.atomic
def create_tender(request):
    approved_requests = PurchaseRequest.objects.filter(
        status='approved'
    ).select_related('nomenclature').order_by('-created_at')
    
    if request.method == 'POST':
        form = TenderForm(request.POST, request.FILES)
        item_formset = TenderItemFormSet(request.POST, request.FILES, prefix='items')
        
        if form.is_valid() and item_formset.is_valid():
            tender = form.save(commit=False)
            tender.created_by = request.user
            tender.status = 'preparation'
            tender.save()
            
            items = item_formset.save(commit=False)
            for item in items:
                item.tender = tender
                item.save()
            
            for obj in item_formset.deleted_objects:
                obj.delete()
            
            messages.success(request, f'Конкурс "{tender.name}" успешно создан')
            return redirect('tender_list')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
            context = {
                'form': form,
                'item_formset': item_formset,
                'approved_requests': approved_requests,
            }
            return render(request, 'purchases/tender_form.html', context)
    else:
        form = TenderForm()
        item_formset = TenderItemFormSet(prefix='items')
    
    context = {
        'form': form,
        'item_formset': item_formset,
        'approved_requests': approved_requests,
    }
    return render(request, 'purchases/tender_form.html', context)


@login_required
def view_tender(request, pk):
    """Просмотр деталей конкурса"""
    tender = get_object_or_404(Tender, pk=pk)
    
    # Проверяем, можно ли просматривать предложения (конкурс закрыт или завершен)
    can_view_proposals = tender.status in ['closed', 'completed']
    
    # Подсчитываем количество предложений
    proposals_count = tender.proposals.filter(is_active=True).count()
    
    # Проверяем, выбран ли победитель
    winner = None
    if hasattr(tender, 'winner'):
        winner = tender.winner
    
    context = {
        'tender': tender,
        'items': tender.items.all().select_related('purchase_request', 'purchase_request__nomenclature'),
        'can_edit': request.user.is_manager or request.user.is_staff or request.user == tender.created_by,
        'can_view_proposals': can_view_proposals,
        'proposals_count': proposals_count,
        'winner': winner,
    }
    return render(request, 'purchases/tender_detail.html', context)


@login_required
@transaction.atomic
def edit_tender(request, pk):
    """Редактирование конкурса"""
    tender = get_object_or_404(Tender, pk=pk)
    
    # Проверяем права на редактирование
    if not (request.user.is_manager or request.user.is_staff or request.user == tender.created_by):
        messages.error(request, 'У вас нет прав для редактирования этого конкурса')
        return redirect('tender_list')
    
    # Нельзя редактировать завершенные или отмененные конкурсы
    if tender.status in ['completed', 'cancelled']:
        messages.error(request, 'Нельзя редактировать завершенный или отмененный конкурс')
        return redirect('view_tender', pk=pk)
    
    # Нельзя редактировать конкурс, по которому уже отправлены задачи (начался)
    if tender.tasks_sent:
        messages.error(request, 'Нельзя редактировать конкурс, который уже начался и разослан пользователям')
        return redirect('view_tender', pk=pk)
    
    approved_requests = PurchaseRequest.objects.filter(
        status='approved'
    ).select_related('nomenclature').order_by('-created_at')
    
    if request.method == 'POST':
        form = TenderForm(request.POST, request.FILES, instance=tender)
        item_formset = TenderItemFormSet(request.POST, request.FILES, prefix='items', instance=tender)
        
        if form.is_valid() and item_formset.is_valid():
            tender = form.save()
            
            items = item_formset.save(commit=False)
            for item in items:
                item.tender = tender
                item.save()
            
            for obj in item_formset.deleted_objects:
                obj.delete()
            
            messages.success(request, f'Конкурс "{tender.name}" успешно обновлен')
            return redirect('view_tender', pk=tender.pk)
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = TenderForm(instance=tender)
        item_formset = TenderItemFormSet(prefix='items', instance=tender)
    
    context = {
        'form': form,
        'item_formset': item_formset,
        'approved_requests': approved_requests,
        'tender': tender,
        'is_edit': True,
    }
    return render(request, 'purchases/tender_form.html', context)


@login_required
@transaction.atomic
def delete_tender(request, pk):
    """Удаление конкурса"""
    tender = get_object_or_404(Tender, pk=pk)
    
    # Проверяем права на удаление
    if not (request.user.is_manager or request.user.is_staff or request.user == tender.created_by):
        messages.error(request, 'У вас нет прав для удаления этого конкурса')
        return redirect('tender_list')
    
    # Нельзя удалять конкурс, по которому уже отправлены задачи (начался)
    if tender.tasks_sent:
        messages.error(request, 'Нельзя удалить конкурс, который уже начался и разослан пользователям')
        return redirect('tender_list')
    
    if request.method == 'POST':
        tender_name = tender.name
        tender.delete()
        messages.success(request, f'Конкурс "{tender_name}" успешно удален')
        return redirect('tender_list')
    
    return redirect('tender_list')


@login_required
@transaction.atomic
def tender_proposal(request, pk):
    """Страница подачи предложения по конкурсу"""
    tender = get_object_or_404(Tender, pk=pk)
    
    # Проверяем, что конкурс активен или был активен (для просмотра старых предложений)
    if tender.status not in ['active', 'closed', 'completed']:
        messages.error(request, 'Конкурс не доступен для подачи предложений')
        return redirect('my_tasks')
    
    # Получаем или создаем предложение пользователя
    proposal, created = TenderProposal.objects.get_or_create(
        tender=tender,
        user=request.user,
        defaults={
            'validity_date': tender.submission_deadline.date(),
        }
    )
    
    # Проверяем, можно ли редактировать предложение
    can_edit = tender.is_active_for_proposals()
    
    # Получаем все позиции конкурса
    tender_items = tender.items.all().select_related('purchase_request', 'purchase_request__nomenclature')
    
    # Получаем уже введенные цены и формируем список с текущими ценами
    proposal_items_dict = {pi.tender_item_id: pi.proposed_price for pi in proposal.items.all()}
    
    items_with_prices = []
    for item in tender_items:
        items_with_prices.append({
            'item': item,
            'current_price': proposal_items_dict.get(item.id, '')
        })
    
    if request.method == 'POST' and can_edit:
        try:
            # Обновляем срок действия КП
            validity_date = request.POST.get('validity_date')
            if validity_date:
                proposal.validity_date = validity_date
            
            # Обновляем примечания
            proposal.notes = request.POST.get('notes', '')
            
            # Обрабатываем файл
            if 'attachment' in request.FILES:
                proposal.attachment = request.FILES['attachment']
            
            # Обрабатываем удаление файла
            if request.POST.get('attachment-clear'):
                proposal.attachment.delete()
                proposal.attachment = None
            
            proposal.save()
            
            # Обрабатываем цены по позициям
            for item in tender_items:
                price_key = f'price_{item.id}'
                proposed_price = request.POST.get(price_key)
                
                if proposed_price:
                    proposal_item, _ = TenderProposalItem.objects.get_or_create(
                        proposal=proposal,
                        tender_item=item,
                        defaults={'proposed_price': proposed_price}
                    )
                    if not _:
                        proposal_item.proposed_price = proposed_price
                        proposal_item.save()
            
            messages.success(request, 'Ваше предложение успешно сохранено!')
            return redirect('tender_proposal', pk=tender.pk)
            
        except Exception as e:
            messages.error(request, f'Ошибка при сохранении предложения: {str(e)}')
    
    context = {
        'tender': tender,
        'proposal': proposal,
        'items_with_prices': items_with_prices,
        'can_edit': can_edit,
        'is_new': created,
    }
    return render(request, 'purchases/tender_proposal.html', context)


@login_required
def get_material_unit(request, material_id):
    material = get_object_or_404(Material, id=material_id)
    return JsonResponse({
        'unit': material.unit,
        'unit_display': material.get_unit_display()
    })


@login_required
def my_tasks(request):
    """
    Только активные задачи. После выполнения задачи удаляются.
    Очищаем старые зависшие задачи-уведомления.
    """
    # Проверяем статусы конкурсов перед отображением задач
    check_tender_statuses()
    
    user = request.user
    
    # ОЧИСТКА: Удаляем все старые задачи-уведомления типа 'general' (которые создавались как "Ваша заявка согласована")
    Task.objects.filter(
        executor=user,
        task_type='general',
        state='active'
    ).exclude(
        title__startswith='Участие в конкурсе:'
    ).delete()
    
    # ОЧИСТКА: Удаляем задачи по удаленным заявкам (где related_request is null)
    Task.objects.filter(
        executor=user,
        related_request__isnull=True,
        task_type__in=['approval', 'review']
    ).delete()
    
    # Только активные задачи согласования, доработки и конкурсов
    active_tasks = Task.objects.filter(
        executor=user,
        state__in=['active', 'pending', 'in_progress']
    ).select_related('created_by', 'related_request').order_by('-created_at')
    
    # Добавляем информацию о конкурсе для задач по конкурсам
    tasks_with_tender = []
    for task in active_tasks:
        tender_id = None
        if task.title.startswith('Участие в конкурсе:'):
            tender_name = task.title.replace('Участие в конкурсе:', '').strip()
            try:
                tender = Tender.objects.filter(name=tender_name).first()
                if tender:
                    tender_id = tender.id
            except:
                pass
        tasks_with_tender.append({
            'task': task,
            'tender_id': tender_id
        })
    
    context = {
        'tasks_with_tender': tasks_with_tender,
        'active_count': active_tasks.count(),
    }
    return render(request, 'tasks/my_tasks.html', context)


# ==================== ФУНКЦИИ ДЛЯ ПРОСМОТРА ПРЕДЛОЖЕНИЙ И ВЫБОРА ПОБЕДИТЕЛЯ ====================

@login_required
def tender_proposals_list(request, pk):
    """
    Просмотр всех предложений по конкурсу (доступно после окончания конкурса)
    """
    tender = get_object_or_404(Tender, pk=pk)
    
    # Проверяем права доступа (только создатель, менеджер или staff)
    if not (request.user.is_manager or request.user.is_staff or request.user == tender.created_by):
        messages.error(request, 'У вас нет прав для просмотра предложений этого конкурса')
        return redirect('tender_list')
    
    # Проверяем статус конкурса (должен быть закрыт или завершен)
    if tender.status not in ['closed', 'completed']:
        messages.warning(request, 'Просмотр предложений доступен только после окончания конкурса')
        return redirect('view_tender', pk=pk)
    
    # Получаем все активные предложения с деталями
    proposals = tender.proposals.filter(is_active=True).select_related('user').prefetch_related('items', 'items__tender_item', 'items__tender_item__purchase_request')
    
    # Формируем структурированные данные для отображения
    proposals_data = []
    for proposal in proposals:
        # Получаем все позиции предложения
        items_data = []
        total_amount = Decimal('0')
        
        for item in proposal.items.all():
            item_total = item.proposed_price * item.quantity
            total_amount += item_total
            items_data.append({
                'nomenclature': item.tender_item.purchase_request.nomenclature.name,
                'quantity': item.quantity,
                'unit': item.tender_item.purchase_request.get_unit_display(),
                'proposed_price': item.proposed_price,
                'total': item_total,
            })
        
        proposals_data.append({
            'proposal': proposal,
            'items': items_data,
            'total_amount': total_amount,
        })
    
    # Сортируем по общей сумме (по возрастанию)
    proposals_data.sort(key=lambda x: x['total_amount'])
    
    # Проверяем, выбран ли уже победитель
    winner = None
    if hasattr(tender, 'winner') and tender.winner:
        winner = tender.winner
    
    context = {
        'tender': tender,
        'proposals_data': proposals_data,
        'proposals_count': len(proposals_data),
        'winner': winner,
        'can_select_winner': request.user.is_manager or request.user.is_staff or request.user == tender.created_by,
    }
    return render(request, 'purchases/tender_proposals_list.html', context)


@login_required
@transaction.atomic
def select_winner(request, pk):
    """
    Выбор победителя конкурса
    """
    tender = get_object_or_404(Tender, pk=pk)
    
    # Проверяем права доступа
    if not (request.user.is_manager or request.user.is_staff or request.user == tender.created_by):
        messages.error(request, 'У вас нет прав для выбора победителя')
        return redirect('tender_list')
    
    # Проверяем статус конкурса
    if tender.status not in ['closed', 'completed']:
        messages.error(request, 'Победитель может быть выбран только после окончания конкурса')
        return redirect('view_tender', pk=pk)
    
    if request.method == 'POST':
        proposal_id = request.POST.get('proposal_id')
        
        if not proposal_id:
            messages.error(request, 'Необходимо выбрать предложение')
            return redirect('tender_proposals_list', pk=pk)
        
        try:
            proposal = TenderProposal.objects.get(pk=proposal_id, tender=tender, is_active=True)
        except TenderProposal.DoesNotExist:
            messages.error(request, 'Выбранное предложение не найдено')
            return redirect('tender_proposals_list', pk=pk)
        
        # Удаляем старого победителя, если есть
        TenderWinner.objects.filter(tender=tender).delete()
        
        # Создаем нового победителя
        winner = TenderWinner.objects.create(
            tender=tender,
            proposal=proposal,
            user=proposal.user,
            selected_by=request.user,
            notes=request.POST.get('notes', '')
        )
        
        # Обновляем статус конкурса на "завершен"
        if tender.status != 'completed':
            tender.status = 'completed'
            tender.save(update_fields=['status'])
        
        messages.success(request, f'Победитель конкурса выбран: {proposal.user.get_full_name()}')
        return redirect('tender_proposals_list', pk=pk)
    
    return redirect('tender_proposals_list', pk=pk)


# ==================== ФУНКЦИИ УПРАВЛЕНИЯ ПОСТАВЩИКАМИ ====================

@login_required
def supplier_list(request):
    """Список поставщиков"""
    suppliers = Supplier.objects.all().order_by('-created_at')
    
    # Подсчет статистики по статусам
    status_counts = {
        'total': suppliers.count(),
        'active': suppliers.filter(status='active').count(),
        'new': suppliers.filter(status='new').count(),
        'inactive': suppliers.filter(status='inactive').count(),
        'blocked': suppliers.filter(status='blocked').count(),
    }
    
    context = {
        'suppliers': suppliers,
        'status_counts': status_counts,
    }
    return render(request, 'purchases/supplier_list.html', context)


@login_required
def view_supplier(request, pk):
    """Просмотр деталей поставщика"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    context = {
        'supplier': supplier,
        'can_edit': request.user.is_manager or request.user.is_staff,
    }
    return render(request, 'purchases/supplier_detail.html', context)


@login_required
@transaction.atomic
def create_supplier(request):
    """Создание нового поставщика"""
    if request.method == 'POST':
        form = SupplierForm(request.POST, request.FILES)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.created_by = request.user
            supplier.save()
            messages.success(request, f'Поставщик "{supplier.name}" успешно создан')
            return redirect('supplier_list')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = SupplierForm()
    
    context = {
        'form': form,
        'is_new': True,
    }
    return render(request, 'purchases/supplier_form.html', context)


@login_required
@transaction.atomic
def edit_supplier(request, pk):
    """Редактирование поставщика"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, request.FILES, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f'Поставщик "{supplier.name}" успешно обновлен')
            return redirect('view_supplier', pk=supplier.pk)
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = SupplierForm(instance=supplier)
    
    context = {
        'form': form,
        'supplier': supplier,
        'is_new': False,
    }
    return render(request, 'purchases/supplier_form.html', context)


@login_required
@transaction.atomic
def delete_supplier(request, pk):
    """Удаление поставщика"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier_name = supplier.name
        supplier.delete()
        messages.success(request, f'Поставщик "{supplier_name}" успешно удален')
        return redirect('supplier_list')
    
    return redirect('supplier_list')


# ==================== ФУНКЦИИ УПРАВЛЕНИЯ ДОГОВОРАМИ ====================

@login_required
def contract_list(request):
    """Список договоров"""
    contracts = Contract.objects.all().select_related('supplier', 'responsible', 'approver').order_by('-created_at')
    
    # Получаем доступных согласующих
    available_approvers = User.objects.filter(
        Q(is_manager=True) | Q(is_staff=True) | Q(is_superuser=True)
    ).distinct().order_by('last_name', 'first_name')
    
    is_privileged = request.user.is_manager or request.user.is_staff or request.user.is_superuser
    
    if not is_privileged:
        available_approvers = available_approvers.exclude(id=request.user.id)
    
    # Статистика по статусам
    status_counts = {
        'total': contracts.count(),
        'draft': contracts.filter(status='draft').count(),
        'pending': contracts.filter(status='pending').count(),
        'approved': contracts.filter(status='approved').count(),
        'active': contracts.filter(status='active').count(),
        'completed': contracts.filter(status='completed').count(),
        'rejected': contracts.filter(status='rejected').count(),
    }
    
    context = {
        'contracts': contracts,
        'status_counts': status_counts,
        'available_approvers': available_approvers,
        'is_privileged_user': is_privileged,
    }
    return render(request, 'purchases/contract_list.html', context)


@login_required
def view_contract(request, pk):
    """Просмотр деталей договора"""
    contract = get_object_or_404(Contract, pk=pk)
    
    is_creator = (request.user == contract.created_by)
    is_responsible = (request.user == contract.responsible)
    is_approver = (request.user == contract.approver)
    can_edit = (is_creator or is_responsible) and contract.is_editable()
    can_approve = is_approver and contract.can_be_approved()
    
    context = {
        'contract': contract,
        'can_edit': can_edit,
        'can_approve': can_approve,
        'is_creator': is_creator,
        'is_responsible': is_responsible,
        'is_approver': is_approver,
    }
    return render(request, 'purchases/contract_detail.html', context)


@login_required
@transaction.atomic
def create_contract(request):
    """Создание нового договора"""
    if request.method == 'POST':
        form = ContractForm(request.POST, request.FILES)
        
        if form.is_valid():
            contract = form.save(commit=False)
            contract.created_by = request.user
            contract.status = 'draft'
            contract.save()
            
            messages.success(request, f'Договор "{contract.name}" успешно создан')
            return redirect('view_contract', pk=contract.pk)
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = ContractForm()
        # Устанавливаем текущую дату по умолчанию
        from datetime import date
        form.initial['contract_date'] = date.today()
    
    context = {
        'form': form,
        'is_new': True,
    }
    return render(request, 'purchases/contract_form.html', context)


@login_required
@transaction.atomic
def edit_contract(request, pk):
    """Редактирование договора"""
    contract = get_object_or_404(Contract, pk=pk)
    
    # Проверяем права на редактирование
    is_creator = request.user == contract.created_by
    is_responsible = request.user == contract.responsible
    is_manager = request.user.is_manager or request.user.is_staff
    
    if not (is_creator or is_responsible or is_manager):
        messages.error(request, 'У вас нет прав для редактирования этого договора')
        return redirect('view_contract', pk=pk)
    
    # Проверяем, можно ли редактировать
    if not contract.is_editable() and not is_manager:
        messages.error(request, 'Редактирование недоступно для договоров в текущем статусе')
        return redirect('view_contract', pk=pk)
    
    if request.method == 'POST':
        form = ContractForm(request.POST, request.FILES, instance=contract)
        if form.is_valid():
            contract = form.save()
            messages.success(request, f'Договор "{contract.name}" успешно обновлен')
            return redirect('view_contract', pk=contract.pk)
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = ContractForm(instance=contract)
    
    context = {
        'form': form,
        'contract': contract,
        'is_new': False,
    }
    return render(request, 'purchases/contract_form.html', context)


@login_required
@transaction.atomic
def delete_contract(request, pk):
    """Удаление договора"""
    contract = get_object_or_404(Contract, pk=pk)
    
    # Проверяем права на удаление
    is_creator = request.user == contract.created_by
    is_manager = request.user.is_manager or request.user.is_staff
    
    if not (is_creator or is_manager):
        messages.error(request, 'У вас нет прав для удаления этого договора')
        return redirect('contract_list')
    
    if request.method == 'POST':
        contract_name = contract.name
        # Удаляем связанные задачи
        Task.objects.filter(related_contract=contract).delete()
        contract.delete()
        messages.success(request, f'Договор "{contract_name}" успешно удален')
        return redirect('contract_list')
    
    return redirect('contract_list')


@login_required
@transaction.atomic
def send_contract_for_approval(request, pk):
    """Отправка договора на согласование"""
    contract = get_object_or_404(Contract, pk=pk)
    
    # Проверяем права
    is_creator = request.user == contract.created_by
    is_responsible = request.user == contract.responsible
    
    if not (is_creator or is_responsible):
        messages.error(request, 'Вы не можете отправить этот договор на согласование')
        return redirect('contract_list')
    
    if request.method == 'POST':
        approver_id = request.POST.get('approver')
        if not approver_id:
            messages.error(request, 'Необходимо выбрать согласующего')
            return redirect('contract_list')
        
        try:
            approver = User.objects.get(pk=approver_id)
        except User.DoesNotExist:
            messages.error(request, 'Выбранный согласующий не найден')
            return redirect('contract_list')
        
        if not (approver.is_manager or approver.is_staff or approver.is_superuser):
            messages.error(request, 'Выбранный пользователь не имеет прав для согласования договоров')
            return redirect('contract_list')
        
        # Проверяем, что не отправляем самому себе (если не привилегированный пользователь)
        is_privileged = request.user.is_manager or request.user.is_staff or request.user.is_superuser
        if approver == request.user and not is_privileged:
            messages.error(request, 'Вы не можете отправить договор на согласование самому себе')
            return redirect('contract_list')
        
        # Удаляем старые задачи согласования по этому договору
        Task.objects.filter(
            related_contract=contract,
            task_type='contract_approval',
            state__in=['active', 'pending', 'in_progress']
        ).delete()
        
        if contract.send_to_approval(approver):
            # Создаем задачу для согласующего
            Task.objects.create(
                title=f'Согласование договора: {contract.name}',
                description=f'Необходимо согласовать договор.\n\n'
                           f'Название: {contract.name}\n'
                           f'Компания: {contract.supplier.name}\n'
                           f'Сумма: {contract.contract_amount:,.2f} ₽\n'
                           f'Срок действия: {contract.end_date.strftime("%d.%m.%Y")}\n'
                           f'Ответственный: {contract.responsible.get_full_name() if contract.responsible else "Не указан"}\n'
                           f'Создатель: {contract.created_by.get_full_name() if contract.created_by else "Не указан"}',
                executor=approver,
                created_by=request.user,
                state='active',
                task_type='contract_approval',
                related_contract=contract
            )
            
            messages.success(request, f'Договор "{contract.name}" отправлен на согласование пользователю {approver.get_full_name()}')
        else:
            messages.error(request, 'Невозможно отправить договор на согласование в текущем статусе')
    
    return redirect('contract_list')


@login_required
@transaction.atomic
def approve_contract_view(request, pk):
    """Страница согласования договора"""
    contract = get_object_or_404(Contract, pk=pk)
    
    # Проверяем права на согласование
    if request.user != contract.approver and not (request.user.is_manager or request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'У вас нет прав для согласования этого договора')
        return redirect('contract_list')
    
    if contract.status != 'pending':
        messages.warning(request, 'Договор уже обработан или находится в другом статусе')
        return redirect('view_contract', pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            if contract.approve():
                # Удаляем задачу согласования
                Task.objects.filter(
                    related_contract=contract,
                    task_type='contract_approval',
                    state__in=['active', 'pending', 'in_progress']
                ).delete()
                
                messages.success(request, f'Договор "{contract.name}" успешно согласован и активирован')
                return redirect('my_tasks')
                
        elif action == 'reject':
            if not comment:
                messages.error(request, 'При отклонении необходимо указать причину')
                return redirect('approve_contract', pk=pk)
            
            if contract.reject(comment):
                # Удаляем задачу согласования
                Task.objects.filter(
                    related_contract=contract,
                    task_type='contract_approval',
                    state__in=['active', 'pending', 'in_progress']
                ).delete()
                
                messages.success(request, 'Договор отклонен')
                return redirect('my_tasks')
    
    context = {
        'contract': contract,
    }
    return render(request, 'purchases/contract_approve.html', context)


# ==================== ФУНКЦИИ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ ====================

from django.contrib.auth.decorators import user_passes_test

def manager_required(view_func):
    """Декоратор для проверки, что пользователь - менеджер или администратор"""
    def check_manager(user):
        return user.is_manager or user.is_staff or user.is_superuser
    return user_passes_test(check_manager, login_url='dashboard')(view_func)


@login_required
@manager_required
def user_list(request):
    """Список пользователей (только для менеджера/администратора)"""
    # Получаем всех пользователей кроме суперпользователей (их не показываем)
    users = User.objects.all().order_by('last_name', 'first_name')
    
    context = {
        'users': users,
    }
    return render(request, 'users/user_list.html', context)


@login_required
@manager_required
@transaction.atomic
def create_supply_employee(request):
    """Создание сотрудника отдела снабжения (только для менеджера)"""
    if request.method == 'POST':
        form = SupplyEmployeeCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Сотрудник {user.get_full_name()} успешно создан')
            return redirect('user_list')
    else:
        form = SupplyEmployeeCreationForm()
    
    context = {
        'form': form,
        'is_new': True,
    }
    return render(request, 'users/user_form.html', context)


@login_required
@manager_required
@transaction.atomic
def edit_user(request, pk):
    """Редактирование пользователя (только для менеджера)"""
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Пользователь {user.get_full_name()} успешно обновлен')
            return redirect('user_list')
    else:
        form = ProfileEditForm(instance=user)
    
    context = {
        'form': form,
        'user_obj': user,
        'is_new': False,
    }
    return render(request, 'users/user_form.html', context)


@login_required
@manager_required
@transaction.atomic
def delete_user(request, pk):
    """Удаление пользователя (только для менеджера)"""
    user = get_object_or_404(User, pk=pk)
    
    # Нельзя удалить самого себя
    if user == request.user:
        messages.error(request, 'Вы не можете удалить свой собственный аккаунт')
        return redirect('user_list')
    
    # Нельзя удалить суперпользователя
    if user.is_superuser:
        messages.error(request, 'Нельзя удалить администратора')
        return redirect('user_list')
    
    if request.method == 'POST':
        user_full_name = user.get_full_name()
        user.delete()
        messages.success(request, f'Пользователь {user_full_name} успешно удален')
        return redirect('user_list')
    
    return redirect('user_list')


@login_required
@manager_required
@transaction.atomic
def reset_user_password(request, pk):
    """Сброс пароля пользователя (только для менеджера)"""
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not new_password:
            messages.error(request, 'Необходимо ввести новый пароль')
            return redirect('user_list')
        
        if new_password != confirm_password:
            messages.error(request, 'Пароли не совпадают')
            return redirect('user_list')
        
        if len(new_password) < 6:
            messages.error(request, 'Пароль должен содержать минимум 6 символов')
            return redirect('user_list')
        
        user.set_password(new_password)
        user.save()
        
        messages.success(request, f'Пароль для пользователя {user.get_full_name()} успешно изменен')
        return redirect('user_list')
    
    return redirect('user_list')