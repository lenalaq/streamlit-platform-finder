import streamlit as st
import pandas as pd
from itertools import combinations
from datetime import datetime
import os
import uuid

# --- Création d'un ID unique par utilisateur (session) ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())  # ex: 'c4e9...'

# --- Fonction pour logger les actions ---
def log_action(action, value):
    """
    Enregistre une action utilisateur avec un identifiant unique dans un fichier local.
    """
    with open("user_logs.csv", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()},{st.session_state.session_id},{action},{value}\n")

@st.cache_data
def load_data(path):
    df = pd.read_csv(path, sep=',', encoding='latin1', on_bad_lines='skip')
    df = df.dropna(subset=['year', 'plateforme', 'genre_hierarchie', 'main_country', 'title'])
    
    df = df[df['main_country'] != '0']
    df = df[df['genre_hierarchie'] != 'short']
    df = df[~df['plateforme'].str.lower().isin(['canal+', 'm6'])]
    
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df = df.dropna(subset=['year'])
    df['year'] = df['year'].astype(int)
    df.loc[df['year'] > 3000, 'year'] = (df.loc[df['year'] > 3000, 'year'] // 10).astype(int)
    df['decade'] = (df['year'] // 10) * 10
    df['main_country'] = df['main_country'].str.lower().str.strip()
    df['genre_hierarchie'] = df['genre_hierarchie'].str.lower().str.strip()
    df['plateforme'] = df['plateforme'].str.strip()
    df['title'] = df['title'].str.strip()
    return df

def button_grid(options, key_prefix, selected_value):
    selected = selected_value
    n_cols = 5
    rows = (len(options) + n_cols - 1) // n_cols
    for i in range(rows):
        cols = st.columns(n_cols)
        for j, option in enumerate(options[i*n_cols:(i+1)*n_cols]):
            btn_key = f"{key_prefix}_{i}_{j}"
            if option == selected_value:
                style = 'background-color: #4CAF50; color: white; font-weight: bold;'
            else:
                style = ''
            if cols[j].button(str(option), key=btn_key):
                selected = option if option != selected_value else None
                log_action(f"select_{key_prefix}", option)
    return selected

def filter_data(df, decade=None, country=None, genre=None):
    df_filtered = df.copy()
    if decade is not None:
        df_filtered = df_filtered[df_filtered['decade'] == decade]
    if country is not None:
        df_filtered = df_filtered[df_filtered['main_country'] == country.lower().strip()]
    if genre is not None:
        df_filtered = df_filtered[df_filtered['genre_hierarchie'] == genre.lower().strip()]
    return df_filtered

def get_top_platform_and_titles(df, n_titles=5):
    """
    Renvoie la plateforme la plus fréquente et jusqu'à n_titles films exemples.
    Les films exemples ne contiennent pas de caractères spéciaux.
    """
    if df.empty:
        return None, []

    top_platform = df['plateforme'].value_counts().idxmax()

    example_titles = (
        df[df['plateforme'] == top_platform]['title']
        .dropna()
        .drop_duplicates()
        .loc[lambda x: x.str.match(r'^[A-Za-z0-9 ]+$', na=False)]
        .head(n_titles)
        .tolist()
    )

    return top_platform, example_titles

def get_selected_pairs(selected_dict):
    keys = [k for k, v in selected_dict.items() if v is not None]
    return list(combinations(keys, 2))

# --- MAIN ---
csv_url = "https://raw.githubusercontent.com/lenalaq/platform/main/dataset_pour_analyse_clean.csv"
df = load_data(csv_url)

st.title("Trouvez la plateforme qui correspond le plus à vos critères")

if "decade" not in st.session_state:
    st.session_state.decade = None
if "country" not in st.session_state:
    st.session_state.country = None
if "genre" not in st.session_state:
    st.session_state.genre = None

# --- Sélection Décennie ---
st.subheader("Décennie")
decade_selected = button_grid(sorted(df['decade'].unique()), "decade", st.session_state.decade)
st.session_state.decade = decade_selected
if decade_selected:
    st.write(f"Décennie sélectionnée : **{decade_selected}**")

# --- Sélection Pays ---
st.subheader("Pays")
country_selected = button_grid(sorted(df['main_country'].unique()), "country", st.session_state.country)
st.session_state.country = country_selected
if country_selected:
    st.write(f"Pays sélectionné : **{country_selected}**")

# --- Sélection Genre ---
st.subheader("Genre")
genre_selected = button_grid(sorted(df['genre_hierarchie'].unique()), "genre", st.session_state.genre)
st.session_state.genre = genre_selected
if genre_selected:
    st.write(f"Genre sélectionné : **{genre_selected}**")

# --- Bouton reset ---
if st.button("Réinitialiser la sélection"):
    log_action("button_click", "Réinitialiser la sélection")
    st.session_state.decade = None
    st.session_state.country = None
    st.session_state.genre = None
    st.experimental_rerun()

# --- Affichage des critères ---
st.markdown("---")
st.subheader("Critères sélectionnés")
st.write(f"- Décennie : **{st.session_state.decade if st.session_state.decade else 'Aucun'}**")
st.write(f"- Pays : **{st.session_state.country if st.session_state.country else 'Aucun'}**")
st.write(f"- Genre : **{st.session_state.genre if st.session_state.genre else 'Aucun'}**")

# --- Filtrage principal ---
df_filtered = filter_data(df, st.session_state.decade, st.session_state.country, st.session_state.genre)
top_platform, example_titles = get_top_platform_and_titles(df_filtered)

if top_platform is not None:
    nb_films = len(df_filtered)
    st.success(f"Plateforme la plus fréquente : **{top_platform}**")
    st.write("Exemples de films :")
    for t in example_titles:
        st.write(f"- {t}")
    st.write(f"Sur l'ensemble des catalogues, cela représente {nb_films} films.")
    
else:
    st.warning("Aucun film ne correspond aux 3 critères sélectionnés.")
    st.info("Recherche de la meilleure plateforme avec critères combinés 2 à 2...")

    selected_criteria = {
        'decade': st.session_state.decade,
        'country': st.session_state.country,
        'genre': st.session_state.genre
    }
    pairs = get_selected_pairs(selected_criteria)
    fallback_results = []

    for pair in pairs:
        filter_args = {k: selected_criteria[k] for k in pair}
        df_2 = filter_data(df, **filter_args)
        p, t_list = get_top_platform_and_titles(df_2)
        if p:
            nb_films_2 = len(df_2)
            combi_name = " + ".join(pair)
            combi_vals = ", ".join(str(selected_criteria[k]) for k in pair)
            fallback_results.append((f"{combi_name} ({combi_vals})", p, t_list, nb_films_2))

    if fallback_results:
        for combi, plat, titles, nb in fallback_results:
            st.success(f"Pour {combi} → Plateforme : **{plat}** ({nb} films), Films exemples :")
            for t in titles:
                st.write(f"- {t}")
    else:
        st.error("Aucun résultat même avec les combinaisons 2 à 2.")
