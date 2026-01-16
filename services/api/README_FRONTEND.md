# Starting the MLS Automation Application

## Quick Start

Everything is already connected! You just need to start the FastAPI server.

### 1. Start the Server

**Option A: Run from project root (Recommended)**
```bash
# From project root directory
uvicorn services.api.main:app --reload --port 8000
```

**Option B: Run from services/api directory**
```bash
cd services/api
python run.py
# OR
uvicorn main:app --reload --port 8000
```

**Option C: Use the run script**
```bash
cd services/api
python run.py
```

### 2. Open in Browser

```
http://localhost:8000
```

That's it! The frontend will load automatically.

---

## How It Works

The frontend (`services/api/static/index.html`) is fully integrated with `main.py`:

1. **Root Endpoint (`/`)**: Serves the HTML file automatically
2. **Static Files**: Mounted at `/static` (if needed for additional assets)
3. **API Endpoints**: All routers are included:
   - `/api/listings` - Listing management
   - `/api/documents` - Document uploads
   - `/api/images` - Image uploads and retrieval
   - `/api/extraction` - Document extraction
   - `/api/enrichment` - Image enrichment
4. **Image Serving**: Images are served via `/api/images/{listing_id}/{image_id}`

---

## Prerequisites

Before starting, make sure:

1. **Database is running:**
   ```bash
   cd infra
   docker-compose up -d
   ```

2. **Environment variables are set:**
   - Create `services/api/.env` file (see `.env.example`)
   - Add your `GROQ_API_KEY`

3. **Dependencies are installed:**
   ```bash
   cd services/api
   pip install -r requirements.txt
   ```

---

## File Structure

```
services/api/
├── main.py              # FastAPI app (serves frontend + API)
├── static/
│   └── index.html       # Frontend interface
├── routers/             # API endpoints
├── services/            # Business logic
└── .env                 # Environment variables (create this)
```

---

## Troubleshooting

### Frontend not loading?
- Check that `services/api/static/index.html` exists
- Check server logs for errors
- Verify you're accessing `http://localhost:8000` (not `/api`)

### API calls failing?
- Check browser console (F12) for errors
- Verify API server is running on port 8000
- Check that database is running and connected

### Images not displaying?
- Verify images were uploaded successfully
- Check that `STORAGE_ROOT` environment variable is set
- Verify image files exist in the storage directory

---

## No Additional Files Needed

You don't need any other files to start the app. Everything is already connected:
- ✅ Frontend HTML is served by `main.py`
- ✅ All API endpoints are registered
- ✅ Image serving is configured
- ✅ Static file serving is set up

Just run `uvicorn main:app --reload` and you're good to go!
