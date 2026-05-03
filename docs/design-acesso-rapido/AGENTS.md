# AGENTS.md

Esta pasta contém sínteses operacionais enxutas para leitura rápida por agentes de IA.

Use esta pasta como primeira parada antes de consultar a documentação completa.

## Rotas rápidas

- `stack.md`: decisões técnicas, stack, apps esperados e fronteiras de domínio.
- `frontend-arquitetura-piloto.md`: arquitetura canônica da SPA do piloto, bloco 0, estrutura de pastas, sequência de implementação, `Makefile`, seed mínima e CI.
- `api-contracts.md`: contratos DRF, autenticação, autorização, serializers, erros, paginação e OpenAPI.
- `matriz-invariantes.md`: invariantes críticos, camada esperada, reforços e testes mínimos.
- `matriz-permissoes.md`: papéis, escopos, permissões, visibilidade e testes de autorização.
- `estado-transicoes-requisicao.md`: estados, eventos, transições, bloqueios e efeitos de estoque/reserva.

## Regras de uso

- Não leia todos os documentos por padrão; escolha o arquivo pela dúvida.
- Ao trabalhar na SPA do piloto, confirme primeiro o bloco 0 e a ordem de implementação em `frontend-arquitetura-piloto.md`.
- Use as matrizes como referência operacional, não como substitutas da documentação completa.
- Se a síntese não resolver a dúvida, consulte `../design-acesso-ocasional/` apenas no ponto necessário.
- Em caso de conflito com a documentação completa, prevalece `../design-acesso-ocasional/`, salvo decisão posterior registrada.
- Ao alterar regra de negócio, atualize a síntese afetada e o documento completo correspondente.
