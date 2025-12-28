import streamlit as st
import pandas as pd
import plotly.express as px
import json
import requests

# Page Configuration
st.set_page_config(page_title="GeneSmart Dashboard", layout="wide", page_icon="🧬")

# Custom CSS for "Premium Biotech" feel
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    :root {
        --primary: #008080;
        --secondary: #0056b3;
    }

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
        background-color: #f0f2f6;
    }
    
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Premium Card Look */
    .stPlotlyChart {
        background: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 15px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(0,0,0,0.05);
    }
    
    /* Button Styling */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        border: none;
        background: white;
        color: #4a5568;
        padding: 10px 15px;
        font-weight: 500;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 4px;
    }
    
    .stButton>button:hover {
        background: var(--primary);
        color: white !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 128, 128, 0.2);
    }
    
    .stButton>button:active {
        transform: translateY(0);
    }

    /* Selected state (simulated) */
    .selected-btn {
        background: var(--primary) !important;
        color: white !important;
    }
    
    h1, h2, h3 {
        color: #2d3748;
        font-weight: 700 !important;
    }

    .stExpander {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# Data Loading & Preprocessing
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("dataheatmap.csv", skiprows=1)
        df.columns = [c.strip() for c in df.columns]
        
        # Name Normalization for matching GeoJSON
        def normalize_name(name):
            if not isinstance(name, str): return name
            # Basic normalization: strip, title case, handle Gabès/Gabes
            n = name.strip()
            # Replace accents for matching if necessary, though gov_name_f usually has accents
            # We'll keep it simple: just strip and ensure matching titles
            return n

        df['Location'] = df['Location'].apply(normalize_name)
        
        # Group by Location and sum
        df_grouped = df.groupby('Location').sum().reset_index()
        return df_grouped
    except Exception as e:
        st.error(f"Erreur lors du chargement des données CSV: {e}")
        return None

@st.cache_data
def load_geojson():
    url = "https://raw.githubusercontent.com/mtimet/tnacmaps/master/geojson/governorates.geojson"
    try:
        response = requests.get(url)
        data = response.json()
        return data
    except Exception as e:
        st.error(f"Erreur lors du chargement du GeoJSON: {e}")
        return None

df = load_data()
geojson = load_geojson()

if df is not None and geojson is not None:
    # Sidebar Metric Selection
    with st.sidebar:
        st.markdown("<div style='text-align: center; padding: 20px;'><img src='https://img.icons8.com/isometric/100/008080/microscope.png' width='80'></div>", unsafe_allow_html=True)
        st.title("GeneSmart")
        st.markdown("<p style='color: #718096; font-size: 0.9em;'>Plateforme de Visualisation Biotech</p>", unsafe_allow_html=True)
        st.divider()
        
        categories = {
            "🧬 Pré-analytique": ["extraction adn", "cfdna", "zymo"],
            "🧪 Réactifs de base": ["amorces pcr", "réactifs pcr", "taq polymerase"],
            "🔬 PCR routinière": ["kit pcr", "qpcr", "rt-pcr"],
            "🛰️ PCR avancée": ["pcr digital"],
            "🩺 Applications cliniques": ["hla b51", "pylori"]
        }
        
        if 'selected_metric' not in st.session_state:
            st.session_state['selected_metric'] = "extraction adn"

        for cat, metrics in categories.items():
            with st.expander(cat, expanded=True):
                for m in metrics:
                    is_selected = st.session_state['selected_metric'] == m
                    if st.button(m.capitalize(), key=f"btn_{m}"):
                        st.session_state['selected_metric'] = m
                        st.rerun()

    current_metric = st.session_state['selected_metric']

    # Header section
    st.markdown(f"### {current_metric.capitalize()}")
    
    # Calculate Average for Threshold logic
    avg_val = df[current_metric].mean()
    
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        st.subheader("Distribution Géographique")
    with col2:
        st.metric("Moyenne", f"{avg_val:.3f}")
    with col3:
        # National Total
        total_val = df[current_metric].sum()
        st.metric("Total National", f"{total_val:.2f}")

    # --- Map Preparation & Color Logic ---
    # 1. Normalize values relative to the average (1.0 = Average)
    # This allows a continuous scale where Yellow is always the Average
    df['ratio_to_avg'] = df[current_metric] / avg_val
    
    # 2. Get all governorate names from GeoJSON to show the full country
    all_govs = [f['properties']['gov_name_f'] for f in geojson['features']]
    base_df = pd.DataFrame({'Location': all_govs})
    
    # 3. Merge with our data
    map_df = pd.merge(base_df, df, on='Location', how='left')
    
    # 4. Handle missing data
    map_df[current_metric] = map_df[current_metric].fillna(0)
    # For regions without data, we'll use a special value or just handle them in the scale
    # But usually, it's better to show them in a neutral gray if they are truly missing
    map_df['ratio_to_avg'] = map_df['ratio_to_avg'].fillna(-1) # Special marker for gray

    # Map Visualization
    fig = px.choropleth(
        map_df,
        geojson=geojson,
        locations="Location",
        featureidkey="properties.gov_name_f",
        color="ratio_to_avg",
        # Customizing the color scale: Red -> Yellow -> Green
        color_continuous_scale=[
            [0.0, "#E2E8F0"],    # Missing data (Gray)
            [0.0001, "#E74C3C"], # Low (Red)
            [0.5, "#F1C40F"],    # Average (Yellow)
            [1.0, "#2ECC71"]     # High (Green)
        ],
        # We'll calculate the bounds dynamically to keep the midpoint at 1.0
        # If we use ratio_to_avg, we want 1.0 to be in the middle of the non-gray scale
        range_color=[0, 2], # 0 to 2, where 1 is the middle
        hover_data={"Location": True, current_metric: ":.3f", "ratio_to_avg": False},
        labels={current_metric: "Valeur", "ratio_to_avg": "Ratio / Moyenne"}
    )
    
    # Sharp traits (borders) and high visibility
    fig.update_traces(
        marker_line_width=1.5, 
        marker_line_color="#2D3748", 
        marker_opacity=1.0 
    )
    
    fig.update_geos(
        fitbounds="geojson", 
        visible=False,
        projection_type="mercator"
    )

    fig.update_layout(
        height=650, 
        margin={"r":0,"t":30,"l":0,"b":0},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        coloraxis_colorbar=dict(
            title="Performance",
            tickvals=[0.2, 1.0, 1.8],
            ticktext=["Basse", "Moyenne", "Haute"],
            lenmode="fraction", len=0.6,
            thickness=15,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#eef2f6",
            borderwidth=1,
            yanchor="middle", y=0.5,
            xanchor="left", x=0.02
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=16,
            font_family="Outfit"
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # Insights Panel
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Classement des Régions")
        sorted_df = df.sort_values(by=current_metric, ascending=False)
        st.dataframe(
            sorted_df[['Location', current_metric]],
            use_container_width=True,
            hide_index=True
        )
    with c2:
        st.markdown("#### 💡 Insights")
        top_reg = sorted_df.iloc[0]['Location']
        low_reg = sorted_df.iloc[-1]['Location']
        st.info(f"📍 **Région Leader :** {top_reg} avec {sorted_df.iloc[0][current_metric]:.3f}")
        st.warning(f"⚠️ **Région en Retrait :** {low_reg} avec {sorted_df.iloc[-1][current_metric]:.3f}")
        
        # Legend explanation
        st.markdown(f"""
        **Interprétation de la Carte :**
        - Les couleurs **vibrantes** (Vert foncé) indiquent une performance nettement supérieure à la moyenne.
        - Le **Jaune** représente la performance moyenne nationale ({avg_val:.3f}).
        - Les tons **Rouges** indiquent les zones nécessitant une attention (sous la moyenne).
        - Le **Gris** indique un manque de données pour la région.
        """)

else:
    st.error("Impossible d'initialiser l'application. Vérifiez la connexion internet et les fichiers de données.")
