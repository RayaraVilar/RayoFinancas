# Operação, SLOs e runbooks

## SLOs iniciais

- disponibilidade API: 99,5% ao mês;
- p95 dashboard: até 800 ms, sem provider externo;
- webhook aceito: p95 até 500 ms;
- 95% das sincronizações concluídas em 10 minutos;
- RPO 24 horas e RTO 4 horas.

Recalibrar após baseline de staging.

## Backup e restauração

Usar backup gerenciado e criptografado. Trimestralmente, restaurar em banco isolado,
verificar `alembic current`, contagens e amostras, e executar testes de leitura.
Nunca restaurar sobre produção para teste.

## Incidente

1. Acionar kill switch e suspender integração afetada.
2. Preservar request IDs sem copiar payload financeiro.
3. Classificar escopo, titulares e período.
4. Revogar sessões/segredos e rotacionar credenciais.
5. Acionar jurídico/segurança e cumprir comunicações aplicáveis.
6. Reconciliar e publicar post-mortem sem PII.

Alertar readiness, fila, falha de sync, assinatura inválida, 401/429/5xx anormais,
divergência e tentativa de habilitar pagamento com kill switch.

Deploy exige lint, tipos, testes, migrations efêmeras, build, scan, aprovação e
smoke test. Produção ainda depende de staging, secrets, monitoramento e rollback.
