# 3D Autorennen 🏎️

Ein einfaches 3D-Autorennspiel, das direkt im Browser läuft (gebaut mit [Three.js](https://threejs.org/)).

Das ist erst die **Grundlage**: eine 3D-Welt mit Boden, einer ovalen Rennstrecke und einem fahrbaren Auto. Aussehen, Strecke, Gegner, Runden usw. bauen wir als Nächstes gemeinsam aus.

## Starten

Weil das Spiel ES-Module lädt, muss es über einen lokalen Webserver geöffnet werden (nicht einfach die `index.html` per Doppelklick öffnen).

```bash
cd race-game
python3 -m http.server 8000
```

Danach im Browser öffnen: [http://localhost:8000](http://localhost:8000)

### Alternative: mit Docker

```bash
cd race-game
docker compose up --build
```

Oder ohne Compose:

```bash
cd race-game
docker build -t race-game .
docker run --rm -p 8000:80 race-game
```

Danach ebenfalls im Browser öffnen: [http://localhost:8000](http://localhost:8000)

## Steuerung

| Taste | Aktion |
| --- | --- |
| `↑` / `W` | Gas geben |
| `↓` / `S` | Bremsen / Rückwärts |
| `←` / `A` | Nach links lenken |
| `→` / `D` | Nach rechts lenken |

## Projektstruktur

```
race-game/
├── index.html          Seite mit Canvas, HUD und Startbildschirm
├── style.css            Layout und Design der Oberfläche
├── main.js               Szene, Auto, Steuerung, Kamera, Spiel-Loop
├── vendor/three/         Lokal eingebundenes Three.js (funktioniert offline)
├── Dockerfile             Statische Dateien in einem nginx-Container ausliefern
└── docker-compose.yml     Bequemer Start des Containers
```

## Stand der Grundlagen

- 3D-Szene mit Himmel, Licht und Schatten
- Ovale Rennstrecke mit Start-/Ziellinie
- Fahrbares Auto mit einfacher Arcade-Physik (Beschleunigen, Bremsen, Lenken, Reibung)
- Kamera, die dem Auto von schräg hinten folgt
- Geschwindigkeitsanzeige (HUD)

Noch **nicht** enthalten (kommt später, je nachdem was ihr euch wünscht): Streckenbegrenzung/Kollision, Rundenzählung, Gegner oder Freunde zum Mitfahren, Hindernisse, Sound, verschiedene Strecken/Autos, Mobile-Steuerung usw.
