# Avaliação da experiência do aluno — Formação Premium e Canal

**Data da avaliação:** 29/08/2026  
**Natureza:** diagnóstico e plano de melhoria; não representa funcionalidade já entregue  
**Fonte de verdade:** código, modelos, contratos editoriais, testes e documentação atual do Data Driven Dojô

## 1. Objetivo e limites

Este documento observa o Data Driven Dojô como se eu fosse um aluno entrando para aprender Dados, IA e Tecnologia. A análise cobre a estrutura digital disponível, a metodologia, a pedagogia e a experiência de uso da Formação Premium e da jornada iniciada pelo canal.

As recomendações estão separadas do estado implementado. Recursos que aparecem em roadmap — como matrícula e progresso persistentes, tentativas de exercício, competências e o Sensei educacional completo — não são descritos aqui como existentes.

Foi tentada uma navegação visual no frontend local. O servidor iniciou, mas o navegador integrado não alcançou o `localhost` da máquina por isolamento de rede. Portanto, não houve auditoria visual renderizada; as conclusões de interface foram obtidas dos componentes, rotas e contratos do sistema. Antes da implantação, é necessária uma rodada complementar em desktop e celular com usuários reais.

## 2. Resumo executivo

O Dojô já possui uma identidade memorável, uma promessa clara e peças valiosas: aulas com vídeo, exercícios, workspace, dashboard, comunidade, portfólio, certificados, chat com especialistas e uma política pedagógica editorial consistente. A filosofia 3DS — Determinação, Disciplina e Direção — dá ao produto uma personalidade que não deve ser diluída.

Como aluno, porém, eu ainda não encontro uma jornada contínua. Entro e sou levado ao primeiro curso e à primeira aula; não escolho uma formação nem retomo claramente de onde parei. Faço um desafio, mas a interface o aprova e concede XP sem conferir minha resposta. O progresso exibido fica no navegador, não representa com segurança minha aprendizagem e pode divergir do backend. Isso enfraquece justamente a promessa Premium: acompanhamento, domínio e evolução comprovável.

A prioridade não é adicionar mais telas. É tornar verdadeiro e contínuo o ciclo já defendido pelo Dojô:

> Aprender → Fazer → Ensinar → Receber feedback → Melhorar.

## 3. Minha experiência como aluno hoje

### Entrada

Eu entendo rapidamente que o Dojô ensina Dados, IA e Tecnologia e reconheço os pilares 3DS. Cadastro, login e recuperação de senha existem. Entretanto, antes de entrar, não vejo uma comparação clara entre a experiência gratuita do canal e o que recebo na Formação Premium, nem uma amostra concreta da jornada, dos projetos e dos critérios de conclusão.

### Primeiro acesso

Após o login, sou direcionado ao workspace. O sistema carrega o primeiro curso retornado pela API, o primeiro módulo e a primeira aula. Não há onboarding, diagnóstico inicial, escolha de objetivo, nível, disponibilidade semanal ou curso. Também não há uma área “continue de onde parou” sustentada por progresso persistente.

### Aula e prática

Encontro vídeo, descrição, exercício, árvore do curso, editor e terminal na mesma área. Essa proximidade entre conteúdo e prática é boa. Porém, ao compilar o desafio, a interface espera meio segundo, marca qualquer resposta como aprovada e concede XP. Não existe envio da tentativa ao backend, feedback por critério, dica progressiva ou registro de nova tentativa.

Existe `Exercise.evaluate_answer()` no backend, com implementação e testes de avaliação. Trata-se de um **avaliador backend existente, porém ainda não integrado à experiência real do aluno**: ele não está exposto ao workspace por endpoint de submissão, não é chamado pelo fluxo atual do aluno, não persiste tentativa, não controla progresso, não concede XP de maneira segura e não fornece idempotência. Assim, a existência desse avaliador não altera a conclusão sobre o fluxo real do workspace: o código ou a resposta não são realmente validados nesse fluxo, nenhuma tentativa é enviada ao backend, `submitChallenge` concede a recompensa, não há persistência de tentativa nem idempotência, e reenvios podem multiplicar XP.

### Progresso

O dashboard apresenta XP, faixa, horas, sequência e histórico. Isso dá sensação de evolução, mas esses indicadores são mantidos no armazenamento local do navegador. Posso perder ou duplicar a percepção de progresso ao trocar de dispositivo, limpar dados ou repetir desafios. Hoje eles não podem funcionar como evidência de domínio, conclusão ou certificação.

