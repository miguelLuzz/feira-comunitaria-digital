import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from werkzeug.security import generate_password_hash
from app import create_app
from domain import initialize, create_product, reserve, reservation, cancel, catalogue, connect


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=os.path.join(self.temp.name,'test.sqlite3')
        initialize(self.path)
        self.product=create_product(self.path,'Alface','Hortaliças',400,8)
    def tearDown(self): self.temp.cleanup()
    def test_reservation_and_cancel_restore_once(self):
        rid=reserve(self.path,self.product,'owner','Cliente',2)
        self.assertEqual(catalogue(self.path)[0]['stock'],6)
        cancel(self.path,rid,'owner')
        self.assertEqual(catalogue(self.path)[0]['stock'],8)
        with self.assertRaises(ValueError): cancel(self.path,rid,'owner')
        self.assertEqual(catalogue(self.path)[0]['stock'],8)
    def test_invalid_quantities_preserve_stock(self):
        for quantity in [0,-1,9,1.5,True]:
            with self.assertRaises(ValueError): reserve(self.path,self.product,'o','Cliente',quantity)
        self.assertEqual(catalogue(self.path)[0]['stock'],8)
    def test_last_unit_concurrent_reservations(self):
        product=create_product(self.path,'Última alface','Hortaliças',400,1)
        def attempt(owner):
            try: reserve(self.path,product,owner,'Cliente',1); return True
            except ValueError: return False
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(attempt,['a','b']))
        self.assertEqual(sum(results),1)
        self.assertEqual(next(p for p in catalogue(self.path) if p['id']==product)['stock'],0)
    def test_parameterized_filter_and_owner(self):
        self.assertEqual(catalogue(self.path,"' OR 1=1 --"),[])
        rid=reserve(self.path,self.product,'a','Cliente',1)
        self.assertIsNone(reservation(self.path,rid,'b'))
        with self.assertRaises(ValueError): cancel(self.path,rid,'b')


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash=generate_password_hash('senha-local-de-teste',method='pbkdf2:sha256:600000')
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=os.path.join(self.temp.name,'http.sqlite3')
        self.app=create_app({'TESTING':True,'SECRET_KEY':'a'*64,'DATABASE':self.path,
                             'ADMIN_PASSWORD_HASH':self.password_hash})
        self.client=self.app.test_client()
        self.product=create_product(self.path,'Alface','Hortaliças',400,8)
    def tearDown(self): self.temp.cleanup()
    def token(self,client=None):
        client=client or self.client
        client.get('/')
        with client.session_transaction() as session: return session['csrf']
    def test_end_to_end_private_reservation_and_cancel(self):
        result=self.client.post('/reserve/'+self.product,data={'csrf':self.token(),'buyer':'Cliente','quantity':'2'})
        self.assertEqual(result.status_code,302)
        self.assertIn('Reserva confirmada',self.client.get(result.location).get_data(as_text=True))
        stranger=self.app.test_client()
        self.assertEqual(stranger.get(result.location).status_code,404)
        rid=result.location.rsplit('/',1)[1]
        self.assertEqual(stranger.post('/cancel/'+rid,data={'csrf':self.token(stranger)}).status_code,400)
        self.assertEqual(self.client.post('/cancel/'+rid,data={'csrf':self.token()}).status_code,302)
        self.assertEqual(catalogue(self.path)[0]['stock'],8)
    def test_csrf_and_producer_authorization(self):
        self.assertEqual(self.client.post('/products/new',data={'name':'Produto'}).status_code,400)
        self.assertEqual(self.client.post('/products/new',data={'csrf':self.token()}).status_code,302)
        result=self.client.post('/login',data={'csrf':self.token(),'password':'senha-local-de-teste'})
        self.assertEqual(result.status_code,302)
        self.assertEqual(self.client.post('/products/new',data={'csrf':self.token(),'name':'Tomate','category':'Hortaliças','price':'7.00','stock':'12'}).status_code,302)
        with self.client.session_transaction() as session: token=session['admin']
        self.client.post('/logout',data={'csrf':self.token()})
        with closing(connect(self.path)) as db:
            self.assertIsNone(db.execute('SELECT * FROM admin_sessions WHERE token=?',(token,)).fetchone())
        self.assertEqual(self.client.get('/products/new').status_code,302)
    def test_xss_escaped_and_security_headers(self):
        create_product(self.path,'<script>alert(1)</script>','Frutas',100,2)
        result=self.client.get('/')
        html=result.get_data(as_text=True)
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertEqual(result.headers['X-Content-Type-Options'],'nosniff')
        self.assertIn('HttpOnly',result.headers.get('Set-Cookie',''))
        self.assertIn('SameSite=Lax',result.headers.get('Set-Cookie',''))
    def test_invalid_quantity_does_not_change_database(self):
        result=self.client.post('/reserve/'+self.product,data={'csrf':self.token(),'buyer':'Cliente','quantity':'99'})
        self.assertEqual(result.status_code,400)
        self.assertEqual(catalogue(self.path)[0]['stock'],8)
    def test_login_rate_limit(self):
        for _ in range(5):
            self.assertEqual(self.client.post('/login',data={'csrf':self.token(),'password':'errada'}).status_code,401)
        self.assertEqual(self.client.post('/login',data={'csrf':self.token(),'password':'errada'}).status_code,429)


if __name__=='__main__': unittest.main()
