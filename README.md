# Gerador de Provas Online

Sistema completo para aplicação de provas online com gestão administrativa, upload de arquivos e envio de resultados por e-mail.

## Funcionalidades

- 📝 Aplicação de provas online com múltipla escolha
- ⏱️ Controle de tempo para realização da prova
- 📊 Relatório detalhado de resultados por e-mail
- 🔒 Área administrativa para gerenciar conteúdo
- 📤 Upload de arquivos Markdown para questões e gabarito
- 🌐 Deploy fácil usando Docker e Traefik

## Configuração

### Variáveis de Ambiente

O sistema utiliza as seguintes variáveis de ambiente, configuráveis no arquivo `.env.local`:

```
# Configurações SMTP
SMTP_HOSTNAME=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-de-app
SMTP_FROM_EMAIL=seu-email@gmail.com
ADMIN_EMAIL=seu-email@gmail.com
```

Para Gmail, use uma senha de aplicativo gerada em:
https://myaccount.google.com/apppasswords (não use sua senha normal do Google!)

### Formato dos Arquivos

#### Arquivo de Questões (exam.md)

O arquivo de exame deve ter o seguinte formato:

```markdown
---
titulo: Título da Prova
duracao_min: 60
---

# Q1. Texto da primeira questão?

A) Alternativa 1
B) Alternativa 2
C) Alternativa 3
D) Alternativa 4

# Q2. Texto da segunda questão?

A) Alternativa 1
B) Alternativa 2
C) Alternativa 3
D) Alternativa 4
```

#### Arquivo de Gabarito (gabarito.md)

O arquivo de gabarito deve ter o formato:

```
Q1: A
Q2: C
Q3: D
Q4: B
...
```

## Uso do Sistema

### Para Administradores

1. Acesse o sistema e clique em "Admin"
2. Faça login com usuário: "admin" e senha: "admin"
3. No painel administrativo você pode:
   - Fazer upload de arquivos .md para questões e gabarito
   - Editar diretamente as questões e gabarito na interface
   - Salvar as alterações com o botão "Salvar Alterações"

### Para Alunos

1. Acesse o sistema e insira seu email
2. Responda as questões da prova
3. Ao finalizar, a pontuação será exibida e um relatório detalhado será enviado por email

## Desenvolvimento Local

Para executar o sistema localmente:

```bash
# Clone o repositório
git clone https://github.com/pardinithales/gerador_provas.git
cd gerador_provas

# Instale as dependências
pip install -r requirements.txt

# Configure o arquivo .env.local
cp .env.example .env.local
# Edite o arquivo .env.local com suas configurações

# Execute o servidor
uvicorn app.main:app --reload
```

## Deployment com Docker

O projeto inclui arquivos Docker para deploy fácil:

```bash
# Construir e iniciar os containers
docker compose up -d
```

O servidor estará disponível em http://localhost:8000 ou no domínio configurado com Traefik.

## Tecnologias Utilizadas

- **Backend**: FastAPI, Python
- **Frontend**: HTML, Tailwind CSS, Alpine.js
- **Containerização**: Docker, Docker Compose
- **Proxy Reverso**: Traefik

## Licença

Este projeto é licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes. 