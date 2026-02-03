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

# NOM EXACT DU PDF (ne pas changer)
TEMPLATE_PDF = "MODELE TRACFIN VENDEUR PHYSIQUE.pdf"

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
        "reference":
