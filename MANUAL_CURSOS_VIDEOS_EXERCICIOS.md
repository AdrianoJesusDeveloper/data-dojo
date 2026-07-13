# Manual: como subir cursos, vídeos e exercícios no Data Driven Dojô

Este manual descreve o fluxo atual suportado pelo sistema para publicar conteúdos no painel administrativo do backend e vê-los aparecer no frontend.

## 1. O que o sistema suporta hoje

O backend já possui quatro entidades principais:

- Curso
- Módulo
- Aula
- Exercício

As aulas podem ter:

- `VIDEO`: para vídeos
- `ARTICLE`: para apostilas ou texto explicativo
- `LAB`: para laboratório interativo

Os vídeos podem ser enviados por:

- `file_upload` (arquivo local, por exemplo `.mp4`)
- `video_url` (URL externa, como YouTube/Vimeo, desde que a URL seja compatível com o player)

Os exercícios agora são tratados como uma entidade própria associada a uma lição. Eles podem ter:

- enunciado
- tipo de resposta (SQL, Python, múltipla escolha ou resposta aberta)
- resposta esperada
- palavras-chave
- modo de avaliação
- pontuação

A correção automática no frontend usa esses critérios para validar a resposta do aluno.

### Evidência desta seção
- Fotos/Vídeos: [preencher]
- Observações: [preencher]

## 2. Consistências e limites encontrados

Ao revisar o projeto, notei os pontos abaixo:

- O sistema agora possui um modelo próprio de exercícios associado a cada lição.
- A correção automática avalia a resposta com base em critérios configurados, como palavras-chave, correspondência exata ou presença da resposta esperada.
- O frontend busca os cursos no endpoint `/api/courses/` e exibe a primeira lição do primeiro módulo automaticamente.
- Para que vídeos apareçam corretamente, o backend precisa estar rodando e o arquivo/URL precisa estar acessível.

Arquivos relevantes:

- [apps/api/core/models.py](apps/api/core/models.py)
- [apps/api/core/admin.py](apps/api/core/admin.py)
- [src/routes/workspace.tsx](src/routes/workspace.tsx)

## 3. Pré-requisitos

1. Ter o backend Django configurado e rodando.
2. Ter um usuário admin criado.
3. Ter o frontend acessando o backend em `http://127.0.0.1:8000`.

### Subir o backend

No terminal, na pasta do projeto:

```powershell
cd apps/api
.\venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Se não existir a virtualenv, crie uma com:

```powershell
cd apps/api
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
```

### Criar um superusuário

```powershell
python manage.py createsuperuser
```

Depois acesse:

- http://127.0.0.1:8000/admin/

### Evidência desta seção
- Fotos/Vídeos: [preencher]
- Observações: [preencher]

## 4. Como subir um curso

1. Entre no painel administrativo.
2. Clique em `Courses`.
3. Clique em `Adicionar Course`.
4. Preencha:
   - `title`: nome do curso
   - `description`: descrição do curso
5. Salve.

Exemplo:

- Título: SQL para Ciência de Dados
- Descrição: Curso introdutório com vídeos e exercícios práticos de SQL

## 5. Como subir módulos

1. Em `Modules`, clique em `Adicionar Module`.
2. Selecione o curso relacionado.
3. Defina o título e a ordem do módulo.
4. Salve.

Exemplo:

- Curso: SQL para Ciência de Dados
- Módulo: Fundamentos do SQL
- Ordem: 1

### Evidência desta seção
- Fotos/Vídeos: [preencher]
- Observações: [preencher]

## 6. Como subir vídeos

### Opção A: enviar um arquivo de vídeo

1. Crie ou edite uma aula.
2. Selecione o módulo correto.
3. Defina o título da aula.
4. Em `content_type`, escolha `VIDEO`.
5. No campo `file_upload`, envie o vídeo.
6. Salve.

### Opção B: usar uma URL de vídeo

1. Crie ou edite uma aula.
2. Escolha `content_type = VIDEO`.
3. No campo `video_url`, cole a URL do vídeo.
4. Salve.

Exemplo de URL válida:

- `https://www.youtube.com/embed/SEU_VIDEO`

