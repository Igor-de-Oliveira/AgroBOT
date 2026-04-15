# Padrao de Templates HTML - Portal AgroBOT

## 1. Objetivo

Definir um padrao unico para novos HTMLs do `api-portal`, com foco em:

- consistencia visual
- consistencia de comportamento
- manutencao simples
- experiencia previsivel para o usuario

Baseado nos templates:

- `system/services/api-portal/src/api-portal/templates/Arquivos.html`
- `system/services/api-portal/src/api-portal/templates/arquivo_detalhe.html`

## 2. Estrutura Obrigatoria

Todo novo template deve seguir a estrutura:

1. `<!DOCTYPE html>` e `<html lang="pt-BR">`
2. `<head>` com:
- `meta charset="UTF-8"`
- `meta name="viewport" content="width=device-width, initial-scale=1.0"`
- `<title>` especifico da pagina
- `<style>` inline (enquanto nao existir pipeline de assets centralizada)
3. `<body>` com:
- navbar padrao do portal
- `<main class="container">` como bloco principal
- area de status global (`id="status"`)
- conteudo funcional da pagina
4. `<script>` ao final do `body`

## 3. Layout e Identidade Visual

## 3.1 Navbar padrao

Manter sempre:

- `.navbar` com `display: flex`, `justify-content: space-between`
- link de marca `.logo` com texto `Portal AgroBot` e logo `/static/image.png`
- bloco `.nav-links` com navegacao principal

## 3.2 Container principal

- usar `.container` centralizado com `margin: 24px auto`
- usar `padding: 0 16px`
- definir largura maxima conforme densidade da tela:
- paginas de tabela/listagem: ate `1380px`
- paginas de detalhe/formulario: entre `760px` e `960px`

## 3.3 Superficies

- usar fundo da pagina: `#f5f7fb`
- blocos de conteudo: fundo branco (`#ffffff`)
- raio de borda padrao: `10px` (cards/tabelas) e `6px` (controles/status)
- sombra padrao: `0 2px 8px rgba(0, 0, 0, 0.08)`

## 4. Componentes de Interface

## 4.1 Status global

Padrao obrigatorio:

- elemento unico com classe base `.status`
- classe dinamica por estado:
- `.loading`
- `.error`
- `.success` (quando aplicavel)
- comportamento:
- sem mensagem: `display: none`
- com mensagem: `display: block`

Texto recomendado:

- loading: "Carregando ..."
- erro: mensagem clara da API ou fallback padrao
- sucesso: acao concluida

## 4.2 Botoes e links de acao

- estilo base unificado para `button`, `select` e `.link-btn`
- botao destrutivo com classe `.danger`
- rotulos curtos e objetivos:
- "Ver arquivo"
- "Excluir arquivo"
- "Voltar para listagem"

## 4.3 Tabela para listagens

Quando houver colecao de itens:

- envolver com `.table-wrapper` e `overflow-x: auto`
- usar `min-width` para preservar legibilidade
- separar colunas de acoes com classe `.actions`
- usar `status-badge` para estados de processamento

## 4.4 Empty state

Sempre prever estado sem dados:

- bloco dedicado (`id="empty-state"` ou equivalente)
- mensagem objetiva:
- "Nenhum arquivo registrado."

## 4.5 Paginacao

Para endpoints paginados:

- controles `Anterior` e `Proxima`
- indicador de pagina + total
- ocultar bloco quando `total = 0`

## 5. Responsividade

Incluir breakpoints minimos:

- `@media (max-width: 900px)` para reduzir colunas nao criticas
- `@media (max-width: 640px)` para ajustar fonte e paddings

Diretriz:

- manter acao principal sempre visivel em mobile
- evitar overflow horizontal sem wrapper

## 6. Padrao de JavaScript (Vanilla)

## 6.1 Estado local

Usar objeto `state` para estado de tela, por exemplo:

- `page`
- `pageSize`
- `total`
- `loading`

## 6.2 Funcoes utilitarias obrigatorias

Padroes recomendados:

- `setStatus(type, message)`
- `formatDate(dateString)` (com `toLocaleString("pt-BR")`)
- funcoes de render separadas por responsabilidade (`renderRows`, `renderStatusBadge`, etc.)

## 6.3 Consumo de API

Padrao para `fetch`:

1. ativar loading antes da requisicao
2. converter resposta com `await response.json()`
3. validar `response.ok`
4. usar `payload.detail` quando disponivel
5. aplicar fallback de erro amigavel
6. finalizar loading em `finally`

## 6.4 Eventos

- usar `addEventListener` (evitar logica inline, exceto navegacao simples)
- para listas dinamicas, usar delegacao de eventos no container

## 7. Convencoes de API no Frontend

- listar: `GET /api/files?page=<n>&page_size=<n>`
- detalhe: `GET /api/files/{id}`
- exclusao: `DELETE /api/files/{id}`
- links externos (download): validar com `new URL(...)` antes de abrir

## 8. Qualidade e Acessibilidade

Minimos obrigatorios por pagina:

- `lang="pt-BR"`
- textos de botao autoexplicativos
- `alt` em imagens
- confirmacao para acao destrutiva (`window.confirm`)
- feedback visual para loading/erro/sucesso

## 9. Checklist para Novos HTMLs

Antes de concluir um novo template, validar:

1. Navbar e container padrao aplicados
2. Area de status implementada (se for nessesario)
3. Estados de loading/erro/sucesso tratados (se for nessesario)
4. Empty state tratado (se houver lista)
5. Responsividade minima em 900px e 640px
6. Consumo de API com validacao de `response.ok`
7. Mensagens de erro amigaveis ao usuario
8. Acoes destrutivas com confirmacao
9. Formatacao de data em `pt-BR`
10. Terminologia consistente com o dominio ("arquivo", "processamento", "detalhe")

## 10. Evolucao Recomendada

Quando houver maturidade para refatoracao:

- extrair CSS compartilhado para arquivo comum
- extrair funcoes JS comuns (`setStatus`, `formatDate`, `request helper`)
- padronizar naming de templates em minusculo com `_` (ex.: `arquivo_detalhe.html`)
