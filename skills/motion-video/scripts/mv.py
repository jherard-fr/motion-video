#!/usr/bin/env python3
"""Motion vidéo - accès aux API (OpenRouter pour image/vidéo, ElevenLabs pour la voix).

Sous-commandes :
  quota                         état des deux clés (crédit restant, alerte si limite proche)
  voices  [--lang fr] [--out voix.json] [--previews DIR]
                                liste les voix ElevenLabs (et télécharge les extraits d'écoute)
  image   --prompt P --aspect 16:9 --out f.png [--ref img.png ...] [--model M]
  video   --prompt P --aspect 16:9 --duration 5 --out f.mp4 [--first-frame img] [--last-frame img]
          [--model kwaivgi/kling-v3.0-std] [--no-audio] [--dry-run]
  music   --prompt P --out musique.mp3 [--model google/lyria-3-pro-preview]
  tts     --voice ID --text-file t.txt --out voix.mp3 [--timestamps t.json] [--model M]
  check                         vérifie l'installation (Python, requests, ffmpeg, Node, Chrome, clés)

Clés : dossier MOTION_VIDEO_KEYS (défaut ~/.motion-video) contenant openrouter.txt et elevenlabs.txt,
  ou variables OPENROUTER_API_KEY / ELEVENLABS_API_KEY.
Codes de sortie : 0 ok, 1 erreur, 3 limite de clé atteinte (crédit ou quota épuisé).
"""
import argparse, base64, json, mimetypes, os, re, shutil, subprocess, sys, time
from datetime import datetime, timezone
try:
    import requests
except ImportError:
    requests = None

KEYS_DIR = os.environ.get("MOTION_VIDEO_KEYS", os.path.join(os.path.expanduser("~"), ".motion-video"))
OR_FILES = ["openrouter.txt", "motion-video-openrouter.txt"]
EL_FILES = ["elevenlabs.txt", "motion-video-elevenlabs.txt"]
OR = "https://openrouter.ai/api/v1"
EL = "https://api.elevenlabs.io/v1"
KLING_RATIOS = {"16:9", "9:16", "1:1"}
# Seuils d'alerte : en dessous, on prévient avant de lancer quoi que ce soit
OR_ALERT_USD = 3.0
EL_ALERT_CHARS = 3000


def read_key(files, env):
    if os.environ.get(env):
        return os.environ[env].strip()
    for f in files:
        p = os.path.join(KEYS_DIR, f)
        if os.path.exists(p):
            k = open(p, encoding="utf-8").read().strip()
            if k:
                return k
    sys.exit(f"Clé introuvable : déposer la clé dans {os.path.join(KEYS_DIR, files[0])}")


def limit_exit(service, detail):
    print(f"LIMITE ATTEINTE - {service} : {detail}", file=sys.stderr)
    sys.exit(3)


def or_headers():
    return {"Authorization": f"Bearer {read_key(OR_FILES, 'OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"}


def el_headers():
    return {"xi-api-key": read_key(EL_FILES, "ELEVENLABS_API_KEY")}


def or_check(r):
    """Traduit les refus OpenRouter liés au crédit en message clair."""
    if r.status_code == 402 or (r.status_code == 403 and "limit" in r.text.lower()):
        q = openrouter_quota()
        limit_exit("OpenRouter", f"crédit de la clé épuisé ({q['restant_usd']} $ restants sur "
                   f"{q['limite_usd']} $, remise à zéro le {q['reset']})")
    if r.status_code >= 300:
        sys.exit(f"Erreur OpenRouter {r.status_code} : {r.text[:500]}")
    return r


def el_check(r):
    if r.status_code == 401 and "missing_permissions" in r.text:
        perm = r.json().get("detail", {}).get("message", "")
        sys.exit("Clé ElevenLabs sans la permission nécessaire : " + perm +
                 " Activer cette permission sur la clé dans elevenlabs.io > Developers > API Keys.")
    if r.status_code in (401, 402, 429) and ("quota" in r.text.lower() or "limit" in r.text.lower()):
        q = elevenlabs_quota()
        limit_exit("ElevenLabs", f"quota de caractères épuisé ({q['restant']} restants sur "
                   f"{q['limite']}, remise à zéro le {q['reset']})")
    if r.status_code >= 300:
        sys.exit(f"Erreur ElevenLabs {r.status_code} : {r.text[:500]}")
    return r


def openrouter_quota():
    d = requests.get(f"{OR}/key", headers=or_headers(), timeout=30).json()["data"]
    b = d.get("effective_budget") or {}
    rest = d.get("limit_remaining")
    return {"limite_usd": d.get("limit"), "restant_usd": None if rest is None else round(rest, 2),
            "depense_mois_usd": round(d.get("usage_monthly", 0), 2),
            "reset": (b.get("resets_at") or "")[:10] or d.get("limit_reset")}