Certificados estão **parcialmente implementados**. Existe uma fundação backend com vínculo entre usuário e curso, data de emissão, código único de verificação e endpoint autenticado de leitura. Ainda não existe o fluxo completo de elegibilidade baseada em competência, emissão após avaliação pedagógica, projeto de graduação, defesa técnica, rubrica, competências demonstradas, aprovação pedagógica, página pública integrada de verificação e promoção de faixa baseada na certificação. Portanto, a **certificação verificável baseada em competência** permanece em roadmap.

### Comunidade, portfólio e IA

A comunidade oferece publicações, comentários e curtidas com ownership. O portfólio permite manter rascunhos privados e publicar projetos. Esses elementos podem transformar aprendizagem em pertencimento e prova profissional. O chat com especialistas e a Biblioteca do Sensei ampliam o suporte, mas ainda não formam um tutor educacional conectado ao progresso, às tentativas e às competências do aluno.

## 4. O que eu não mudaria

- A identidade visual e verbal do dojô, das faixas, do Kaizen e dos pilares Determinação, Disciplina e Direção.
- A promessa de aprender fundamentos, praticar, construir projetos e explicar o que foi aprendido.
- A aula integrada a vídeo, desafio, editor e terminal.
- A possibilidade de manter um projeto privado antes de publicá-lo no portfólio.
- A comunidade e o reconhecimento entre alunos, desde que a gamificação recompense aprendizagem real.
- A IA como parceira de raciocínio, nunca como substituta do pensamento do aluno.
- A aprovação humana e o Fact Checker no processo editorial antes da publicação de materiais.
- A separação editorial entre Formação Premium e Trilha YouTube.

## 5. O que mudaria primeiro

### P0 — Integridade pedagógica

1. **Validar de verdade os exercícios.** O workspace deve enviar a resposta a um endpoint autenticado, usar os critérios do exercício no servidor e só conceder XP após aprovação real. O serializer atual expõe ao cliente critérios como `expected_answer`, `expected_keywords` e `evaluation_mode`; uma implementação server-side segura deve evitar enviar ao navegador critérios que permitam descobrir a resposta esperada.
2. **Registrar tentativas e feedback.** Cada tentativa deve guardar aluno, exercício, resposta ou referência ao artefato, resultado, feedback, data e duração. O aluno precisa saber o que acertou, o que falta e qual é o próximo passo.
3. **Persistir progresso no backend.** Matrícula, aula iniciada/concluída, último ponto acessado, XP válido e critérios de certificação precisam ser confiáveis entre dispositivos.
4. **Impedir recompensa repetida indevida.** Reenviar um desafio já concluído pode servir como prática, mas não deve multiplicar XP ou conclusão sem regra explícita.

Critério de saída do P0: uma resposta incorreta não é aprovada; uma correta gera feedback, progresso e recompensa uma única vez; o estado permanece após logout, troca de navegador e novo login.

### P1 — Jornada principal do aluno

1. Criar uma “Minha Formação” com cursos matriculados, progresso, próximo passo e prazo opcional.
2. Fazer onboarding leve: objetivo profissional, nível atual, horas por semana e preferência de trilha.
3. Retomar a última aula em vez de abrir sempre o primeiro curso.
4. Exibir objetivos, pré-requisitos, carga estimada e entregável de cada módulo.
5. Organizar cada aula no ciclo: **entender → tentar sem IA → consultar IA → validar → explicar → refletir**.
6. Incluir dicas graduais antes de revelar uma solução e oferecer feedback acionável após cada tentativa.
7. Conectar projetos ao portfólio sem exigir publicação pública.
8. Tornar conclusão e certificado dependentes de critérios verificáveis, não apenas de XP local.

### P2 — Diferenciação Premium e continuidade do canal

1. Implementar rubricas para projetos e feedback humano ou assíncrono com prazo de resposta visível.
2. Oferecer checkpoints por módulo e uma revisão de lacunas antes do projeto final.
3. Recomendar revisão espaçada com base em erros reais, sem criar uma agenda punitiva.
4. Conectar o Sensei ao contexto autorizado da aula e às tentativas do próprio aluno.
5. Criar continuidade entre vídeos do canal, exercícios curtos e trilhas da plataforma.
6. Instrumentar a jornada para aprender com abandono, dificuldade e sucesso reais.

## 6. Experiência desejada por público

### Formação Premium

