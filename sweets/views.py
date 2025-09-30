from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.core.mail import send_mail
from .models import Produto, Categoria, Encomenda, Carrinho, ItemCarrinho, ComprovativoPagamento, Avaliacao, Reclamacao, SecureLink, ChatMessage
from django.db.models import Q, Avg
from django.utils import timezone
from datetime import timedelta

def index(request):
    if request.user.is_authenticated and request.user.username == 'ivsweets':
        return redirect('sweets:admin_dashboard')
    if not request.user.is_authenticated:
        # Página inicial básica sem login
        produtos_destaque = Produto.objects.filter(disponivel=True)[:3]  # Mostrar apenas alguns sem login
        categorias = Categoria.objects.all()
        return render(request, 'sweets/index.html', {
            'produtos_destaque': produtos_destaque,
            'categorias': categorias,
            'login_required': True  # Flag para mostrar mensagem de login
        })
    else:
        produtos_destaque = Produto.objects.filter(disponivel=True)[:6]
        categorias = Categoria.objects.all()
        return render(request, 'sweets/index.html', {'produtos_destaque': produtos_destaque, 'categorias': categorias})

@login_required
def catalogo(request):
    if request.user.username == 'ivsweets':
        return redirect('sweets:admin_dashboard')
    produtos = Produto.objects.filter(disponivel=True)
    categoria_id = request.GET.get('categoria')
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    busca = request.GET.get('busca')
    if busca:
        produtos = produtos.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca))
    categorias = Categoria.objects.all()
    return render(request, 'sweets/catalogo.html', {'produtos': produtos, 'categorias': categorias, 'busca': busca, 'categoria_selecionada': categoria_id})

@login_required
def produto_detalhe(request, id):
    if request.user.username == 'ivsweets':
        return redirect('sweets:admin_dashboard')
    produto = get_object_or_404(Produto, id=id, disponivel=True)
    avaliacoes = produto.avaliacoes.all()
    avg_rating = produto.avaliacoes.aggregate(avg=Avg('estrelas'))['avg'] or 0
    count_avaliacoes = produto.avaliacoes.count()
    user_has_rated = produto.avaliacoes.filter(usuario=request.user).exists()
    produtos_relacionados = Produto.objects.filter(categoria=produto.categoria).exclude(id=produto.id)[:4]

    # Calculate star display
    full_stars = int(avg_rating)
    has_half_star = avg_rating - full_stars >= 0.5
    empty_stars = 5 - full_stars - (1 if has_half_star else 0)

    return render(request, 'sweets/produto_detalhe.html', {
        'produto': produto,
        'avaliacoes': avaliacoes,
        'avg_rating': avg_rating,
        'count_avaliacoes': count_avaliacoes,
        'user_has_rated': user_has_rated,
        'produtos_relacionados': produtos_relacionados,
        'full_stars': range(full_stars),
        'has_half_star': has_half_star,
        'empty_stars': range(empty_stars)
    })

