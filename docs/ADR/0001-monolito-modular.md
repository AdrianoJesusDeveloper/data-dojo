# ADR-0001 — Monólito modular como arquitetura de evolução

**Status:** Aceito

## Contexto

O Data Driven Dojô possui frontend React/TypeScript e backend Django REST. O produto ainda está em fase de evolução e seus domínios continuam mudando rapidamente.

## Decisão

Manter o backend como **monólito modular**, separando responsabilidades por domínio antes de considerar microserviços.

Domínios previstos:

- Identity / Core
- Learning
- Gamification
- Community
- Portfolio
- Analytics
- AI Sensei

## Motivos

- menor complexidade operacional;
- desenvolvimento e deploy mais simples;
- transações locais mais fáceis;
- observabilidade centralizada;
- menor custo inicial;
- possibilidade de extração futura baseada em evidências.

## Consequência

A modularidade deve ser respeitada no código para que um domínio possa ser extraído futuramente sem reescrever a plataforma inteira.

## Regra

**Não adotar microserviços por estética arquitetural.** Extração de serviço exige evidência de escala, isolamento, ciclo de deploy ou necessidade operacional.
