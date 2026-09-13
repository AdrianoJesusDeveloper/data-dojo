# Auditoria global Django — 2026-09-12

## Execução inicial

Comando: `docker compose exec api python manage.py test -v 2`

389 testes em 143.080s; 367 aprovados; 0 failures; 23 errors em 22 métodos de teste (Desafio de Autoria tem dois subcasos com erro). Nenhum teste ignorado. Migrations aplicadas com sucesso no banco temporário test_dojo_db.

## Classificação anterior às correções

- A — Testes: três SimpleNamespace sem original_intent, campo existente no modelo StudioProject e consumido legitimamente pelo gerador editorial.
- B — Implementação/PostgreSQL: 20 erros em 19 métodos, distribuídos entre review_response (5 erros), publish_preview (8), LibrarySourceProcessView (6) e SandboxPaymentApproveView (1). select_for_update combinado com select_related em relações opcionais produz OUTER JOIN que PostgreSQL não permite bloquear.
- C — Ambiente: anteriormente, `ENVIRONMENT=docker` e `DDJ_CONTENT_STUDIO_ENABLED=False` impediam o registro das URLs do Content Studio. Após a correção do ambiente DEV para `ENVIRONMENT=development` e `DDJ_CONTENT_STUDIO_ENABLED=true`, mais de 100 erros desapareceram, conforme confirmação manual do usuário. A execução inicial de 389 testes registrada acima corresponde à etapa posterior a essa correção de ambiente. Acesso ao Docker exigiu execução fora do sandbox e foi autorizado. Código inicial de ai/tests.py e studio_agents.py confirmado por SHA256 no host/container.

## Testes quebrados na execução inicial

