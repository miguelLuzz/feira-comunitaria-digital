# Feira Comunitária Digital — Python/Flask/SQLite

MVP acadêmico, criado a partir do planejamento da Experiência II. Cenário e dados fictícios. Não houve entrevista ou validação externa. A versão demonstrativa foi publicada em https://miguelg1.pythonanywhere.com/ em 28/09/2026. A versão Node.js foi a demonstração preliminar; esta versão aplica a tecnologia Python selecionada.

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

Há um único produtor administrador; contas múltiplas, pagamentos e agendamento de retirada não estão implementados. A sessão administrativa expira em 30 minutos; o limite por IP é simplificado e precisará ser revisto atrás de proxy. SQLite atende à demonstração, sem comprovação de escalabilidade. A hospedagem usa servidor WSGI, HTTPS obrigatório, cookie Secure e configuração privada. Backups automatizados e política de retenção permanecem pendentes. A acessibilidade foi projetada e inspecionada localmente, sem teste com leitor de tela ou representante externo.

Código publicado em [miguelLuzz/feira-comunitaria-digital](https://github.com/miguelLuzz/feira-comunitaria-digital). O [PR #1](https://github.com/miguelLuzz/feira-comunitaria-digital/pull/1) incluiu testes e workflow e foi integrado após dois checks aprovados. A [execução remota de testes](https://github.com/miguelLuzz/feira-comunitaria-digital/actions/runs/36428240945) passou nos nove testes em 1,482s, em 28/09/2026. Não houve aprovação por revisor externo, entrevista ou validação de campo.

## Publicação e monitoramento

- Aplicação demonstrativa: https://miguelg1.pythonanywhere.com/
- PythonAnywhere Beginner, Python 3.12 e Flask 3.1.3, com ambiente virtual e SQLite em armazenamento persistente fora do repositório. A senha do produtor e o segredo de sessão foram gerados na hospedagem e não estão no GitHub.
- Reserva pública de duas alfaces: estoque 8 → 6. Após recarga do servidor, a reserva permaneceu acessível; o cancelamento repôs estoque 8. Dados demonstrativos.
- Nove testes também passaram no ambiente da hospedagem em 4,739s.
- Workflow `.github/workflows/monitor.yml`: consulta horária e execução manual, com timeout de 20s, status UP/DOWN e resumo com HTTP/latência. A agenda pode atrasar.
- Primeira execução: https://github.com/miguelLuzz/feira-comunitaria-digital/actions/runs/36481337724 — UP, HTTP 200, 226ms em 28/09/2026 às 20:44:39 UTC.
- O plano gratuito exige renovação manual mensal. Expiração observada: 28/10/2026.
- Não foram confirmados alertas por e-mail, disponibilidade histórica, validação comunitária ou impacto social.

## Referências

[Segurança Flask](https://flask.palletsprojects.com/en/stable/web-security/) e [Testes Flask](https://flask.palletsprojects.com/en/stable/testing/). Consultados em 28/09/2026.
