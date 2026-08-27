# COORDINATION — Data Driven Dojo

## Coordenação
ChatGPT coordena a sequência, revisa relatórios e autoriza integração.

## Equipe A — Codex App
Responsável pela Fase 0, commits, estabilização e integração.
- Um commit controlado por vez.
- Sem push sem autorização.
- Não iniciar domínio curricular futuro.

## Equipe B — Codex VS Code
Responsável por Guardião local e preparação curricular/handoff.
- No worktree compartilhado: somente leitura.
- Não corrigir automaticamente erros.
- Não fazer commit/push/merge/rebase/cherry-pick/stash/reset.
- Testar oficialmente apenas marcos declarados concluídos pela Equipe A.

## Regras anti-colisão
1. Verificar branch/worktree e `git status`.
2. Não editar a mesma feature simultaneamente.
3. Alteração inesperada: não reverter; parar e relatar.
4. Integração de worktree/branch paralela somente após revisão.
5. Evidência: Git > testes > relatório Codex > diário > memória.