1. **Antes de começar:** vejo resultado esperado, requisitos, carga, projetos, suporte e critérios de certificação.
2. **Onboarding:** informo objetivo, nível e disponibilidade; recebo um ponto de partida, não uma promessa de personalização inexistente.
3. **Plano semanal:** encontro uma próxima ação clara e um ritmo ajustável.
4. **Aula:** compreendo o objetivo, vejo um exemplo e faço uma recuperação ativa curta.
5. **Prática:** tento primeiro, recebo feedback por critério e posso pedir uma dica.
6. **IA:** uso o Sensei para perguntas, alternativas e crítica; a IA não entrega automaticamente a atividade avaliada.
7. **Projeto:** aplico o conteúdo em um problema real, recebo rubrica e feedback e decido se publico no portfólio.
8. **Fechamento:** explico o que fiz, reflito sobre decisões e recebo certificado somente quando cumpro os critérios.

O diferencial Premium deve ser profundidade, acompanhamento, feedback, prática validada e prova de competência — não apenas mais vídeos.

### Canal e Trilha YouTube

1. Cada vídeo resolve uma pergunta completa e não esconde o fundamento para forçar conversão.
2. A descrição oferece um próximo passo único: exercício curto, material ou playlist correspondente.
3. Playlists têm ordem, pré-requisitos, resultado esperado e fechamento.
4. Um microdesafio gera um artefato útil mesmo para quem não compra a formação.
5. O convite para o Premium explica o ganho concreto: feedback, projetos, acompanhamento, comunidade e certificação com critérios.
6. O aluno pode entrar na plataforma pelo ponto relacionado ao vídeo, sem cair genericamente na primeira aula disponível.

## 7. Estrutura digital e experiência de uso

| Área | Estado observado | Melhoria proposta |
|---|---|---|
| Entrada | Marca e proposta fortes; cadastro, login e recuperação existem | Explicar jornadas Canal e Premium, mostrar projeto de saída e critérios |
| Navegação | Rotas para dashboard, workspace, IA, comunidade, portfólio e perfil | Criar hierarquia “Minha Formação” e uma próxima ação dominante |
| Workspace | Vídeo, exercício, árvore, editor e terminal integrados | Validar respostas, salvar rascunho, mostrar feedback, tentativas e progresso |
| Curso | Primeiro curso/aula selecionados automaticamente | Escolha/matrícula e retomada do último ponto |
| Dashboard | XP, faixa, horas, sequência e histórico locais | Métricas persistentes, explicáveis e ligadas a atividades válidas |
| Comunidade | Feed, comentários, curtidas e ownership | Comunidades por turma/módulo, busca, moderação e feedback construtivo |
| Portfólio | Rascunho privado e publicação pública | Vincular entregas, rubricas e versões; manter publicação opcional |
| Sensei | Chat com especialistas e histórico | Contexto da aula, citações, limites e suporte socrático baseado em tentativa |
| Mobile/acessibilidade | Componentes usam responsividade parcial | Auditoria real de teclado, leitor de tela, contraste, legenda e celular |

### Estrutura física, quando houver encontros presenciais ou ao vivo

O repositório não comprova uma operação física atual; portanto, os itens abaixo são requisitos propostos, não descrição do serviço existente:

- Mesas que permitam alternar foco individual, dupla e revisão coletiva.
- Tela legível, áudio claro, tomadas, internet redundante e ambiente acessível.
- Opção equivalente para aluno remoto, com gravação, legenda e materiais.
- Blocos curtos de exposição intercalados com prática; monitor não deve resolver o desafio pelo aluno.
- Plantão com agenda, objetivo e registro do encaminhamento, preservando privacidade.

## 8. Método pedagógico recomendado

### Unidade mínima de aprendizagem

Cada aula deve declarar:

- objetivo observável;
- pré-requisito;
- problema motivador;
- explicação e exemplo;
- tentativa sem IA;
- apoio opcional do Sensei;
- validação objetiva ou rubrica;
- explicação do aluno;
- reflexão e próximo passo;
- desafio de transferência para outro contexto.

### Uso responsável de IA

A política editorial atual já define uma boa direção: raciocinar antes, formular hipóteses, usar IA como parceira, revisar criticamente, validar, implementar e explicar. Na experiência do aluno isso deve se tornar visível:

- perguntar “o que você já tentou?” antes de fornecer solução;
- oferecer dica em níveis;
- citar a fonte privada usada quando houver RAG;
- distinguir fato, hipótese e sugestão;
- nunca usar conversa de outro usuário;
- exigir explicação independente em atividades avaliadas;
- permitir fazer e concluir desafios sem IA.

## 9. Backlog priorizado para implantação

