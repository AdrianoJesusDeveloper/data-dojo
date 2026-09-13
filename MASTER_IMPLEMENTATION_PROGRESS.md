# Progresso — Missão Mestre Data Driven Dojô

## Fase 1 — Exportação didática

- **Status:** concluída e validada localmente.
- **Arquivos alterados:** `apps/api/library/services/didactic_export.py`, `apps/api/library/views.py`, `apps/api/library/urls.py`, `apps/api/library/tests/test_didactic_content.py`, `src/components/content-studio/DidacticContentV1.tsx`, `src/tests/DidacticContentV1.spec.tsx`.
- **Migrations criadas:** nenhuma.
- **Funcionalidades:** exportação DOCX e HTML no backend; metadados de formação, módulo e unidade; status, audiência e modo de fonte; proveniência de IA; fontes; seções ordenadas; aviso obrigatório para conteúdo `AI_GENERATED_UNSOURCED`; IDs e timestamp de rastreabilidade; downloads no Content Studio; controles interativos excluídos dos documentos.
- **Testes executados:** `library.tests.test_didactic_content` (10/10); `DidacticContentV1.spec.tsx` (10/10); `tsc --noEmit`; `manage.py check`; `makemigrations --check --dry-run`.
- **Resultados:** todos aprovados; nenhuma mudança de schema detectada.
- **Pendências:** validação visual manual dos arquivos baixados no navegador/Word ao final da missão.
- **Riscos:** o executável global `npm` local aponta para um `npm-cli.js` inexistente; testes frontend foram executados diretamente com Node e os binários instalados em `node_modules`.
- **Dívida técnica identificada:** reparar a instalação global do npm fora do escopo do produto; a execução padrão do Vitest também deve excluir `.venv` neste ambiente (a validação focada usou `--exclude '**/.venv/**'`).

## Fases 2–3 — Publicação e adaptação Sensei → Student

- **Status:** concluídas e validadas localmente.
- **Arquivos alterados:** `apps/api/library/models.py`, `apps/api/library/migrations/0026_didactic_student_publication.py`, `apps/api/library/services/didactic_publication.py`, `apps/api/library/serializers.py`, `apps/api/library/views.py`, `apps/api/library/urls.py`, `apps/api/library/tests/test_didactic_publication.py`, `src/components/content-studio/DidacticContentV1.tsx`, `src/tests/DidacticContentV1.spec.tsx`.
- **Migration criada:** `library.0026_didactic_student_publication`, aplicada com sucesso somente ao banco local.
- **Funcionalidades:** adaptação pedagógica explícita `SENSEI → STUDENT`; preview persistido e obrigatório; confirmação humana; publicação por aula, módulo ou formação; integração aditiva com `core.Course`, `core.Module` e `core.Lesson`; rastreabilidade entre origem, derivação e Workspace; cópia de proveniência e fontes; invalidação de preview quando a origem muda; detecção `student_is_stale`; bloqueio de aula não aprovada; token de preview isolado por usuário e formação; conclusão de conteúdo sem concessão automática de mastery.
- **Testes executados:** testes focados das Fases 1–3 (16/16); regressão Django `library.tests core.tests` (203 aprovados, 3 ignorados); frontend focado `DidacticContentV1`, `ContentStudio`, `Workspace`, `LessonPlayer` (44/44); `tsc --noEmit`; `manage.py check`; `makemigrations --check --dry-run`.
- **Resultados:** todos aprovados; migration alinhada aos modelos; contratos existentes do Workspace preservados.
- **Pendências:** validação funcional manual no navegador do preview nos três escopos e confirmação visual no Workspace; será incluída no E2E consolidado.
- **Riscos:** publicação requer que todas as aulas SENSEI do escopo estejam em `APPROVED`; qualquer mudança posterior exige nova prévia, por desenho.
- **Dívida técnica identificada:** o perfil determinístico `guided-student-v1` é extensível e pode futuramente receber proposta assistida por IA, mantendo revisão e publicação humanas obrigatórias.

### Correção pós-E2E — workflow editorial da aula

- **Status:** corrigido e validado; aguardando repetição manual do E2E.
- **Arquivos alterados nesta correção:** `src/components/content-studio/DidacticContentV1.tsx`, `src/tests/DidacticContentV1.spec.tsx`, `apps/api/library/tests/test_didactic_content.py`, `apps/api/library/tests/test_didactic_publication.py`, além deste relatório.
- **Migration:** nenhuma; reutilizado o status e o endpoint `PATCH` existentes de `DidacticLesson`.
- **Funcionalidades:** controles visuais `DRAFT → REVIEW → APPROVED`, retorno `REVIEW → DRAFT`, reabertura `APPROVED → REVIEW`, atualização imediata do cache, invalidação de preview antigo e bloqueio visual da confirmação de publicação antes de `APPROVED`.
- **Separação de domínio:** aprovação editorial da aula não altera fonte, atividade, evidência, competência, XP ou progresso acadêmico.
- **Testes focados:** backend 18/18; frontend 13/13; Django check, TypeScript e verificação de migrations aprovados.
- **Regressão ampliada:** Library + Core 205 aprovados e 3 ignorados; frontend afetado 45/45.
