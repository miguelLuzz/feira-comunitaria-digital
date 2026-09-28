"""Regras e persistência do MVP. Nenhum dado de campo real é utilizado."""
import sqlite3
import uuid
from contextlib import closing


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def initialize(path):
    with closing(connect(path)) as db, db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS products (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
          price INTEGER NOT NULL CHECK(price>0), stock INTEGER NOT NULL CHECK(stock>=0));
        CREATE TABLE IF NOT EXISTS reservations (
          id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(id),
          owner TEXT NOT NULL, buyer TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity>0),
          status TEXT NOT NULL CHECK(status IN ('pendente','cancelada')),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS admin_sessions (token TEXT PRIMARY KEY, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS login_attempts (ip TEXT PRIMARY KEY, count INTEGER, reset REAL);
        ''')


def integer(value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError('Informe um número inteiro válido.')
    return value


def text(value, maximum=80):
    if not isinstance(value, str) or not 2 <= len(value.strip()) <= maximum:
        raise ValueError('Informe um texto com 2 a %s caracteres.' % maximum)
    return value.strip()


def create_product(path, name, category, price, stock):
    data = (str(uuid.uuid4()), text(name), text(category), integer(price,1), integer(stock))
    with closing(connect(path)) as db, db:
        db.execute('INSERT INTO products VALUES (?,?,?,?,?)', data)
    return data[0]


def catalogue(path, category=None):
    with closing(connect(path)) as db:
        if category:
            rows = db.execute('SELECT * FROM products WHERE category=? ORDER BY name',(category,))
        else:
            rows = db.execute('SELECT * FROM products ORDER BY name')
        return [dict(row) for row in rows]


def reserve(path, product_id, owner, buyer, quantity):
    buyer = text(buyer,60)
    quantity = integer(quantity,1)
    reservation_id = str(uuid.uuid4())
    with closing(connect(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        updated = db.execute('UPDATE products SET stock=stock-? WHERE id=? AND stock>=?',
                             (quantity,product_id,quantity)).rowcount
        if not updated:
            raise ValueError('Produto indisponível ou quantidade maior que o estoque.')
        db.execute('INSERT INTO reservations (id,product_id,owner,buyer,quantity,status) VALUES (?,?,?,?,?,?)',
                   (reservation_id,product_id,owner,buyer,quantity,'pendente'))
    return reservation_id


def reservation(path, reservation_id, owner):
    with closing(connect(path)) as db:
        row=db.execute('''SELECT r.*,p.name,p.price,p.stock FROM reservations r
            JOIN products p ON p.id=r.product_id WHERE r.id=? AND r.owner=?''',(reservation_id,owner)).fetchone()
        return dict(row) if row else None


def cancel(path, reservation_id, owner):
    with closing(connect(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM reservations WHERE id=? AND owner=? AND status=?',
                       (reservation_id,owner,'pendente')).fetchone()
        if not row:
            raise ValueError('Reserva indisponível para cancelamento.')
        db.execute('UPDATE reservations SET status=? WHERE id=?',('cancelada',reservation_id))
        db.execute('UPDATE products SET stock=stock+? WHERE id=?',(row['quantity'],row['product_id']))
