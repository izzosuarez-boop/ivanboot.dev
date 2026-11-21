# Playbook de imágenes y videos con IA (Ardea Skin)

Guía práctica para generar las fotos de producto, las imágenes de categoría y los videos explicativos
de la tienda, con los errores que ya encontramos y cómo se resolvieron. Si vas a crear medios
nuevos, lee primero la sección de errores conocidos.

Última actualización: 2026-11-20. Las 3 categorías de la demo (limpiadores, sérums y mascarillas)
tienen portada y video.

---

## 1. El flujo completo

```
categories.json  ──►  imagen de portada (Nano Banana Pro)  ─┐
 (textos, tomas,      clip de 15 s (Gemini Omni)            ├─► revisión manual ─► Shopify Files ─► category-media.json ─► web
  subtítulos, voz)    voz por subtítulo (Gemini TTS)        │
                      montaje (ffmpeg)  ────────────────────┘
```

| Paso | Herramienta | Comando | Costo aprox. |
|---|---|---|---|
| Foto de producto 1:1 | `gemini-3-pro-image` (Nano Banana Pro), 2K | `python scripts/images/generate_product_image.py <handle> --ref <aprobada>` | 0,14 USD |
| Imagen de portada 16:9 | `gemini-3-pro-image`, 2K | `python scripts/media/generate_category_media.py <slug> hero` | 0,14 USD |
| Clip de video 15 s | `gemini-omni-1.2-flash`, 1080p | `python scripts/media/generate_category_media.py <slug> clip` | 1,56 USD (720p: 1,04) |
| Voz | `gemini-3.8-flash-tts` | `python scripts/media/generate_category_media.py <slug> voice` | < 0,01 USD |
| Montaje | ffmpeg (vía `pip install imageio-ffmpeg`) | `python scripts/media/generate_category_media.py <slug> assemble` | gratis |
| Subida al CDN | Shopify Files | `python scripts/shopify/upload_files.py <slug> --hero … --poster … --video …` | gratis |

**Una categoría completa cuesta ≈ 1,70–1,90 USD.** Precios verificados el 2026-11-20 en
`aistudio.google.com/docs/pricing`. Google duplica el precio de la voz desde el 1 de enero de 2027.

### Dónde vive cada cosa

- **Textos de la página y guion del video:** `apps/web/src/content/categories.json`. Página y video
  salen del mismo archivo para que no se desincronicen.
- **URLs de los medios publicados:** `apps/web/src/content/category-media.json` (lo escribe `upload_files.py`).
- **Fotos de producto aprobadas:** `scripts/images/approved.json`. Los archivos están en
  `scripts/images/out/` y no se suben a git.
- **Salidas de video:** `scripts/media/out/<slug>/` (no se suben a git).
- **Tipografías para subtítulos:** `scripts/media/fonts/` (Fraunces e Inter, licencia OFL).

---

## 2. Errores conocidos y su solución

Cada error se encontró generando de verdad. El "cómo se detectó" importa: casi ninguno daba un
mensaje de error, el resultado simplemente salía mal.

### Voz (TTS)

**V1. El modelo de voz lee en voz alta las instrucciones de estilo.**
- **Síntoma:** una frase de 5 palabras duraba más de 4 s, y la narración completa 20-25 s.
- **Causa:** `gemini-3.8-flash-tts` no interpreta prefijos como "Read this in a calm voice…" ni
  "Say warmly and calmly:". Los lee como parte del texto.
- **Cómo se detectó:** transcribiendo el audio con `gemini-flash-latest`. La transcripción decía
  literalmente *"Say warmly and calmly, start on clean, toned skin"*.
- **Solución:** enviar **solo el texto que debe decirse**. El tono se controla eligiendo la voz
  (usamos `Aoede`), no con instrucciones.
- **Regla:** después de cambiar algo de la voz, transcribe siempre el resultado. No te fíes de la duración.

**V2. El audio ya llega como WAV.**
- **Síntoma:** duraciones raras y un posible clic al inicio.
- **Causa:** el modelo 3.8 devuelve `audio/wav` con cabecera; los modelos 2.5 devolvían PCM sin cabecera.
  Envolverlo otra vez en WAV metía la cabecera como si fuera sonido.
- **Solución:** si el `mimeType` contiene `wav` o los bytes empiezan por `RIFF`, guardarlo tal cual.

**V3. Cada frase trae silencio al principio y al final.**
- **Causa:** el modelo agrega relleno de silencio.
- **Solución:** recortar ambos extremos con ffmpeg (`silenceremove` + `areverse`, ya está en el script).

