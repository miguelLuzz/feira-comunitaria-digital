# Feira Comunitária Digital — Python/Flask/SQLite

MVP acadêmico local, criado a partir do planejamento da Experiência II. Cenário e dados fictícios. Não houve entrevista, validação externa ou implantação pública. A versão Node.js foi a demonstração preliminar; esta versão aplica a tecnologia Python selecionada.

## Executar (Python 3.12)

Crie ambiente virtual e instale `pip install -r requirements.txt`.
Defina `FEIRA_SECRET_KEY` com segredo aleatório de pelo menos 32 caracteres e `FEIRA_ADMIN_PASSWORD_HASH` com o resultado de `werkzeug.security.generate_password_hash(senha, method='pbkdf2:sha256:600000')`. Os segredos ficam no ambiente, nunca no repositório. Não use credenciais do Blackboard.

Execute `flask --app app:create_app seed-demo` para produtos fictícios, depois `python app.py`. Abra `http://127.0.0.1:8881`. O servidor de desenvolvimento fica vinculado somente ao computador local.

Para testar: `python -m unittest -v`. As bases são temporárias e não afetam a base demonstrativa.

## Escopo e arquitetura

- `domain.py`: domínio e SQLite; cadastro, catálogo, reserva atômica e cancelamento que repõe o estoque uma única vez.
- `app.py`: aplicação Flask, validação HTTP, CSRF, acesso do produtor por senha com hash, sessão revogável no servidor e limite de login.
- `templates/page.html` e `static/style.css`: interface HTML com escape automático, rótulos persistentes, foco visível, mensagens textuais e controles de pelo menos 48px.
- RF01 cadastro restrito ao produtor; RF02 catálogo e categoria; RF03 reserva; RF04 cancelamento.
- Cada navegador recebe identificador aleatório assinado e só acessa suas reservas. Não são solicitados documentos, endereço ou telefone. Limpar cookies perde o acesso às reservas locais; identificação permanente de compradores fica fora deste MVP.

## Testes

Regras de estoque e cancelamento; dados inválidos; concorrência pela última unidade; filtro parametrizado; isolamento entre compradores; fluxo HTTP real pelo cliente de testes Flask; autorização do produtor; CSRF; logout revogado; escape de XSS; cabeçalhos/cookies; limite de tentativas de login.

## Limitações e publicação

Há um único produtor administrador; contas múltiplas, pagamentos e agendamento de retirada não estão implementados. A sessão administrativa expira em 30 minutos; o limite por IP é simplificado e precisará ser revisto atrás de proxy. SQLite atende demonstração local, não prova escalabilidade. O ambiente público precisará de servidor WSGI, HTTPS, `FEIRA_COOKIE_SECURE=1`, gestão de segredos, backups e política de retenção. A acessibilidade foi projetada e inspecionada localmente, sem teste com leitor de tela ou representante externo.

`.github/workflows/tests.yml` prepara os testes no GitHub Actions. Configuração escrita não equivale a execução remota. GitHub público, PR/revisão externa e CI remoto permanecem pendentes até publicação e execução efetivas.

## Referências

[Segurança Flask](https://flask.palletsprojects.com/en/stable/web-security/) e [Testes Flask](https://flask.palletsprojects.com/en/stable/testing/). Consultados em 28/09/2026.