- `test_content_studio_selects_openai_without_client_input (ai.tests.ContentStudioProviderTests.test_content_studio_selects_openai_without_client_input)`
- `test_explicit_server_override_can_select_gemini (ai.tests.ContentStudioProviderTests.test_explicit_server_override_can_select_gemini)`
- `test_invalid_editorial_json_remains_rejected (ai.tests.ContentStudioProviderTests.test_invalid_editorial_json_remains_rejected)`
- `test_challenge_is_available_for_both_source_modes_and_feedback_is_append_only (library.tests.test_authorship_challenge.AuthorshipChallengeApiTests.test_challenge_is_available_for_both_source_modes_and_feedback_is_append_only) (source_mode=DidacticLesson.SourceMode.APPROVED_SOURCES)`
- `test_challenge_is_available_for_both_source_modes_and_feedback_is_append_only (library.tests.test_authorship_challenge.AuthorshipChallengeApiTests.test_challenge_is_available_for_both_source_modes_and_feedback_is_append_only) (source_mode=DidacticLesson.SourceMode.AI_GENERATED_UNSOURCED)`
- `test_formation_preview_groups_multiple_modules_and_invalidates_on_scope_change (library.tests.test_didactic_publication.DidacticPublicationTests.test_formation_preview_groups_multiple_modules_and_invalidates_on_scope_change)`
- `test_module_and_formation_scopes_select_exact_lessons (library.tests.test_didactic_publication.DidacticPublicationTests.test_module_and_formation_scopes_select_exact_lessons)`
- `test_module_preview_classifies_every_unit_and_publishes_only_approved (library.tests.test_didactic_publication.DidacticPublicationTests.test_module_preview_classifies_every_unit_and_publishes_only_approved)`
- `test_new_preview_detects_student_derivation_as_stale (library.tests.test_didactic_publication.DidacticPublicationTests.test_new_preview_detects_student_derivation_as_stale)`
- `test_publish_creates_traceable_student_and_existing_workspace_models (library.tests.test_didactic_publication.DidacticPublicationTests.test_publish_creates_traceable_student_and_existing_workspace_models)`
- `test_publish_rejects_draft_changed_reused_or_foreign_preview (library.tests.test_didactic_publication.DidacticPublicationTests.test_publish_rejects_draft_changed_reused_or_foreign_preview)`
- `test_republishing_lesson_in_module_reuses_all_derivations (library.tests.test_didactic_publication.DidacticPublicationTests.test_republishing_lesson_in_module_reuses_all_derivations)`
- `test_zero_eligible_preview_blocks_without_empty_workspace_hierarchy (library.tests.test_didactic_publication.DidacticPublicationTests.test_zero_eligible_preview_blocks_without_empty_workspace_hierarchy)`
- `test_attempt_records_provider_selected_for_current_formation (library.tests.test_sensei_learning.SenseiLearningApiTests.test_attempt_records_provider_selected_for_current_formation)`
- `test_feedback_provider_failure_does_not_create_partial_attempt (library.tests.test_sensei_learning.SenseiLearningApiTests.test_feedback_provider_failure_does_not_create_partial_attempt)`
- `test_multiple_attempts_preserve_history_without_mastery_or_evidence (library.tests.test_sensei_learning.SenseiLearningApiTests.test_multiple_attempts_preserve_history_without_mastery_or_evidence)`
- `test_catalog_source_reaches_book_and_chunks (library.tests.test_source_processing.LibrarySourceProcessingTests.test_catalog_source_reaches_book_and_chunks)`
- `test_duplicate_missing_and_unsupported_sources_are_rejected (library.tests.test_source_processing.LibrarySourceProcessingTests.test_duplicate_missing_and_unsupported_sources_are_rejected)`
- `test_path_traversal_and_absolute_outside_path_are_rejected (library.tests.test_source_processing.LibrarySourceProcessingTests.test_path_traversal_and_absolute_outside_path_are_rejected)`
- `test_second_call_reuses_book_without_enqueuing_again (library.tests.test_source_processing.LibrarySourceProcessingTests.test_second_call_reuses_book_without_enqueuing_again)`
- `test_supported_source_creates_book_and_enqueues_task (library.tests.test_source_processing.LibrarySourceProcessingTests.test_supported_source_creates_book_and_enqueues_task)`
- `test_symlink_escaping_library_root_is_rejected (library.tests.test_source_processing.LibrarySourceProcessingTests.test_symlink_escaping_library_root_is_rejected)`
- `test_sandbox_payment_can_be_approved_only_by_order_owner (store.tests.StoreApiTests.test_sandbox_payment_can_be_approved_only_by_order_owner)`

## Correções desta auditoria

- apps/api/ai/tests.py: adicionar original_intent vazio às três fixtures; não alterar o contrato editorial.
- apps/api/library/services/sensei_learning.py: prefetch da relação opcional unit__study_plan; manter bloqueios da atividade, unidade e competência.
- apps/api/library/services/didactic_publication.py: prefetch de module e unit opcionais; manter bloqueios da publicação e formação.
- apps/api/library/views.py: prefetch do livro opcional; manter bloqueio da fonte.
- apps/api/store/views.py: prefetch do pagamento; manter bloqueio do pedido e filtro de proprietário/status.

Transações, permissões, validação humana e regras de progresso preservadas. Nenhuma migration/configuração de produção alterada. Nenhum commit ou operação destrutiva de Git. Arquivos sincronizados individualmente via docker compose cp, sem recriar serviços, banco persistente ou volumes. Alterações preexistentes do usuário preservadas.

## Validação

- ContentStudioProviderTests: 7 testes, OK.
- Suíte global final executada manualmente após as correções da auditoria, no ambiente Docker + PostgreSQL, com resultado confirmado pelo usuário.
- Comando executado manualmente: `docker compose exec api python manage.py test -v 2`

Resultado:

```text
Ran 389 tests in 165.305s
OK

Tests: 389
Passed: 389
Failures: 0
Errors: 0
```

A pendência de validação global está encerrada pelo resultado manual confirmado. A suíte não foi executada novamente nesta atualização documental.