def elevenlabs_quota():
    d = el_check(requests.get(f"{EL}/user/subscription", headers=el_headers(), timeout=30)).json()
    reset = datetime.fromtimestamp(d["next_character_count_reset_unix"], timezone.utc).strftime("%Y-%m-%d")
    return {"utilise": d["character_count"], "limite": d["character_limit"],
            "restant": d["character_limit"] - d["character_count"], "reset": reset}


def cmd_quota(o):
    res = {"maj": datetime.now().strftime("%Y-%m-%d %H:%M")}
    try:
        q = openrouter_quota()
        q["etat"] = ("limite" if q["restant_usd"] is not None and q["restant_usd"] <= 0.05 else
                     "alerte" if q["restant_usd"] is not None and q["restant_usd"] < OR_ALERT_USD else "ok")
        res["openrouter"] = q
    except SystemExit as e:
        res["openrouter"] = {"etat": "erreur", "message": str(e)}
    try:
        q = elevenlabs_quota()
        q["etat"] = "limite" if q["restant"] <= 0 else "alerte" if q["restant"] < EL_ALERT_CHARS else "ok"
        res["elevenlabs"] = q
    except SystemExit as e:
        res["elevenlabs"] = {"etat": "erreur", "message": str(e)}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if any(res[k].get("etat") == "limite" for k in ("openrouter", "elevenlabs")):
        sys.exit(3)


def cmd_voices(o):
    d = el_check(requests.get(f"{EL}/voices", headers=el_headers(), timeout=60)).json()
    out = []
    for v in d.get("voices", []):
        lab = v.get("labels") or {}
        if o.lang and lab.get("language") != o.lang:
            continue
        name = re.sub(r"^MD(?: [FM])?\s*[-|]\s*", "", v["name"]).strip()  # retire les préfixes de bibliothèque ("MD F - ...")
        out.append({"id": v["voice_id"], "nom": name.split(" - ")[0].strip(),
                    "description": name.split(" - ", 1)[1].strip() if " - " in name else lab.get("descriptive", ""),
                    "langue": lab.get("language"), "genre": lab.get("gender"), "age": lab.get("age"),
                    "accent": lab.get("accent"), "usage": lab.get("use_case"),
                    "categorie": v.get("category"), "preview_url": v.get("preview_url")})
    if o.previews:
        os.makedirs(o.previews, exist_ok=True)
        for v in out:
            if v["preview_url"]:
                p = os.path.join(o.previews, f"voix-{v['id']}.mp3")
                if not os.path.exists(p):
                    open(p, "wb").write(requests.get(v["preview_url"], timeout=60).content)
                v["fichier"] = p
    s = json.dumps(out, ensure_ascii=False, indent=1)
    if o.out:
        open(o.out, "w", encoding="utf-8").write(s)
        print(f"{len(out)} voix -> {o.out}")
    else:
        print(s)


def as_data_uri(src):
    if src.startswith(("http://", "https://", "data:")):
        return src
    mime = mimetypes.guess_type(src)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(open(src, "rb").read()).decode()


def cmd_image(o):
    if not o.ref:
        # Génération pure : endpoint /images (GPT Image)
        p = {"model": o.model, "prompt": o.prompt, "aspect_ratio": o.aspect}
        r = or_check(requests.post(f"{OR}/images", headers=or_headers(), json=p, timeout=600)).json()
        if not r.get("data"):
            sys.exit("Aucune image renvoyée : " + json.dumps(r)[:300])
        data = base64.b64decode(r["data"][0]["b64_json"])
    else:
        # Avec image(s) de référence : modèle conversationnel qui accepte des images en entrée
        content = [{"type": "text", "text": o.prompt}]
        for ref in o.ref:
            content.append({"type": "image_url", "image_url": {"url": as_data_uri(ref)}})
        p = {"model": o.ref_model, "modalities": ["image", "text"],
             "messages": [{"role": "user", "content": content}],
             "image_config": {"aspect_ratio": o.aspect}}
        r = or_check(requests.post(f"{OR}/chat/completions", headers=or_headers(), json=p, timeout=600)).json()
        imgs = r["choices"][0]["message"].get("images") or []
        if not imgs:
            sys.exit("Aucune image renvoyée : " + str(r["choices"][0]["message"].get("content"))[:300])
        url = imgs[0]["image_url"]["url"]
        data = base64.b64decode(url.split(",", 1)[1]) if url.startswith("data:") else requests.get(url, timeout=120).content
    open(o.out, "wb").write(data)
    print(json.dumps({"fichier": o.out, "cout_usd": r.get("usage", {}).get("cost")}, ensure_ascii=False))


