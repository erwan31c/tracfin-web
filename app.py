import os
import re
import io
from datetime import datetime

import fitz  # PyMuPDF
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# NOM EXACT DU PDF (ne pas changer)
TEMPLATE_PDF = "modele.pdf"

# ----- Sécurité simple -----
security = HTTPBasic()
APP_USER = os.getenv("APP_USER", "admin")
APP_PASS = os.getenv("APP_PASS", "motdepasse")

def auth(credentials: HTTPBasicCredentials = Depends(security)):
    user_ok = secrets.compare_digest(credentials.username, APP_USER)
    pass_ok = secrets.compare_digest(credentials.password, APP_PASS)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            detail="Accès refusé",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

# ----- Coordonnées sur le PDF -----
POS = {
    "date": (235, 275),
    "reference": (235, 305),
    "nom": (165, 345),
    "date_naissance": (215, 362),
    "lieu_naissance": (360, 362),
    "nationalite": (165, 380),
    "situation": (205, 397),
    "adresse": (200, 414),
    "telephone": (165, 431),
    "email": (145, 448),
    "justificatif": (235, 465),

    # NOTATION (toujours pareil)
    "q1_oui": (497, 513),
    "q2_non": (548, 545),
    "q3_non": (548, 570),
    "risque_faible": (266, 616),
}

FONT = "helv"

def nettoyer(txt):
    return re.sub(r"\s+", " ", txt or "").strip()

def chercher(texte, motifs):
    for m in motifs:
        r = re.search(m, texte, re.IGNORECASE)
        if r:
            return nettoyer(r.group(1))
    return ""

def analyser_texte(texte):
    return {
        "reference": chercher(texte, [
            r"référence\s*dossier\s*:\s*(.+)",
            r"ref\s*:\s*(.+)",
        ]),
        "date": chercher(texte, [
            r"fiche.*le\s*:\s*(.+)",
            r"date\s*:\s*(\d{1,2}/\d{1,2}/\d{4})",
        ]) or datetime.now().strftime("%d/%m/%Y"),
        "nom": chercher(texte, [
            r"client\s*:\s*(.+)",
            r"nom\s*:\s*(.+)",
        ]),
        "date_naissance": chercher(texte, [
            r"né le\s*(.+?)\s+à",
        ]),
        "lieu_naissance": chercher(texte, [
            r"né le.+?\s+à\s+(.+)",
        ]),
        "nationalite": chercher(texte, [
            r"nationalité\s*:\s*(.+)",
        ]),
        "situation": chercher(texte, [
            r"situation\s*familiale\s*:\s*(.+)",
        ]),
        "adresse": chercher(texte, [
            r"adresse\s*:\s*(.+)",
        ]),
        "telephone": chercher(texte, [
            r"téléphone\s*:\s*(.+)",
            r"tel\s*:\s*(.+)",
        ]),
        "email": chercher(texte, [
            r"email\s*:\s*(.+)",
        ]),
        "justificatif": chercher(texte, [
            r"justificatif\s*:\s*(.+)",
        ]),
    }


app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def accueil(request: Request, ok: bool = Depends(auth)):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate")
def creer_pdf(texte: str = Form(...), ok: bool = Depends(auth)):
    if not texte.strip():
        raise HTTPException(status_code=400, detail="Texte vide")
    pdf = generer_pdf(texte)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=TRACFIN_REMPLI.pdf"},
    )



