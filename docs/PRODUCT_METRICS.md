# 📊 Métricas de produto e aprendizagem

O Data Driven Dojô deve usar seus próprios dados para medir se a experiência de aprendizagem está funcionando.

## North Star Metric

**Usuários ativos que concluem uma atividade prática por semana.**

A métrica combina uso recorrente com evidência de aprendizagem ativa.

## Learning KPIs

| Métrica | Definição |
|---|---|
| DAU / WAU / MAU | Usuários ativos por período |
| Lesson Completion Rate | Aulas concluídas / aulas iniciadas |
| Exercise Success Rate | Desafios aprovados / desafios enviados |
| Course Completion Rate | Cursos concluídos / cursos iniciados |
| Weekly Practice Rate | Usuários que praticaram na semana |
| Learning Streak | Sequência de dias com atividade |
| XP per Active User | XP médio por usuário ativo |
| Time to First Challenge | Tempo até o primeiro desafio |
| Time to First Project | Tempo até o primeiro projeto |
| Retention | Retorno de usuários após períodos definidos |

## Eventos sugeridos

```text
user_registered
onboarding_completed
course_started
lesson_started
lesson_completed
exercise_started
exercise_submitted
exercise_completed
xp_earned
badge_unlocked
streak_updated
community_post_created
project_created
portfolio_published
ai_session_started
```

## Princípios

- medir eventos úteis para decisão;
- evitar coleta desnecessária de dados pessoais;
- separar métricas de produto de métricas operacionais;
- documentar definições antes de criar dashboards;
- tratar métricas como contratos versionados.
