# laticinios_armazem/app.py

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta, date
import functools
import logging
from models import (
    Usuario, ProdutoLacteo, AreaArmazem, Venda, ProdutoCatalogo,
    popular_dados_iniciais, init_db 
)

# Inicializa a aplicação Flask
app = Flask(__name__)
# Define uma chave secreta para a sessão. Em produção, use uma chave mais segura e gerada aleatoriamente.
app.secret_key = 'chave_secreta_para_sessoes_flask_laticinios_minerva'

# Configura o logging básico para a aplicação, útil para depuração.
logging.basicConfig(level=logging.DEBUG)

# Filtro Jinja2 personalizado para converter strings de data em objetos date.
def to_date_filter(value):
    """Converte uma string de data (AAAA-MM-DD) para um objeto date.
    Se o valor já for um objeto date, retorna o próprio valor.
    Retorna o valor original em caso de erro na conversão.
    """
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (ValueError, TypeError) as e:
        logging.error(f"Erro ao converter data: {value}, erro: {e}")
        return value

# Registra o filtro personalizado no ambiente Jinja2 da aplicação.
app.jinja_env.filters['to_date'] = to_date_filter

# Inicializa o banco de dados (cria tabelas se não existirem).
init_db()

# Popula o banco de dados com dados iniciais (se ainda não estiver populado).
popular_dados_iniciais()