| Prioridade | Entrega | Valor para o aluno | Evidência de pronto |
|---|---|---|---|
| P0 | Avaliação server-side e contrato seguro do exercício | Confia que aprovação significa domínio | Testes de correto, incorreto, critérios ocultos e autorização |
| P0 | Tentativas, conclusão e XP persistentes | Continua em qualquer dispositivo | Testes de persistência, idempotência e ownership |
| P0 | Remover aprovação simulada do workspace | Feedback deixa de ser enganoso | Nenhum caminho concede XP sem resultado válido |
| P1 | Minha Formação e “continuar” | Sabe exatamente o próximo passo | Retoma curso, módulo e aula corretos |
| P1 | Onboarding e diagnóstico | Inicia no nível adequado | Pode revisar escolhas; sem falsa personalização |
| P1 | Feedback, dicas e explicação | Aprende com erro, não só com acerto | Rubrica/critério visível e nova tentativa possível |
| P1 | Entrega ligada ao portfólio | Constrói prova profissional | Rascunho privado por padrão; publicação consentida |
| P2 | Sensei contextual e socrático | Recebe apoio sem terceirizar raciocínio | Respostas citadas, isoladas e ligadas à aula autorizada |
| P2 | Checkpoints e revisão espaçada | Retém conhecimento | Recomendações baseadas em erros e domínio |
| P2 | Ponte Canal → plataforma → Premium | Mantém continuidade | Deep link leva ao exercício/trilha correspondente |
| P2 | Acessibilidade e QA mobile | Aprende sem barreira evitável | WCAG, teclado, legenda e dispositivos testados |

## 10. Métricas recomendadas

Estas métricas ainda precisam de instrumentação e governança; não são declaradas como disponíveis hoje.

- **Ativação:** aluno chega à primeira prática válida e recebe feedback.
- **Tempo até o primeiro artefato:** do cadastro ao primeiro exercício/projeto concluído.
- **Aprendizagem:** taxa de acerto inicial, evolução por tentativa e retenção em revisão posterior.
- **Continuidade:** retorno semanal e retomada após interrupção.
- **Conclusão:** aulas, módulos, projetos e formação concluídos com critérios válidos.
- **Ajuda:** uso de dicas e Sensei antes/depois da tentativa, sem premiar dependência.
- **Portfólio:** projetos concluídos e percentual publicado voluntariamente.
- **Experiência:** CES após tarefa, satisfação por módulo e NPS em marcos adequados.
- **Canal:** vídeo → material/exercício, exercício → cadastro e cadastro → Premium, sempre com consentimento e definição única de evento.

Não usar tempo de tela ou XP isoladamente como prova de aprendizagem.

## 11. Sequência de implantação

### Fase 0 — Confiança

Corrigir avaliação, tentativas, progresso, idempotência e segurança dos critérios. Até isso estar pronto, não usar XP ou desafio “aprovado” como evidência acadêmica.

### Fase 1 — Direção

Entregar Minha Formação, retomada, onboarding mínimo, objetivos por aula e feedback acionável.

### Fase 2 — Profundidade Premium

Adicionar rubricas, checkpoints, revisão, feedback humano e critérios de certificação verificáveis.

### Fase 3 — Continuidade do canal

Mapear playlists para microdesafios e deep links; comunicar honestamente o diferencial Premium.

### Fase 4 — Kaizen orientado por evidência

Instrumentar métricas, entrevistar alunos, testar acessibilidade e melhorar por coortes sem manipular resultados.

## 12. Validação com alunos antes de escalar

Conduzir sessões com pelo menos estes perfis: iniciante absoluto, profissional em transição, aluno avançado, usuário de celular e pessoa que utiliza tecnologia assistiva. Pedir que realizem, sem orientação do pesquisador: cadastro, escolha de curso, retomada, aula, desafio incorreto, correção, pedido ao Sensei, publicação privada de projeto e localização do próximo passo.

Registrar tempo, erros, dúvidas, abandono e linguagem usada pelo aluno. Não perguntar apenas se ele “gostou”; verificar se conseguiu aprender e agir.

## 13. Decisão final

Eu manteria a alma do Dojô e reduziria a distância entre a promessa e a evidência. O produto não precisa parecer maior; precisa fazer cada aprovação significar algo, cada faixa representar evolução real e cada aluno saber o próximo passo.

Para a Formação Premium, a melhor experiência nasce de prática validada, feedback, acompanhamento e projetos que comprovam competência. Para o canal, nasce de conteúdo completo, continuidade e uma ponte honesta para quem deseja aprofundar. Em ambos, a IA deve fortalecer a autoria do aluno — nunca substituí-la.
