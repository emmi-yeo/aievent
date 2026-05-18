# Market Research Tool — MVP

AI-powered market analysis platform for strategic consulting.

## What It Does

**Client Side:**
- Gemini-powered onboarding chatbot collects business context conversationally
- 7-category document upload portal (Financial Report, Business Plan, Market View, Fact Finding, Value Proposition, Pricing Structure, Market Research)
- Automated email reminders if documents are not uploaded before the deadline

**Consultant Side:**
- Dashboard showing all client engagements and upload status per category
- One-click AI analysis powered by Gemini (RAG over uploaded documents)
- Structured Analysed Summary with collapsible sections
- Downloadable PDF report

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, Tailwind CSS |
| Backend | Python, FastAPI |
| LLM | Google Gemini 1.5 Pro |
| Vector Store | ChromaDB |
| File Storage | Google Drive |
| Database | Google Sheets |
| Email | Resend |
| PDF | WeasyPrint |
| Scheduler | APScheduler |

## Project Structure

```
/
├── frontend/    # Next.js app (Vercel)
└── backend/     # FastAPI app (Railway/Render)
```

## Setup

### 1. Google Cloud Setup

1. Create a Google Cloud project
2. Enable: Google Drive API, Google Sheets API, Gemini API
3. Create a Service Account → download JSON key
4. Create a Google Sheets spreadsheet (note the ID from the URL)
5. Create a Google Drive folder (note the folder ID)
6. Share both the spreadsheet and Drive folder with the service account email

### 2. Get API Keys

- **Gemini API Key**: https://aistudio.google.com/app/apikey
- **Resend API Key**: https://resend.com (free tier: 100 emails/day)

### 3. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env from example
cp .env.example .env
# Fill in all values in .env

uvicorn main:app --reload
```

#### Environment Variables (backend/.env)

```
GEMINI_API_KEY=your_gemini_api_key
RESEND_API_KEY=your_resend_api_key
SECRET_KEY=your_random_secret_min_32_chars
GOOGLE_SERVICE_ACCOUNT_JSON=<base64 of service account JSON>
GOOGLE_SHEETS_ID=your_spreadsheet_id
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
FRONTEND_URL=http://localhost:3000
```

To encode your service account JSON:
```bash
base64 -i service-account.json | tr -d '\n'
```

### 4. Frontend Setup

```bash
cd frontend
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev
```

Open http://localhost:3000

## Deployment

### Backend → Railway

1. Push backend to GitHub
2. New Railway project → Deploy from GitHub
3. Set all environment variables in Railway dashboard
4. Deploy

### Frontend → Vercel

1. Push frontend to GitHub
2. Import to Vercel
3. Set `NEXT_PUBLIC_API_URL=https://your-railway-backend-url.up.railway.app`
4. Deploy

## First Use

1. Go to `/register` to create a consultant account
2. Login → you land on the dashboard
3. Click "New Engagement" → fill in client details
4. Client receives an email with login credentials
5. Client logs in → completes onboarding chatbot → uploads 7 documents
6. Consultant clicks "Run Analysis" → Gemini generates the Analysed Summary
7. Download PDF for the strategy meeting
