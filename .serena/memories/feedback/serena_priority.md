---
name: Usar Serena para tudo neste repositório
description: Priorizar ferramentas Serena para exploração e edição de código
type: feedback
---

**Regra**: Use Serena para TODAS operações de código neste repositório — exploração, leitura e edição.

**Por quê**: 
- Serena é token-eficiente (lê símbolos, não arquivos inteiros)
- Melhor adequado para este projeto Python/Django
- Mantém consistência com a arquitetura do projeto

**Como aplicar**:
- Exploração: `get_symbols_overview`, `find_symbol`, `find_referencing_symbols`, `search_for_pattern`
- Edição: `replace_symbol_body`, `insert_before_symbol`, `insert_after_symbol`
- Leitura: `read_file` apenas como último recurso (quando preciso ver contexto amplo)
- Evitar: `Read`, `Edit`, `Write` tools — use Serena equivalentes
- Para shell: usar `rtk` com prefixo (já configurado via hook)
