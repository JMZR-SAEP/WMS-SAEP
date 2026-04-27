# Importação SCPI CSV — ERP-SAEP

## 1. Objetivo

Definir como o ERP-SAEP importa, normaliza e aplica dados de materiais e saldos vindos do SCPI por arquivo CSV.

O SCPI é a fonte oficial dos dados cadastrais dos materiais e da correção de saldo físico. O ERP-SAEP usa esses dados como base operacional, mas não substitui o cadastro oficial do SCPI.

---

## 2. Arquivo de origem

O arquivo analisado é um relatório CSV emitido pelo SCPI.

Características observadas:

- Encoding: UTF-8 com BOM.
- Separador: ponto e vírgula (`;`).
- O relatório contém apenas itens visíveis e com estoque maior que zero.
- Pode conter descrições longas quebradas em múltiplas linhas físicas.
- Uma nova linha lógica de produto começa quando a linha inicia com código no padrão `000.000.000;`.
- Linhas que não começam com código de produto devem ser tratadas como continuação da descrição do produto anterior.

Cabeçalhos identificados no relatório:

- `CADPRO`
- `DISC1`
- `UNID1`
- `QUAN3`
- `VAUN1`
- `PRECOMEDIO`
- `GRUPO`
- `SUBGRUPO`
- `NOMEGRUPO`
- `NOMESUBGRUPO`
- `DISCR1`
- `QUANMIN`
- `QUANMAX`
- `CODREDUZ`
- `CODBARRA`
- `NOCULTAR`
- `USUARIO`
- `DTAINSERE`
- `USUALT`
- `DTAALT`
- `LOCALFISICO`

---

## 3. Campos importados no MVP

No MVP, devem ser importados apenas os campos necessários ao ERP-SAEP:

| Campo normalizado | Origem SCPI | Observação |
|---|---|---|
| `codigo_completo` | `CADPRO` | Código no padrão `xxx.yyy.zzz` |
| `grupo_codigo` | `GRUPO` | Primeira parte de `CADPRO` |
| `grupo_nome` | `NOMEGRUPO` | Nome do grupo |
| `subgrupo_codigo` | `SUBGRUPO` | Segunda parte de `CADPRO` |
| `subgrupo_nome` | `NOMESUBGRUPO` | Nome do subgrupo |
| `sequencial_produto` | terceira parte de `CADPRO` | Trecho `zzz` |
| `nome` | `DISC1` | Nome principal do material |
| `descricao` | `DISCR1` | Descrição detalhada, quando preenchida |
| `unidade_medida` | `UNID1` | Unidade oficial do SCPI |
| `saldo_fisico` / `saldo_inicial` | `QUAN3` | Usado conforme carga inicial ou reimportação |

Campos fora da importação do MVP:

- `VAUN1`
- `PRECOMEDIO`
- `QUANMIN`
- `QUANMAX`
- `CODREDUZ`
- `CODBARRA`
- `NOCULTAR`
- `USUARIO`
- `DTAINSERE`
- `USUALT`
- `DTAALT`
- `LOCALFISICO`

O campo `NOCULTAR` não precisa ser importado no MVP, pois o relatório de origem já traz apenas itens visíveis e com estoque maior que zero.

---

## 4. Normalização

A importação deve possuir uma etapa de normalização antes da aplicação no banco do ERP-SAEP.

Regras:

- Reconstruir produtos lógicos a partir das linhas físicas do CSV.
- Uma nova linha lógica começa quando a linha inicia com código no padrão `000.000.000;`.
- Linhas que não começam com código de produto são continuação da descrição do produto anterior.
- Após reconstrução, cada produto lógico deve possuir a mesma quantidade de colunas do cabeçalho.
- O importador deve tratar problemas de leitura causados por BOM, quebras de linha em descrições e estrutura própria do relatório SCPI.

---

## 5. Carga inicial

Na carga inicial:

- O ERP-SAEP importa grupos, subgrupos e materiais.
- O campo `QUAN3` cria o saldo inicial do material.
- Deve ser registrada movimentação de **entrada por saldo inicial**.
- Essa carga pode ser executada por modo técnico/script administrativo durante o piloto, se isso acelerar a validação.