@login_required
@require_http_methods(["POST"])
def adicionar_avaliacao(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    estrelas = request.POST.get('estrelas')
    comentario = request.POST.get('comentario')
    if estrelas:
        avaliacao, created = Avaliacao.objects.get_or_create(
            produto=produto,
            usuario=request.user,
            defaults={'estrelas': int(estrelas), 'comentario': comentario}
        )
        if not created:
            avaliacao.estrelas = int(estrelas)
            avaliacao.comentario = comentario
            avaliacao.save()
        messages.success(request, 'Avaliação enviada com sucesso!')
    return redirect('sweets:produto_detalhe', id=produto_id)

@login_required
def carrinho(request):
    if request.user.username == 'ivsweets':
        return redirect('sweets:admin_dashboard')
    carrinho = Carrinho.objects.filter(usuario=request.user, encomendado=False).first()
    if not carrinho:
        carrinho = Carrinho.objects.create(usuario=request.user)
    itens = ItemCarrinho.objects.filter(carrinho=carrinho)
    total = sum(item.subtotal for item in itens)
    return render(request, 'sweets/carrinho.html', {'itens': itens, 'total': total, 'carrinho': carrinho})

@login_required
@require_http_methods(["POST"])
def adicionar_carrinho(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id, disponivel=True)
    carrinho = Carrinho.objects.filter(usuario=request.user, encomendado=False).first()
    if not carrinho:
        carrinho = Carrinho.objects.create(usuario=request.user)
    item, created = ItemCarrinho.objects.get_or_create(
        carrinho=carrinho, 
        produto=produto, 
        defaults={'quantidade': 1}
    )
    if not created:
        item.quantidade += 1
        item.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': f'{produto.nome} adicionado ao carrinho!'})
    messages.success(request, f'{produto.nome} adicionado ao carrinho!')
    return redirect('sweets:carrinho')

@login_required
@require_http_methods(["POST"])
def remover_carrinho(request, item_id):
    item = get_object_or_404(ItemCarrinho, id=item_id, carrinho__usuario=request.user, carrinho__encomendado=False)
    item.delete()
    messages.success(request, 'Item removido do carrinho!')
    return redirect('sweets:carrinho')

@login_required
@require_http_methods(["POST"])
def atualizar_quantidade_carrinho(request, item_id):
    item = get_object_or_404(ItemCarrinho, id=item_id, carrinho__usuario=request.user, carrinho__encomendado=False)
    quantidade = int(request.POST.get('quantidade', 1))
    if quantidade > 0:
        item.quantidade = quantidade
        item.save()
    else:
        item.delete()
    return JsonResponse({'success': True})

@login_required
def finalizar_encomenda(request):
    carrinho = Carrinho.objects.filter(usuario=request.user, encomendado=False).first()
    if not carrinho or not carrinho.itens.exists():
        messages.error(request, 'Carrinho vazio!')
        return redirect('sweets:carrinho')

    if request.method == 'POST':
        # Check if payment fields are present (combined form submission)
        metodo_pagamento = request.POST.get('metodo_pagamento')
        numero_referencia = request.POST.get('numero_referencia')
        comprovativo_file = request.FILES.get('comprovativo')

        # Process the order finalization
        descricao = request.POST.get('descricao', '')
        data_recepcao = request.POST.get('data_recepcao')
        data_recepcao_obj = timezone.datetime.strptime(data_recepcao, '%Y-%m-%d').date() if data_recepcao else None

        encomenda = Encomenda.objects.create(
            usuario=request.user,
            total=carrinho.total,
            descricao_encomenda=descricao,
            imagem_referencia_1=request.FILES.get('imagem_referencia_1'),
            imagem_referencia_2=request.FILES.get('imagem_referencia_2'),
            data_recepcao=data_recepcao_obj
        )
        encomenda.itens.set(carrinho.itens.all())
        carrinho.encomendado = True
        carrinho.save()

        # If payment information is provided, process it
        if metodo_pagamento and numero_referencia and comprovativo_file:
            ComprovativoPagamento.objects.create(
                encomenda=encomenda,
                usuario=request.user,
                metodo_pagamento=metodo_pagamento,
                numero_referencia=numero_referencia,
                valor=encomenda.total,
                comprovativo=comprovativo_file,
                observacoes=request.POST.get('observacoes', '')
            )
            messages.success(request, 'Encomenda e comprovativo de pagamento enviados! Aguarde aprovação.')
            return redirect('sweets:minhas_encomendas')
        else:
            # If no payment info, redirect to payment page (legacy behavior)
            messages.success(request, 'Encomenda finalizada! Prossiga para o pagamento.')
            return redirect('sweets:efetuar_pagamento', encomenda_id=encomenda.id)
    else:
        # Show the finalization form
        itens = ItemCarrinho.objects.filter(carrinho=carrinho)
        total = sum(item.subtotal for item in itens)
        return render(request, 'sweets/finalizar_encomenda.html', {
            'itens': itens,
            'total': total,
            'carrinho': carrinho
        })

@login_required
def efetuar_pagamento(request, encomenda_id):
    encomenda = get_object_or_404(Encomenda, id=encomenda_id, usuario=request.user, status='pendente')
    if request.method == 'POST':
        metodo = request.POST.get('metodo_pagamento')
        numero_referencia = request.POST.get('numero_referencia')
        observacoes = request.POST.get('observacoes')
        comprovativo_file = request.FILES.get('comprovativo')
        if metodo and numero_referencia and comprovativo_file:
            ComprovativoPagamento.objects.create(
                encomenda=encomenda,
                usuario=request.user,
                metodo_pagamento=metodo,
                numero_referencia=numero_referencia,
                valor=encomenda.total,
                comprovativo=comprovativo_file,
                observacoes=observacoes
            )
            messages.success(request, 'Comprovativo de pagamento enviado! Aguarde aprovação.')
            return redirect('sweets:minhas_encomendas')
        else:
            messages.error(request, 'Preencha todos os campos corretamente.')
    return render(request, 'sweets/efetuar_pagamento.html', {'encomenda': encomenda})

@login_required
def minhas_encomendas(request):
    if request.user.username == 'ivsweets':
        return redirect('sweets:admin_dashboard')
    encomendas = Encomenda.objects.filter(usuario=request.user).order_by('-created_at')
    return render(request, 'sweets/minhas_encomendas.html', {'encomendas': encomendas})

@login_required
def encomenda_detalhe(request, id):
    encomenda = get_object_or_404(Encomenda, id=id, usuario=request.user)
    comprovativos = ComprovativoPagamento.objects.filter(encomenda=encomenda)
    return render(request, 'sweets/encomenda_detalhe.html', {'encomenda': encomenda, 'comprovativos': comprovativos})



def sobre_nos(request):
    if request.user.is_authenticated and request.user.username == 'ivsweets':
        return redirect('sweets:admin_dashboard')
    return render(request, 'sweets/sobre_nos.html')

def pagamentos(request):
    if request.user.is_authenticated and request.user.username == 'ivsweets':
        return redirect('sweets:admin_dashboard')
    return render(request, 'sweets/pagamentos_atualizado.html')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Conta criada com sucesso para {username}! Faça login para continuar.')
            return redirect('sweets:login')
    else:
        form = UserCreationForm()
        form.fields['username'].help_text = ""
        form.fields['password1'].help_text = ""
        form.fields['password2'].help_text = ""
    return render(request, 'sweets/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Verificar se é admin
            if username == 'ivsweets' and password == 'Naite2025':
                return redirect('sweets:admin_dashboard')
            else:
                return redirect('sweets:index')
        else:
            messages.error(request, 'Credenciais inválidas. Tente novamente.')
    return render(request, 'sweets/login.html')

def admin_login_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.username == 'ivsweets' and user.check_password('Naite2025'):
            login(request, user)
            return redirect('sweets:admin_dashboard')
        else:
            messages.error(request, 'Credenciais inválidas para acesso restrito.')
    return render(request, 'sweets/admin_login.html')

@login_required
def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'Logout realizado com sucesso!')
    return redirect(reverse('sweets:index'))

# Admin Views
def admin_dashboard(request):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        messages.error(request, 'Acesso negado. Credenciais de admin inválidas.')
        return redirect('sweets:index')
    total_produtos = Produto.objects.count()
    total_encomendas = Encomenda.objects.count()
    total_clientes = User.objects.exclude(username='ivsweets').count()
    comprovativos_pendentes = ComprovativoPagamento.objects.filter(status='pendente').count()
    total_avaliacoes = Avaliacao.objects.count()
    encomendas_recentes = Encomenda.objects.order_by('-created_at')[:5]
    categorias = Categoria.objects.all()
    return render(request, 'sweets/admin_dashboard.html', {
        'total_produtos': total_produtos,
        'total_encomendas': total_encomendas,
        'total_clientes': total_clientes,
        'comprovativos_pendentes': comprovativos_pendentes,
        'total_avaliacoes': total_avaliacoes,
        'encomendas_recentes': encomendas_recentes,
        'categorias': categorias
    })

def admin_produtos(request):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return redirect('sweets:index')
    if request.method == 'POST':
        if 'remover' in request.POST:
            # Remover produto
            produto_id = request.POST.get('produto_id')
            if produto_id:
                produto = get_object_or_404(Produto, id=produto_id)
                nome_produto = produto.nome
                produto.delete()
                messages.success(request, f'Produto {nome_produto} removido com sucesso!')
        elif 'adicionar_categoria' in request.POST:
            # Adicionar nova categoria
            nome_categoria = request.POST.get('nome_categoria')
            descricao_categoria = request.POST.get('descricao_categoria')
            if nome_categoria:
                categoria = Categoria.objects.create(
                    nome=nome_categoria,
                    descricao=descricao_categoria
                )
                messages.success(request, f'Categoria {categoria.nome} adicionada com sucesso!')
        else:
            # Adicionar novo produto
            nome = request.POST.get('nome')
            descricao = request.POST.get('descricao')
            preco = request.POST.get('preco')
            categoria_id = request.POST.get('categoria')
            imagem = request.FILES.get('imagem')
            disponivel = request.POST.get('disponivel') == 'True'
            if nome and descricao and preco and categoria_id:
                categoria = get_object_or_404(Categoria, id=categoria_id)
                produto = Produto.objects.create(
                    nome=nome,
                    descricao=descricao,
                    preco=float(preco),
                    categoria=categoria,
                    imagem=imagem,
                    disponivel=disponivel
                )
                messages.success(request, f'Produto {produto.nome} adicionado com sucesso!')
    produtos = Produto.objects.all()
    categorias = Categoria.objects.all()
    return render(request, 'sweets/admin_produtos.html', {'produtos': produtos, 'categorias': categorias})

def admin_produto_editar(request, id):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return redirect('sweets:index')
    produto = get_object_or_404(Produto, id=id)
    if request.method == 'POST':
        produto.nome = request.POST.get('nome')
        produto.descricao = request.POST.get('descricao')
        produto.preco = float(request.POST.get('preco'))
        produto.categoria_id = request.POST.get('categoria')
        if request.FILES.get('imagem'):
            produto.imagem = request.FILES['imagem']
        produto.save()
        messages.success(request, 'Produto atualizado com sucesso!')
        return redirect('sweets:admin_produtos')
    categorias = Categoria.objects.all()
    return render(request, 'sweets/admin_produto_editar.html', {'produto': produto, 'categorias': categorias})

def admin_encomendas(request):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return redirect('sweets:index')
    if request.method == 'POST':
        encomenda_id = request.POST.get('encomenda_id')
        action = request.POST.get('action')
        encomenda = get_object_or_404(Encomenda, id=encomenda_id)
        if action == 'aprovar_pagamento':
            comprovativo = ComprovativoPagamento.objects.filter(encomenda=encomenda).first()
            if comprovativo:
                comprovativo.status = 'aprovado'
                comprovativo.processado_por = request.user
                comprovativo.processado_em = timezone.now()
                comprovativo.save()
                encomenda.paga = True
                encomenda.save()
                messages.success(request, f'Pagamento da encomenda {encomenda_id} aprovado!')
            else:
                messages.error(request, 'Nenhum comprovativo encontrado para esta encomenda.')
        elif action == 'rejeitar_pagamento':
            comprovativo = ComprovativoPagamento.objects.filter(encomenda=encomenda).first()
            if comprovativo:
                comprovativo.status = 'rejeitado'
                comprovativo.processado_por = request.user
                comprovativo.processado_em = timezone.now()
                comprovativo.save()
                messages.success(request, f'Pagamento da encomenda {encomenda_id} rejeitado!')
            else:
                messages.error(request, 'Nenhum comprovativo encontrado para esta encomenda.')
        elif action == 'marcar_entregue':
            encomenda.entregue = True
            encomenda.save()
            messages.success(request, f'Encomenda {encomenda_id} marcada como entregue!')
        elif action == 'update_status':
            status = request.POST.get('status')
            if status in dict(Encomenda.STATUS_CHOICES):
                encomenda.status = status
                encomenda.save()
                messages.success(request, f'Status da encomenda atualizado para {status}!')
    encomendas = Encomenda.objects.all().order_by('-created_at')
    return render(request, 'sweets/admin_encomendas.html', {'encomendas': encomendas})

def admin_encomenda_detalhe(request, id):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return redirect('sweets:index')
    encomenda = get_object_or_404(Encomenda, id=id)
    if request.method == 'POST' and request.POST.get('action') == 'generate_link':
        link, created = SecureLink.objects.get_or_create(
            encomenda=encomenda, 
            defaults={'expires_at': timezone.now() + timezone.timedelta(days=7)}
        )
        if not created:
            link.expires_at = timezone.now() + timezone.timedelta(days=7)
            link.save()
        share_url = request.build_absolute_uri(reverse('sweets:secure_order_view', args=[str(link.token)]))
        messages.success(request, f'Link seguro gerado: {share_url}')
    secure_links = SecureLink.objects.filter(encomenda=encomenda)
    comprovativos = ComprovativoPagamento.objects.filter(encomenda=encomenda)
    if request.method == 'POST' and 'comprovativo_id' in request.POST:
        comprovativo_id = request.POST.get('comprovativo_id')
        action = request.POST.get('action')
        comprovativo = get_object_or_404(ComprovativoPagamento, id=comprovativo_id)
        if action == 'aprovar':
            comprovativo.status = 'aprovado'
            comprovativo.processado_por = request.user
            comprovativo.processado_em = timezone.now()
            comprovativo.save()
            encomenda.status = 'confirmada'
            encomenda.save()
            messages.success(request, 'Comprovativo aprovado e encomenda confirmada!')
        elif action == 'rejeitar':
            comprovativo.status = 'rejeitado'
            comprovativo.processado_por = request.user
            comprovativo.processado_em = timezone.now()
            comprovativo.save()
            messages.success(request, 'Comprovativo rejeitado!')
    return render(request, 'sweets/admin_encomenda_detalhe.html', {
        'encomenda': encomenda, 
        'secure_links': secure_links,
        'comprovativos': comprovativos
    })



def admin_clientes(request):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return redirect('sweets:index')
    clientes = User.objects.exclude(username='ivsweets').order_by('-date_joined')
    total_clientes = clientes.count()
    total_clientes_ativos = User.objects.exclude(username='ivsweets').filter(
        encomenda__created_at__gte=timezone.now() - timezone.timedelta(days=30)
    ).distinct().count()  # Clientes com encomendas nos últimos 30 dias
    online_users = User.objects.exclude(username='ivsweets').filter(last_login__gte=timezone.now() - timedelta(minutes=5))
    total_visitors = User.objects.exclude(username='ivsweets').count()
    # Atividades: encomendas por cliente
    for cliente in clientes:
        cliente.is_online = cliente in online_users
        cliente.encomendas_count = Encomenda.objects.filter(usuario=cliente).count()
        cliente.avaliacoes_count = Avaliacao.objects.filter(usuario=cliente).count()
        ultima_encomenda = Encomenda.objects.filter(usuario=cliente).order_by('-created_at').first()
        cliente.ultima_atividade = ultima_encomenda.created_at if ultima_encomenda else cliente.date_joined
        if cliente.avaliacoes_count > 0:
            total_estrelas = sum(Avaliacao.objects.filter(usuario=cliente).values_list('estrelas', flat=True))
            cliente.media_estrelas = round(total_estrelas / cliente.avaliacoes_count, 1)
        else:
            cliente.media_estrelas = 0
    return render(request, 'sweets/admin_clientes.html', {
        'clientes': clientes,
        'total_clientes': total_clientes,
        'total_clientes_ativos': total_clientes_ativos,
        'total_visitors': total_visitors
    })

def admin_avaliacoes(request):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return redirect('sweets:index')
    avaliacoes = Avaliacao.objects.all().order_by('-criado_em')
    return render(request, 'sweets/admin_avaliacoes.html', {'avaliacoes': avaliacoes})

def admin_comprovativos(request):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return redirect('sweets:index')
    if request.method == 'POST':
        comprovativo_id = request.POST.get('comprovativo_id')
        action = request.POST.get('action')
        comprovativo = get_object_or_404(ComprovativoPagamento, id=comprovativo_id)
        if action == 'aprovar':
            comprovativo.status = 'aprovado'
            comprovativo.processado_por = request.user
            comprovativo.processado_em = timezone.now()
            comprovativo.save()
            encomenda = comprovativo.encomenda
            encomenda.paga = True
            encomenda.save()
            messages.success(request, 'Comprovativo aprovado!')
        elif action == 'rejeitar':
            motivo = request.POST.get('motivo_rejeicao')
            comprovativo.status = 'rejeitado'
            comprovativo.motivo_rejeicao = motivo
            comprovativo.processado_por = request.user
            comprovativo.processado_em = timezone.now()
            comprovativo.save()
            messages.success(request, 'Comprovativo rejeitado!')
        return redirect('sweets:admin_comprovativos')
    comprovativos = ComprovativoPagamento.objects.select_related('encomenda__usuario', 'usuario').all().order_by('-enviado_em')
    return render(request, 'sweets/admin_comprovativos.html', {'comprovativos': comprovativos})

def secure_order_view(request, token):
    try:
        link = SecureLink.objects.get(token=token)
        if not link.is_valid():
            messages.error(request, 'Link expirado.')
            return redirect('sweets:index')
        encomenda = link.encomenda
        return render(request, 'sweets/secure_link_share.html', {'encomenda': encomenda})
    except SecureLink.DoesNotExist:
        messages.error(request, 'Link inválido.')
        return redirect('sweets:index')


from django.forms import Form, CharField
from django.db.models import Q

@login_required
def user_chat(request):
    if request.user.username == 'ivsweets':
        return redirect('sweets:admin_dashboard')
    try:
        admin = User.objects.get(username='ivsweets')
    except User.DoesNotExist:
        messages.error(request, 'Admin não encontrado.')
        return redirect('sweets:index')

    mensagens = ChatMessage.objects.filter(
        Q(sender=request.user, recipient=admin) | Q(sender=admin, recipient=request.user)
    ).order_by('timestamp')

    # Marcar mensagens do admin como lidas
    mensagens.filter(sender=admin, recipient=request.user, is_read=False).update(is_read=True)

    if request.method == 'POST':
        mensagem = request.POST.get('message')
        attachment = request.FILES.get('attachment')

        if mensagem.strip() or attachment:
            ChatMessage.objects.create(
                sender=request.user,
                recipient=admin,
                message=mensagem.strip() if mensagem else None,
                attachment=attachment
            )
            messages.success(request, 'Mensagem enviada!')
            return redirect('sweets:user_chat')
        else:
            messages.error(request, 'Digite uma mensagem ou selecione um arquivo.')

    return render(request, 'sweets/chat.html', {
        'mensagens': mensagens,
        'admin': admin,
        'is_user': True
    })

@login_required
@require_http_methods(["POST"])
def send_message_user(request):
    if request.user.username == 'ivsweets':
        return redirect('sweets:admin_dashboard')
    try:
        admin = User.objects.get(username='ivsweets')
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Admin não encontrado.'})

    mensagem = request.POST.get('message')
    attachment = request.FILES.get('attachment')

    if mensagem.strip() or attachment:
        ChatMessage.objects.create(
            sender=request.user,
            recipient=admin,
            message=mensagem.strip() if mensagem else None,
            attachment=attachment
        )
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Mensagem vazia.'})

def admin_chats(request):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return redirect('sweets:index')
    
    # Usuários com mensagens não lidas ou recentes
    nao_lidas = ChatMessage.objects.filter(
        recipient=request.user, is_read=False
    ).values_list('sender_id', flat=True).distinct()
    
    todas_conversas = ChatMessage.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).values_list('sender_id', 'recipient_id').distinct()
    
    user_ids = set(nao_lidas)
    for sender_id, recipient_id in todas_conversas:
        if sender_id != request.user.id:
            user_ids.add(sender_id)
        if recipient_id != request.user.id:
            user_ids.add(recipient_id)
    
    usuarios = User.objects.filter(id__in=user_ids).exclude(username='ivsweets').order_by('-last_login')
    
    # Contar não lidas por usuário
    for usuario in usuarios:
        nao_lidas_count = ChatMessage.objects.filter(
            sender=usuario, recipient=request.user, is_read=False
        ).count()
        usuario.nao_lidas_count = nao_lidas_count
    
    return render(request, 'sweets/admin_chats.html', {'usuarios': usuarios})

