from __future__ import annotations
import hashlib
import random
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from supabase import create_client

APP_DIR = Path(__file__).resolve().parent
VIDEO_DIR = APP_DIR / "videos"

EMOTIONS = ["asco", "felicidad", "miedo", "neutro"]
VIDEO_FILES = ["video_1.mp4", "video_2.mp4", "video_3.mp4", "video_4.mp4"]

def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_ANON_KEY"],
    )

def ordered_videos(expert_code: str):
    seed = int(hashlib.sha256(expert_code.encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)
    videos = VIDEO_FILES.copy()
    rng.shuffle(videos)
    return videos

def main():
    st.set_page_config(page_title="Validación de expresiones faciales", page_icon="🙂")
    st.title("Validación de expresiones faciales")
    st.write(
        "Observe los cuatro videos y clasifique cada uno. "
        "Debe usar una sola vez cada categoría: asco, felicidad, miedo y neutro."
    )

    expert_code = st.text_input("Código del experto", placeholder="EXP01").strip()
    expert_role = st.text_input("Área o rol profesional (opcional)")
    years = st.number_input("Años de experiencia (opcional)", min_value=0, max_value=60, value=0)

    if not expert_code:
        st.info("Ingrese un código de experto para comenzar.")
        st.stop()

    videos = ordered_videos(expert_code)
    answers = {}

    with st.form("validation_form"):
        for i, video_name in enumerate(videos, start=1):
            st.markdown(f"### Video {i}")
            video_path = VIDEO_DIR / video_name
            if video_path.exists():
                st.video(str(video_path))
            else:
                st.error(f"No se encontró {video_name} en {VIDEO_DIR}")

            answers[video_name] = st.selectbox(
                f"¿A qué emoción corresponde el Video {i}?",
                ["Seleccionar..."] + EMOTIONS,
                key=f"emotion_{video_name}",
            )

        comments = st.text_area("Comentario opcional")
        submit = st.form_submit_button("Enviar respuestas")

    if not submit:
        st.stop()

    if any(v == "Seleccionar..." for v in answers.values()):
        st.error("Debe clasificar los cuatro videos.")
        st.stop()

    if len(set(answers.values())) != 4:
        st.error("Debe usar cada emoción exactamente una vez.")
        st.stop()

    session_id = hashlib.sha256(
        f"{expert_code}|{datetime.now(timezone.utc).isoformat()}".encode("utf-8")
    ).hexdigest()[:16]

    rows = []
    for position, video_name in enumerate(videos, start=1):
        rows.append({
            "session_id": session_id,
            "expert_code": expert_code,
            "expert_role": expert_role.strip() or None,
            "years_experience": int(years) if years > 0 else None,
            "video_position": position,
            "video_file": video_name,
            "selected_emotion": answers[video_name],
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        })

    try:
        supabase = get_supabase()
        supabase.table("face_validation_comments").insert(
            {
                "expert_code": expert_code,
                "comment": comments.strip(),
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            },
            returning="minimal"
        ).execute()

        if comments.strip():
            supabase.table("face_validation_comments").insert({
                "expert_code": expert_code,
                "comment": comments.strip(),
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }).execute()

        st.success("Respuestas guardadas correctamente. Muchas gracias.")
    except Exception as exc:
        st.error("No se pudieron guardar las respuestas.")
        st.code(str(exc))

if __name__ == "__main__":
    main()