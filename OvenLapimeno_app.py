import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, time, timedelta

# --- Sovelluksen otsikko ---
st.set_page_config(page_title="Oven läpimenoanalyysi", page_icon="🏭")
st.title("Oven läpimenoanalyysi")

# --- Vuorot ---
vuorot = [(time(6,0), time(14,30)), (time(14,30), time(23,0))]

def rajaa_vuoroon(t):
    if pd.isna(t): return pd.NaT
    return t if any(start <= t <= end for start,end in vuorot) else pd.NaT

def ota_aika(x):
    try: return pd.to_datetime(x).time()
    except: return pd.NaT

def laske_kesto(t1, t2):
    if pd.isna(t1) or pd.isna(t2): return pd.NA
    dt1, dt2 = datetime.combine(datetime.today(), t1), datetime.combine(datetime.today(), t2)
    if dt2 < dt1: dt2 += timedelta(days=1)
    return (dt2 - dt1).total_seconds()/3600

# --- Excelin lataus ---
tiedosto = st.file_uploader("Valitse Excel-tiedosto (.xlsx)", type=["xlsx"])
if tiedosto:
    df = pd.read_excel(tiedosto)
    st.subheader("Kuittaukset")
    st.dataframe(df.head())

    # --- Työpisteet ---
    tyopisteet = st.multiselect(
        "Valitse työpisteet:",
        options=[col for col in df.columns if col != "model"],
        default=[col for col in df.columns if col != "model"]
    )

    # --- Ovimalleja ---
    valitut_mallit = None
    if "model" in df.columns:
        valitut_mallit = st.multiselect(
            "Valitse ovimallit:",
            options=df["model"].unique(),
            default=list(df["model"].unique())
        )

    # --- Laske-painike ---
    if st.button("Laske"):
        df_valittu = df.copy()
        if valitut_mallit:
            df_valittu = df_valittu[df_valittu["model"].isin(valitut_mallit)]

        # Muunna kellonaikaan ja rajaa vuoroon
        for tp in tyopisteet:
            df_valittu[tp+"_time"] = df_valittu[tp].apply(ota_aika).apply(rajaa_vuoroon)

        # Laske työvaiheiden kestot
        for i in range(len(tyopisteet)-1):
            tp1, tp2 = tyopisteet[i], tyopisteet[i+1]
            df_valittu[tp1+"_h"] = [laske_kesto(t1,t2) for t1,t2 in zip(df_valittu[tp1+"_time"], df_valittu[tp2+"_time"])]

        # Kokonaisläpimeno
        def laske_kokonais(row):
            ajat = [row[tp+"_time"] for tp in tyopisteet if pd.notna(row[tp+"_time"])]
            if len(ajat)<2: return 0
            dt = [datetime.combine(datetime.today(), t) for t in ajat]
            if dt[-1] < dt[0]: dt[-1] += timedelta(days=1)
            return (max(dt)-min(dt)).total_seconds()/3600
        df_valittu["kokonaisläpimeno_h"] = df_valittu.apply(laske_kokonais, axis=1)

        # --- Näytä tulokset ---
        cols = (["model"] if "model" in df_valittu.columns else []) + [tp+"_h" for tp in tyopisteet[:-1]] + ["kokonaisläpimeno_h"]
        st.dataframe(df_valittu[cols])

        # --- Graafi yksittäisestä rivistä ---
        st.subheader("Graafi yksittäisestä rivistä")
        rivi_idx = st.selectbox("Valitse rivi graafiin:", df_valittu.index)
        rivi = df_valittu.loc[rivi_idx]
        kestot = [rivi[tp+"_h"] for tp in tyopisteet[:-1] if pd.notna(rivi[tp+"_h"])]
        vaiheet = [tp for tp in tyopisteet[:-1] if pd.notna(rivi[tp+"_h"])]
        fig, ax = plt.subplots(figsize=(10,5))
        ax.bar(vaiheet, kestot, color='skyblue')
        ax.set_ylabel("Kesto (tunteina)")
        ax.set_xlabel("Työvaihe")
        ax.set_title(f"Ovi: {rivi.get('model','rivi')}")
        ax.tick_params(axis='x', rotation=45)
        st.pyplot(fig)

        # --- Graafi keskiarvoista ---
        st.subheader("Keskimääräiset kestot valituille riveille")
        keskiarvot = df_valittu[[tp+"_h" for tp in tyopisteet[:-1]]].mean(skipna=True)
        fig2, ax2 = plt.subplots(figsize=(10,5))
        ax2.bar(keskiarvot.index, keskiarvot.values, color='orange')
        ax2.set_ylabel("Keskimääräinen kesto (tunteina)")
        ax2.set_xlabel("Työvaihe")
        ax2.set_title("Keskimääräiset työvaiheiden kestot")
        ax2.tick_params(axis='x', rotation=45)
        st.pyplot(fig2)

        # --- Excel-tallennus ---
        tiedostonimi = st.text_input("Anna tiedostonimi:", value="Oven_lapimenot.xlsx")
        if st.button("Tallenna Exceliin"):
            df_valittu.to_excel(tiedostonimi, index=False)
            st.success(f"Tulokset tallennettu tiedostoon: {tiedostonimi}")
