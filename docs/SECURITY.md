# 🔐 Segurança — Data Driven Dojô

Este documento define as práticas de segurança esperadas para desenvolvimento, revisão e produção.

## Princípios

- Segredos nunca entram no Git.
- Configuração de ambiente fica em variáveis de ambiente.
- Endpoints protegidos exigem autenticação quando aplicável.
- Entrada do usuário deve ser validada no backend.
- CORS deve permitir apenas origens necessárias.
- Banco e Redis devem permanecer em rede privada quando o provedor suportar.
- Logs não devem expor tokens, senhas ou dados pessoais.

## Checklist de produção

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` forte e exclusivo
- [ ] `ALLOWED_HOSTS` restrito
- [ ] `CORS_ALLOWED_ORIGINS` restrito ao frontend
- [ ] `CSRF_TRUSTED_ORIGINS` restrito ao frontend/API
- [ ] HTTPS habilitado no provedor
- [ ] cookies seguros em ambientes com sessão
- [ ] banco sem acesso público desnecessário
- [ ] Redis/Key Value privado
- [ ] backups do PostgreSQL em ambiente pago
- [ ] rotação de credenciais
- [ ] dependências atualizadas
- [ ] CI executando lint, typecheck, testes e build

## Segredos

Use `.env` apenas localmente. O repositório contém `.env.example`, nunca valores reais.

Nunca publique:

- chaves de API;
- tokens de autenticação;
- senhas;
- credenciais SMTP;
- credenciais AWS;
- URLs privadas contendo credenciais.

## Incidentes

Se um segredo for exposto:

1. revogue a credencial imediatamente;
2. gere uma nova credencial;
3. atualize o provedor de deploy;
4. verifique logs e histórico;
5. registre o incidente antes de continuar o desenvolvimento.
