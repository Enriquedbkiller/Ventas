import os
import pandas as pd
import streamlit as st

# Aumentar el límite de celdas permitidas para Pandas Styler
pd.set_option("styler.render.max_elements", 500000)

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Ventas - City Market Santa Fe",
    page_icon="📊",
    layout="wide",
)

# Estilos CSS para el formato condicional en rojo para negativos
st.markdown(
    """
    <style>
    .negative-value {
        color: #ff4d4d !important;
        font-weight: bold;
    }
    </style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_data(file_name):
  try:
    if file_name.endswith(".xlsx"):
      df = pd.read_excel(file_name, sheet_name=0)
    else:
      try:
        df = pd.read_csv(file_name, encoding="utf-16", sep="\t")
      except Exception:
        try:
          df = pd.read_csv(file_name, encoding="utf-8", sep="\t")
        except Exception:
          df = pd.read_csv(file_name, encoding="latin1")
  except Exception as e:
    st.error(f"Error al cargar el archivo {file_name}: {e}")
    return pd.DataFrame()

  # Normalizar nombres de columnas clave por si tienen variaciones de acentos o mayúsculas
  rename_map = {}
  for col in df.columns:
    col_clean = col.strip()
    col_lower = col_clean.lower()
    if "divis" in col_lower:
      rename_map[col] = "División"
    elif "secc" in col_lower:
      rename_map[col] = "Sección"
    elif "prod" in col_lower:
      rename_map[col] = "Producto"
  df = df.rename(columns=rename_map)

  if "División" in df.columns:
    df = df[df["División"].astype(str).str.contains("Total general", case=False, na=False) == False]

  for col in df.columns:
    if any(
        kw in col.lower()
        for kw in [
            "importe",
            "venta",
            "unidades",
            "precio",
            "clientes",
            "ticket",
        ]
    ):
      df[col] = (
          df[col]
          .astype(str)
          .str.replace("$", "", regex=False)
          .str.replace(",", "", regex=False)
          .str.strip()
      )
      df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
  return df


# Cargar bases de datos principales
df_acumulada = load_data("venta_acumulada.csv")

if os.path.exists("venta_diaria.xlsx"):
  df_diaria = load_data("venta_diaria.xlsx")
else:
  df_diaria = df_acumulada.copy()

if os.path.exists("Ventas Clientes y Ticket.csv"):
  df_clientes_ticket = load_data("Ventas Clientes y Ticket.csv")
else:
  df_clientes_ticket = pd.DataFrame()

st.title("📊 Tablero Gerencial - City Market Santa Fe")

# --- MÓDULO PRINCIPAL: SELECCIÓN DE VISTA GENERAL ---
st.markdown("### 🗂️ Módulo de Consulta")
modulo_principal = st.radio(
    "Selecciona Módulo",
    [
        "Ventas (División / Sección / Producto)",
        "Clientes y Ticket Promedio",
        "Temporalidades",
    ],
    horizontal=True,
)

st.markdown("---")

if modulo_principal == "Temporalidades":
  st.subheader("🎃 Módulo de Temporalidades y Campañas Especiales")

  archivos_temporada = [
      f
      for f in os.listdir(".")
      if f.endswith(".csv")
      and f not in ["venta_acumulada.csv", "Ventas Clientes y Ticket.csv"]
  ]

  if not archivos_temporada:
    st.warning(
        "No se encontraron archivos de temporalidad en la carpeta. (Asegúrate"
        " de guardar tu archivo de temporada, ej. 'Pan de muerto.csv')."
    )
  else:
    campana_seleccionada = st.selectbox(
        "Selecciona la Campaña / Temporalidad:", archivos_temporada
    )

    try:
      df_raw = pd.read_csv(
          campana_seleccionada, encoding="utf-16", sep="\t", header=None
      )
    except Exception:
      try:
        df_raw = pd.read_csv(
            campana_seleccionada, encoding="utf-8", sep="\t", header=None
        )
      except Exception:
        df_raw = pd.read_csv(
            campana_seleccionada, encoding="latin1", header=None
        )

    if len(df_raw) > 2:
      row_prod = df_raw.iloc[1].values
      row_metric = df_raw.iloc[2].values

      cols = []
      current_prod = "Total Tienda"
      for i, (p, m) in enumerate(zip(row_prod, row_metric)):
        if i == 0:
          cols.append("Tienda")
          continue
        if pd.notna(p) and "Total general" not in str(p) and str(p).strip():
          current_prod = str(p).strip()
        metric_name = str(m).strip() if pd.notna(m) else "Valor"
        cols.append(f"{current_prod} | {metric_name}")

      df_temp = df_raw.iloc[3:].copy()
      df_temp.columns = cols
      df_temp = df_temp.dropna(subset=["Tienda"])


      def clean_val(v):
        if pd.isna(v):
          return 0.0
        v_str = (
            str(v).replace("$", "").replace(",", "").replace("nan", "0").strip()
        )
        try:
          return float(v_str)
        except:
          return 0.0


      # --- 1. CONSTRUIR RANKING DE TIENDAS ---
      ranking_data = []
      for idx, row in df_temp.iterrows():
        t_name = str(row["Tienda"]).strip()
        if (
            "Total general" in t_name
            or "Total Tienda" in t_name
            or not t_name
        ):
          continue

        tot_imp_t = 0.0
        tot_uni_t = 0.0
        c_names = df_temp.columns[1:]
        j = 0
        while j < len(c_names) - 1:
          c_imp = c_names[j]
          c_uni = c_names[j + 1]
          tot_imp_t += clean_val(row[c_imp])
          tot_uni_t += clean_val(row[c_uni])
          j += 2

        ranking_data.append(
            {
                "TIENDA": t_name,
                "VENTA TOTAL ($)": tot_imp_t,
                "UNIDADES TOTALES": tot_uni_t,
            }
        )

      df_ranking = pd.DataFrame(ranking_data)
      if not df_ranking.empty:
        df_ranking = df_ranking.sort_values(
            by="VENTA TOTAL ($)", ascending=False
        ).reset_index(drop=True)
        df_ranking.index = df_ranking.index + 1

        fmt_rank = {
            "VENTA TOTAL ($)": "{:,.2f}",
            "UNIDADES TOTALES": "{:,.2f}",
        }

        def highlight_santa_fe(row):
          if "SANTA FE" in str(row["TIENDA"]).upper():
            return [
                "font-weight: bold; background-color: rgba(0, 128, 0, 0.15)"
            ] * len(row)
          return [""] * len(row)

        st.markdown(
            f"#### 🏆 Ranking de Tiendas - {campana_seleccionada.replace('.csv', '')}"
        )
        styled_rank = df_ranking.style.format(fmt_rank).apply(
            highlight_santa_fe, axis=1
        )
        st.dataframe(styled_rank, use_container_width=True)

      st.markdown("---")

      # --- 2. DETALLE DE ARTÍCULOS POR TIENDA ---
      lista_tiendas = sorted(df_temp["Tienda"].dropna().unique())
      tienda_elegida = st.selectbox(
          "Selecciona la Tienda para ver Detalle de Artículos:",
          ["TODAS (Consolidado de Cadena)"] + list(lista_tiendas),
      )

      if tienda_elegida != "TODAS (Consolidado de Cadena)":
        df_temp_filtered = df_temp[df_temp["Tienda"] == tienda_elegida]
      else:
        df_temp_filtered = df_temp[
            df_temp["Tienda"].str.contains(
                "Total general", case=False, na=False
            )
        ]
        if df_temp_filtered.empty:
          df_temp_filtered = df_temp.head(1)

      productos_data = []
      col_names = df_temp.columns[1:]
      i = 0
      while i < len(col_names) - 1:
        col_imp = col_names[i]
        col_uni = col_names[i + 1]
        prod_name = col_imp.split(" | ")[0]

        val_imp = df_temp_filtered[col_imp].values[0]
        val_uni = df_temp_filtered[col_uni].values[0]

        v_imp_num = clean_val(val_imp)
        v_uni_num = clean_val(val_uni)

        if (
            prod_name != "Total Tienda"
            and prod_name != "Total general"
            and v_imp_num > 0
        ):
          productos_data.append(
              {
                  "PRODUCTO": prod_name,
                  "IMPORTE VENTA": v_imp_num,
                  "UNIDADES VENTA": v_uni_num,
              }
          )
        i += 2

      df_resultado_temp = pd.DataFrame(productos_data)
      if not df_resultado_temp.empty:
        df_resultado_temp = df_resultado_temp.sort_values(
            by="IMPORTE VENTA", ascending=False
        )

        tot_imp = df_resultado_temp["IMPORTE VENTA"].sum()
        tot_uni = df_resultado_temp["UNIDADES VENTA"].sum()
        fila_tot = pd.DataFrame(
            {
                "PRODUCTO": ["TOTAL TEMPORADA"],
                "IMPORTE VENTA": [tot_imp],
                "UNIDADES VENTA": [tot_uni],
            }
        )
        df_resultado_temp = pd.concat(
            [df_resultado_temp, fila_tot], ignore_index=True
        )

        fmt_temp = {
            "IMPORTE VENTA": "{:,.2f}",
            "UNIDADES VENTA": "{:,.2f}",
        }


        def highlight_last_row_temp(row):
          if row.name == len(df_resultado_temp) - 1:
            return [
                "font-weight: bold; background-color: rgba(128,128,128,0.1)"
            ] * len(row)
          return [""] * len(row)


        styled_temp = df_resultado_temp.style.format(fmt_temp).apply(
            highlight_last_row_temp, axis=1
        )

        st.markdown(f"#### 🏷️ Desglose de Artículos ({tienda_elegida})")
        st.dataframe(styled_temp, use_container_width=True)
      else:
        st.info("No hay datos de venta registrados para los filtros actuales.")

elif modulo_principal == "Clientes y Ticket Promedio":
  st.subheader("👥 Comportamiento Diario de Clientes y Ticket Promedio")

  if df_clientes_ticket.empty:
    st.warning(
        "No se encontró el archivo 'Ventas Clientes y Ticket.csv' en la"
        " carpeta."
    )
  else:
    df_ct = df_clientes_ticket.copy()

    col_vta_act = (
        "Venta Actual" if "Venta Actual" in df_ct.columns else df_ct.columns[5]
    )
    col_vta_ant = (
        "Venta Año Anterior"
        if "Venta Año Anterior" in df_ct.columns
        else df_ct.columns[6]
    )
    col_cli_act = "Clientes" if "Clientes" in df_ct.columns else df_ct.columns[7]
    col_cli_ant = (
        "Clientes Año Anterior"
        if "Clientes Año Anterior" in df_ct.columns
        else df_ct.columns[8]
    )
    col_tic_act = (
        "Ticket Promedio"
        if "Ticket Promedio" in df_ct.columns
        else df_ct.columns[9]
    )
    col_tic_ant = (
        "Ticket Promedio Año Anterior"
        if "Ticket Promedio Año Anterior" in df_ct.columns
        else df_ct.columns[10]
    )
    col_dia = (
        "Mes, Día, Año de Fecha"
        if "Mes, Día, Año de Fecha" in df_ct.columns
        else df_ct.columns[4]
    )

    df_clientes_view = pd.DataFrame()
    df_clientes_view["FECHA"] = df_ct[col_dia]
    df_clientes_view["CLIENTES 2026"] = df_ct[col_cli_act]
    df_clientes_view["CLIENTES 2025"] = df_ct[col_cli_ant]
    df_clientes_view["Var $ (Clientes)"] = (
        df_clientes_view["CLIENTES 2026"] - df_clientes_view["CLIENTES 2025"]
    )
    df_clientes_view["Var % (Clientes)"] = df_clientes_view.apply(
        lambda r: (
            (r["CLIENTES 2026"] / r["CLIENTES 2025"] * 100) - 100
            if r["CLIENTES 2025"] != 0
            else 0
        ),
        axis=1,
    )

    tot_cli_26 = df_clientes_view["CLIENTES 2026"].sum()
    tot_cli_25 = df_clientes_view["CLIENTES 2025"].sum()
    var_cli_tot_val = tot_cli_26 - tot_cli_25
    var_cli_tot_pct = (
        (tot_cli_26 / tot_cli_25 * 100) - 100 if tot_cli_25 != 0 else 0
    )

    fila_acum_cli = pd.DataFrame(
        {
            "FECHA": ["ACUMULADO TOTAL"],
            "CLIENTES 2026": [tot_cli_26],
            "CLIENTES 2025": [tot_cli_25],
            "Var $ (Clientes)": [var_cli_tot_val],
            "Var % (Clientes)": [var_cli_tot_pct],
        }
    )
    df_clientes_view = pd.concat(
        [df_clientes_view, fila_acum_cli], ignore_index=True
    )

    fmt_cli = {
        "CLIENTES 2026": "{:,.0f}",
        "CLIENTES 2025": "{:,.0f}",
        "Var $ (Clientes)": "{:+,.0f}",
        "Var % (Clientes)": "{:,.2f}%",
    }


    def color_neg(val):
      if isinstance(val, (int, float)) and val < 0:
        return "color: #ff4d4d; font-weight: bold;"
      return ""


    st.markdown("#### 🛒 Clientes por Día")


    def highlight_last_row(row):
      if row.name == len(df_clientes_view) - 1:
        return [
            "font-weight: bold; background-color: rgba(128,128,128,0.1)"
        ] * len(row)
      return [""] * len(row)


    styled_cli = df_clientes_view.style.format(fmt_cli).apply(
        highlight_last_row, axis=1
    )
    try:
      styled_cli = styled_cli.map(
          color_neg, subset=["Var $ (Clientes)", "Var % (Clientes)"]
      )
    except AttributeError:
      styled_cli = styled_cli.applymap(
          color_neg, subset=["Var $ (Clientes)", "Var % (Clientes)"]
      )

    st.dataframe(styled_cli, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    df_ticket_view = pd.DataFrame()
    df_ticket_view["FECHA"] = df_ct[col_dia]
    df_ticket_view["TICKET 2026"] = df_ct[col_tic_act]
    df_ticket_view["TICKET 2025"] = df_ct[col_tic_ant]
    df_ticket_view["Var $ (Ticket)"] = (
        df_ticket_view["TICKET 2026"] - df_ticket_view["TICKET 2025"]
    )
    df_ticket_view["Var % (Ticket)"] = df_ticket_view.apply(
        lambda r: (
            (r["TICKET 2026"] / r["TICKET 2025"] * 100) - 100
            if r["TICKET 2025"] != 0
            else 0
        ),
        axis=1,
    )

    tot_vta_26 = df_ct[col_vta_act].sum()
    tot_vta_25 = df_ct[col_vta_ant].sum()
    prom_tic_26 = tot_vta_26 / tot_cli_26 if tot_cli_26 > 0 else 0
    prom_tic_25 = tot_vta_25 / tot_cli_25 if tot_cli_25 > 0 else 0
    var_tic_tot_val = prom_tic_26 - prom_tic_25
    var_tic_tot_pct = (
        (prom_tic_26 / prom_tic_25 * 100) - 100 if prom_tic_25 != 0 else 0
    )

    fila_acum_tic = pd.DataFrame(
        {
            "FECHA": ["ACUMULADO PROMEDIO"],
            "TICKET 2026": [prom_tic_26],
            "TICKET 2025": [prom_tic_25],
            "Var $ (Ticket)": [var_tic_tot_val],
            "Var % (Ticket)": [var_tic_tot_pct],
        }
    )
    df_ticket_view = pd.concat(
        [df_ticket_view, fila_acum_tic], ignore_index=True
    )

    fmt_tic = {
        "TICKET 2026": "{:,.2f}",
        "TICKET 2025": "{:,.2f}",
        "Var $ (Ticket)": "{:+,.2f}",
        "Var % (Ticket)": "{:,.2f}%",
    }

    st.markdown("#### 🧾 Ticket Promedio por Día")


    def highlight_last_row_tic(row):
      if row.name == len(df_ticket_view) - 1:
        return [
            "font-weight: bold; background-color: rgba(128,128,128,0.1)"
        ] * len(row)
      return [""] * len(row)


    styled_tic = df_ticket_view.style.format(fmt_tic).apply(
        highlight_last_row_tic, axis=1
    )
    try:
      styled_tic = styled_tic.map(
          color_neg, subset=["Var $ (Ticket)", "Var % (Ticket)"]
      )
    except AttributeError:
      styled_tic = styled_tic.applymap(
          color_neg, subset=["Var $ (Ticket)", "Var % (Ticket)"]
      )

    st.dataframe(styled_tic, use_container_width=True)

else:
  # --- MÓDULO DE VENTAS (División, Sección, Producto) ---
  st.markdown("### 📅 Tipo de Reporte de Venta")
  tipo_reporte = st.radio(
      "Reporte", ["Acumulada", "Diaria", "Ambas"], horizontal=True
  )

  st.markdown("---")

  col_1, col_2, col_3 = st.columns([2, 2, 2])

  with col_1:
    st.write("**Nivel de Visualización**")
    nivel = st.radio(
        "Selecciona nivel",
        ["División", "Sección", "Producto"],
        horizontal=True,
        label_visibility="collapsed",
    )

  with col_2:
    st.write("**Métrica a Consultar**")
    metrica_tipo = st.radio(
        "Métrica",
        ["Venta ($)", "Unidades"],
        horizontal=True,
        label_visibility="collapsed",
    )

  with col_3:
    st.write("**Ordenamiento por Var $**")
    orden_tipo = st.radio(
        "Orden",
        ["Incremento (Mayor a Menor)", "Decremento (Menor a Mayor)"],
        horizontal=True,
        label_visibility="collapsed",
    )

  ascending_order = True if "Decremento" in orden_tipo else False

  tipo_participacion = None
  if nivel in ["División", "Sección"]:
    st.markdown("<br>", unsafe_allow_html=True)
    col_p1, col_p2 = st.columns([2, 4])
    with col_p1:
      st.write("**Base para cálculo de Participación**")
      if nivel == "División":
        st.info("ℹ️ En nivel División, la participación es sobre la Venta Total.")
        tipo_participacion = "Sobre Venta Total de la Tienda"
      else:
        tipo_participacion = st.radio(
            "Participación sobre:",
            ["Sobre Venta Total de la Tienda", "Sobre la División"],
            horizontal=True,
            label_visibility="collapsed",
        )

  filtro_seleccionado = "Todas"

  if nivel == "Sección":
    lista_divisiones = sorted(df_acumulada["División"].dropna().unique())
    filtro_seleccionado = st.selectbox(
        "Filtrar por División:", ["Todas"] + list(lista_divisiones)
    )
  elif nivel == "Producto":
    lista_secciones = sorted(df_acumulada["Sección"].dropna().unique())
    filtro_seleccionado = st.selectbox(
        "Filtrar por Sección para ver Productos:",
        ["Todas"] + list(lista_secciones),
    )


  def procesar_dataframe(df_source, titulo_tabla):
    col_v26 = (
        "Importe venta" if metrica_tipo == "Venta ($)" else "Unidades venta"
    )
    col_v25 = (
        "Importe venta comp."
        if metrica_tipo == "Venta ($)"
        else "Unidades venta comp."
    )

    temp_source = df_source.copy()
    if (
        nivel == "Sección"
        and filtro_seleccionado
        and filtro_seleccionado != "Todas"
    ):
      temp_source = temp_source[temp_source["División"] == filtro_seleccionado]
    elif (
        nivel == "Producto"
        and filtro_seleccionado
        and filtro_seleccionado != "Todas"
    ):
      temp_source = temp_source[temp_source["Sección"] == filtro_seleccionado]

    total_tienda_2026 = df_source[col_v26].sum()
    total_tienda_2025 = df_source[col_v25].sum()

    if nivel == "División":
      df_grouped = (
          temp_source.groupby("División")
          .agg({col_v26: "sum", col_v25: "sum"})
          .reset_index()
      )
      df_grouped.rename(columns={"División": "DIVISIÓN"}, inplace=True)
      df_grouped["Part. 2026 (%)"] = (
          df_grouped[col_v26] / total_tienda_2026 * 100
          if total_tienda_2026 > 0
          else 0
      )
      df_grouped["Part. 2025 (%)"] = (
          df_grouped[col_v25] / total_tienda_2025 * 100
          if total_tienda_2025 > 0
          else 0
      )

    elif nivel == "Sección":
      df_grouped = (
          temp_source.groupby(["División", "Sección"])
          .agg({col_v26: "sum", col_v25: "sum"})
          .reset_index()
      )
      df_grouped.rename(
          columns={"División": "DIVISIÓN", "Sección": "SECCIÓN"}, inplace=True
      )

      if tipo_participacion == "Sobre la División":
        div_totales = (
            df_source.groupby("División")
            .agg({col_v26: "sum", col_v25: "sum"})
            .reset_index()
        )
        div_totales.rename(
            columns={
                "División": "DIVISIÓN",
                col_v26: "div_26",
                col_v25: "div_25",
            },
            inplace=True,
        )
        df_grouped = df_grouped.merge(div_totales, on="DIVISIÓN", how="left")
        df_grouped["Part. 2026 (%)"] = df_grouped.apply(
            lambda r: (r[col_v26] / r["div_26"] * 100) if r["div_26"] > 0 else 0,
            axis=1,
        )
        df_grouped["Part. 2025 (%)"] = df_grouped.apply(
            lambda r: (r[col_v25] / r["div_25"] * 100) if r["div_25"] > 0 else 0,
            axis=1,
        )
        df_grouped.drop(columns=["div_26", "div_25"], inplace=True)
      else:
        df_grouped["Part. 2026 (%)"] = (
            df_grouped[col_v26] / total_tienda_2026 * 100
            if total_tienda_2026 > 0
            else 0
        )
        df_grouped["Part. 2025 (%)"] = (
            df_grouped[col_v25] / total_tienda_2025 * 100
            if total_tienda_2025 > 0
            else 0
        )

    else:
      df_grouped = (
          temp_source.groupby(["División", "Sección", "Producto"])
          .agg({col_v26: "sum", col_v25: "sum"})
          .reset_index()
      )
      df_grouped.rename(
          columns={
              "División": "DIVISIÓN",
              "Sección": "SECCIÓN",
              "Producto": "PRODUCTO",
          },
          inplace=True,
      )

    df_grouped["Var $"] = df_grouped[col_v26] - df_grouped[col_v25]
    df_grouped["Var %"] = df_grouped.apply(
        lambda row: (
            (row[col_v26] / row[col_v25] * 100) - 100
            if row[col_v25] != 0
            else (100.0 if row[col_v26] > 0 else 0.0)
        ),
        axis=1,
    )

    df_grouped.rename(
        columns={col_v26: "Venta 2026", col_v25: "Venta 2025"}, inplace=True
    )

    if nivel == "División":
      df_grouped = df_grouped[
          [
              "DIVISIÓN",
              "Venta 2026",
              "Part. 2026 (%)",
              "Venta 2025",
              "Part. 2025 (%)",
              "Var $",
              "Var %",
          ]
      ]
    elif nivel == "Sección":
      df_grouped = df_grouped[
          [
              "DIVISIÓN",
              "SECCIÓN",
              "Venta 2026",
              "Part. 2026 (%)",
              "Venta 2025",
              "Part. 2025 (%)",
              "Var $",
              "Var %",
          ]
      ]
    else:
      df_grouped = df_grouped[
          [
              "DIVISIÓN",
              "SECCIÓN",
              "PRODUCTO",
              "Venta 2026",
              "Venta 2025",
              "Var $",
              "Var %",
          ]
      ]

    df_grouped = df_grouped.sort_values(by="Var $", ascending=ascending_order)

    format_dict = {
        "Venta 2026": "{:,.2f}",
        "Venta 2025": "{:,.2f}",
        "Var $": "{:,.2f}",
        "Var %": "{:,.2f}%",
    }
    if nivel in ["División", "Sección"]:
      format_dict["Part. 2026 (%)"] = "{:,.2f}%"
      format_dict["Part. 2025 (%)"] = "{:,.2f}%"

    def color_negative_red(val):
      if isinstance(val, (int, float)) and val < 0:
        return "color: #ff4d4d; font-weight: bold;"
      return ""

    cols_to_colorize = ["Var $", "Var %"]
    try:
      styled_df = (
          df_grouped.style.format(format_dict)
          .map(color_negative_red, subset=cols_to_colorize)
      )
    except AttributeError:
      styled_df = (
          df_grouped.style.format(format_dict)
          .applymap(color_negative_red, subset=cols_to_colorize)
      )

    st.subheader(titulo_tabla)
    st.dataframe(styled_df, use_container_width=True)


  st.markdown("---")
  if tipo_reporte == "Acumulada":
    procesar_dataframe(df_acumulada, "📈 Vista de Venta Acumulada")
  elif tipo_reporte == "Diaria":
    procesar_dataframe(df_diaria, "📅 Vista de Venta Diaria")
  elif tipo_reporte == "Ambas":
    procesar_dataframe(df_acumulada, "📈 1. Vista de Venta Acumulada")
    st.markdown("<br>", unsafe_allow_html=True)
    procesar_dataframe(df_diaria, "📅 2. Vista de Venta Diaria")
