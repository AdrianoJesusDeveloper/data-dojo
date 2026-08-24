# Manual do Data Driven Dojô

## 3DStore — catálogo, produtos e operação

A **3DStore** é a loja pública do Data Driven Dojô. Ela foi projetada para comercializar produtos do ecossistema do Dojô e, futuramente, serviços da agência de marketing digital.

### Filosofia 3D

**Determinação · Disciplina · Direção**

---

## 1. Acesso público

A 3DStore é pública. O visitante pode abrir `/store` sem estar autenticado.

Também são públicas:

- `/`
- `/store`
- `/conheca-sensey`
- `/ai-sales`
- `/portfolio`
- `/login`
- `/register`

As demais áreas da plataforma continuam protegidas por autenticação.

---

## 2. Como inserir produtos

Os produtos são administrados pelo **Django Admin**.

### Acesso

Abra:

`https://data-dojo.onrender.com/admin/`

Entre com uma conta de administrador/superusuário.

No painel **3DStore**, você encontrará:

- Categories
- Products
- Orders

### 2.1 Criar uma categoria

1. Entre em **Categories**.
2. Clique em **Add Category**.
3. Preencha `Name`.
4. O `Slug` deve ser único. Exemplo: `ebooks-guias`.
5. Preencha `Description`, se necessário.
6. Deixe `Active` marcado para disponibilizar a categoria.
7. Salve.

Categorias iniciais previstas:

- E-books & Guias
- Templates & Dados
- IA & Automação

Você pode criar outras, por exemplo:

- Cursos
- Mentorias
- Comunidade
- Produtos Físicos
- Serviços

### 2.2 Criar um produto

1. Entre em **Products**.
2. Clique em **Add Product**.
3. Selecione a categoria.
4. Informe o nome comercial.
5. Defina o `Slug` único.
6. Escreva uma descrição curta em `Short description`.
7. Escreva a descrição completa em `Description`.
8. Escolha o tipo:
   - `Digital` — e-book, template, dataset, curso ou outro conteúdo digital.
   - `Physical` — camiseta, caneca, adesivo etc.
   - `Service` — mentoria, consultoria, pacote de marketing etc.
9. Informe o `Price` em reais.
10. Se houver preço anterior, informe `Compare at price`.
11. Informe a URL da imagem em `Image URL`.
12. Para produtos digitais, informe posteriormente a URL protegida de entrega em `Digital URL`.
13. Marque `Active` para publicar.
14. Marque `Featured` para destacar o produto.
15. Salve.

### Exemplo

```text
Name: Fundamentos de Python para Dados
Slug: fundamentos-python-dados
Category: E-books & Guias
Product type: Digital
Price: 39.90
Compare at price: 59.90
Short description: Guia prático para dominar os fundamentos de Python aplicados a Dados.
Image URL: https://...
Digital URL: https://...
Active: Sim
Featured: Sim
```

> **Importante:** não coloque arquivos privados, tokens, chaves de API ou links de download irrestritos em `Digital URL`. A entrega protegida deve ser implementada antes de vender conteúdo pago.

---

## 3. Estado atual da loja

A primeira versão já possui a base de catálogo no Django:

```text
Category
Product
Order
OrderItem
```

A API pública do catálogo está em:

```text
/api/store/categories/
/api/store/products/
```

O frontend atual da 3DStore já apresenta a identidade visual, filosofia 3D e catálogo inicial, mas os botões de compra ainda são placeholders de **Em breve**.

---

## 4. Próxima evolução obrigatória: comércio completo

A loja deve evoluir para este fluxo:

```text
Visitante
   ↓
3DStore pública
   ↓
Catálogo
   ↓
Produto
   ↓
Adicionar ao carrinho
   ↓
Carrinho
   ↓
Checkout
   ↓
Pagamento
   ↓
Pedido confirmado
   ↓
Entrega
```

### Menu esperado da 3DStore

```text
3DStore
├── Início
├── Produtos
├── Categorias
├── Ofertas
├── Meus pedidos
└── 🛒 Carrinho (0)
```

Para visitantes, `Meus pedidos` deve direcionar para login quando essa área for implementada.

### Carrinho

O carrinho deverá permitir:

- adicionar produto;
- remover produto;
- alterar quantidade;
- visualizar subtotal;
- visualizar total;
- continuar comprando;
- iniciar checkout.

### Checkout

O checkout deverá reunir:

- identificação do cliente;
- e-mail;
- dados necessários ao pagamento;
- resumo do pedido;
- valor total;
- forma de pagamento;
- confirmação.

O gateway de pagamento deve ser integrado antes de considerar a loja pronta para venda real.

---

## 5. Tipos de produto e regras

### Digital

Exemplos:

- e-books;
- apostilas;
- templates;
- datasets;
- prompts;
- cursos;
- materiais premium.

Não exige frete.

### Physical

Exemplos:

- camisetas;
- canecas;
- adesivos;
- materiais do Dojô.

Deverá utilizar estoque e cálculo de frete quando o checkout físico for implementado.

### Service

Exemplos:

- mentoria;
- consultoria de dados;
- automação;
- desenvolvimento;
- serviços de marketing digital.

A modalidade poderá futuramente ser integrada à agência do ecossistema Dojô.

---

## 6. Operação recomendada

Antes de publicar um produto:

- conferir nome;
- conferir preço;
- conferir categoria;
- conferir imagem;
- revisar descrição;
- verificar se o produto é digital, físico ou serviço;
- testar o fluxo de compra;
- somente então marcar `Active`.

Para produto digital pago, **não publicar links de arquivos privados antes de existir entrega autenticada/protegida**.

---

## 7. Roadmap da 3DStore

### Fase 1 — Fundação

- [x] App Django `store`
- [x] Categorias
- [x] Produtos
- [x] Pedidos
- [x] Itens do pedido
- [x] API pública do catálogo
- [x] Django Admin
- [x] Loja pública
- [x] Identidade visual do Dojô

### Fase 2 — E-commerce

- [ ] Menu completo da loja
- [ ] Página individual do produto
- [ ] Carrinho persistente
- [ ] Checkout
- [ ] Cálculo de totais
- [ ] Criação de pedido pelo checkout
- [ ] Gateway de pagamento
- [ ] Webhook de pagamento

### Fase 3 — Pós-compra

- [ ] Área Meus Pedidos
- [ ] Entrega protegida de produtos digitais
- [ ] E-mail de confirmação
- [ ] Histórico de pedidos
- [ ] Status do pedido
- [ ] Cupons
- [ ] Ofertas

### Fase 4 — Ecossistema comercial

- [ ] Serviços da agência
- [ ] Consultoria
- [ ] Mentorias
- [ ] Produtos físicos
- [ ] Integração com campanhas de marketing
- [ ] Métricas de vendas
- [ ] CRM comercial

---

## 8. Regra de ouro

A 3DStore deve continuar sendo **pública para descoberta e compra**, enquanto o ambiente de aprendizagem permanece protegido.

> **Visitante conhece. Cliente compra. Aluno evolui.**