def admin_chat_with_user(request, user_id):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return redirect('sweets:index')
    
    user = get_object_or_404(User, id=user_id)
    admin = request.user
    
    mensagens = ChatMessage.objects.filter(
        Q(sender=user, recipient=admin) | Q(sender=admin, recipient=user)
    ).order_by('timestamp')
    
    # Marcar mensagens do user como lidas
    mensagens.filter(sender=user, recipient=admin, is_read=False).update(is_read=True)
    
    if request.method == 'POST':
        mensagem = request.POST.get('message')
        attachment = request.FILES.get('attachment')

        if mensagem.strip() or attachment:
            ChatMessage.objects.create(
                sender=admin,
                recipient=user,
                message=mensagem.strip() if mensagem else None,
                attachment=attachment
            )
            messages.success(request, 'Mensagem enviada!')
            return redirect('sweets:admin_chat_with_user', user_id=user_id)
        else:
            messages.error(request, 'Digite uma mensagem ou selecione um arquivo.')
    
    return render(request, 'sweets/admin_chat.html', {
        'mensagens': mensagens,
        'user': user,
        'admin': admin,
        'is_admin': True
    })

@require_http_methods(["POST"])
def send_message_admin(request, user_id):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return JsonResponse({'success': False, 'error': 'Acesso negado.'})

    user = get_object_or_404(User, id=user_id)
    mensagem = request.POST.get('message')
    attachment = request.FILES.get('attachment')

    if mensagem.strip() or attachment:
        ChatMessage.objects.create(
            sender=request.user,
            recipient=user,
            message=mensagem.strip() if mensagem else None,
            attachment=attachment
        )
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Mensagem vazia.'})