---

## 6. Reimportações futuras

Em reimportações futuras:

- Se o material já existir no ERP-SAEP com o mesmo código completo, seus dados cadastrais devem ser atualizados conforme o SCPI.
- Para materiais já existentes, `QUAN3` deve atualizar o saldo físico do ERP-SAEP.
- Quando `QUAN3` alterar o saldo físico de material existente, registrar evento histórico **Atualização de saldo via SCPI**.

Esse evento deve guardar:

- saldo anterior;
- saldo novo;
- diferença;
- data/hora da importação;
- usuário que executou a importação.

Essa atualização não é ajuste manual de estoque; é sincronização formal com fonte oficial externa.

Se um material novo aparecer pela primeira vez:

- Deve ser criado automaticamente como material ativo.
- `QUAN3` deve ser usado como saldo inicial.
- Deve gerar movimentação de entrada por saldo inicial.
- Não precisa de confirmação prévia do superusuário.
- Não deve aparecer como erro, pois é caso esperado.

---

## 7. Materiais ausentes no CSV

Se um material existir no ERP-SAEP, mas não vier no CSV do SCPI:

- Não deve ser inativado automaticamente.
- Deve aparecer em relatório/lista de divergência.
- A ausência não significa necessariamente que deixou de existir, pois o relatório fonte contém apenas itens visíveis e com estoque maior que zero.
- A lista de ausentes deve ser exibida para análise.
- A lista pode ser exportada.
- A importação não deve oferecer inativação automática a partir dessa lista.
- Inativação continua sendo ação manual separada, feita por fluxo administrativo controlado pelo chefe de almoxarifado ou superusuário, respeitando saldo físico e saldo reservado zerados.

---

## 8. Divergência crítica

Pode ocorrer quando o saldo físico importado do SCPI fica menor que o saldo reservado no ERP-SAEP.

Exemplo:

- Saldo físico importado: 10.
- Saldo reservado no ERP-SAEP: 20.
- Saldo disponível: -10.

Regras:

- A importação deve atualizar o saldo físico mesmo assim.
- O sistema registra divergência crítica.
- O sistema não cancela reservas automaticamente.
- O material fica bloqueado para novas requisições e novas autorizações.
- Requisições já autorizadas continuam existindo.
- O Almoxarifado ainda pode cancelar requisições autorizadas, atender parcialmente quando houver saldo físico suficiente e realizar estornos quando aplicável.
- O material continua visível em relatórios e histórico.
- O sistema deve mostrar alerta claro de divergência crítica para o Almoxarifado.
- A divergência crítica deve aparecer como pendência/alerta no painel de Gestão do Almoxarifado para acompanhamento pelo chefe de almoxarifado até ser resolvida.
- A divergência crítica deve ser considerada resolvida automaticamente quando o saldo físico voltar a ser maior ou igual ao saldo reservado.
- A resolução pode ocorrer após cancelamentos de requisições autorizadas, atendimentos parciais, estornos ou nova importação CSV.
- Quando a divergência for resolvida, o material deve sair da lista de pendências/alertas de gestão e voltar a permitir novas requisições e autorizações, desde que tenha saldo disponível.

---

## 9. Pré-visualização da importação

No MVP completo, a importação deve ter pré-visualização técnica antes de aplicar alterações.

Fluxo:

1. Superusuário envia o CSV.
2. Sistema normaliza o arquivo.
3. Sistema valida se existem erros técnicos impeditivos.
4. Sistema apresenta resumo.
5. Superusuário confirma ou cancela. Quando houver alertas ou divergências, a confirmação deve ser explícita.
6. Se confirmado e não houver erro técnico impeditivo, sistema aplica alterações.

A pré-visualização deve apresentar:

- total de produtos lógicos lidos;
- quantidade de materiais novos;
- quantidade de materiais existentes que serão atualizados;
- materiais existentes no ERP-SAEP que não vieram no CSV;
- quantidade de erros técnicos;
- lista detalhada apenas dos erros;
- botão para confirmar importação;
- botão para cancelar.

A pré-visualização e o resultado da importação devem separar achados por categoria:

- materiais ausentes no CSV;
- materiais novos criados;
- materiais atualizados;
- saldos atualizados via SCPI;
- divergências críticas: saldo físico menor que saldo reservado;
- erros técnicos.

Divergências e atualizações normais não devem ser tratadas como erros técnicos.

Se não houver erro técnico impeditivo, a importação pode ser aplicada mesmo quando houver alertas, materiais ausentes no CSV, saldos atualizados ou divergências críticas. Nesses casos, o status da importação deve ser **Concluída com alertas**.

Quando a pré-visualização apresentar alertas ou divergências, o sistema deve destacá-los antes da confirmação e exigir confirmação explícita do superusuário, como: “Estou ciente dos alertas e desejo aplicar a importação.”

---

## 10. Histórico de importações

O MVP completo deve manter histórico das importações CSV realizadas.

Esse recurso tem caráter técnico/administrativo e não é um relatório operacional principal.

Deve exibir:

- data/hora da importação;
- usuário que executou;
- arquivo importado;
- total de produtos lógicos lidos;
- quantidade de materiais novos;
- quantidade de materiais atualizados;
- quantidade de saldos atualizados via SCPI;
- quantidade de materiais ausentes no CSV;
- quantidade de divergências críticas;
- quantidade de erros técnicos;
- status da importação.

Status possíveis:

- **Concluída**: importação aplicada sem erros técnicos nem divergências críticas.
- **Concluída com alertas**: importação aplicada sem erro técnico impeditivo, mas com alertas, materiais ausentes no CSV, saldos atualizados ou divergências críticas.
- **Falhou**: importação não foi aplicada por erro técnico impeditivo. No MVP, a importação deve seguir a regra de tudo ou nada.

Acesso:

- Superusuário pode acessar o histórico completo.
- Chefe de almoxarifado pode consultar o histórico.

---

## 11. Erros de importação

O ERP-SAEP deve confiar que os dados cadastrais principais já foram validados pelo SCPI, incluindo:

- formato do `CADPRO`;
- relação entre `CADPRO`, `GRUPO` e `SUBGRUPO`;
- nome do produto;
- unidade de medida;
- quantidade/saldo;
- ausência de duplicidade lógica.

O importador do ERP-SAEP deve reportar principalmente erros técnicos de leitura, normalização ou salvamento.

No MVP, a importação deve seguir a regra de **tudo ou nada**: se houver erro técnico impeditivo, nenhuma alteração deve ser aplicada. O sistema não deve importar parcialmente os registros válidos quando houver falha técnica que comprometa a leitura, normalização ou gravação confiável do arquivo.

Alertas e divergências não são erros técnicos impeditivos. Materiais ausentes no CSV, saldos atualizados via SCPI e divergências críticas devem ser registrados no resultado da importação, mas não impedem a aplicação quando o arquivo foi lido, normalizado e validado tecnicamente com sucesso.

Devem ser tratados como erro:

- CSV ilegível;
- cabeçalho esperado não encontrado;
- linha reconstruída que não consiga ser interpretada;
- falha ao salvar material;
- falha ao salvar grupo;
- falha ao salvar subgrupo;
- falha ao salvar estoque;
- falha ao salvar movimentação de saldo inicial;
- falha ao registrar atualização de saldo via SCPI.

Ao final da importação, o sistema deve apresentar relatório apenas de erros, sem necessidade de relatório detalhado de sucessos. Quando a importação falhar por erro técnico impeditivo, o histórico deve registrar o status **Falhou** e nenhuma alteração de material, grupo, subgrupo, estoque ou movimentação deve ser persistida.

---

## 12. Permissões

- Durante o piloto, a importação pode ser feita por script ou modo técnico controlado pelo administrador.
- No MVP completo, a importação deve ser executada pelo superusuário por comando, endpoint autenticado ou outro fluxo técnico controlado.
- Superusuário não opera estoque no dia a dia; sua atuação aqui é administrativa/técnica.

---

## 13. Fora do MVP

- Importação de campos financeiros do SCPI.
- Importação de preço médio.
- Importação de código de barras.
- Importação de local físico.
- Importação de estoque mínimo e máximo.
- Sincronização automática com SCPI.
- Interface avançada de conciliação bidirecional.
