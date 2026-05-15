# Débito Técnico: Write-once DB-level para campos de auditoria de retirada

## Status
Aberto — PR #9 (feat/pickup-state)

## Problema
`data_retirada` e `retirante_fisico` em `apps/requisitions/models.py` são protegidos apenas no nível ORM:
- `Requisicao.save()` (linhas ~240-300): verifica se campo já preenchido antes de sobrescrever
- `RequisicaoQuerySet.update()` (linhas ~70-78): bloqueia kwargs com esses campos quando já preenchidos via `exists()` + `update()`

Proteção ORM **não cobre**:
- SQL direto (`cursor.execute`)
- Bibliotecas que bypassam o ORM
- Janela de corrida no padrão `exists()` → `update()` sob concorrência

## Correção esperada
Trigger PostgreSQL `BEFORE UPDATE` na tabela `requisitions_requisicao`:
```sql
CREATE OR REPLACE FUNCTION requisicao_auditoria_retirada_write_once()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.data_retirada IS NOT NULL AND NEW.data_retirada IS DISTINCT FROM OLD.data_retirada THEN
        RAISE EXCEPTION 'data_retirada é imutável após preenchimento';
    END IF;
    IF OLD.retirante_fisico IS NOT NULL AND OLD.retirante_fisico <> '' AND NEW.retirante_fisico IS DISTINCT FROM OLD.retirante_fisico THEN
        RAISE EXCEPTION 'retirante_fisico é imutável após preenchimento';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER requisicao_write_once_auditoria
BEFORE UPDATE ON requisitions_requisicao
FOR EACH ROW EXECUTE FUNCTION requisicao_auditoria_retirada_write_once();
```

Implementar via `migrations.RunSQL(forward_sql, reverse_sql)` em nova migration.

## Bloqueio atual
Migrations são gitignored (`apps/**/migrations/*.py`). A migration com trigger não seria versionada/aplicada em CI. Resolver antes de implementar: decidir se a migration inicial deve incluir o trigger ou se o gitignore deve ser ajustado para migrations de infra (triggers, funções).

## Referências
- `apps/requisitions/models.py`: `RequisicaoQuerySet` e `Requisicao.save()`
- Guideline: "Protect snapshot/historical fields against modification after creation"
- Guideline: "Do not rely only on save(), clean() or serializer validation for critical invariants"
- CodeRabbit finding aberto em PR #9
