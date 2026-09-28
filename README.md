# Validación web de caras sintéticas

1. Copia 4 videos a `videos/` y renómbralos:
   - video_1.mp4
   - video_2.mp4
   - video_3.mp4
   - video_4.mp4

2. En Supabase > SQL Editor ejecuta `supabase_setup.sql`.

3. Crea `.streamlit/secrets.toml` con:
   SUPABASE_URL = "..."
   SUPABASE_ANON_KEY = "..."

4. Instala:
   python -m pip install -r requirements.txt

5. Ejecuta:
   streamlit run app.py

6. Para compartir por link, sube la carpeta a GitHub y despliega en Streamlit Community Cloud.
   Añade allí los mismos Secrets. No subas tus claves reales al repositorio.

La app:
- randomiza el orden de los 4 videos según el código del experto;
- no muestra la emoción real;
- obliga a usar una vez cada categoría;
- guarda respuestas en Supabase.