**V4. Una sola narración larga no coincide con las tomas.**
- **Síntoma:** las cuatro frases se decían en los primeros 7 s de un video de 15 s, así que la voz
  iba por delante de la imagen.
- **Solución:** **una frase por subtítulo** (campo `say` en `categories.json`). En el montaje cada
  frase se retrasa hasta el `from` de su subtítulo + 0,2 s. El script avisa si una frase dura más
  que su ventana.

**V5. La voz debe describir lo que se ve.**
- **Síntoma:** la voz decía "on your fingertips" mientras las gotas caían en la palma.
- **Solución:** después de generar el clip, mira los fotogramas y ajusta las frases `say` a lo que
  realmente muestra. Regenerar una frase cuesta céntimos; regenerar el clip, 1,56 USD.

### Video (Gemini Omni)

**C1. Veo no está disponible.**
- El modelo de video actual de esta API es **Gemini Omni 1.2 Flash** (`gemini-omni-1.2-flash`).
  Veo 3.1 Preview fue retirado.
- **No usa `generateContent`.** Usa la **Interactions API**: `POST /v1beta/interactions`.
- Cuerpo: `model`, `input` (lista de items `{"type":"image","data":<base64>,"mime_type":…}` y
  `{"type":"text","text":…}`) y `response_format`
  (`{"type":"video","aspect_ratio":"16:9","resolution":"1080p","duration":"15s","delivery":"uri"}`).
- Duración de 3 a 15 s. Se puede extender hasta 30 s en turnos de 3-10 s.
- El audio se genera siempre. No hay interruptor: se controla desde el prompt.
- Documentación: `https://aistudio.google.com/docs/omni`.

**C2. La URL de descarga viene completa.**
- **Síntoma:** el script falló *después* de generar (y cobrar) el video. Intentó leer como JSON lo
  que en realidad era el MP4.
- **Causa:** el campo `uri` trae `https://…/v1beta/files/<id>:download?alt=media`, no `files/<id>`.
- **Solución:** extraer el id con `re.search(r"files/([^:/?]+)", uri)`. Ya está corregido.
- **Si vuelve a fallar algo tras generar: NO regeneres.** La respuesta queda guardada en
  `out/<slug>/clip-response.json` y el archivo sigue disponible unas 48 h en
  `GET /v1beta/files/<id>:download?alt=media`. Descárgalo desde ahí.

**C3. El producto del video debe ser el nuestro.**
- **Solución:** pasar la foto aprobada del producto como imagen de referencia (`video.reference`
  en `categories.json`) y repetir en el prompt *"must look exactly like the product in the reference image"*.
- **Resultado:** el frasco salió idéntico, con "ARDEA" y el nombre del producto legibles.

**C4. Nada de texto generado dentro del video.**
- Pedimos *"Do not add any on-screen text, captions, subtitles or logos other than the ARDEA lettering"*.
  Los subtítulos los pone ffmpeg, con nuestra tipografía y en el momento exacto. El texto que genera
  un modelo puede salir con faltas o desalineado.

**C5. El audio del clip se usa como música de fondo.**
- Pedimos *"no dialogue, no voiceover, no singing; soft ambient room tone and a gentle, calm acoustic
  background track"*. En el montaje se baja al 30 % y la voz va encima, con normalización a -16 LUFS.

### Imágenes (Nano Banana Pro)

**I1. Lógica física: dos goteros.**
- **Síntoma:** en la portada de sérums, la mano sostenía un gotero y el frasco seguía con el suyo puesto.
- **Solución:** describir el estado de cada objeto sin ambigüedad: *"the bottle stands OPEN … its
  dropper is the one in her hand … there is only ONE dropper in the image"*.
- **Regla:** cuando una escena tiene un objeto en uso (gotero, tapa, tarro abierto), di dónde está cada pieza.

**I2. Describir el encuadre "por partes" produce collages.**
- **Síntoma 1:** pedir "espacio libre a la izquierda para el título" dio un rectángulo liso pegado a la izquierda.
- **Síntoma 2, peor:** corregirlo con *"the left third is the same out-of-focus background…"* dio
  **dípticos** (dos fotos pegadas con un corte vertical) en 3 de 4 portadas. Mencionar "el tercio izquierdo"
  hace que el modelo piense la imagen en partes.
