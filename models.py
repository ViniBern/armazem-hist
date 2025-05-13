import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Definir caminho do banco de dados
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'laticinios.db')

def get_db_connection():
    os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas pelo nome
    return conn

def init_db():
    # Inicializa o banco de dados usando o schema.sql
    conn = get_db_connection()
    with open(os.path.join(os.path.dirname(__file__), 'schema.sql'), 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso")

# ------- Funções para usuários -------
def create_user(username, password, role='user'):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), role)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False  # Indica falha (ex: usuário já existe)
    conn.close()
    return True  # Indica sucesso

def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user

def check_user_password(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None

# ------- Funções para áreas -------
def add_area(nome, descricao=''):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO areas_armazen (nome, descricao) VALUES (?, ?)",
            (nome, descricao)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True

def get_all_areas():
    conn = get_db_connection()
    areas = conn.execute("SELECT * FROM areas_armazen").fetchall()
    conn.close()
    return areas
