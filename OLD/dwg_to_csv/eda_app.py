"""
╔══════════════════════════════════════════════════════════╗
║          EDA Dashboard — DWG/DXF Survey Data            ║
║          ניתוח נתוני מדידות                              ║
╚══════════════════════════════════════════════════════════╝
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# ═══════════════════════════════════════════════════════════
# Page Configuration
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="EDA Dashboard — Survey Data",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════
# Custom CSS — Premium Dark Theme
# ═══════════════════════════════════════════════════════════

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 40%, #24243e 100%);
        font-family: 'Inter', sans-serif;
    }

    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15));
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        backdrop-filter: blur(10px);
        text-align: center;
    }

    .main-header h1 {
        background: linear-gradient(135deg, #818cf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }

    .main-header p {
        color: #a5b4fc;
        font-size: 1rem;
        margin: 8px 0 0 0;
        font-weight: 300;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.8), rgba(30, 27, 75, 0.4));
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        border-color: rgba(139, 92, 246, 0.6);
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(99, 102, 241, 0.15);
    }

    .metric-icon {
        font-size: 2rem;
        margin-bottom: 8px;
    }

    .metric-value {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 4px 0;
    }

    .metric-label {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }

    /* Section headers */
    .section-header {
        color: #e2e8f0;
        font-size: 1.3rem;
        font-weight: 600;
        padding: 12px 0;
        margin: 20px 0 12px 0;
        border-bottom: 2px solid rgba(99, 102, 241, 0.3);
    }

    /* Chart containers */
    .chart-container {
        background: rgba(30, 27, 75, 0.4);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 16px;
        padding: 20px;
        backdrop-filter: blur(10px);
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1b4b 0%, #312e81 100%);
    }

    /* Sidebar Titles (App Name) */
    [data-testid="stSidebar"] h2 {
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 1.8rem !important;
        text-shadow: 0 2px 15px rgba(139, 92, 246, 0.6);
        letter-spacing: 0.5px;
    }

    /* Navigation / Radio labels (Pages) */
    [data-testid="stSidebar"] .stRadio > label {
        color: #ffffff !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
    }
    
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label p {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
    }

    [data-testid="stSidebar"] .stMarkdown p {
        color: #c7d2fe;
    }

    /* Selectbox styling */
    .stSelectbox > label {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* Data table */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #64748b;
        font-size: 0.75rem;
        padding: 20px;
        margin-top: 40px;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# Plotly Theme
# ═══════════════════════════════════════════════════════════

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15, 12, 41, 0.6)",
    font=dict(family="Inter, sans-serif", color="#c7d2fe"),
    title_font=dict(size=18, color="#e2e8f0"),
    margin=dict(l=40, r=40, t=60, b=40),
    xaxis=dict(
        gridcolor="rgba(99, 102, 241, 0.1)",
        zerolinecolor="rgba(99, 102, 241, 0.2)",
    ),
    yaxis=dict(
        gridcolor="rgba(99, 102, 241, 0.1)",
        zerolinecolor="rgba(99, 102, 241, 0.2)",
    ),
    hoverlabel=dict(
        bgcolor="#1e1b4b",
        font_size=13,
        font_family="Inter",
        bordercolor="#6366f1",
    ),
)

COLORS = px.colors.sequential.Purp
SCATTER_COLORS = px.colors.qualitative.Pastel


# ═══════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════

@st.cache_data
def load_data(uploaded_file):
    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
    return df


# ═══════════════════════════════════════════════════════════
# Sidebar & Navigation
# ═══════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🗺️ SurveyGIS")
    st.markdown("---")
    
    app_page = st.radio("📌 ניווט", ["📊 EDA Dashboard", "🧩 Clustering", "ℹ️ אודות המערכת"])
    st.markdown("---")

if app_page == "ℹ️ אודות המערכת":
    st.markdown("""
    <div class="main-header">
        <h1>ℹ️ אודות SurveyGIS</h1>
        <p>מערכת מידע גאוגרפי לניהול משרדי</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="chart-container" style="font-size: 1.1rem; line-height: 1.8; color: #e2e8f0;">
        <h3 style="color: #c084fc;">שם הפרויקט: SurveyGIS</h3>
        <p>
        <strong>מערכת מידע גאוגרפי</strong> לניהול, שליפה והצגת מדידות שנעשו בעבר, המיועדת למשרדי מדידות.
        </p>
        <h3 style="color: #c084fc; margin-top: 24px;">מטרת המערכת</h3>
        <p>
        ארגון פנים-משרדי של החומר הקיים בצורה גאוגרפית הנוחה לחיפוש ומעקב אחר מדידות. 
        המערכת מאפשרת התמצאות מהירה במרחב ושליפה של פרויקטים רלוונטיים באזור המבוקש.
        </p>
        <h3 style="color: #c084fc; margin-top: 24px;">מקור הנתונים</h3>
        <p>
        מפות מדידה שנעשו במשרד (שחולצו מתוך קבצי <strong>DWG / DXF</strong>).
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