def cmd_video(o):
    h = or_headers()
    if o.aspect not in KLING_RATIOS and "kling" in o.model:
        sys.exit(f"Kling ne génère qu'en {sorted(KLING_RATIOS)} : générer dans le ratio le plus proche et recadrer au montage")
    models = or_check(requests.get(f"{OR}/videos/models", headers=h, timeout=60)).json()["data"]
    m = next((x for x in models if x["id"] == o.model), None)
    if not m:
        sys.exit("Modèle inconnu : " + o.model)
    sk = m["pricing_skus"]
    key = "duration_seconds" if o.no_audio else "duration_seconds_with_audio"
    per_s = float(sk.get(key, sk.get("duration_seconds", 0)))
    cost = per_s * o.duration
    q = openrouter_quota()
    print(json.dumps({"cout_estime_usd": round(cost, 2), "restant_usd": q["restant_usd"]}))
    if q["restant_usd"] is not None and cost > q["restant_usd"]:
        limit_exit("OpenRouter", f"ce clip coûterait {cost:.2f} $ mais il ne reste que {q['restant_usd']} $ "
                   f"(remise à zéro le {q['reset']})")
    if o.dry_run:
        return
    p = {"model": o.model, "prompt": o.prompt, "duration": o.duration,
         "aspect_ratio": o.aspect, "generate_audio": not o.no_audio}
    frames = []
    for src, kind in ((o.first_frame, "first_frame"), (o.last_frame, "last_frame")):
        if src:
            frames.append({"type": "image_url", "image_url": {"url": as_data_uri(src)}, "frame_type": kind})
    if frames:
        p["frame_images"] = frames
    job = or_check(requests.post(f"{OR}/videos", headers=h, json=p, timeout=120)).json()
    print("job", job["id"], job["status"], flush=True)
    while True:
        time.sleep(15)
        s = requests.get(job["polling_url"], headers=h, timeout=60).json()
        print("  ", s["status"], flush=True)
        if s["status"] == "completed":
            open(o.out, "wb").write(requests.get(s["unsigned_urls"][0], headers=h, timeout=300).content)
            print(json.dumps({"fichier": o.out, "cout_usd": s.get("usage", {}).get("cost")}))
            return
        if s["status"] in ("failed", "cancelled", "expired"):
            err = str(s.get("error", s))
            if "credit" in err.lower() or "limit" in err.lower():
                limit_exit("OpenRouter", err)
            sys.exit("Échec : " + err)


def cmd_check(o):
    """Vérifie que tout ce dont la skill a besoin est installé et que les clés répondent."""
    ok = True
    def line(good, what, hint=""):
        nonlocal ok
        ok = ok and good
        print(("OK      " if good else "MANQUE  ") + what + ("" if good or not hint else "  ->  " + hint))
    line(sys.version_info >= (3, 9), f"Python {sys.version.split()[0]}", "installer Python 3.9 ou plus récent")
    line(requests is not None, "module Python requests", "python -m pip install requests")
    for exe, hint in (("ffmpeg", "installer ffmpeg (voir le README)"), ("ffprobe", "fourni avec ffmpeg"),
                      ("node", "installer Node.js 22 LTS"), ("npx", "fourni avec Node.js"), ("git", "installer Git")):
        line(shutil.which(exe) is not None, exe, hint)
    chrome = [p for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                          "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome") if os.path.exists(p)] or \
             [shutil.which(x) for x in ("google-chrome", "chromium", "chrome") if shutil.which(x)]
    line(bool(chrome), "Google Chrome (vérification des extraits animés)", "installer Google Chrome")
    for name, files, env in (("OpenRouter", OR_FILES, "OPENROUTER_API_KEY"), ("ElevenLabs", EL_FILES, "ELEVENLABS_API_KEY")):
        found = os.environ.get(env) or any(os.path.exists(os.path.join(KEYS_DIR, f)) and
                                           open(os.path.join(KEYS_DIR, f), encoding="utf-8").read().strip() for f in files)
        line(bool(found), f"clé {name}", f"déposer la clé dans {os.path.join(KEYS_DIR, files[0])}")
    if requests is not None and ok:
        try:
            q = openrouter_quota(); line(True, f"OpenRouter répond : {q['restant_usd']} $ restants")
        except SystemExit as e:
            line(False, "OpenRouter répond", str(e))
        try:
            q = elevenlabs_quota(); line(True, f"ElevenLabs répond : {q['restant']} caractères restants")
        except SystemExit as e:
            line(False, "ElevenLabs répond", str(e))
    print("\nTout est prêt." if ok else "\nÀ compléter avant d'utiliser la skill.")
    sys.exit(0 if ok else 1)


