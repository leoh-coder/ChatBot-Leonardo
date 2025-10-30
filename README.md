#  ChatBot-Leonardo – Chatbot com Memória Persistente

É um chatbot com *memória de conversação persistente, desenvolvido em **FastAPI + LangChain + Google Gemini, com **interface HTML*.  
Ele foi criado como um projeto de demonstração para integrar backend, frontend e IA generativa de forma simples e funcional.

---

## Tecnologias Utilizadas
- Backend         | *FastAPI*
- LLM             | *Google Gemini (via LangChain)* 
- Framework de IA | *LangChain (LCEL)* 
- Banco de Dados  | *SQLite*
- Frontend        | *HTML + CSS + JavaScript puro*
- Ambiente        | *Python 3.10*

---

##  Como Rodar o Projeto (Passo a Passo Completo)

Copie e cole *cada bloco de código no terminal*, na ordem abaixo 👇  

### 1️⃣ Clonar o repositório do GitHub
```bash
git clone https://github.com/leoh-coder/ChatBot-Leonardo.git
cd ChatBot-Leonardo


---

2️⃣ Criar e ativar o ambiente virtual (Windows)

python -m venv .venv
.venv\Scripts\activate


---

3️⃣ Instalar as dependências

pip install -r requirements.txt


---

4️⃣ Criar o arquivo .env (variáveis secretas)

# Copie o arquivo .env.example e renomeie para .env
# Depois abra o .env e adicione sua chave real da API:
# GEMINI_API_KEY=sua_chave_aqui
# GEMINI_MODEL=gemini-2.5-flash


---

⚡ 5️⃣ Iniciar o servidor backend (FastAPI)

uvicorn app:app --reload --port 8010


---

🌐 6️⃣ Em outro terminal, iniciar o servidor frontend (HTML)

python -m http.server 5500


---

🧠 7️⃣ Abrir no navegador

# Acesse: http://127.0.0.1:5500
# O frontend se conecta automaticamente à API (http://127.0.0.1:8010)


---

👨‍💻 Autor

Desenvolvido por: Leonardo Henrique Ramos Ferreira

Estudante de Análise e Desenvolvimento de Sistemas

Focado em IA, Ciência e Engenharia de Dados

Projeto criado para demonstração técnica


© 2025 Leonardo Henrique Ramos Ferreira — Todos os direitos reservados.

---