# --- Autenticação e Controle de Acesso ---
def login_necessario(permissao_requerida: str = None):
    """Decorador para proteger rotas que exigem login e, opcionalmente, uma permissão específica."""
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(*args, **kwargs):
            if 'username' not in session or 'password' not in session: # Verifica também a senha na sessão
                flash("Por favor, faça login para acessar esta página.", "warning")
                return redirect(url_for('login', next=request.url))
            
            usuario_logado = Usuario.verificar_senha(session['username'], session.get('password'))
            if not usuario_logado:
                session.clear()
                flash("Sua sessão é inválida ou expirou. Por favor, faça login novamente.", "danger")
                return redirect(url_for('login'))

            # Armazena o objeto usuário na sessão para uso pelo context_processor
            # session['usuario_obj'] = usuario_logado # Não é ideal armazenar objetos complexos diretamente na sessão
                                                # O context_processor deve buscar o objeto a cada request se necessário.

            if permissao_requerida and not usuario_logado.tem_permissao(permissao_requerida):
                flash("Você não tem permissão para realizar esta ação ou acessar esta página.", "danger")
                return redirect(request.referrer or url_for('pagina_inicial_armazem')) 
            
            return view_func(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Rota para login de usuários."""
    if request.method == 'POST':
        username = request.form.get('username')
        senha = request.form.get('password')
        usuario = Usuario.verificar_senha(username, senha)

        if usuario:
            session['username'] = usuario.username
            session['user_funcao'] = usuario.funcao # Mantido para referência rápida, mas o objeto é rei
            session['user_nome'] = usuario.nome   # Mantido para referência rápida
            session['password'] = senha # ATENÇÃO: Prática insegura para produção.
            app.logger.debug(f"Sessão criada para usuário: {usuario.username}")
            flash(f"Login bem-sucedido! Bem-vindo(a), {usuario.nome}.", "success")
            
            next_url = request.args.get('next')
            return redirect(next_url or url_for('pagina_inicial_armazem'))
        else:
            flash("Usuário ou senha inválidos. Tente novamente.", "danger")
    
    if 'username' in session:
        return redirect(url_for('pagina_inicial_armazem'))
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Rota para logout de usuários."""
    session.clear()
    flash("Você foi desconectado com sucesso.", "info")
    return redirect(url_for('login'))

# --- Rotas Principais da Aplicação ---
@app.route('/')
@login_necessario()
def index_redirect():
    """Rota raiz da aplicação, redireciona para a página inicial do armazém."""
    return redirect(url_for('pagina_inicial_armazem'))

@app.route('/armazem')
@login_necessario(permissao_requerida='visualizar_armazem')
def pagina_inicial_armazem():
    """Rota para a página inicial do armazém, exibe todas as áreas."""
    areas = AreaArmazem.listar_todas()
    return render_template('armazem.html', areas=areas)

@app.route('/armazem/<id_area>')
@login_necessario(permissao_requerida='detalhes_area')
def detalhes_da_area(id_area):
    """Rota para exibir os detalhes de uma área de armazenamento específica."""
    area = AreaArmazem.buscar_por_id(id_area)
    if not area:
        flash(f"Área com ID '{id_area}' não encontrada.", "danger")
        return redirect(url_for('pagina_inicial_armazem'))
    
    produtos_na_area = sorted(area.listar_produtos(), key=lambda p: p.data_validade)
    produtos_catalogo_list = ProdutoCatalogo.listar_todos()
    produtos_catalogo_dropdown = {pc.id_produto: {'nome': pc.nome} for pc in produtos_catalogo_list}

    return render_template('area_detalhes.html', 
                         area=area, 
                         produtos=produtos_na_area,
                         produtos_catalogo=produtos_catalogo_dropdown,
                         data_hoje=date.today()
                        )

@app.route('/armazem/<id_area>/adicionar_produto', methods=['POST'])
@login_necessario(permissao_requerida='gerenciar_produtos_em_areas')
def adicionar_produto_na_area(id_area):
    """Rota para adicionar um novo produto a uma área de armazenamento."""
    area = AreaArmazem.buscar_por_id(id_area)
    if not area:
        flash(f"Área '{id_area}' não encontrada.", "danger")
        return redirect(url_for('pagina_inicial_armazem'))

    try:
        id_catalogo_produto = request.form.get('id_produto_catalogo')
        quantidade_str = request.form.get('quantidade')
        data_validade_str = request.form.get('data_validade')
        lote = request.form.get('lote')

        if not all([id_catalogo_produto, quantidade_str, data_validade_str, lote]):
            flash("Todos os campos são obrigatórios para adicionar o produto.", "warning")
            return redirect(url_for('detalhes_da_area', id_area=id_area))

        quantidade = int(quantidade_str)
        if quantidade <= 0:
            flash("A quantidade deve ser um número positivo.", "warning")
            return redirect(url_for('detalhes_da_area', id_area=id_area))

        produto_do_catalogo_obj = ProdutoCatalogo.buscar_por_id(id_catalogo_produto)
        if not produto_do_catalogo_obj:
            flash("Produto do catálogo inválido.", "danger")
            return redirect(url_for('detalhes_da_area', id_area=id_area))

        novo_produto = ProdutoLacteo(
            id_catalogo_produto=id_catalogo_produto,
            nome=produto_do_catalogo_obj.nome, 
            quantidade=quantidade,
            data_validade_str=data_validade_str,
            lote=lote.strip().upper()
        )
        area.adicionar_produto(novo_produto)
        flash(f"Produto '{novo_produto.nome}' (Lote: {novo_produto.lote}) adicionado/atualizado com sucesso na área {area.nome}!", "success")
    
    except ValueError as e: 
        flash(f"Erro ao adicionar produto: {e}", "danger")
    except Exception as e: 
        app.logger.error(f"Erro inesperado ao adicionar produto na área {id_area}: {e}", exc_info=True)
        flash("Ocorreu um erro inesperado ao processar sua solicitação.", "danger")
        
    return redirect(url_for('detalhes_da_area', id_area=id_area))

@app.route('/armazem/<id_area>/vender_produto', methods=['POST'])
@login_necessario(permissao_requerida='registrar_venda')
def vender_produto_da_area(id_area):
    """Rota para registrar a venda de um produto de uma área específica."""
    area = AreaArmazem.buscar_por_id(id_area)
    if not area:
        flash(f"Área '{id_area}' não encontrada.", "danger")
        return redirect(url_for('pagina_inicial_armazem'))

    try:
        id_instancia_venda_str = request.form.get('id_instancia_venda') 
        quantidade_venda_str = request.form.get('quantidade_venda')
        destino_venda = request.form.get('destino_venda')

        if not all([id_instancia_venda_str, quantidade_venda_str, destino_venda]):
            flash("Informações insuficientes para registrar a venda.", "warning")
            return redirect(url_for('detalhes_da_area', id_area=id_area))
        
        quantidade_venda = int(quantidade_venda_str)
        id_instancia_venda = int(id_instancia_venda_str)

        if quantidade_venda <= 0:
            flash("A quantidade para venda deve ser positiva.", "warning")
            return redirect(url_for('detalhes_da_area', id_area=id_area))

        produto_para_venda = ProdutoLacteo.buscar_instancia_por_id(id_instancia_venda)

        if not produto_para_venda:
            flash(f"Produto com ID de instância '{id_instancia_venda}' não encontrado.", "danger")
            return redirect(url_for('detalhes_da_area', id_area=id_area))
        
        produto_na_area_correta = any(p.id == id_instancia_venda for p in area.listar_produtos())
        if not produto_na_area_correta:
            flash(f"Produto com ID de instância '{id_instancia_venda}' não pertence à área '{area.nome}'.", "danger")
            return redirect(url_for('detalhes_da_area', id_area=id_area))

        if produto_para_venda.quantidade < quantidade_venda:
            flash(f"Quantidade insuficiente em estoque para '{produto_para_venda.nome}' (Lote: {produto_para_venda.lote}). Disponível: {produto_para_venda.quantidade}", "warning")
            return redirect(url_for('detalhes_da_area', id_area=id_area))

        sucesso_remocao = area.remover_produto(produto_para_venda.id, quantidade_venda)

        if sucesso_remocao:
            nova_venda = Venda(
                id_catalogo_produto=produto_para_venda.id_catalogo_produto,
                nome=produto_para_venda.nome,
                lote=produto_para_venda.lote,
                data_validade_produto=produto_para_venda.data_validade.strftime('%Y-%m-%d'),
                quantidade_vendida=quantidade_venda,
                destino=destino_venda.strip(),
                area_origem_id=id_area,
                usuario_responsavel=session['username']
            )
            Venda.registrar(nova_venda)
            flash(f"Venda de {quantidade_venda} unidade(s) de '{produto_para_venda.nome}' (Lote: {produto_para_venda.lote}) registrada com sucesso!", "success")
        else:
            flash(f"Falha ao tentar vender {quantidade_venda} unidade(s) de '{produto_para_venda.nome}'. Verifique o estoque ou ID do produto.", "danger")
    
    except ValueError: 
        flash("Quantidade para venda inválida ou ID do produto inválido. Devem ser números.", "danger")
    except Exception as e:
        app.logger.error(f"Erro inesperado ao vender produto da área {id_area}: {e}", exc_info=True)
        flash("Ocorreu um erro inesperado ao processar a venda.", "danger")

    return redirect(url_for('detalhes_da_area', id_area=id_area))

# --- Rotas de Gerenciamento (CRUD) ---

@app.route('/admin/areas')
@login_necessario(permissao_requerida='gerenciar_areas')
def listar_areas_admin():
    """Rota para listar todas as áreas de armazenamento para administração."""
    areas = AreaArmazem.listar_todas()
    return render_template('admin_listar_areas.html', areas=areas)

@app.route('/admin/areas/adicionar', methods=['GET', 'POST'])
@login_necessario(permissao_requerida='gerenciar_areas')
def adicionar_area():
    """Rota para adicionar uma nova área de armazenamento."""
    if request.method == 'POST':
        id_area = request.form.get('id_area')
        nome = request.form.get('nome')
        tipo_armazenamento = request.form.get('tipo_armazenamento')

        if not all([id_area, nome, tipo_armazenamento]):
            flash("Todos os campos são obrigatórios.", "warning")
        else:
            nova_area = AreaArmazem.criar(id_area.strip().upper(), nome.strip(), tipo_armazenamento)
            if nova_area:
                flash(f"Área '{nova_area.nome}' adicionada com sucesso!", "success")
                return redirect(url_for('listar_areas_admin'))
            else:
                flash(f"Erro ao adicionar área. O ID '{id_area}' já pode existir.", "danger")
    return render_template('admin_form_area.html', acao='Adicionar', area=None)

@app.route('/admin/areas/editar/<id_area_original>', methods=['GET', 'POST'])
@login_necessario(permissao_requerida='gerenciar_areas')
def editar_area(id_area_original):
    """Rota para editar uma área de armazenamento existente."""
    area = AreaArmazem.buscar_por_id(id_area_original)
    if not area:
        flash(f"Área com ID '{id_area_original}' não encontrada.", "danger")
        return redirect(url_for('listar_areas_admin'))

    if request.method == 'POST':
        novo_nome = request.form.get('nome')
        novo_tipo_armazenamento = request.form.get('tipo_armazenamento')

        if not all([novo_nome, novo_tipo_armazenamento]):
            flash("Nome e Tipo de Armazenamento são obrigatórios.", "warning")
        else:
            if area.atualizar(novo_nome.strip(), novo_tipo_armazenamento):
                flash(f"Área '{area.nome}' atualizada com sucesso!", "success")
                return redirect(url_for('listar_areas_admin'))
            else:
                flash("Erro ao atualizar a área.", "danger")
    return render_template('admin_form_area.html', acao='Editar', area=area)

@app.route('/admin/areas/excluir/<id_area>', methods=['POST'])
@login_necessario(permissao_requerida='gerenciar_areas')
def excluir_area(id_area):
    """Rota para excluir uma área de armazenamento."""
    area = AreaArmazem.buscar_por_id(id_area)
    if not area:
        flash(f"Área com ID '{id_area}' não encontrada.", "danger")
    else:
        sucesso, mensagem = area.deletar()
        if sucesso:
            flash(mensagem, "success")
        else:
            flash(mensagem, "danger")
    return redirect(url_for('listar_areas_admin'))

@app.route('/admin/catalogo')
@login_necessario(permissao_requerida='gerenciar_catalogo_produtos')
def listar_produtos_catalogo_admin():
    """Rota para listar todos os produtos do catálogo para administração."""
    produtos = ProdutoCatalogo.listar_todos()
    return render_template('admin_listar_produtos_catalogo.html', produtos=produtos)

@app.route('/admin/catalogo/adicionar', methods=['GET', 'POST'])
@login_necessario(permissao_requerida='gerenciar_catalogo_produtos')
def adicionar_produto_catalogo():
    """Rota para adicionar um novo produto ao catálogo."""
    if request.method == 'POST':
        id_produto = request.form.get('id_produto')
        nome = request.form.get('nome')

        if not all([id_produto, nome]):
            flash("ID do Produto e Nome são obrigatórios.", "warning")
        else:
            novo_produto = ProdutoCatalogo.criar(id_produto.strip().upper(), nome.strip())
            if novo_produto:
                flash(f"Produto '{novo_produto.nome}' adicionado ao catálogo com sucesso!", "success")
                return redirect(url_for('listar_produtos_catalogo_admin'))
            else:
                flash(f"Erro ao adicionar produto ao catálogo. O ID '{id_produto}' já pode existir.", "danger")
    return render_template('admin_form_produto_catalogo.html', acao='Adicionar', produto=None)

@app.route('/admin/catalogo/editar/<id_produto_catalogo>', methods=['GET', 'POST'])
@login_necessario(permissao_requerida='gerenciar_catalogo_produtos')
def editar_produto_catalogo(id_produto_catalogo):
    """Rota para editar um produto existente no catálogo."""
    produto = ProdutoCatalogo.buscar_por_id(id_produto_catalogo)
    if not produto:
        flash(f"Produto do catálogo com ID '{id_produto_catalogo}' não encontrado.", "danger")
        return redirect(url_for('listar_produtos_catalogo_admin'))

    if request.method == 'POST':
        novo_nome = request.form.get('nome')
        if not novo_nome:
            flash("O nome do produto é obrigatório.", "warning")
        else:
            if produto.atualizar(novo_nome.strip()):
                flash(f"Produto '{produto.nome}' atualizado com sucesso!", "success")
                return redirect(url_for('listar_produtos_catalogo_admin'))
            else:
                flash("Erro ao atualizar o produto no catálogo.", "danger")
    return render_template('admin_form_produto_catalogo.html', acao='Editar', produto=produto)

@app.route('/admin/catalogo/excluir/<id_produto_catalogo>', methods=['POST'])
@login_necessario(permissao_requerida='gerenciar_catalogo_produtos')
def excluir_produto_catalogo(id_produto_catalogo):
    """Rota para excluir um produto do catálogo."""
    produto = ProdutoCatalogo.buscar_por_id(id_produto_catalogo)
    if not produto:
        flash(f"Produto do catálogo com ID '{id_produto_catalogo}' não encontrado.", "danger")
    else:
        sucesso, mensagem = produto.deletar()
        if sucesso:
            flash(mensagem, "success")
        else:
            flash(mensagem, "danger")
    return redirect(url_for('listar_produtos_catalogo_admin'))

@app.route('/admin/area/<id_area>/produto/<int:id_instancia_produto>/editar', methods=['GET', 'POST'])
@login_necessario(permissao_requerida='gerenciar_produtos_em_areas')
def editar_produto_em_area(id_area, id_instancia_produto):
    """Rota para editar uma instância de produto específica em uma área."""
    area = AreaArmazem.buscar_por_id(id_area)
    if not area:
        flash(f"Área com ID '{id_area}' não encontrada.", "danger")
        return redirect(url_for('pagina_inicial_armazem'))

    produto_instancia = ProdutoLacteo.buscar_instancia_por_id(id_instancia_produto)
    if not produto_instancia:
        flash(f"Instância de produto com ID '{id_instancia_produto}' não encontrada.", "danger")
        return redirect(url_for('detalhes_da_area', id_area=id_area))
    
    produto_encontrado_na_area = any(p.id == id_instancia_produto for p in area.listar_produtos())
    if not produto_encontrado_na_area:
        flash(f"Produto com ID de instância '{id_instancia_produto}' não pertence à área '{area.nome}'.", "danger")
        return redirect(url_for('detalhes_da_area', id_area=id_area))

    if request.method == 'POST':
        nova_quantidade_str = request.form.get('quantidade')
        nova_data_validade_str = request.form.get('data_validade')
        novo_lote = request.form.get('lote')

        if not all([nova_quantidade_str, nova_data_validade_str, novo_lote]):
            flash("Todos os campos (Quantidade, Data de Validade, Lote) são obrigatórios.", "warning")
        else:
            try:
                nova_quantidade = int(nova_quantidade_str)
                if nova_quantidade < 0: 
                    flash("A quantidade não pode ser negativa.", "warning")
                elif produto_instancia.atualizar_instancia(nova_quantidade, nova_data_validade_str, novo_lote.strip().upper()):
                    flash(f"Produto '{produto_instancia.nome}' (Lote: {produto_instancia.lote}) atualizado com sucesso na área {area.nome}!", "success")
                    return redirect(url_for('detalhes_da_area', id_area=id_area))
                else:
                    flash("Erro ao atualizar o produto. Verifique os dados (ex: formato da data AAAA-MM-DD).", "danger")
            except ValueError: 
                flash("Quantidade inválida. Deve ser um número.", "danger")
            except Exception as e:
                app.logger.error(f"Erro ao editar produto {id_instancia_produto} na área {id_area}: {e}", exc_info=True)
                flash("Ocorreu um erro inesperado ao atualizar o produto.", "danger")
                
    return render_template('admin_form_produto_area.html', 
                           acao='Editar', 
                           area=area, 
                           produto=produto_instancia)

@app.route('/admin/area/<id_area>/produto/<int:id_instancia_produto>/excluir', methods=['POST'])
@login_necessario(permissao_requerida='gerenciar_produtos_em_areas')
def excluir_produto_de_area(id_area, id_instancia_produto):
    """Rota para excluir completamente uma instância de produto de uma área."""
    area = AreaArmazem.buscar_por_id(id_area)
    if not area:
        flash(f"Área com ID '{id_area}' não encontrada.", "danger")
        return redirect(url_for('pagina_inicial_armazem'))

    produto_instancia = ProdutoLacteo.buscar_instancia_por_id(id_instancia_produto)
    if not produto_instancia:
        flash(f"Instância de produto com ID '{id_instancia_produto}' não encontrada.", "danger")
    else:
        produto_na_area_correta = any(p.id == id_instancia_produto for p in area.listar_produtos())
        if not produto_na_area_correta:
            flash(f"Produto com ID de instância '{id_instancia_produto}' não pertence à área '{area.nome}'.", "danger")
        elif produto_instancia.deletar_instancia():
            flash(f"Produto '{produto_instancia.nome}' (Lote: {produto_instancia.lote}) excluído com sucesso da área {area.nome}!", "success")
        else:
            flash(f"Erro ao excluir o produto '{produto_instancia.nome}' da área.", "danger")
            
    return redirect(url_for('detalhes_da_area', id_area=id_area))

@app.route('/relatorios')
@login_necessario(permissao_requerida='gerente')
def pagina_relatorios():
    """Rota para a página de relatórios."""
    estoque_total = {}
    for area_obj in AreaArmazem.listar_todas():
        for prod_instancia in area_obj.listar_produtos():
            chave_produto = prod_instancia.id_catalogo_produto 
            if chave_produto not in estoque_total:
                estoque_total[chave_produto] = {"nome": prod_instancia.nome, "quantidade_total": 0}
            estoque_total[chave_produto]["quantidade_total"] += prod_instancia.quantidade
    
    vendas = sorted([v.to_dict() for v in Venda.listar_todas()], key=lambda x: datetime.strptime(x['data_hora'], '%d/%m/%Y %H:%M:%S'), reverse=True)

    dias_alerta_antecedencia = 7 
    data_hoje_obj = date.today()
    limite_alerta = data_hoje_obj + timedelta(days=dias_alerta_antecedencia)
    produtos_alerta_validade = []

    for area_obj in AreaArmazem.listar_todas():
        for produto_obj in area_obj.listar_produtos(): 
            status_validade = ""
            dias_para_vencer_calc = (produto_obj.data_validade - data_hoje_obj).days

            if produto_obj.data_validade < data_hoje_obj:
                status_validade = "VENCIDO"
            elif produto_obj.data_validade <= limite_alerta:
                status_validade = "PROXIMO_VENCIMENTO"
            
            if status_validade:
                produtos_alerta_validade.append({
                    "area_id": area_obj.id_area,
                    "nome_area": area_obj.nome,
                    "produto": produto_obj.to_dict(), 
                    "status_validade": status_validade,
                    "dias_para_vencer": dias_para_vencer_calc
                })
    
    produtos_alerta_validade.sort(key=lambda x: (x["status_validade"] != "VENCIDO", x["dias_para_vencer"]))

    return render_template('relatorios.html', 
                         estoque_total=estoque_total, 
                         vendas_registradas=vendas, 
                         produtos_alerta_validade=produtos_alerta_validade,
                         dias_alerta=dias_alerta_antecedencia)

@app.route('/api/armazem/<id_area>/produtos', methods=['GET'])
@login_necessario(permissao_requerida='visualizar_armazem')
def api_produtos_por_area(id_area):
    """Endpoint da API para listar produtos de uma área específica em formato JSON."""
    area = AreaArmazem.buscar_por_id(id_area)
    if not area:
        return jsonify({"erro": "Área não encontrada"}), 404
    return jsonify(area.to_dict())

@app.route('/api/estoque_geral', methods=['GET'])
@login_necessario(permissao_requerida='gerente')
def api_estoque_geral():
    """Endpoint da API para listar o estoque completo de todas as áreas em formato JSON."""
    estoque_completo = [area.to_dict() for area in AreaArmazem.listar_todas()]
    return jsonify(estoque_completo)

# --- Context Processor ---
@app.context_processor
def injetar_dados_globais():
    """Disponibiliza o objeto Usuario logado para todos os templates."""
    usuario_obj = None
    if 'username' in session and 'password' in session: # Verifica se há um usuário logado
        # Busca o objeto Usuario completo para disponibilizar seus métodos (como tem_permissao)
        usuario_obj = Usuario.verificar_senha(session['username'], session['password'])
    return dict(usuario_logado=usuario_obj, data_hoje_global=date.today())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