def cmd_music(o):
    """Musique instrumentale via Lyria (OpenRouter, réponse audio en flux obligatoire)."""
    q = openrouter_quota()
    if q["restant_usd"] is not None and q["restant_usd"] < 0.2:
        limit_exit("OpenRouter", f"il ne reste que {q['restant_usd']} $ (remise à zéro le {q['reset']})")
    p = {"model": o.model, "stream": True, "modalities": ["text", "audio"],
         "messages": [{"role": "user", "content": o.prompt}]}
    r = or_check(requests.post(f"{OR}/chat/completions", headers=or_headers(), json=p, stream=True, timeout=900))
    chunks, cost = [], None
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: {"):
            continue
        d = json.loads(line[6:])
        if d.get("error"):
            sys.exit("Erreur musique : " + json.dumps(d["error"])[:300])
        for c in d.get("choices", []):
            a = (c.get("delta") or {}).get("audio") or {}
            if a.get("data"):
                chunks.append(a["data"])
        cost = (d.get("usage") or {}).get("cost", cost)
    if not chunks:
        sys.exit("Aucun audio renvoyé par " + o.model)
    open(o.out, "wb").write(base64.b64decode("".join(chunks)))
    print(json.dumps({"fichier": o.out, "cout_usd": cost}))


def cmd_tts(o):
    text = open(o.text_file, encoding="utf-8").read().strip() if o.text_file else o.text
    q = elevenlabs_quota()
    if len(text) > q["restant"]:
        limit_exit("ElevenLabs", f"le texte fait {len(text)} caractères mais il n'en reste que {q['restant']} "
                   f"(remise à zéro le {q['reset']})")
    p = {"text": text, "model_id": o.model,
         "voice_settings": {"stability": o.stability, "similarity_boost": 0.75, "style": o.style}}
    r = el_check(requests.post(f"{EL}/text-to-speech/{o.voice}/with-timestamps",
                               headers={**el_headers(), "Content-Type": "application/json"}, json=p, timeout=300)).json()
    open(o.out, "wb").write(base64.b64decode(r["audio_base64"]))
    if o.timestamps:
        a = r.get("alignment") or {}
        # Regroupe les caractères en mots horodatés (pour les sous-titres)
        words, cur, start = [], "", None
        for ch, t0, t1 in zip(a.get("characters", []), a.get("character_start_times_seconds", []),
                              a.get("character_end_times_seconds", [])):
            if ch.isspace():
                if cur:
                    words.append({"mot": cur, "debut": start, "fin": last})
                cur, start = "", None
            else:
                cur += ch
                start = t0 if start is None else start
                last = t1
        if cur:
            words.append({"mot": cur, "debut": start, "fin": last})
        json.dump(words, open(o.timestamps, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    dur = (r.get("alignment") or {}).get("character_end_times_seconds", [0])[-1]
    print(json.dumps({"fichier": o.out, "duree_s": round(dur, 2), "caracteres": len(text),
                      "restant_apres": q["restant"] - len(text)}))


def main():
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    a = argparse.ArgumentParser(description="Motion vidéo - API")
    sub = a.add_subparsers(dest="cmd", required=True)
    sub.add_parser("quota"); sub.add_parser("check")
    v = sub.add_parser("voices"); v.add_argument("--lang"); v.add_argument("--out"); v.add_argument("--previews")
    i = sub.add_parser("image"); i.add_argument("--prompt", required=True); i.add_argument("--aspect", default="16:9")
    i.add_argument("--out", required=True); i.add_argument("--ref", action="append")
    i.add_argument("--model", default="openai/gpt-image-2.5-flare")
    i.add_argument("--ref-model", default="google/gemini-3.1-flash-image")
    d = sub.add_parser("video"); d.add_argument("--prompt", required=True); d.add_argument("--aspect", default="16:9")
    d.add_argument("--duration", type=int, default=5); d.add_argument("--out", default="clip.mp4")
    d.add_argument("--first-frame"); d.add_argument("--last-frame")
    d.add_argument("--model", default="kwaivgi/kling-v3.0-std")
    d.add_argument("--no-audio", action="store_true"); d.add_argument("--dry-run", action="store_true")
    m = sub.add_parser("music"); m.add_argument("--prompt", required=True); m.add_argument("--out", required=True)
    m.add_argument("--model", default="google/lyria-3-pro-preview")
    t = sub.add_parser("tts"); t.add_argument("--voice", required=True); t.add_argument("--text")
    t.add_argument("--text-file"); t.add_argument("--out", required=True); t.add_argument("--timestamps")
    t.add_argument("--model", default="eleven_multilingual_v2")
    t.add_argument("--stability", type=float, default=0.5); t.add_argument("--style", type=float, default=0.0)
    o = a.parse_args()
    if requests is None and o.cmd != "check":
        sys.exit("Module Python requests manquant : python -m pip install requests")
    {"check": cmd_check, "quota": cmd_quota, "voices": cmd_voices, "image": cmd_image, "video": cmd_video, "music": cmd_music,
     "tts": cmd_tts}[o.cmd](o)


main()
