"""Aplicação local Flask/SQLite. Publicação e testes externos ainda pendentes."""
import os
import secrets
import time
from contextlib import closing
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from domain import connect, initialize, catalogue, create_product, reserve, reservation, cancel


def create_app(config=None):
    app=Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get('FEIRA_SECRET_KEY'),
        DATABASE=os.environ.get('FEIRA_DATABASE','feira.sqlite3'),
        ADMIN_PASSWORD_HASH=os.environ.get('FEIRA_ADMIN_PASSWORD_HASH'),
        SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('FEIRA_COOKIE_SECURE')=='1',
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),MAX_CONTENT_LENGTH=16384)
    if config: app.config.update(config)
    if not app.config['SECRET_KEY'] or len(app.config['SECRET_KEY'])<32:
        raise RuntimeError('Configure FEIRA_SECRET_KEY com pelo menos 32 caracteres aleatórios.')
    initialize(app.config['DATABASE'])

    @app.template_filter('money')
    def money(value):
        return ('R$ %.2f' % (value/100)).replace('.',',')

    @app.before_request
    def context_and_csrf():
        session.permanent=True
        session.setdefault('owner',secrets.token_urlsafe(32))
        session.setdefault('csrf',secrets.token_urlsafe(32))
        if request.method=='POST' and not secrets.compare_digest(request.form.get('csrf',''),session['csrf']):
            abort(400,description='Formulário expirado. Reabra a página e tente novamente.')

    def admin_active():
        with closing(connect(app.config['DATABASE'])) as db:
            return db.execute('SELECT 1 FROM admin_sessions WHERE token=? AND expires>?',
                              (session.get('admin',''),time.time())).fetchone() is not None

    def admin_required(function):
        @wraps(function)
        def wrapper(*args,**kwargs):
            if not admin_active(): return redirect(url_for('login'))
            return function(*args,**kwargs)
        return wrapper

    @app.context_processor
    def context(): return {'admin_active':admin_active()}

    @app.after_request
    def headers(response):
        response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Cache-Control']='no-store'
        return response

    @app.get('/')
    def index():
        return render_template('page.html',page='catalogue',products=catalogue(app.config['DATABASE'],request.args.get('category') or None),
                               categories=sorted({p['category'] for p in catalogue(app.config['DATABASE'])}))

    @app.route('/login',methods=['GET','POST'])
    def login():
        if request.method=='POST':
            now=time.time(); ip=request.remote_addr or 'unknown'
            with closing(connect(app.config['DATABASE'])) as db,db:
                attempt=db.execute('SELECT * FROM login_attempts WHERE ip=?',(ip,)).fetchone()
                if attempt and attempt['reset']>now and attempt['count']>=5:
                    return render_template('page.html',page='login',error='Muitas tentativas. Aguarde 10 minutos.'),429
                count=attempt['count']+1 if attempt and attempt['reset']>now else 1
                reset=attempt['reset'] if attempt and attempt['reset']>now else now+600
                db.execute('INSERT OR REPLACE INTO login_attempts VALUES (?,?,?)',(ip,count,reset))
                hash_value=app.config['ADMIN_PASSWORD_HASH']
                if not hash_value or not check_password_hash(hash_value,request.form.get('password','')):
                    return render_template('page.html',page='login',error='Acesso não autorizado.'),401
                token=secrets.token_urlsafe(32)
                db.execute('INSERT INTO admin_sessions VALUES (?,?)',(token,now+1800))
                db.execute('DELETE FROM login_attempts WHERE ip=?',(ip,))
            session['admin']=token
            session['csrf']=secrets.token_urlsafe(32)
            return redirect(url_for('new_product'))
        return render_template('page.html',page='login')

    @app.post('/logout')
    def logout():
        with closing(connect(app.config['DATABASE'])) as db,db:
            db.execute('DELETE FROM admin_sessions WHERE token=?',(session.pop('admin',''),))
        session['csrf']=secrets.token_urlsafe(32)
        return redirect(url_for('index'))

    @app.route('/products/new',methods=['GET','POST'])
    @admin_required
    def new_product():
        error=None
        if request.method=='POST':
            try:
                price=Decimal(request.form.get('price','').replace(',','.'))
                if not price.is_finite() or price*100 != (price*100).to_integral_value():
                    raise ValueError('Informe preço com até duas casas decimais.')
                create_product(app.config['DATABASE'],request.form.get('name',''),request.form.get('category',''),int(price*100),int(request.form.get('stock','')))
                flash('Produto cadastrado.'); return redirect(url_for('index'))
            except (ValueError,InvalidOperation): error='Confira nome, categoria, preço positivo e estoque inteiro não negativo.'
        return render_template('page.html',page='product',error=error),400 if error else 200

    @app.route('/reserve/<product_id>',methods=['GET','POST'])
    def make_reservation(product_id):
        product=next((p for p in catalogue(app.config['DATABASE']) if p['id']==product_id),None)
        if not product: abort(404)
        error=None
        if request.method=='POST':
            try:
                rid=reserve(app.config['DATABASE'],product_id,session['owner'],request.form.get('buyer',''),int(request.form.get('quantity','')))
                return redirect(url_for('result',reservation_id=rid))
            except ValueError: error='Confira seu nome e informe quantidade inteira entre 1 e o estoque disponível.'
        return render_template('page.html',page='reserve',product=product,error=error),400 if error else 200

    @app.get('/result/<reservation_id>')
    def result(reservation_id):
        item=reservation(app.config['DATABASE'],reservation_id,session['owner'])
        if not item: abort(404)
        return render_template('page.html',page='result',item=item)

    @app.post('/cancel/<reservation_id>')
    def cancellation(reservation_id):
        try: cancel(app.config['DATABASE'],reservation_id,session['owner'])
        except ValueError: abort(400,description='Reserva indisponível para cancelamento.')
        return redirect(url_for('result',reservation_id=reservation_id))

    @app.cli.command('seed-demo')
    def seed_demo():
        if not catalogue(app.config['DATABASE']):
            for row in [('Alface','Hortaliças',400,8),('Tomate','Hortaliças',700,12),('Banana','Frutas',600,10)]:
                create_product(app.config['DATABASE'],*row)
        print('Dados fictícios carregados.')
    return app


if __name__=='__main__':
    create_app().run(host='127.0.0.1',port=8881,debug=False)
