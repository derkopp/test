# Deployment auf Proxmox (LXC + Docker + Tailscale)

Diese Anleitung betreibt die App auf einem eigenen Proxmox-Server, ohne
Ports im Heimrouter öffnen zu müssen.

## 1. LXC-Container anlegen

- Proxmox-Web-UI → "Create CT"
- Template: Debian 12 (oder Ubuntu 22.04)
- Unprivileged: ja
- Ressourcen: 1 vCPU, 512 MB–1 GB RAM, 4–8 GB Platte reichen locker
- **Wichtig für Docker im LXC**: Container → Options → Features →
  `nesting=1` und `keyctl=1` aktivieren, sonst startet der Docker-Daemon
  im Container nicht. Alternative, falls das Probleme macht: eine
  kleine VM statt eines LXC-Containers nehmen (braucht etwas mehr
  Ressourcen, dafür keine Nesting-Sonderfälle).

## 2. Docker installieren (im Container)

```bash
apt update && apt install -y ca-certificates curl gnupg git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

## 3. App klonen und starten

```bash
git clone https://github.com/derkopp/test.git ruhestandsrechner
cd ruhestandsrechner
docker compose up -d --build
```

Prüfen: `curl http://localhost:8501` sollte HTML liefern, `docker compose
logs -f` zeigt die Logs. `restart: unless-stopped` in der
`docker-compose.yml` sorgt dafür, dass der Container nach einem Neustart
des LXC-Containers automatisch wieder hochkommt.

## 4. Sicherer Fernzugriff mit Tailscale (statt Portfreigabe)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
```

Node im Tailscale-Adminpanel bestätigen. Danach die App per HTTPS mit
automatischem Zertifikat freigeben:

```bash
tailscale serve --bg https / http://localhost:8501
```

Das liefert eine URL wie `https://<container-name>.<dein-tailnet>.ts.net`,
erreichbar von jedem Gerät mit Tailscale (Handy, Laptop unterwegs) –
ganz ohne offenen Port am Router.

Soll die App auch für Leute *ohne* Tailscale-Client erreichbar sein, kann
stattdessen `tailscale funnel 443 on` verwendet werden, oder man betreibt
sie öffentlich auf einem VPS mit eigener Domain (dort übernimmt z. B.
Caddy automatisch die Let's-Encrypt-Zertifikate).

## 5. Autostart absichern

- LXC-Container: Proxmox → Options → "Start at boot" aktivieren.
- Docker-Container: startet dank `restart: unless-stopped` automatisch
  mit.
- Die `tailscale serve`-Konfiguration bleibt nach einem Neustart
  erhalten.

## 6. Updates einspielen

```bash
cd ruhestandsrechner
git pull
docker compose up -d --build
```