> Para o frontend exibir o vídeo, a URL precisa ser compatível com o iframe ou o arquivo precisa estar disponível no servidor.

## 7. Como subir exercícios

O fluxo atual para exercícios é este:

1. Crie uma aula dentro de um módulo.
2. Defina `content_type` como `ARTICLE` ou `LAB`.
3. Crie um registro em `Exercises` associado a essa aula.
4. Preencha os campos do exercício:
   - `title`: nome do exercício
   - `statement`: enunciado do desafio
   - `answer_type`: tipo de resposta (SQL, Python, múltipla escolha ou resposta aberta)
   - `expected_answer`: resposta esperada
   - `expected_keywords`: palavras-chave esperadas
   - `evaluation_mode`: modo de validação
   - `points`: pontuação do exercício
5. Salve.

### Exemplo de exercício SQL

Dados de exemplo:

- Título: Exercício 1: selecionar nomes de clientes
- Statement: Escreva uma consulta SQL que retorne os nomes dos clientes da tabela clientes.
- Answer type: SQL
- Expected answer: `SELECT name FROM customers`
- Expected keywords: `SELECT`, `FROM`
- Evaluation mode: `keywords`
- Points: `100`

### Exemplo de exercício de resposta aberta

- Título: Explique o conceito de JOIN
- Statement: Descreva em poucas linhas o que é um JOIN e quando ele é usado.
- Answer type: OPEN
- Expected answer: `JOIN combina linhas entre tabelas relacionadas`
- Expected keywords: `JOIN`, `tabelas`
- Evaluation mode: `contains`
- Points: `80`

### Importante sobre correção

A validação automática agora usa os critérios configurados no exercício:

- `keywords`: verifica se todas as palavras-chave aparecem na resposta
- `contains`: verifica se a resposta esperada aparece dentro da resposta do aluno
- `exact`: exige correspondência exata ao texto esperado

Portanto, para o sistema “corrigir” a resposta, o exercício precisa ser cadastrado corretamente no painel administrativo.

### Evidência desta seção
- Fotos/Vídeos: [preencher]
- Observações: [preencher]

## 8. Exemplo de estrutura recomendada

Curso:

- SQL para Ciência de Dados

Módulos:

1. Fundamentos do SQL
   - Aula 1: Introdução ao SELECT
   - Aula 2: Filtrando dados com WHERE
   - Aula 3: Exercício prático de SELECT

2. Agregações
   - Aula 4: Funções de agregação
   - Aula 5: Exercício prático com GROUP BY

### Evidência desta seção
- Fotos/Vídeos: [preencher]
- Observações: [preencher]

## 9. Como verificar se o conteúdo apareceu

1. Rode o backend.
2. Abra o frontend no navegador.
3. Acesse a área do workspace.
4. Verifique se:
   - o curso aparece na lista
   - os módulos e aulas aparecem na navegação
   - o vídeo ou o player é exibido
   - o enunciado do exercício aparece na interface
   - a avaliação do desafio utiliza os critérios do exercício

## 10. Seed de exemplo rápido

Se quiser popular o banco com conteúdo de demonstração rapidamente, execute:

```powershell
cd apps/api
.\venv\Scripts\Activate.ps1
python manage.py seed_demo_content
```

Esse comando cria automaticamente:

- um curso de exemplo
- um módulo
- uma aula
- um exercício associado

### Evidência desta seção
- Fotos/Vídeos: [preencher]
- Observações: [preencher]

## 11. Dicas de uso

- Use `order` para controlar a sequência das aulas.
- Mantenha um curso com poucos módulos no início para facilitar a validação.
- Para testes rápidos, comece com um único curso, um módulo e 3 aulas.
- Se o vídeo não aparecer, verifique:
  - se o arquivo foi realmente enviado
  - se a URL do vídeo é válida
  - se o backend está rodando em `127.0.0.1:8000`

### Evidência desta seção
- Fotos/Vídeos: [preencher]
- Observações: [preencher]

