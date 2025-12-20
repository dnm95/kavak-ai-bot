# 🚗 Kavak AI Sales Bot (FastAPI + OpenAI + Twilio WhatsApp)

A pragmatic demo of a Kavak Mexico AI sales agent, built with **Python 3.11** + **FastAPI**, powered by **OpenAI LLMs**, and exposed via a REST API and **WhatsApp** (Twilio Sandbox).

> **Project Context:** This project was designed as a technical challenge for the AI Engineer position, focusing on architectural clarity, hallucination reduction, clean orchestration, and reproducibility.

## ✨ Features

### 1. Value Proposition & Processes
* **Grounded Knowledge:** Answers questions about Kavak’s value proposition, warranty, trial period, locations, and buying/selling processes using a strict internal context to **prevent hallucinations**.
* **Buying & Selling:** Explains requirements and steps clearly based on official data.

### 2. Financing Calculator
* **Real-time Quotes:** Simulates monthly payments based on the car price and down payment.
* **Logic:** Uses a fixed **10% annual interest rate** and supports terms of 3, 4, 5, or 6 years.

### 3. Smart Catalog Search
* **Natural Language Processing:** Searches a sample catalog (`CSV`) allowing for typos or incomplete names (Fuzzy Matching).
* **Filtering:** Filters by year, budget, kilometers, and specific features (e.g., "Bluetooth", "CarPlay").

### 4. WhatsApp Integration
* **Twilio Sandbox:** Fully functional two-way communication.
* **Session Management:** Keeps per-user conversation history in memory (optimized for demo purposes).

---

## 🛠️ Requirements

* **Python 3.11+**
* **Make** (standard on macOS/Linux)
* **OpenAI API Key**

## 🚀 Quickstart

**Bonus Point:** This project prioritizes reproducibility. You can set it up in 2 steps.

### 1. Install Dependencies
This command creates a virtual environment (`.venv`) and installs all requirements.
```bash
make install
```

### 2. Configure Environment
Create a `.env` file in the project root:
```properties
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional defaults
MODEL=gpt-4o-mini
CATALOG_PATH=app/data/sample_caso_ai_engineer.csv
```

### 3. Run the API
```bash
make run
```
* **Server URL:** `http://localhost:8000`
* **Health Check:** `http://localhost:8000/health`

---

## 📡 API Usage

### Health Check
```bash
curl http://localhost:8000/health
```

### Chat Endpoint (Local Testing)
Interact with the bot directly without WhatsApp:

```bash
curl -X POST http://localhost:8000/chat \
-H "Content-Type: application/json" \
-d '{
    "user_id": "demo_user",
    "messages": [
        { "role": "user", "content": "¿Qué documentos necesito para financiar?" }
    ]
}'
```
**Response:**
* `reply`: The assistant's answer.
* `messages`: Updated conversation history.
* `debug`: Internal routing and tool execution info (useful for evaluation).

---

## 📱 WhatsApp Demo (Twilio Sandbox)

### 1. Expose Local Server
Use **ngrok** to tunnel your localhost to the internet:
```bash
ngrok http 8000
```
*Copy the HTTPS URL (e.g., `https://abcd-1234.ngrok-free.app`).*

### 2. Configure Twilio Webhook
1. Go to **Twilio Console** → **Messaging** → **Try it out** → **Send a WhatsApp message**.
2. Open **Sandbox Settings**.
3. In **"When a message comes in"**, paste your ngrok URL with the webhook path:
   `https://abcd-1234.ngrok-free.app/twilio/webhook`
4. Save.

### 3. Test Prompts
Try sending these messages via WhatsApp:
* *"¿Qué documentos necesito para financiar?"*
* *"¿Cuánto pago al mes si el auto cuesta 350000 y doy 100000 de enganche?"*
* *"Busco un Mazda 3 2020 máximo 350 mil y que tenga bluetooth"*
* *"¿Dónde hay Kavak en Monterrey?"*

### Simulating Twilio Locally (No Phone Needed)
```bash
curl -X POST http://localhost:8000/twilio/webhook \
-H "Content-Type: application/x-www-form-urlencoded" \
--data-urlencode "From=whatsapp:+5215555555555" \
--data-urlencode "Body=Hola, busco un auto barato"
```

---

## 📂 Project Structure

```text
app/
├── main.py              # FastAPI app and REST endpoints
├── schemas.py           # Pydantic models for validation
├── routers/
│   └── twilio.py        # WhatsApp webhook handler
├── bot/
│   ├── orchestrator.py  # LLM routing & orchestration logic
│   ├── tools_finance.py # Financing math calculations
│   ├── tools_catalog.py # Pandas/Fuzzy search logic
│   └── prompts.py       # System prompts & knowledge context
└── data/
    └── sample_caso_ai_engineer.csv  # Car catalog
```

## 🧑‍💻 Developer Commands

* `make run` - Start the server.
* `make test` - Run unit tests.
* `make lint` - Check code style.
* `make fmt` - Auto-format code.

---

## 🔮 Production Roadmap (High Level)

To take this from a "Technical Challenge Demo" to **Production**:

1.  **Persistence:** Replace in-memory dictionaries with **PostgreSQL** or **Redis** for robust session management.
2.  **Testing:** Implement regression tests for prompts to ensure new iterations don't break existing logic.
3.  **Scalability:**
    * Introduce **Embeddings + Vector Search** (e.g., Pinecone/pgvector) for the catalog and knowledge base scaling.
    * Use an async task queue (RabbitMQ/SQS) for handling high-volume webhooks.
4.  **Deployment:** Containerize with **Docker** and deploy to AWS/GCP with autoscaling and HTTPS.

---

## 📄 License
This project is a technical exercise for recruitment purposes.
