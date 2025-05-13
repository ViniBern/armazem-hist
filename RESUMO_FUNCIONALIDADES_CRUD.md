# Resumo das Novas Funcionalidades CRUD e Instruções

Este documento detalha as novas funcionalidades de Gerenciamento (CRUD - Criar, Ler, Atualizar, Deletar) implementadas no sistema de Laticínios Armazém. Essas funcionalidades permitem ao administrador do sistema um controle mais dinâmico sobre as áreas de armazenamento, o catálogo de produtos e os produtos específicos alocados em cada área.

## 1. Gerenciamento de Áreas de Armazenamento

Permite criar, visualizar, editar e excluir as áreas onde os produtos são armazenados.

*   **Listar Áreas**: 
    *   Acesse `/admin/areas` para ver todas as áreas cadastradas.
    *   A página exibe ID, Nome e Tipo de Armazenamento de cada área.
*   **Adicionar Nova Área**:
    *   Clique em "Adicionar Nova Área" na página de listagem de áreas ou acesse `/admin/areas/adicionar`.
    *   Campos obrigatórios: ID da Área (único), Nome da Área, Tipo de Armazenamento (Refrigerado, Congelado, Seco).
*   **Editar Área Existente**:
    *   Na lista de áreas, clique em "Editar" para a área desejada ou acesse `/admin/areas/editar/<id_area_original>`.
    *   Você pode alterar o Nome e o Tipo de Armazenamento. O ID da Área não pode ser alterado após a criação.
*   **Excluir Área**:
    *   Na lista de áreas, clique em "Excluir" para a área desejada (via método POST).
    *   O sistema verificará se a área contém produtos. Se contiver, a exclusão será impedida para manter a integridade dos dados, e uma mensagem informativa será exibida. Uma área só pode ser excluída se estiver vazia.
*   **Permissão Necessária**: `gerenciar_areas` (normalmente atribuída à função "gerente").

## 2. Gerenciamento de Produtos do Catálogo

Permite gerenciar a lista mestre de todos os produtos que podem ser armazenados.

*   **Listar Produtos do Catálogo**:
    *   Acesse `/admin/catalogo` para ver todos os produtos do catálogo.
    *   A página exibe ID e Nome de cada produto.
*   **Adicionar Novo Produto ao Catálogo**:
    *   Clique em "Adicionar Novo Produto ao Catálogo" na página de listagem ou acesse `/admin/catalogo/adicionar`.
    *   Campos obrigatórios: ID do Produto (único, ex: "QUEIJO001"), Nome do Produto.
*   **Editar Produto do Catálogo**:
    *   Na lista de produtos do catálogo, clique em "Editar" ou acesse `/admin/catalogo/editar/<id_produto_catalogo>`.
    *   Você pode alterar o Nome do Produto. O ID do Produto não pode ser alterado.
*   **Excluir Produto do Catálogo**:
    *   Na lista de produtos do catálogo, clique em "Excluir" (via método POST).
    *   O sistema verificará se o produto do catálogo está sendo usado em alguma instância de produto nas áreas. Se estiver, a exclusão será impedida, e uma mensagem informativa será exibida.
*   **Permissão Necessária**: `gerenciar_catalogo_produtos` (normalmente atribuída à função "gerente").

## 3. Gerenciamento de Produtos Específicos nas Áreas

Permite editar e remover instâncias de produtos que já foram adicionadas a uma área de armazenamento específica.

*   **Visualização e Acesso**: 
    *   As opções para editar ou excluir um produto específico aparecem na tabela de produtos dentro da página de detalhes de cada área (`/armazem/<id_area>`).
*   **Adicionar Produto a uma Área**:
    *   A funcionalidade de adicionar produtos a uma área (disponível na página de detalhes da área para usuários com permissão) agora utiliza o catálogo de produtos. Você selecionará um produto do catálogo e informará quantidade, data de validade e lote.
*   **Editar Produto em uma Área**:
    *   Ao lado de cada produto listado na página de detalhes da área, clique em "Editar". Isso levará para `/admin/area/<id_area>/produto/<id_produto_area>/editar`.
    *   Você pode alterar: Quantidade, Data de Validade e Lote.
    *   O nome do produto e seu ID de catálogo são fixos para essa instância.
*   **Excluir Produto de uma Área**:
    *   Ao lado de cada produto listado na página de detalhes da área, clique em "Excluir" (via método POST).
    *   Isso removerá completamente a instância específica daquele produto (lote/validade) da área.
*   **Permissão Necessária**: `gerenciar_produtos_em_areas` (normalmente atribuída à função "gerente").

## 4. Navegação e Interface

*   Foram adicionados links nas páginas de administração para facilitar a navegação entre as seções de gerenciamento de áreas e catálogo.
*   Na página de detalhes da área, usuários com permissão verão botões para "Gerenciar Áreas" e "Gerenciar Catálogo".
*   As mensagens de feedback (sucesso, erro, aviso) foram padronizadas para todas as operações CRUD.

## 5. Considerações Importantes

*   **Permissões**: Todas as funcionalidades de gerenciamento (CRUD) são protegidas por permissões. Certifique-se de que os usuários (especialmente os administradores/gerentes) tenham as permissões corretas (`gerenciar_areas`, `gerenciar_catalogo_produtos`, `gerenciar_produtos_em_areas`) atribuídas às suas funções no `schema.sql` ou através de uma interface de gerenciamento de usuários (se implementada futuramente).
*   **Backup**: Antes de realizar operações de exclusão em massa ou alterações significativas, é sempre recomendável ter um backup do arquivo do banco de dados (`laticinios.db`).
*   **Teste**: Recomenda-se testar todas as funcionalidades em um ambiente de desenvolvimento ou homologação antes de aplicar em produção, especialmente as operações de exclusão.

Esperamos que estas novas funcionalidades tornem o gerenciamento do seu armazém de laticínios mais eficiente e completo!

