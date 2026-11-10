# SGE — Sistema de Gestão de Estoque

Sistema web de controle de estoque feito em Django. Reúne cadastro de produtos,
marcas, categorias e fornecedores, registro de entradas e saídas, um dashboard
com os números do estoque e das vendas, e uma API REST com autenticação JWT para
outros sistemas lerem e gravarem os mesmos dados.

## Telas

- **Dashboard** (`/`): total de custo, de venda e de lucro do que está em
  estoque, quantidade de itens, número de vendas e valor vendido, além de dois
  gráficos dos últimos 7 dias (valor das vendas e quantidade vendida). Cada
  bloco só aparece se o usuário tiver a permissão correspondente.
- **Produtos** (`/products/list/`): listagem paginada de 10 em 10, com busca por
  título, número de série, categoria e marca; telas de cadastro, detalhe, edição
  e exclusão.
- **Entradas** (`/inflows/list/`): registro de compra ou recebimento por
  fornecedor, com busca por produto.
- **Saídas** (`/outflows/list/`): registro de venda ou retirada, com busca por
  produto e os totais de vendas no topo da lista.
- **Fornecedores**, **Marcas** e **Categorias**: cadastro, edição, detalhe e
  exclusão.
- **Login e logout** por sessão. O menu lateral mostra apenas os itens liberados
  pelas permissões do usuário.

## O que o sistema faz por trás das telas

- Toda entrada soma a quantidade no produto e toda saída abate — feito por
  signals `post_save`, então vale também para registros criados pela API.
- A saída é validada contra o estoque disponível: se a quantidade pedida for
  maior que a em estoque, o formulário recusa e informa o saldo atual do produto.
- Preços de custo e de venda são `DecimalField(20, 2)`. O dashboard soma custo e
  venda de todo o estoque em mãos para chegar no lucro.
- Cada saída dispara uma tentativa de evento para o Notify (veja a seção de
  integração), sem interromper o registro caso o outro serviço esteja fora.
- Usuários e permissões vêm do admin do Django; as views de tela exigem login e
  a permissão de visualizar, criar, editar ou excluir de cada modelo.

## Stack

- Python 3.12 e Django 6.1
- SQLite no modo de desenvolvimento; PostgreSQL quando `DJANGO_ENV=prd`
- Django REST Framework 3.18 com SimpleJWT (access token de 1 dia, refresh de 7)
- Chart.js via CDN para os gráficos do dashboard
- python-decouple para ler as variáveis do `.env`
- Docker e docker-compose (aplicação + PostgreSQL 15)

## Como rodar

### Local, com SQLite

```bash
git clone https://github.com/marcusvgcruz/sge.git
cd sge

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env     # edite o SECRET_KEY; mantenha DJANGO_ENV=dev

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abra `http://127.0.0.1:8000/` e entre com o usuário criado. No modo dev o banco é
o `db.sqlite3` na raiz do projeto.

### Com Docker

```bash
cp .env.example .env     # edite o SECRET_KEY; POSTGRES_* já vêm preenchidos
docker compose up --build
```

A aplicação sobe em `http://localhost:8000`. O container roda as migrações
(`python manage.py migrate`) antes de iniciar o servidor.

Observação: o compose levanta um PostgreSQL 15, mas o projeto só usa PostgreSQL
quando `DJANGO_ENV=prd`. Com o `.env` de exemplo (`dev`), a aplicação roda em
SQLite dentro do container. Para usar o banco do compose, coloque
`DJANGO_ENV=prd` no `.env`.

Crie o primeiro usuário dentro do container:

```bash
docker compose exec sge_web python manage.py createsuperuser
```

## Estrutura de pastas

```
app/             settings, urls raiz, view e metricas do dashboard, templates base
authentication/  rotas de token JWT
brands/          marcas
categories/      categorias
suppliers/       fornecedores
products/        produtos (telas + API)
inflows/         entradas (telas + API + signal que soma estoque)
outflows/        saidas (telas + API + signals que abatem estoque e disparam evento)
services/        client do Notify
manage.py
Dockerfile
docker-compose.yml
```

Cada app repete o mesmo desenho: `models.py`, `forms.py`, `views.py`, `urls.py`,
`serializers.py`, `templates/` e `migrations/`.

## API

A autenticação é por JWT:

```
POST /api/v1/authentication/token/           access + refresh
POST /api/v1/authentication/token/refresh/
POST /api/v1/authentication/token/verify/
```

Use o access token no header `Authorization: Bearer <token>`. As rotas de dados
são:

```
/api/v1/products/            /api/v1/products/<id>/
/api/v1/brands/              /api/v1/brands/<id>/
/api/v1/categories/          /api/v1/categories/<id>/
/api/v1/suppliers/           /api/v1/suppliers/<id>/
/api/v1/inflows/             /api/v1/inflows/<id>/
/api/v1/outflows/            /api/v1/outflows/<id>/
```

Produtos, marcas, categorias e fornecedores aceitam leitura, criação, edição e
exclusão. Entradas e saídas aceitam listagem, criação e consulta de um registro
(as views não expõem edição nem exclusão). Todas exigem usuário autenticado e as
permissões de modelo do Django.

## Integração com o Notify

O [marcusvgcruz/notify](https://github.com/marcusvgcruz/notify) é o complemento
do SGE para webhooks: recebe o evento de cada saída registrada e avisa por
WhatsApp (CallMeBot) e por e-mail. O client que o SGE usa fica em
`services/notify.py`, com a URL base `http://localhost:8001`, e é chamado no
signal de criação de saída em `outflows/signals.py`. O envio é opcional: qualquer
falha é descartada para não impedir a baixa de estoque.

Para a integração funcionar como está configurada, suba o Notify na mesma
máquina, na porta 8001.

## Licença

Repositório pessoal de Marcus Cruz, sem licença declarada.