with st.sidebar:
    # File Upload (Cloud Compatible)
    selected_file = st.file_uploader("📁 העלה קובץ CSV", type=["csv"])
    
    if not selected_file:
        st.info("👆 אנא העלה קובץ CSV כדי להמשיך.")
        st.stop()

    st.markdown("---")
    st.markdown("""
    <div style='color: #818cf8; font-size: 0.85rem;'>
        <strong>כלי EDA</strong> לניתוח נתוני מדידות<br>
        שחולצו מקבצי DWG/DXF<br><br>
        📊 היסטוגרמות<br>
        🔬 Scatter Plot<br>
        📋 סטטיסטיקות
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# Load Data & Sidebar Filters
# ═══════════════════════════════════════════════════════════

df = load_data(selected_file)

with st.sidebar:
    st.markdown("---")
    st.markdown("<h3 style='color: #f472b6; text-shadow: 0 0 5px rgba(244,114,182,0.4); margin-bottom: 10px;'>🎛️ סינון נתונים</h3>", unsafe_allow_html=True)
    if 'Layer' in df.columns:
        all_layers = df['Layer'].unique().tolist()
        # By default, select all layers or a subset if too many
        selected_layers = st.multiselect(
            "🏷️ סינון לפי Layer",
            options=all_layers,
            default=all_layers
        )
        if selected_layers:
            df = df[df['Layer'].isin(selected_layers)]
        else:
            st.warning("⚠️ לא נבחרו שכבות. מציג נתונים ריקים.")
            df = df.iloc[0:0]

numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
categorical_cols = df.select_dtypes(exclude=["number"]).columns.tolist()
all_cols = df.columns.tolist()

total_cells = df.shape[0] * df.shape[1]
missing_cells = df.isnull().sum().sum()
missing_pct = (missing_cells / total_cells * 100) if total_cells > 0 else 0

# ═══════════════════════════════════════════════════════════
# Clustering Page Logic
# ═══════════════════════════════════════════════════════════

if app_page == "🧩 Clustering":
    st.markdown(f'''
    <div class="main-header">
        <h1>🧩 Clustering (K-Means)</h1>
        <p>ניתוח אשכולות — {selected_file.name}</p>
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">🎛️ הגדרות מודל</div>', unsafe_allow_html=True)
    
    if len(numeric_cols) < 2:
        st.warning("⚠️ נדרשות לפחות 2 עמודות מספריות לביצוע Clustering.")
    else:
        col_sel1, col_sel2, col_sel3 = st.columns([2, 1, 1])
        with col_sel1:
            selected_features = st.multiselect(
                "בחר עמודות מספריות (לפחות 2):",
                options=numeric_cols,
                default=numeric_cols[:2] if len(numeric_cols) >= 2 else []
            )
        with col_sel2:
            k_clusters = st.slider("בחר מספר אשכולות (K):", min_value=2, max_value=8, value=3)
        with col_sel3:
            st.markdown("<br>", unsafe_allow_html=True)
            use_scaler = st.checkbox("הפעל נרמול (StandardScaler)", value=True)
        
        if len(selected_features) >= 2:
            # Run KMeans
            X = df[selected_features].dropna()
            if X.empty:
                st.error("❌ הנתונים שנבחרו ריקים לאחר הסרת ערכים חסרים.")
            else:
                st.markdown('<div class="section-header">📉 גרף Elbow (מציאת K אופטימלי)</div>', unsafe_allow_html=True)
                
                st.info("""
                **מה זה גרף Elbow (מרפק)?**  
                גרף זה עוזר לנו למצוא את מספר האשכולות (K) האופטימלי. הוא מציג את מדד ה-Inertia (סכום ריבועי המרחקים של הנקודות ממרכזי האשכולות שלהן) עבור ערכים שונים של K. ככל שה-Inertia נמוך יותר, האשכולות צפופים יותר.

                **איך בוחרים K?**  
                מחפשים את נקודת ה"מרפק" בגרף — הנקודה שבה הירידה התלולה ב-Inertia מתחילה להתמתן משמעותית (כמו צורה של זרוע כפופה). נקודה זו מייצגת לרוב את האיזון הטוב ביותר: הוספת אשכולות נוספים מעבר לנקודה זו כבר לא תורמת משמעותית לדחיסות.
                """)
                
                # Scaler logic for elbow
                X_elbow = StandardScaler().fit_transform(X) if use_scaler else X.values
                
                inertias = []
                K_range = range(1, 11)
                for k in K_range:
                    km = KMeans(n_clusters=k, random_state=42, n_init='auto')
                    km.fit(X_elbow)
                    inertias.append(km.inertia_)
                
                fig_elbow = px.line(
                    x=list(K_range), y=inertias, markers=True,
                    title="Elbow Method For Optimal K" + (" (עם StandardScaler)" if use_scaler else " (ללא נרמול)"),
                    labels={"x": "מספר אשכולות (K)", "y": "Inertia (SSW)"}
                )
                fig_elbow.update_traces(line_color="#c084fc", marker=dict(size=8, color="#818cf8"))
                fig_elbow.update_layout(**PLOTLY_LAYOUT)
                st.plotly_chart(fig_elbow, use_container_width=True)
                
                st.markdown('<div class="section-header">🔬 תוצאות אשכול (Scatter Plot)</div>', unsafe_allow_html=True)
                
                def create_cluster_plot(X_raw, clusters_labels, title, apply_scaling=False):
                    if apply_scaling:
                        X_val = StandardScaler().fit_transform(X_raw)
                    else:
                        X_val = X_raw.values
                        
                    if X_raw.shape[1] > 2:
                        pca = PCA(n_components=2)
                        X_pca = pca.fit_transform(X_val)
                        plot_df = pd.DataFrame(X_pca, columns=['PC1', 'PC2'])
                        plot_df['Cluster'] = clusters_labels.astype(str)
                        
                        fig = px.scatter(plot_df, x='PC1', y='PC2', color='Cluster',
                                         color_discrete_sequence=SCATTER_COLORS, title=title + " (PCA 2D)")
                    else:
                        plot_df = X_raw.copy()
                        plot_df['Cluster'] = clusters_labels.astype(str)
                        feat_x = X_raw.columns[0]
                        feat_y = X_raw.columns[1]
                        
                        fig = px.scatter(plot_df, x=feat_x, y=feat_y, color='Cluster',
                                         color_discrete_sequence=SCATTER_COLORS, title=title)
                    
                    fig.update_traces(marker=dict(size=8, line=dict(width=1, color='rgba(255,255,255,0.2)')))
                    fig.update_layout(**PLOTLY_LAYOUT)
                    return fig

                km_unscaled = KMeans(n_clusters=k_clusters, random_state=42, n_init='auto')
                clusters_unscaled = km_unscaled.fit_predict(X)

                if use_scaler:
                    km_scaled = KMeans(n_clusters=k_clusters, random_state=42, n_init='auto')
                    clusters_scaled = km_scaled.fit_predict(StandardScaler().fit_transform(X))
                    
                    col_plot1, col_plot2 = st.columns(2)
                    with col_plot1:
                        st.plotly_chart(create_cluster_plot(X, clusters_unscaled, f"ללא נרמול (K={k_clusters})", apply_scaling=False), use_container_width=True)
                    with col_plot2:
                        st.plotly_chart(create_cluster_plot(X, clusters_scaled, f"עם נרמול (K={k_clusters})", apply_scaling=True), use_container_width=True)
                else:
                    st.plotly_chart(create_cluster_plot(X, clusters_unscaled, f"K-Means (K={k_clusters}) - ללא נרמול", apply_scaling=False), use_container_width=True)
        else:
            st.warning("⚠️ יש לבחור לפחות 2 עמודות להצגת הגרפים.")
            
    st.markdown('''
    <div class="footer">
        🗺️ Clustering Dashboard — Built with Streamlit, Plotly & Scikit-Learn
    </div>
    ''', unsafe_allow_html=True)
    st.stop()


# ═══════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════

st.markdown(f"""
<div class="main-header">
    <h1>📊 EDA Dashboard</h1>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# KPI Metrics — Top Row
# ═══════════════════════════════════════════════════════════

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-icon">📋</div>
        <div class="metric-value">{df.shape[0]:,}</div>
        <div class="metric-label">סה"כ שורות</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    num_layers = df['Layer'].nunique() if 'Layer' in df.columns else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-icon">🏷️</div>
        <div class="metric-value">{num_layers:,}</div>
        <div class="metric-label">שכבות (Layers) פעילות</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    avg_vertices = df['VertexCount'].mean() if 'VertexCount' in df.columns and not df.empty else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-icon">🔺</div>
        <div class="metric-value">{avg_vertices:.1f}</div>
        <div class="metric-label">ממוצע VertexCount</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# Histogram - VertexCount
# ═══════════════════════════════════════════════════════════

st.markdown('<div class="section-header">📈 התפלגות VertexCount</div>', unsafe_allow_html=True)

if 'VertexCount' in df.columns and not df.empty:
    fig_hist = px.histogram(
        df, x="VertexCount",
        nbins=40,
        title="היסטוגרמה - מספרי VertexCount",
        color_discrete_sequence=["#818cf8"],
    )
    fig_hist.update_traces(
        marker_line_color="#4f46e5",
        marker_line_width=1,
        opacity=0.85,
    )
    fig_hist.update_layout(**PLOTLY_LAYOUT)
    fig_hist.update_layout(height=420)
    st.plotly_chart(fig_hist, width="stretch")
else:
    st.info("ℹ️ אין נתונים זמינים עבור VertexCount להצגה.")


# ═══════════════════════════════════════════════════════════
# Bar Chart - Average Geometry by Layer
# ═══════════════════════════════════════════════════════════

st.markdown('<div class="section-header">📊 ממוצע Geometry לפי Layer</div>', unsafe_allow_html=True)

if 'Layer' in df.columns and 'VertexCount' in df.columns and not df.empty:
    # Calculating the average VertexCount (Geometry complexity) per layer
    geom_avg = df.groupby('Layer')['VertexCount'].mean().reset_index()
    geom_avg.columns = ['Layer', 'AverageGeometry']
    
    # Sort by Average Geometry to show the highest ones
    geom_avg = geom_avg.sort_values('AverageGeometry', ascending=False)
    
    fig_bar = px.bar(
        geom_avg, x='Layer', y='AverageGeometry',
        title="ממוצע Geometry (VertexCount) לפי Layer",
        color='AverageGeometry',
        color_continuous_scale=["#312e81", "#6366f1", "#a78bfa", "#c084fc"],
        text_auto='.1f'
    )
    fig_bar.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
    fig_bar.update_layout(**PLOTLY_LAYOUT)
    fig_bar.update_layout(coloraxis_showscale=False, height=520)
    
    st.plotly_chart(fig_bar, width="stretch")
else:
    st.info("ℹ️ אין מספיק נתונים להצגת ממוצע Geometry לפי Layer.")


# ═══════════════════════════════════════════════════════════
# Data Preview
# ═══════════════════════════════════════════════════════════

st.markdown('<div class="section-header">📋 תצוגה מקדימה של הנתונים</div>', unsafe_allow_html=True)

preview_col1, preview_col2 = st.columns([3, 1])

with preview_col1:
    st.dataframe(
        df.head(50),
        width="stretch",
        height=350,
    )

with preview_col2:
    # Column types summary
    type_counts = {
        "📏 רציף (Numeric)": len(numeric_cols),
        "🏷️ קטגורי (Categorical)": len(categorical_cols),
    }

    fig_types = go.Figure(data=[go.Pie(
        labels=list(type_counts.keys()),
        values=list(type_counts.values()),
        hole=0.65,
        marker=dict(colors=["#818cf8", "#f472b6"]),
        textinfo="value",
        textfont=dict(size=16, color="#e2e8f0"),
        hoverinfo="label+value",
    )])

    fig_types.update_layout(
        title="סוגי עמודות",
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k != "xaxis" and k != "yaxis"},
        height=300,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color="#a5b4fc"),
        ),
    )

    st.plotly_chart(fig_types, width="stretch")


# ═══════════════════════════════════════════════════════════
# Footer
# ═══════════════════════════════════════════════════════════

st.markdown("""
<div class="footer">
    🗺️ EDA Dashboard — Survey Data Analysis | Built with Streamlit & Plotly
</div>
""", unsafe_allow_html=True)
