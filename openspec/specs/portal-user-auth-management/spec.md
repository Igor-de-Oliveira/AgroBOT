# portal-user-auth-management Specification

## Purpose
TBD - created by archiving change sistema-login-de-usuarios. Update Purpose after archive.
## Requirements
### Requirement: Exigir login para acesso ao portal
The system SHALL exigir autenticacao previa para permitir acesso as rotas protegidas do portal.

#### Scenario: Acesso inicial sem sessao autenticada
- **WHEN** o usuario acessar o portal sem sessao valida
- **THEN** o sistema SHALL redirecionar para a tela de login
- **AND** SHALL impedir renderizacao de conteudo protegido

#### Scenario: Sessao autenticada valida
- **WHEN** o usuario possuir sessao autenticada valida
- **THEN** o sistema SHALL permitir acesso as rotas protegidas do portal

### Requirement: Disponibilizar autenticacao por credenciais
The system SHALL autenticar usuarios por credenciais de `username` e `password` validadas no backend.

#### Scenario: Login com credenciais validas
- **WHEN** o usuario informar `username` e `password` corretos
- **THEN** o sistema SHALL criar sessao autenticada
- **AND** SHALL redirecionar para a pagina principal protegida

#### Scenario: Login com credenciais invalidas
- **WHEN** o usuario informar credenciais invalidas
- **THEN** o sistema SHALL negar autenticacao
- **AND** SHALL exibir mensagem de erro amigavel sem revelar detalhes sensiveis

### Requirement: Permitir logout com invalidacao de sessao
The system SHALL encerrar a sessao autenticada quando o usuario solicitar logout.

#### Scenario: Usuario executa logout
- **WHEN** o usuario acionar a opcao de logout
- **THEN** o sistema SHALL invalidar a sessao atual
- **AND** SHALL redirecionar para a tela de login

### Requirement: Disponibilizar gestao de usuarios pela navbar
The system SHALL disponibilizar acesso a tela de gestao de usuarios na navbar da tela principal do portal.

#### Scenario: Usuario autenticado abre tela de usuarios
- **WHEN** o usuario autenticado clicar no item de usuarios da navbar
- **THEN** o sistema SHALL abrir a tela de cadastro/edicao/remocao de usuarios

### Requirement: Restringir gestao de usuarios por credential administrativa
The system SHALL permitir operacoes de gestao de usuarios apenas para contas com `credential=admin`.

#### Scenario: Usuario administrador acessa gestao de usuarios
- **WHEN** um usuario com `credential=admin` acessar rotas de gestao de usuarios
- **THEN** o sistema SHALL autorizar as operacoes permitidas de cadastro, edicao, inativacao e remocao

#### Scenario: Usuario nao administrador tenta acessar gestao de usuarios
- **WHEN** um usuario autenticado sem `credential=admin` tentar acessar rotas de gestao de usuarios
- **THEN** o sistema SHALL negar o acesso por autorizacao

### Requirement: Cadastrar, editar e remover usuarios no portal
The system SHALL permitir operacoes de cadastro, edicao, inativacao e remocao fisica de usuarios na tela de gestao.

#### Scenario: Cadastro de novo usuario
- **WHEN** o usuario autorizado cadastrar um novo usuario com dados validos
- **THEN** o sistema SHALL persistir o usuario na nova tabela relacional
- **AND** SHALL armazenar senha somente como hash seguro

#### Scenario: Edicao de usuario existente
- **WHEN** o usuario autorizado editar um usuario existente
- **THEN** o sistema SHALL atualizar apenas campos permitidos
- **AND** SHALL reprocessar hash caso haja alteracao de senha

#### Scenario: Inativacao de usuario existente
- **WHEN** o usuario administrador inativar um usuario existente
- **THEN** o sistema SHALL atualizar o usuario para `is_active=false`
- **AND** SHALL impedir novos logins dessa conta

#### Scenario: Remocao fisica de usuario existente
- **WHEN** o usuario administrador remover fisicamente um usuario existente
- **THEN** o sistema SHALL excluir o registro do usuario conforme regra operacional definida
- **AND** SHALL refletir o estado atualizado na listagem

### Requirement: Persistir usuarios em nova tabela dedicada
The system SHALL criar e utilizar uma tabela dedicada para identidade de usuarios do portal.

#### Scenario: Estrutura minima da tabela de usuarios
- **WHEN** a migration da funcionalidade for aplicada
- **THEN** o sistema SHALL criar tabela com identificador unico, `username` unico, `credential`, `password_hash`, status de ativo e metadados de auditoria

#### Scenario: Classificacao por tipo de usuario
- **WHEN** um usuario for criado ou atualizado
- **THEN** o sistema SHALL persistir `credential` com valores iniciais `admin` ou `usuario`
- **AND** SHALL permitir extensao controlada para novos tipos de credencial no futuro

### Requirement: Proteger dados sensiveis de autenticacao
The system SHALL impedir exposicao de credenciais sensiveis em APIs, templates e logs.

#### Scenario: Consulta de usuarios na tela de gestao
- **WHEN** a tela de usuarios consultar dados cadastrados
- **THEN** o sistema SHALL retornar apenas campos nao sensiveis
- **AND** SHALL nunca retornar senha em texto claro ou `password_hash`

#### Scenario: Operacoes de autenticacao e gestao
- **WHEN** ocorrer login, cadastro ou edicao de senha
- **THEN** o sistema SHALL nunca registrar senha informada em logs de aplicacao