@login_required
@require_http_methods(["POST"])
def delete_chat(request, user_id):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return JsonResponse({'success': False, 'error': 'Acesso negado.'})

    user = get_object_or_404(User, id=user_id)
    admin = request.user

    # Delete all messages between admin and this user
    ChatMessage.objects.filter(
        Q(sender=user, recipient=admin) | Q(sender=admin, recipient=user)
    ).delete()

    messages.success(request, f'Conversa com {user.username} foi deletada com sucesso!')
    return redirect('sweets:admin_chats')

def admin_reclamacoes(request):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return redirect('sweets:index')
    reclamacoes = Reclamacao.objects.all().order_by('-data_criacao')
    return render(request, 'sweets/admin_reclamacoes.html', {'reclamacoes': reclamacoes})

def admin_reclamacao_detalhe(request, id):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return redirect('sweets:index')
    reclamacao = get_object_or_404(Reclamacao, id=id)
    return render(request, 'sweets/admin_reclamacao_detalhe.html', {'reclamacao': reclamacao})

def admin_responder_reclamacao(request, id):
    if not (request.user.username == 'ivsweets' and request.user.check_password('Naite2025')):
        return redirect('sweets:index')
    reclamacao = get_object_or_404(Reclamacao, id=id)
    if request.method == 'POST':
        resposta = request.POST.get('resposta')
        if resposta:
            reclamacao.resposta = resposta
            reclamacao.respondida_por = request.user
            reclamacao.respondida_em = timezone.now()
            reclamacao.save()
            messages.success(request, 'Resposta enviada com sucesso!')
            return redirect('sweets:admin_reclamacao_detalhe', id=id)
        else:
            messages.error(request, 'Por favor, escreva uma resposta.')
    return render(request, 'sweets/admin_responder_reclamacao.html', {'reclamacao': reclamacao})

