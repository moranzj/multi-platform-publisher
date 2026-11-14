<div align="center">

# Multi-Platform Video Publisher (Editor multplataforma de vídeos)

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · **Español** · [Français](README.fr.md) · [Deutsch](README.de.md) · [Русский](README.ru.md) · [Português (BR)](README.pt-BR.md) · [Italiano](README.it.md) · [Türkçe](README.tr.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [ไทย](README.th.md) · [Polski](README.pl.md) · [Nederlands](README.nl.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md)

Un vídeo → **Bilibili · Kuaishou · Douyin** — las tres páginas de publicación, rellenadas por ti.

Gratis y de código abierto (MIT) · Exe portable, sin instalación · Rellena y se detiene: el botón «Publicar» lo pulsas tú

[⬇️ Descargar (exe portable)](https://github.com/moranzj/multi-platform-publisher/releases/latest) · [📖 Tutorial paso a paso (inglés)](docs/tutorial-en.md)

</div>

<p align="center">
  <img src="docs/images/app-form.png" width="32%" alt="formulario">
  <img src="docs/images/app-run.png" width="32%" alt="registro">
  <img src="docs/images/app-done.png" width="32%" alt="listo">
</p>

## Qué hace

Rellena el formulario **una vez**: la herramienta abre las páginas de subida de las tres plataformas en tu Chrome/Edge y lo completa todo: subida del vídeo, título, descripción, hashtags, portada y programación. Al terminar, las páginas quedan abiertas — las revisas y pulsas «Publicar» tú mismo. La herramienta nunca envía sin tu permiso.

- **Bilibili / Kuaishou / Douyin** — un vídeo, publicación por lotes
- Títulos y descripciones por plataforma, hashtags, portada (sube una imagen o usa automáticamente el primer fotograma del vídeo)
- **Publicación inmediata o programada** (ventanas validadas por plataforma: Bilibili +5 min–15 días, Kuaishou +1 h–14 días, Douyin +2 h–14 días)
- Etiqueta «perilla de juego» para Douyin (la web de Kuaishou no tiene esa opción)
- Vista previa y comprobaciones antes de abrir nada: longitud de título/descripción, número de etiquetas, proporción de portada, tamaño de archivo
- Registro en vivo, capturas por paso, plantillas históricas (hasta 50)
- Sin extensiones de navegador — inicia sesión una vez por plataforma con código QR y queda guardada

> La interfaz está en chino; el [tutorial](docs/tutorial-en.md) explica cada campo con capturas de pantalla.

## Descargar y ejecutar (Windows 10/11)

1. Descarga `multi-platform-publisher-<version>-exe.zip` desde [Releases](https://github.com/moranzj/multi-platform-publisher/releases/latest).
2. Descomprime en cualquier carpeta **escribible** (no en Program Files).
3. Doble clic en **`多平台发布器.exe`** — solo necesita Chrome o Edge. Primer uso: pulsa «重新登录» (reinicar sesión) y escanea el código QR una vez por plataforma.

> El exe no está firmado, por lo que algún antivirus puede marcarlo — falso positivo habitual de PyInstaller; añádelo a la lista blanca. ¿Prefieres el código fuente? `git clone` + `setup.bat` (Python 3.9+).

```powershell
python cli.py doctor    # autocomprobación del entorno
python cli.py login     # inicio de sesión QR, tres pestañas
python cli.py publish --video "D:\v\clip.mp4" --title "Título" --ks-topics "#etiqueta1 #etiqueta2" --date 2026-11-20 --time 06:00
```

Comportamiento por defecto: rellena todo y **se detiene** — revisas las páginas y pulsas Publicar tú mismo (`--auto` activa el envío automático; `--now` publica al instante).

## Preguntas frecuentes

| Síntoma | Solución |
|---|---|
| Se queda en la página de inicio de sesión | Sesión caducada — «重新登录» y escanea de nuevo |
| «profile is busy» | Cierra la ventana del navegador de la ejecución anterior |
| El antivirus marca el exe | Falso positivo de PyInstaller — lista blanca |
| Un hashtag no se convierte en píldora | El tema no existe en esa plataforma — redáctalo de otra forma |
| CAPTCHA | Resuélvelo una vez a mano; publicar con mucha frecuencia puede activar comprobaciones |

## Notas y limitaciones

- Las plataformas se procesan en serie; 3–8 min por vídeo (según el tamaño del archivo)
- La sesión se guarda en `profile/` — **no la compartas nunca** (son tus cuentas)
- Un rediseño de la plataforma puede romper los selectores; las correcciones van en `platforms/<plataforma>.py`
- No es una API oficial ni está afiliado a Bilibili, Kuaishou o Douyin. La automatización del navegador puede violar los términos de las plataformas — prueba con una cuenta secundaria y publica con responsabilidad, bajo tu propio riesgo.

## Licencia

[MIT](LICENSE)