- **Solución:** nunca describir el encuadre por zonas. Pedir **una sola fotografía**
  (`ONE_FRAME_TEXT` en el script: *"ONE single continuous photograph … not a collage, diptych … no vertical
  dividing lines … main subject slightly right of center"*) y resolver el área del texto con CSS (degradado).
- **Detector automático:** `seam_score()` mide en qué fracción de filas hay un borde fuerte en la misma
  columna. Calibrado con imágenes reales: dípticos 0,89–1,0, foto buena 0,24–0,34. Por encima de 0,6 el
  script imprime `WARNING` y la imagen no se usa.

**I3. Letras de dos colores en vidrio oscuro.**
- **Síntoma:** en el sérum de retinal (vidrio ámbar), "ARD" salió blanco y "EA" marrón.
- **Solución:** en envases oscuros, especificar *"ALL lettering … in one uniform solid ivory-cream color"*.

**I4. Aspecto "de laboratorio".**
- **Síntoma:** la primera foto parecía de farmacia: gotero estándar y etiqueta de papel pegada.
- **Solución (dirección de arte aprobada):**
  - vidrio grueso y pesado, de hombros redondeados;
  - **metal champán cepillado**;
  - letras **impresas sobre el envase**, sin pegatina;
  - pedestal de travertino, luz cálida de tarde, poca utilería.
- Está en `ART_DIRECTION` de `generate_product_image.py`.

**I5. Todos los envases iguales.**
- **Solución:** la marca es común, la escena no. Cada categoría tiene su envase y su escena
  (`PACKAGING` y `SCENES`), y los sérums se diferencian por el tono del vidrio o del líquido (`SERUM_TINTS`).

**I6. La foto de referencia puede contagiar la escena.**
- Al pasar la foto aprobada como referencia, aclarar: *"match its lettering style, champagne-gold
  finish, color grading … Do NOT copy its packaging shape or its set"*.

**I7. Revisar el texto letra por letra, recortando y ampliando la etiqueta.**
- El modelo escribe bien las etiquetas casi siempre, pero no siempre. Así se detectaron I3 y un
  "130 ML" en un tubo de 150 ml (portada de limpiadores). En la vista reducida no se distingue:
  **recorta la zona de la etiqueta, gírala si va en vertical y amplíala** antes de aprobar.

**I8. Un error de texto se corrige editando, no regenerando.**
- Se le pasa la imagen buena a Nano Banana Pro con *"Change only '130 ML' to '150 ML', in exactly the
  same font, size, color and position. Keep everything else in the image exactly the same."*
- Cuesta lo mismo (0,14 USD) pero conserva la composición aprobada.
- **Verificación:** diferencia píxel a píxel con la original. Salió una media de 1,4/255, solo en la zona de la etiqueta.

### Subida a Shopify Files

**S1. Los videos se cortan al subir.** Un MP4 de 6 MB falló con un tiempo de espera de 120 s y luego
con un corte SSL. Ahora: 900 s de espera para videos y un reintento automático.

**S2. Archivos huérfanos.** El script guardaba las URLs solo al final, así que cuando falló el video, la
portada y la miniatura ya subidas quedaron sin registrar y se duplicaron al reintentar. Ahora guarda
`category-media.json` después de cada archivo. Si vuelve a pasar, busca con
`files(query:"filename:<nombre>*")` y borra con `fileDelete` los que no estén en el JSON.

**S3. Shopify recodifica los videos a más peso.** Un MP4 de 2,2 MB (1080p) subido como `VIDEO` se sirvió
a 4,8 MB, y uno de 0,98 MB (720p) a 3 MB. Para videos de fondo que cargan en cada visita, sube tus propias
versiones como **archivo genérico** (`--raw-video brand-1080.mp4 brand-720.mp4`), que se sirven tal cual.
Para los tutoriales, que solo cargan cuando se ven, la versión de Shopify (1080/720/480) está bien.

### Video de marca (portada de la tienda)

- `python -c "import generate_category_media as g; g.brand()"` → un clip de 15 s con las **3 fotos de
  producto como referencia** (Omni admite hasta 6). Recorre mañana → tarde → noche, el mismo orden que la
  rutina, y termina con los tres productos juntos.
- `g.brand_web(<clip>)` → versiones web **sin pista de audio**, con fundido de entrada y salida al color
  arena de la página (`0xf5f0e8`) para que el bucle no dé saltos.
- En la web va en `autoPlay muted loop playsInline`. Si el visitante pidió menos movimiento
  (`prefers-reduced-motion`) o usa ahorro de datos, solo se muestra la miniatura.

### Reproducción automática de los tutoriales (`howto-video.tsx`)

- Arranca una vez cuando el reproductor se ve completo, se pausa con el 50 % o menos visible, y después
  solo el visitante lo reanuda.
- Los navegadores bloquean el autoplay **con sonido** si el visitante no ha interactuado: se intenta con
  sonido y, si falla, se reproduce en silencio con un botón "Tap for sound".
- **Probado con un navegador real** (Playwright, en `scripts/tests/video_behavior_test.py`, usando el Chrome
  instalado con `channel="chrome"`: el Chromium descargado por Playwright no coincidía con la versión del
  paquete).

### Cuentas y facturación

**F1.** Los modelos de imagen y video de Gemini tienen **cuota 0 en el nivel gratuito** (error 429
`limit: 0`). Hace falta activar la facturación. En Colombia es una recarga prepago; hicimos una de 100 000 COP.

**F2.** El costo de cada imagen se calcula desde `usageMetadata` (tokens de imagen × 120 USD/M +
texto y razonamiento × 12 USD/M + entrada × 2 USD/M). El script lo imprime. El de cada video, desde
`usage.output_tokens_by_modality` (1080p ≈ 8 688 tokens/s × 12 USD/M).

---

## 3. Lista de control para una categoría nueva

1. **Escribir el contenido en `categories.json`:** beneficios, pasos, guía de elección y `video`.
   En `video` van `reference` (handle del producto), `captions` con `from`/`to`/`text`/`say` y `shots` con tiempos.
   - 4 tomas de unos 3,5 s cada una. Las tomas en el prompt (`[0-4s] …`) deben coincidir con los subtítulos.
   - Frases `say` cortas, de 5 a 8 palabras: cada una debe durar menos que su ventana.
2. **Agregar la escena de portada** en `HERO_SCENES` (`generate_category_media.py`), describiendo el
   estado de cada objeto (I1) y el fondo continuo (I2).
3. `… <slug> voice` → **transcribir el resultado** y confirmar que dice exactamente el texto (V1).
4. `… <slug> hero` → revisar: un solo objeto de cada tipo, sin paneles, texto correcto.
5. `… <slug> clip` → extraer 4 fotogramas (uno por toma) y revisar el producto, las manos y la coherencia.
6. **Ajustar las frases `say`** a lo que muestra el clip (V5) y regenerar solo esas.
7. `… <slug> assemble` → revisar un fotograma con subtítulo y el volumen (media de unos -20 dB y
   picos por debajo de -1 dB: `ffmpeg -af volumedetect`).
8. `upload_files.py <slug> --hero … --poster … --video …` → actualiza `category-media.json`.
9. Compilar, desplegar (`bash infra/deploy.sh`) y comprobar que la página carga el video.

### Comandos útiles

```bash
FF=$(python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")

# Fotogramas de revisión, uno por toma
for t in 1.5 5.5 9.5 13.5; do "$FF" -y -loglevel error -ss $t -i clip.mp4 -frames:v 1 -vf scale=960:-1 f$t.jpg; done

# Silencios dentro de una voz (si dura demasiado)
"$FF" -i voice0.wav -af silencedetect=noise=-40dB:d=0.3 -f null - 2>&1 | grep silence_

# Volumen final
"$FF" -i final.mp4 -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

Para transcribir una voz y verificarla: enviar el WAV a `gemini-flash-latest` con
*"Transcribe exactly what is spoken, word for word"*. Hay un ejemplo en el historial de esta sesión
y es fácil de rehacer con `generate_category_media.post()`.

---

## 4. Plantilla del guion de video

```json
"video": {
  "reference": "<handle del producto que aparece>",
  "captions": [
    { "from": 0.3,  "to": 3.8,  "text": "1  <paso corto>", "say": "<frase de 5-8 palabras>" },
    { "from": 3.9,  "to": 7.6,  "text": "2  <paso corto>", "say": "<frase>" },
    { "from": 7.7,  "to": 11.4, "text": "3  <paso corto>", "say": "<frase>" },
    { "from": 11.5, "to": 14.8, "text": "4  <paso corto>", "say": "<frase>" }
  ],
  "shots": "[0-4s] <toma 1> [4-8s] <toma 2> [8-12s] <toma 3> [12-15s] plano final del producto sobre travertino, lento acercamiento, letras ARDEA nítidas."
}
```

La última toma siempre es el producto solo, en reposo: de ahí sale la miniatura del video (el script
toma un fotograma 1,5 s antes del final).
