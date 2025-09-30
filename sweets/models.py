from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone

class Categoria(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome da Categoria")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

class Produto(models.Model):
    nome = models.CharField(max_length=200, verbose_name="Nome do Produto")
    descricao = models.TextField(verbose_name="Descrição")
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True, verbose_name="Imagem")
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, verbose_name="Categoria")
    disponivel = models.BooleanField(default=True, verbose_name="Disponível")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

class Avaliacao(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='avaliacoes', verbose_name="Produto")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuário")
    estrelas = models.PositiveSmallIntegerField(verbose_name="Estrelas")
    comentario = models.TextField(blank=True, null=True, verbose_name="Comentário")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    def __str__(self):
        return f"{self.estrelas} estrelas para {self.produto.nome} por {self.usuario.username}"

    class Meta:
        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"

class Reclamacao(models.Model):
    STATUS_CHOICES = [
        ('nova', 'Nova'),
        ('lida', 'Lida'),
        ('respondida', 'Respondida'),
        ('resolvida', 'Resolvida'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Cliente")
    assunto = models.CharField(max_length=200, verbose_name="Assunto")
    mensagem = models.TextField(verbose_name="Mensagem")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='nova', verbose_name="Status")
    resposta = models.TextField(blank=True, null=True, verbose_name="Resposta do Admin")
    respondida_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reclamacoes_respondidas', verbose_name="Respondida por")
    respondida_em = models.DateTimeField(null=True, blank=True, verbose_name="Respondida em")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    def __str__(self):
        return f"Reclamação: {self.assunto}"

    class Meta:
        verbose_name = "Reclamação"
        verbose_name_plural = "Reclamações"

class Carrinho(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuário")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    encomendado = models.BooleanField(default=False, verbose_name="Encomendado")

    def __str__(self):
        return f"Carrinho de {self.usuario.username}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.itens.all())

    class Meta:
        verbose_name = "Carrinho"
        verbose_name_plural = "Carrinhos"

class ItemCarrinho(models.Model):
    carrinho = models.ForeignKey(Carrinho, on_delete=models.CASCADE, related_name='itens', verbose_name="Carrinho")
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, verbose_name="Produto")
    quantidade = models.PositiveIntegerField(default=1, verbose_name="Quantidade")

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"

    @property
    def subtotal(self):
        return self.quantidade * self.produto.preco

    class Meta:
        verbose_name = "Item do Carrinho"
        verbose_name_plural = "Itens do Carrinho"

class Encomenda(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('confirmada', 'Confirmada'),
        ('em_preparo', 'Em Preparo'),
        ('pronta', 'Pronta'),
        ('entregue', 'Entregue'),
        ('cancelada', 'Cancelada'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Cliente")
    itens = models.ManyToManyField(ItemCarrinho, verbose_name="Itens")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', verbose_name="Status")
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total")
    descricao_encomenda = models.TextField(blank=True, null=True, verbose_name="Descrição da Encomenda")
    imagem_referencia_1 = models.ImageField(upload_to='encomendas/referencias/', blank=True, null=True, verbose_name="Imagem de Referência 1")
    imagem_referencia_2 = models.ImageField(upload_to='encomendas/referencias/', blank=True, null=True, verbose_name="Imagem de Referência 2")
    data_recepcao = models.DateField(blank=True, null=True, verbose_name="Data de Recepção")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    def __str__(self):
        return f"Encomenda #{self.id} - {self.usuario.username}"

    class Meta:
        verbose_name = "Encomenda"
        verbose_name_plural = "Encomendas"



class ComprovativoPagamento(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]

    METODO_PAGAMENTO_CHOICES = [
        ('emola', 'E-MOLA'),
        ('mpesa', 'M-PESA'),
        ('bim', 'BIM'),
    ]

    encomenda = models.ForeignKey(Encomenda, on_delete=models.CASCADE, verbose_name="Encomenda")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Cliente")
    metodo_pagamento = models.CharField(max_length=20, choices=METODO_PAGAMENTO_CHOICES, verbose_name="Método de Pagamento")
    numero_referencia = models.CharField(max_length=50, verbose_name="Número de Referência")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor")
    comprovativo = models.ImageField(upload_to='comprovativos/', verbose_name="Comprovativo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', verbose_name="Status")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    enviado_em = models.DateTimeField(auto_now_add=True, verbose_name="Enviado em")
    processado_em = models.DateTimeField(null=True, blank=True, verbose_name="Processado em")
    processado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='comprovativos_processados', verbose_name="Processado por")

    def __str__(self):
        return f"Comprovativo #{self.id} - {self.encomenda.id} - {self.metodo_pagamento}"

    class Meta:
        verbose_name = "Comprovativo de Pagamento"
        verbose_name_plural = "Comprovativos de Pagamento"

class SecureLink(models.Model):
    encomenda = models.ForeignKey(Encomenda, on_delete=models.CASCADE, related_name='secure_links', verbose_name="Encomenda", null=True, blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        if self.expires_at:
            return timezone.now() < self.expires_at
        return True

    def __str__(self):
        return str(self.token)

    class Meta:
        verbose_name = "Link Seguro"
        verbose_name_plural = "Links Seguros"


class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name="Remetente")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', verbose_name="Destinatário")
    message = models.TextField(blank=True, null=True, verbose_name="Mensagem")
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True, verbose_name="Anexo")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Timestamp")
    is_read = models.BooleanField(default=False, verbose_name="Lida")

    def __str__(self):
        if self.message:
            return f"{self.sender.username} para {self.recipient.username}: {self.message[:50]}"
        elif self.attachment:
            return f"{self.sender.username} para {self.recipient.username}: [Anexo] {self.attachment.name.split('/')[-1]}"
        else:
            return f"{self.sender.username} para {self.recipient.username}: [Mensagem vazia]"

    class Meta:
        ordering = ['timestamp']
        verbose_name = "Mensagem de Chat"
        verbose_name_plural = "Mensagens de Chat"
