from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from supabase import create_client


# ============================================================
# CONFIGURACIÓN
# ============================================================

APP_DIR = Path(__file__).resolve().parent
VIDEO_DIR = APP_DIR / "videos"

EMOTIONS = [
    "asco",
    "felicidad",
    "miedo",
    "neutro",
]

PAGES = {
    1: [
        "video_01.mp4",
        "video_02.mp4",
        "video_03.mp4",
        "video_04.mp4",
    ],
    2: [
        "video_05.mp4",
        "video_06.mp4",
        "video_07.mp4",
        "video_08.mp4",
    ],
    3: [
        "video_09.mp4",
        "video_10.mp4",
        "video_11.mp4",
        "video_12.mp4",
    ],
}

TOTAL_PAGES = 3


# ============================================================
# SUPABASE
# ============================================================

def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_ANON_KEY"],
    )


# ============================================================
# ESTADO
# ============================================================

def initialize_state():
    defaults = {
        "started": False,
        "completed": False,
        "full_name": "",
        "current_page": 1,
        "answers": {},
        "video_orders": {},
        "session_id": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_validation():
    keys = [
        "started",
        "completed",
        "full_name",
        "current_page",
        "answers",
        "video_orders",
        "session_id",
    ]

    for key in keys:
        if key in st.session_state:
            del st.session_state[key]

    st.rerun()


# ============================================================
# ORDEN DE VIDEOS
# ============================================================

def get_page_order(page_number: int) -> list[str]:
    """
    Todos los evaluadores reciben los mismos 12 videos.

    El orden dentro de cada página se modifica de forma
    determinística según el nombre del evaluador para reducir
    posibles efectos de posición.
    """

    if page_number in st.session_state.video_orders:
        return st.session_state.video_orders[page_number]

    videos = PAGES[page_number].copy()

    seed_text = (
        f"{st.session_state.full_name.lower().strip()}"
        f"|page={page_number}"
    )

    seed = int(
        hashlib.sha256(
            seed_text.encode("utf-8")
        ).hexdigest()[:8],
        16,
    )

    rng = random.Random(seed)
    rng.shuffle(videos)

    st.session_state.video_orders[page_number] = videos

    return videos


# ============================================================
# VALIDACIONES
# ============================================================

def page_is_complete(page_number: int) -> bool:
    videos = PAGES[page_number]

    return all(
        st.session_state.answers.get(video)
        in EMOTIONS
        for video in videos
    )


def page_uses_all_emotions_once(page_number: int) -> bool:
    videos = PAGES[page_number]

    answers = [
        st.session_state.answers.get(video)
        for video in videos
    ]

    if any(answer not in EMOTIONS for answer in answers):
        return False

    return sorted(answers) == sorted(EMOTIONS)


# ============================================================
# GUARDADO
# ============================================================

def save_results():
    now = datetime.now(timezone.utc)

    session_id = st.session_state.session_id

    if not session_id:
        session_id = hashlib.sha256(
            (
                st.session_state.full_name
                + "|"
                + now.isoformat()
            ).encode("utf-8")
        ).hexdigest()[:16]

        st.session_state.session_id = session_id

    rows = []

    global_position = 1

    for page_number in range(1, TOTAL_PAGES + 1):

        page_order = get_page_order(page_number)

        for page_position, video_name in enumerate(
            page_order,
            start=1,
        ):
            rows.append({
                "session_id": session_id,
                "full_name": st.session_state.full_name,
                "page_number": page_number,
                "page_position": page_position,
                "video_position": global_position,
                "video_file": video_name,
                "selected_emotion":
                    st.session_state.answers[video_name],
                "submitted_at": now.isoformat(),
            })

            global_position += 1

    supabase = get_supabase()

    supabase.table(
        "face_validation_responses"
    ).insert(
        rows,
        returning="minimal",
    ).execute()


# ============================================================
# PANTALLA INICIAL
# ============================================================

def render_start():
    st.title("Validación de expresiones faciales")

    st.write(
        "A continuación observará 12 videos de "
        "representaciones faciales sintéticas."
    )

    st.write(
        "La actividad está dividida en tres etapas. "
        "En cada una deberá observar cuatro videos y "
        "clasificar cada expresión como asco, felicidad, "
        "miedo o neutro."
    )

    st.info(
        "En cada grupo de cuatro videos debe utilizar "
        "cada categoría exactamente una vez."
    )

    full_name = st.text_input(
        "Nombre completo",
        placeholder="Escriba su nombre completo",
    )

    if st.button(
        "Comenzar validación",
        type="primary",
        use_container_width=True,
    ):
        clean_name = full_name.strip()

        if len(clean_name) < 3:
            st.error(
                "Por favor ingrese su nombre completo."
            )
            return

        st.session_state.full_name = clean_name
        st.session_state.started = True
        st.session_state.current_page = 1
        st.session_state.answers = {}
        st.session_state.video_orders = {}

        st.rerun()


# ============================================================
# PÁGINAS DE VALIDACIÓN
# ============================================================

def render_validation_page():
    page_number = st.session_state.current_page

    st.title("Validación de expresiones faciales")

    st.caption(
        f"Etapa {page_number} de {TOTAL_PAGES}"
    )

    st.progress(
        page_number / TOTAL_PAGES
    )

    st.write(
        "Observe cada video y seleccione la emoción "
        "que considere que representa."
    )

    st.info(
        "En esta etapa debe utilizar una sola vez cada "
        "categoría: asco, felicidad, miedo y neutro."
    )

    videos = get_page_order(page_number)

    for display_position, video_name in enumerate(
        videos,
        start=1,
    ):

        st.divider()

        st.subheader(
            f"Video {display_position}"
        )

        video_path = VIDEO_DIR / video_name

        if video_path.exists():
            st.video(str(video_path))
        else:
            st.error(
                f"No se encontró el archivo {video_name}."
            )

        current_answer = (
            st.session_state.answers
            .get(video_name)
        )

        options = [
            "Seleccionar...",
            *EMOTIONS,
        ]

        if current_answer in EMOTIONS:
            selected_index = options.index(
                current_answer
            )
        else:
            selected_index = 0

        answer = st.selectbox(
            f"¿Qué emoción representa el Video "
            f"{display_position}?",
            options,
            index=selected_index,
            key=(
                f"select_"
                f"{page_number}_"
                f"{video_name}"
            ),
        )

        if answer == "Seleccionar...":
            st.session_state.answers.pop(
                video_name,
                None,
            )
        else:
            st.session_state.answers[
                video_name
            ] = answer

    st.divider()

    left, right = st.columns(2)

    with left:

        if page_number > 1:

            if st.button(
                "← Anterior",
                use_container_width=True,
            ):
                st.session_state.current_page -= 1
                st.rerun()

    with right:

        if page_number < TOTAL_PAGES:

            if st.button(
                "Siguiente →",
                type="primary",
                use_container_width=True,
            ):

                if not page_is_complete(
                    page_number
                ):
                    st.error(
                        "Debe clasificar los cuatro videos "
                        "antes de continuar."
                    )

                elif not page_uses_all_emotions_once(
                    page_number
                ):
                    st.error(
                        "Debe utilizar cada emoción "
                        "exactamente una vez en esta etapa."
                    )

                else:
                    st.session_state.current_page += 1
                    st.rerun()

        else:

            if st.button(
                "Enviar respuestas",
                type="primary",
                use_container_width=True,
            ):

                if not page_is_complete(
                    page_number
                ):
                    st.error(
                        "Debe clasificar los cuatro videos."
                    )
                    return

                if not page_uses_all_emotions_once(
                    page_number
                ):
                    st.error(
                        "Debe utilizar cada emoción "
                        "exactamente una vez en esta etapa."
                    )
                    return

                # Verificación final de las tres páginas
                for page in range(
                    1,
                    TOTAL_PAGES + 1,
                ):
                    if not page_is_complete(page):
                        st.error(
                            f"La etapa {page} tiene "
                            "respuestas incompletas."
                        )
                        return

                    if not page_uses_all_emotions_once(
                        page
                    ):
                        st.error(
                            f"La etapa {page} no utiliza "
                            "las cuatro emociones una vez."
                        )
                        return

                try:
                    with st.spinner(
                        "Guardando respuestas..."
                    ):
                        save_results()

                    st.session_state.completed = True
                    st.rerun()

                except Exception as exc:
                    st.error(
                        "No se pudieron guardar "
                        "las respuestas."
                    )
                    st.code(str(exc))


# ============================================================
# FINAL
# ============================================================

def render_completed():
    st.title("Validación completada")

    st.success(
        "Sus respuestas fueron guardadas correctamente."
    )

    st.write(
        "Muchas gracias por participar en esta "
        "validación."
    )

    st.write(
        "Ya puede cerrar esta página."
    )


# ============================================================
# MAIN
# ============================================================

def main():
    st.set_page_config(
        page_title="Validación de expresiones faciales",
        page_icon="🙂",
        layout="centered",
    )

    initialize_state()

    if st.session_state.completed:
        render_completed()
        return

    if not st.session_state.started:
        render_start()
        return

    render_validation_page()


if __name__ == "__main__":
    main()
