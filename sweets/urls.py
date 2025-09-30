from django.urls import path
from . import views

app_name = 'sweets'

urlpatterns = [
    # User views
    path('', views.index, name='index'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('produto/<int:id>/', views.produto_detalhe, name='produto_detalhe'),
    path('produto/<int:produto_id>/avaliar/', views.adicionar_avaliacao, name='adicionar_avaliacao'),
    path('carrinho/', views.carrinho, name='carrinho'),
    path('carrinho/adicionar/<int:produto_id>/', views.adicionar_carrinho, name='adicionar_carrinho'),
    path('carrinho/remover/<int:item_id>/', views.remover_carrinho, name='remover_carrinho'),
    path('carrinho/atualizar/<int:item_id>/', views.atualizar_quantidade_carrinho, name='atualizar_quantidade_carrinho'),
    path('finalizar-encomenda/', views.finalizar_encomenda, name='finalizar_encomenda'),
    path('pagamento/<int:encomenda_id>/', views.efetuar_pagamento, name='efetuar_pagamento'),
    path('minhas-encomendas/', views.minhas_encomendas, name='minhas_encomendas'),
    path('encomenda/<int:id>/', views.encomenda_detalhe, name='encomenda_detalhe'),
    path('sobre-nos/', views.sobre_nos, name='sobre_nos'),
    path('pagamentos/', views.pagamentos, name='pagamentos'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-login/', views.admin_login_page, name='admin_login'),

    # Admin views
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/produtos/', views.admin_produtos, name='admin_produtos'),
    path('admin/produto/editar/<int:id>/', views.admin_produto_editar, name='admin_produto_editar'),
    path('admin/encomendas/', views.admin_encomendas, name='admin_encomendas'),
    path('admin/encomenda/<int:id>/', views.admin_encomenda_detalhe, name='admin_encomenda_detalhe'),
    path('admin/clientes/', views.admin_clientes, name='admin_clientes'),
    path('admin/avaliacoes/', views.admin_avaliacoes, name='admin_avaliacoes'),
    path('admin/comprovativos/', views.admin_comprovativos, name='admin_comprovativos'),
    path('admin/reclamacoes/', views.admin_reclamacoes, name='admin_reclamacoes'),
    path('admin/reclamacao/<int:id>/', views.admin_reclamacao_detalhe, name='admin_reclamacao_detalhe'),
    path('admin/reclamacao/<int:id>/responder/', views.admin_responder_reclamacao, name='admin_responder_reclamacao'),
    path('secure-order/<uuid:token>/', views.secure_order_view, name='secure_order_view'),

    # Chat views
    path('chat/', views.user_chat, name='user_chat'),
    path('chat/send/', views.send_message_user, name='send_message_user'),
    path('admin/chats/', views.admin_chats, name='admin_chats'),
    path('admin/chat/<int:user_id>/', views.admin_chat_with_user, name='admin_chat_with_user'),
    path('admin/chat/<int:user_id>/send/', views.send_message_admin, name='send_message_admin'),
    path('admin/chat/<int:user_id>/delete/', views.delete_chat, name='delete_chat'),
]
