# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('profile/', views.profile_detail, name='profile_detail'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    # Закупки
    path('purchases/requests/', views.purchase_request_list, name='purchase_request_list'),
    path('purchases/requests/create/', views.create_purchase_request, name='create_purchase_request'),
    path('purchases/requests/<int:pk>/', views.view_purchase_request, name='view_purchase_request'),
    path('purchases/requests/<int:pk>/edit/', views.edit_purchase_request, name='edit_purchase_request'),
    path('purchases/requests/<int:pk>/delete/', views.delete_purchase_request, name='delete_purchase_request'),
    path('purchases/requests/<int:pk>/send-for-approval/', views.send_for_approval, name='send_for_approval'),
    path('purchases/requests/<int:pk>/approve/', views.approve_request_view, name='approve_request'),
    # Планы закупок
    path('purchases/plans/', views.purchase_plans_list, name='purchase_plans_list'),
    path('purchases/plans/<str:plan_type>/', views.purchase_plan_detail, name='purchase_plan_detail'),
    # Конкурсы
    path('purchases/tenders/', views.tender_list, name='tender_list'),
    path('purchases/tenders/create/', views.create_tender, name='create_tender'),
    path('purchases/tenders/<int:pk>/', views.view_tender, name='view_tender'),
    path('purchases/tenders/<int:pk>/edit/', views.edit_tender, name='edit_tender'),
    path('purchases/tenders/<int:pk>/delete/', views.delete_tender, name='delete_tender'),
    # Подача предложений по конкурсу
    path('purchases/tenders/<int:pk>/proposal/', views.tender_proposal, name='tender_proposal'),
    # Просмотр предложений и выбор победителя
    path('purchases/tenders/<int:pk>/proposals/', views.tender_proposals_list, name='tender_proposals_list'),
    path('purchases/tenders/<int:pk>/winner/', views.select_winner, name='select_winner'),
    # Поставщики
    path('purchases/suppliers/', views.supplier_list, name='supplier_list'),
    path('purchases/suppliers/create/', views.create_supplier, name='create_supplier'),
    path('purchases/suppliers/<int:pk>/', views.view_supplier, name='view_supplier'),
    path('purchases/suppliers/<int:pk>/edit/', views.edit_supplier, name='edit_supplier'),
    path('purchases/suppliers/<int:pk>/delete/', views.delete_supplier, name='delete_supplier'),
    # Мои задачи
    path('tasks/', views.my_tasks, name='my_tasks'),
    # AJAX
    path('api/material/<int:material_id>/unit/', views.get_material_unit, name='get_material_unit'),
    
    # ==================== ДОГОВОРЫ ====================
    path('purchases/contracts/', views.contract_list, name='contract_list'),
    path('purchases/contracts/create/', views.create_contract, name='create_contract'),
    path('purchases/contracts/<int:pk>/', views.view_contract, name='view_contract'),
    path('purchases/contracts/<int:pk>/edit/', views.edit_contract, name='edit_contract'),
    path('purchases/contracts/<int:pk>/delete/', views.delete_contract, name='delete_contract'),
    path('purchases/contracts/<int:pk>/send-for-approval/', views.send_contract_for_approval, name='send_contract_for_approval'),
    path('purchases/contracts/<int:pk>/approve/', views.approve_contract_view, name='approve_contract'),
    
    # ==================== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ (ТОЛЬКО ДЛЯ МЕНЕДЖЕРА) ====================
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.create_supply_employee, name='create_supply_employee'),
    path('users/<int:pk>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:pk>/delete/', views.delete_user, name='delete_user'),
    path('users/<int:pk>/reset-password/', views.reset_user_password, name='reset_user_password'),
]