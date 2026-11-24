"""
Simulador Interactivo de Cascada de RF para Front-End Receiver (FER) - Versión 6.5
Autor: Jaime Huenuqueo Salazar| Libro: Fundamentos y Diseño de Sistemas de Guerra Electrónica / ESM

Mejoras v4.5:
1. Auto-actualización reactiva de NF = |G| en componentes pasivas en la tabla de reordenamiento.
2. Incorporación de los campos IIP2 (dBm), IIP3 (dBm) e IP1dB (dBm = OP1dB - G) en la interfaz.
3. Despliegue de la curva de IP1dB (saturación de entrada) en la gráfica de Psig.
4. Valores por defecto de OIP2 y OIP3 fijados en 249.0 dBm para componentes ideales/pasivas.
5. Campo Part Number (PN) por componente para trazabilidad de modelos reales y exportación en CSV.
"""

import io
import uuid
import qrcode
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Simulador FER v4.5 - Jaime",
    page_icon="📡",
    layout="wide"
)

K_BOLTZMANN = 1.380649e-23  # J/K

PASSIVE_KEYWORDS = [
    "cable", "atenuador", "divisor", "divider", "filtro",
    "switch", "spdt", "sp3t", "sp4t", "diplexer", "triplexer", "protección pin", "limitador"
]


def is_passive_component(comp_type: str, comp_name: str = "") -> bool:
    """Identifica si una componente es física y termodinámicamente pasiva."""
    target = f"{comp_type} {comp_name}".lower()
    return any(k in target for k in PASSIVE_KEYWORDS)


def db_to_lin(val_db):
    return 10.0 ** (val_db / 10.0)


def lin_to_db(val_lin):
    return 10.0 * np.log10(np.maximum(val_lin, 1e-20))


def dbm_to_mw(val_dbm):
    return 10.0 ** (val_dbm / 10.0)


def mw_to_dbm(val_mw):
    return 10.0 * np.log10(np.maximum(val_mw, 1e-20))


def compute_noise_power_density_dbm_mhz(temp_kelvin):
    p_noise_w_per_hz = K_BOLTZMANN * temp_kelvin
    p_noise_mw_per_hz = p_noise_w_per_hz * 1e3
    p_noise_dbm_per_hz = 10.0 * np.log10(np.maximum(p_noise_mw_per_hz, 1e-30))
    return p_noise_dbm_per_hz + 60.0


def generate_qr_code_bytes(url: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1A365D", back_color="#FFFFFF").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def compute_cascade_v4(stages, b_rf_mhz, b_video_mhz, snr_min_db, pin_rf_dbm, temp_kelvin, f_calc_ghz):
    if not stages:
        return pd.DataFrame(), {}

    n = len(stages)
    cum_gain_db = np.zeros(n)
    cum_nf_db = np.zeros(n)
    cum_iip3_dbm = np.zeros(n)
    cum_oip3_dbm = np.zeros(n)
    cum_iip2_dbm = np.zeros(n)
    cum_oip2_dbm = np.zeros(n)
    cum_ip1db_dbm = np.zeros(n)
    cum_op1db_dbm = np.zeros(n)
    sig_level_dbm = np.zeros(n)
    noise_floor_dbm = np.zeros(n)
    snr_stage_db = np.zeros(n)
    pmax_limited_dbm = np.zeros(n)
    is_saturated = [False] * n

    calc_ip1_list = np.zeros(n)
    calc_iip3_list = np.zeros(n)
    calc_iip2_list = np.zeros(n)

    kt0_dbm_mhz = compute_noise_power_density_dbm_mhz(temp_kelvin)

    g_lin_cum = 1.0
    f_lin_cum = 0.0
    inv_iip3_mw = 0.0
    inv_iip2_mw = 0.0
    inv_ip1db_mw = 0.0
    running_pmax_limited = 999.0

    for i, stg in enumerate(stages):
        g_i_db = float(stg["gain_db"])

        # Coerción de componentes pasivas
        if is_passive_component(stg.get("type", ""), stg.get("name", "")):
            if g_i_db > 0:
                g_i_db = -abs(g_i_db)
                stg["gain_db"] = g_i_db
            nf_i_db = abs(g_i_db)
            stg["nf_db"] = nf_i_db
        else:
            nf_i_db = float(stg["nf_db"])

        op1_i_dbm = float(stg.get("op1db_dbm", 30.0))
        oip3_i_dbm = float(stg.get("oip3_dbm", 249.0))
        oip2_i_dbm = float(stg.get("oip2_dbm", 249.0))
        opmax_stage = float(stg.get("opmax_dbm", 249.0))

        # Cálculo de parámetros referidos a la entrada
        ip1db_i_dbm = op1_i_dbm - g_i_db
        iip3_i_dbm = oip3_i_dbm - g_i_db
        iip2_i_dbm = oip2_i_dbm - g_i_db

        calc_ip1_list[i] = ip1db_i_dbm
        calc_iip3_list[i] = iip3_i_dbm
        calc_iip2_list[i] = iip2_i_dbm

        g_i_lin = db_to_lin(g_i_db)
        f_i_lin = db_to_lin(nf_i_db)
        iip3_i_mw = dbm_to_mw(iip3_i_dbm)
        iip2_i_mw = dbm_to_mw(iip2_i_dbm)
        ip1db_i_mw = dbm_to_mw(ip1db_i_dbm)

        if i == 0:
            g_lin_cum = g_i_lin
            f_lin_cum = f_i_lin
            inv_iip3_mw = 1.0 / iip3_i_mw
            inv_iip2_mw = 1.0 / iip2_i_mw
            inv_ip1db_mw = 1.0 / ip1db_i_mw
        else:
            f_lin_cum += (f_i_lin - 1.0) / g_lin_cum
            inv_iip3_mw += g_lin_cum / iip3_i_mw
            inv_iip2_mw += (g_lin_cum ** 2) / iip2_i_mw
            inv_ip1db_mw += g_lin_cum / ip1db_i_mw
            g_lin_cum *= g_i_lin

        cum_gain_db[i] = lin_to_db(g_lin_cum)
        cum_nf_db[i] = lin_to_db(f_lin_cum)
        cum_iip3_dbm[i] = mw_to_dbm(1.0 / inv_iip3_mw)
        cum_oip3_dbm[i] = cum_iip3_dbm[i] + cum_gain_db[i]
        cum_iip2_dbm[i] = mw_to_dbm(1.0 / inv_iip2_mw)
        cum_oip2_dbm[i] = cum_iip2_dbm[i] + cum_gain_db[i]
        cum_ip1db_dbm[i] = mw_to_dbm(1.0 / inv_ip1db_mw)
        cum_op1db_dbm[i] = cum_ip1db_dbm[i] + cum_gain_db[i]

        sig_level_dbm[i] = pin_rf_dbm + cum_gain_db[i]
        noise_floor_dbm[i] = kt0_dbm_mhz + 10.0 * np.log10(b_rf_mhz) + cum_nf_db[i] + cum_gain_db[i]
        snr_stage_db[i] = sig_level_dbm[i] - noise_floor_dbm[i]

        if opmax_stage < 200.0:
            running_pmax_limited = min(running_pmax_limited + g_i_db, opmax_stage)
        else:
            running_pmax_limited = running_pmax_limited + g_i_db
        pmax_limited_dbm[i] = min(running_pmax_limited, cum_op1db_dbm[i])

        if sig_level_dbm[i] >= cum_op1db_dbm[i] or (opmax_stage < 200.0 and sig_level_dbm[i] >= opmax_stage):
            is_saturated[i] = True

    total_nf = cum_nf_db[-1]
    total_gain = cum_gain_db[-1]
    total_iip3 = cum_iip3_dbm[-1]
    total_oip3 = cum_oip3_dbm[-1]
    total_iip2 = cum_iip2_dbm[-1]
    total_oip2 = cum_oip2_dbm[-1]
    total_ip1db = cum_ip1db_dbm[-1]
    total_op1db = cum_op1db_dbm[-1]

    mds_rf_dbm = kt0_dbm_mhz + 10.0 * np.log10(b_rf_mhz) + total_nf + snr_min_db
    term_inside = 2.5 * b_video_mhz + 4.0 * np.sqrt(np.maximum(2.0 * b_rf_mhz * b_video_mhz - (b_video_mhz ** 2), 1e-6))
    tss_video_dbm = kt0_dbm_mhz + total_nf + 10.0 * np.log10(np.maximum(term_inside, 1e-6))
    sfdr_db = (2.0 / 3.0) * (total_iip3 - (kt0_dbm_mhz + 10.0 * np.log10(b_rf_mhz) + total_nf))
    idr_db = total_ip1db - mds_rf_dbm

    df_results = pd.DataFrame({
        "Etapa": [f"{i + 1}. {s['name']}" for i, s in enumerate(stages)],
        "PN": [s.get("pn", "N/A") for s in stages],
        "Tipo": [s["type"] for s in stages],
        "Frecuencia (GHz)": [f_calc_ghz] * n,
        "Temp (K)": [temp_kelvin] * n,
        "G [dB]": [s["gain_db"] for s in stages],
        "NF Etapa [dB]": [s["nf_db"] for s in stages],
        "OP1 [dBm]": [s.get("op1db_dbm", 30.0) for s in stages],
        "OIP3 [dBm]": [s.get("oip3_dbm", 249.0) for s in stages],
        "OIP2 [dBm]": [s.get("oip2_dbm", 249.0) for s in stages],
        "OPmax [dBm]": [s.get("opmax_dbm", 249.0) for s in stages],
        "IP1dB Entrada [dBm]": np.round(calc_ip1_list, 2),
        "IIP3 Entrada [dBm]": np.round(calc_iip3_list, 2),
        "IIP2 Entrada [dBm]": np.round(calc_iip2_list, 2),
        "Gain Acum [dB]": np.round(cum_gain_db, 2),
        "NF Acum Friis [dB]": np.round(cum_nf_db, 2),
        "OP1 Acum [dBm]": np.round(cum_op1db_dbm, 2),
        "OIP3 Acum [dBm]": np.round(cum_oip3_dbm, 2),
        "OIP2 Acum [dBm]": np.round(cum_oip2_dbm, 2),
        "Psig [dBm]": np.round(sig_level_dbm, 2),
        "Pnoise [dBm]": np.round(noise_floor_dbm, 2),
        "SNR [dB]": np.round(snr_stage_db, 2),
        "PMaxLimited [dBm]": np.round(pmax_limited_dbm, 2),
        "Estado": ["⚠️ SATURADO" if sat else "✅ Lineal" for sat in is_saturated]
    })

    summary = {
        "f_calc_ghz": f_calc_ghz,
        "temp_kelvin": temp_kelvin,
        "total_gain_db": total_gain,
        "total_nf_db": total_nf,
        "total_ip1db_dbm": total_ip1db,
        "total_op1db_dbm": total_op1db,
        "total_iip3_dbm": total_iip3,
        "total_oip3_dbm": total_oip3,
        "total_iip2_dbm": total_iip2,
        "total_oip2_dbm": total_oip2,
        "mds_rf_dbm": mds_rf_dbm,
        "tss_video_dbm": tss_video_dbm,
        "sfdr_db": sfdr_db,
        "idr_db": idr_db,
        "cum_gain_db": cum_gain_db,
        "cum_nf_db": cum_nf_db,
        "cum_op1db_dbm": cum_op1db_dbm,
        "cum_oip3_dbm": cum_oip3_dbm,
        "cum_oip2_dbm": cum_oip2_dbm,
        "sig_level_dbm": sig_level_dbm,
        "noise_floor_dbm": noise_floor_dbm,
        "snr_stage_db": snr_stage_db,
        "pmax_limited_dbm": pmax_limited_dbm,
        "calc_ip1_list": calc_ip1_list,
        "is_saturated": is_saturated,
    }

    return df_results, summary


def render_block_diagram_v4(stages, is_saturated, f_calc_ghz, temp_kelvin):
    if not stages:
        return

    cards = []
    for i, s in enumerate(stages):
        sat = is_saturated[i] if i < len(is_saturated) else False
        bg = "#4A1515" if sat else "#1A365D"
        border = "#E53E3E" if sat else "#3182CE"
        badge = "⚠️ SATURADO" if sat else "✅ Lineal"
        bcolor = "#FEB2B2" if sat else "#9AE6B4"

        stype = s["type"]
        pn_val = s.get("pn", "")
        pn_str = f"<div style='font-size:10px; color:#F6AD55; font-weight:bold;'>PN: {pn_val}</div>" if pn_val else ""
        icon = "📡" if "antena" in stype.lower() else ("🔄" if "converter" in stype.lower() else (
            "🔀" if "plexer" in stype.lower() or "divider" in stype.lower() or "divisor" in stype.lower() else (
                "〰️" if "cable" in stype.lower() else "📦")))

        card_html = (
            f'<div style="display:inline-block; vertical-align:top; background:{bg}; '
            f'border:2px solid {border}; border-radius:8px; padding:10px 12px; min-width:145px; '
            f'text-align:center; box-shadow:0 4px 6px rgba(0,0,0,0.3); margin:0 4px;">'
            f'<div style="font-size:10px; color:#A0AEC0; font-weight:bold; text-transform:uppercase;">ETAPA {i + 1}</div>'
            f'<div style="font-size:13px; color:#FFFFFF; font-weight:bold; margin:3px 0;">{icon} {s["name"]}</div>'
            f'{pn_str}'
            f'<div style="font-size:10px; color:#CBD5E0; background:rgba(0,0,0,0.25); padding:2px 4px; border-radius:4px; margin-bottom:4px;">{s["type"]}</div>'
            f'<div style="font-size:11px; color:#90CDF4; font-family:monospace;">G:{s["gain_db"]:+.1f}dB | NF:{s["nf_db"]:.1f}dB</div>'
            f'<div style="font-size:10px; font-weight:bold; color:{bcolor}; margin-top:4px;">{badge}</div>'
            f'</div>'
        )
        cards.append(card_html)

    arrow_html = '<div style="display:inline-block; vertical-align:middle; color:#63B3ED; font-weight:bold; font-size:16px; margin:0 2px;">▶</div>'

    diagram_html = (
            '<div style="display:block; overflow-x:auto; white-space:nowrap; padding:15px; '
            'background:#1A202C; border-radius:10px; border:1px solid #2D3748; margin-bottom:20px;">'
            + arrow_html.join(cards) +
            arrow_html +
            '<div style="display:inline-block; vertical-align:top; background:#2D3748; border:1px solid #4A5568; '
            'border-radius:8px; padding:10px 14px; min-width:110px; text-align:center;">'
            '<div style="font-size:10px; color:#A0AEC0; font-weight:bold;">DESTINO</div>'
            '<div style="font-size:13px; color:#FFFFFF; font-weight:bold; margin-top:3px;">🎯 Salida FER</div>'
            f'<div style="font-size:10px; color:#90CDF4;">@{f_calc_ghz:.2f}GHz, {temp_kelvin:.1f}K</div>'
            '</div>'
            '</div>'
    )
    st.markdown(diagram_html, unsafe_allow_html=True)


def main():
    st.title("📡 Simulador de Cascada de RF - Front-End Receiver (FER) V6.5")
    st.caption("Autor: **Jaime Huenuqueo Salazar** | *Libro: Fundamentos y Diseño de Sistemas de Guerra Electrónica / ESM*")

    st.sidebar.header("🌐 Cobertura Espectral")
    col_f1, col_f2 = st.sidebar.columns(2)
    with col_f1:
        f_min_ghz = st.number_input("F_min (GHz)", min_value=0.01, max_value=100.0, value=2.0, step=0.5)
    with col_f2:
        f_max_ghz = st.number_input("F_max (GHz)", min_value=0.02, max_value=110.0, value=18.0, step=0.5)

    if f_max_ghz <= f_min_ghz:
        st.sidebar.error("F_max debe ser mayor a F_min")
        b_rf_mhz = 1000.0
    else:
        b_rf_ghz = f_max_ghz - f_min_ghz
        b_rf_mhz = b_rf_ghz * 1000.0
        st.sidebar.success(f"**B_RF:** {b_rf_mhz:,.0f} MHz ({b_rf_ghz:.2f} GHz)")

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Parámetros de Operación")

    col_op1, col_op2 = st.sidebar.columns(2)
    with col_op1:
        f_calc_ghz = st.number_input("Frecuencia f_calc (GHz)", min_value=float(f_min_ghz), max_value=float(f_max_ghz),
                                     value=float(min(max(10.0, f_min_ghz), f_max_ghz)), step=0.5, format="%.2f")
    with col_op2:
        st.metric("Frecuencia (MHz)", f"{f_calc_ghz * 1000.0:,.0f} MHz")

    col_t1, col_t2 = st.sidebar.columns(2)
    with col_t1:
        temp_kelvin = st.number_input("Temperatura T (K)", min_value=1.0, max_value=600.0, value=290.0, step=5.0)
    with col_t2:
        st.metric("Temp (°C)", f"{temp_kelvin - 273.15:+.1f} °C")

    kt_val = compute_noise_power_density_dbm_mhz(temp_kelvin)
    st.sidebar.caption(f"Densidad k*T: **{kt_val:.2f} dBm/MHz** (a {temp_kelvin:.1f} K)")

    b_video_mhz = st.sidebar.number_input("Ancho Banda Video, B_v (MHz)", min_value=0.1, max_value=200.0, value=10.0,
                                          step=1.0)
    snr_min_db = st.sidebar.number_input("SNR mínimo de detección (dB)", min_value=0.0, max_value=30.0, value=12.0,
                                         step=0.5)
    pin_rf_dbm = st.sidebar.number_input("Potencia Entrada Pin (dBm)", min_value=-130.0, max_value=30.0, value=-40.0,
                                         step=5.0)

    # Catálogo con PN por defecto y OIP2/OIP3 en 249 dBm
    component_templates = {
        "Cable Coaxial RF": {"type": "Cable RF", "pn": "RG-142", "gain_db": -2.5, "nf_db": 2.5, "op1db_dbm": 45.0,
                             "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
        "Atenuador Fijo/Variable": {"type": "Atenuador", "pn": "PE4302", "gain_db": -6.0, "nf_db": 6.0,
                                    "op1db_dbm": 35.0, "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
        "Power Divider 1:2": {"type": "Divisor 1:2", "pn": "PE2000", "gain_db": -3.5, "nf_db": 3.5, "op1db_dbm": 40.0,
                              "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
        "Power Divider 1:4": {"type": "Divisor 1:4", "pn": "PE2002", "gain_db": -7.0, "nf_db": 7.0, "op1db_dbm": 40.0,
                              "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
        "Conmutador SPDT": {"type": "Switch SPDT", "pn": "PE42420", "gain_db": -1.2, "nf_db": 1.2, "op1db_dbm": 30.0,
                            "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
        "Conmutador SP3T": {"type": "Switch SP3T", "pn": "HMC245A", "gain_db": -1.6, "nf_db": 1.6, "op1db_dbm": 28.0,
                            "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
        "Conmutador SP4T": {"type": "Switch SP4T", "pn": "PE42441", "gain_db": -2.0, "nf_db": 2.0, "op1db_dbm": 27.0,
                            "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
        "Diplexer (Multiplexor 2 Vías)": {"type": "Diplexer", "pn": "DPX-2000", "gain_db": -1.5, "nf_db": 1.5,
                                          "op1db_dbm": 40.0, "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
        "Triplexer (Multiplexor 3 Vías)": {"type": "Triplexer", "pn": "TPX-3000", "gain_db": -2.2, "nf_db": 2.2,
                                           "op1db_dbm": 40.0, "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
        "Filtro Preselector": {"type": "Filtro", "pn": "BPF-0218", "gain_db": -2.0, "nf_db": 2.0, "op1db_dbm": 35.0,
                               "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
        "Limitador PIN (Protección)": {"type": "Protección PIN", "pn": "LM-0218", "gain_db": -1.0, "nf_db": 1.0,
                                       "op1db_dbm": 24.0, "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 15.0},
        "Antena ESM (Espiral / Bocina)": {"type": "Antena", "pn": "ANT-ESM-01", "gain_db": 6.0, "nf_db": 0.0,
                                          "op1db_dbm": 50.0, "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
        "Amplificador LNA (GaN/GaAs)": {"type": "LNA", "pn": "CMD283C3", "gain_db": 20.0, "nf_db": 2.2,
                                        "op1db_dbm": 20.0, "oip3_dbm": 32.0, "oip2_dbm": 52.0, "opmax_dbm": 249.0},
        "Módulo Downconverter (Activo)": {"type": "Downconverter", "pn": "HMC7044-DC", "gain_db": 12.0, "nf_db": 6.5,
                                          "op1db_dbm": 7.0, "oip3_dbm": 17.0, "oip2_dbm": 37.0, "opmax_dbm": 10.0},
        "Módulo UpConverter": {"type": "UpConverter", "pn": "HMC7044-UC", "gain_db": 10.0, "nf_db": 7.0,
                               "op1db_dbm": 8.0, "oip3_dbm": 18.0, "oip2_dbm": 38.0, "opmax_dbm": 12.0},
    }

    st.sidebar.markdown("---")
    st.sidebar.header("➕ Añadir Etapa")
    sel_template = st.sidebar.selectbox("Seleccionar Plantilla:", list(component_templates.keys()))
    t_vals = component_templates[sel_template]
    is_tmpl_passive = is_passive_component(t_vals["type"], sel_template)

    with st.sidebar.form("add_comp_form", clear_on_submit=True):
        c_name = st.text_input("Nombre de la Etapa:", value=sel_template)
        c_pn = st.text_input("Part Number (PN):", value=t_vals.get("pn", "N/A"))
        c_type = t_vals["type"]

        if is_tmpl_passive:
            st.caption("ℹ️ *Pasivo: G debe ser <= 0 dB. La NF es bloqueada en |G|.*")
            raw_gain = st.number_input("Pérdida / Ganancia G (dB):", value=float(t_vals["gain_db"]), max_value=0.0,
                                       step=0.5)
            c_gain = -abs(raw_gain)
            c_nf = abs(c_gain)
            st.number_input("Figura de Ruido NF (dB):", value=float(c_nf), disabled=True)
        else:
            c_gain = st.number_input("Ganancia G (dB):", value=float(t_vals["gain_db"]), step=0.5)
            c_nf = st.number_input("Figura de Ruido NF (dB):", value=float(t_vals["nf_db"]), min_value=0.0, step=0.5)

        c_op1 = st.number_input("OP1dB de Salida (dBm):", value=float(t_vals["op1db_dbm"]), step=1.0)
        c_oip3 = st.number_input("OIP3 de Salida (dBm):", value=float(t_vals.get("oip3_dbm", 249.0)), step=1.0)
        c_oip2 = st.number_input("OIP2 de Salida (dBm):", value=float(t_vals.get("oip2_dbm", 249.0)), step=1.0)
        c_opmax = st.number_input("OPmax Límite (dBm):", value=float(t_vals.get("opmax_dbm", 249.0)), step=1.0)

        if st.form_submit_button("➕ Insertar Etapa"):
            if "stages" not in st.session_state:
                st.session_state.stages = []
            st.session_state.stages.append({
                "id": str(uuid.uuid4())[:8],
                "name": c_name, "pn": c_pn, "type": c_type, "gain_db": c_gain, "nf_db": c_nf,
                "op1db_dbm": c_op1, "oip3_dbm": c_oip3, "oip2_dbm": c_oip2,
                "opmax_dbm": c_opmax
            })
            st.rerun()

    # Estado por defecto con PNs y OIP2/OIP3 = 249 dBm
    if "stages" not in st.session_state:
        st.session_state.stages = [
            {"id": "s1", "name": "Antena Espiral ESM", "pn": "ANT-ESM-01", "type": "Antena", "gain_db": 6.0,
             "nf_db": 0.0, "op1db_dbm": 50.0, "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
            {"id": "s2", "name": "Cable Coaxial Entrada", "pn": "RG-142", "type": "Cable RF", "gain_db": -2.5,
             "nf_db": 2.5, "op1db_dbm": 45.0, "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
            {"id": "s3", "name": "Limitador PIN", "pn": "LM-0218", "type": "Protección PIN", "gain_db": -1.0,
             "nf_db": 1.0, "op1db_dbm": 24.0, "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 15.0},
            {"id": "s4", "name": "LNA GaN Banda Ancha", "pn": "CMD283C3", "type": "LNA", "gain_db": 20.0, "nf_db": 2.2,
             "op1db_dbm": 20.0, "oip3_dbm": 32.0, "oip2_dbm": 52.0, "opmax_dbm": 249.0},
            {"id": "s5", "name": "Diplexer Sub-Bandas", "pn": "DPX-2000", "type": "Diplexer", "gain_db": -1.5,
             "nf_db": 1.5, "op1db_dbm": 40.0, "oip3_dbm": 249.0, "oip2_dbm": 249.0, "opmax_dbm": 249.0},
            {"id": "s6", "name": "Módulo Downconverter", "pn": "HMC7044-DC", "type": "Downconverter", "gain_db": 12.0,
             "nf_db": 6.5, "op1db_dbm": 7.0, "oip3_dbm": 17.0, "oip2_dbm": 37.0, "opmax_dbm": 10.0},
        ]
    else:
        for s in st.session_state.stages:
            if "id" not in s:
                s["id"] = str(uuid.uuid4())[:8]
            if "pn" not in s:
                s["pn"] = "N/A"

    # QR
    st.sidebar.markdown("---")
    st.sidebar.subheader("📱 Acceso Móvil / QR")
    app_url = "https://apprfcascade-e2yarkcbf6pohnlcedr5mx.streamlit.app/"
    try:
        qr_buf = generate_qr_code_bytes(app_url)
        st.sidebar.image(qr_buf, caption="Escanea para abrir el simulador", use_container_width=True)
        st.sidebar.markdown(f"[🔗 Enlace Directo]({app_url})")
    except Exception:
        st.sidebar.markdown(f"**URL:** {app_url}")

    _, temp_summary = compute_cascade_v4(
        st.session_state.stages, b_rf_mhz, b_video_mhz, snr_min_db, pin_rf_dbm, temp_kelvin, f_calc_ghz
    )
    is_saturated_list = temp_summary.get("is_saturated", [False] * len(st.session_state.stages))

    st.subheader(f"🧩 Diagrama Esquemático de la Cadena [f_calc = {f_calc_ghz:.2f} GHz | T = {temp_kelvin:.1f} K]")
    render_block_diagram_v4(st.session_state.stages, is_saturated_list, f_calc_ghz, temp_kelvin)

    st.subheader("🔀 Reordenamiento y Configuración de Componentes")
    st.caption(
        "💡 **Cálculos de Entrada:** IP1dB = OP1dB - G | IIP3 = OIP3 - G | IIP2 = OIP2 - G. Para componentes pasivas NF = |G| se actualiza en tiempo real.")

    col_w = [0.5, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.5]
    h0, h1, h2, h3, h4, h5, h6, h7, h8, h9 = st.columns(col_w)
    h0.markdown("**#**")
    h1.markdown("**Nombre / PN**")
    h2.markdown("**G (dB)**")
    h3.markdown("**NF (dB)**")
    h4.markdown("**OP1 / IP1**")
    h5.markdown("**OIP3 / IIP3**")
    h6.markdown("**OIP2 / IIP2**")
    h7.markdown("**OPmax**")
    h8.markdown("**Tipo**")
    h9.markdown("**Mover / Quitar**")

    warn_passive_gain = False

    for i in range(len(st.session_state.stages)):
        stg = st.session_state.stages[i]
        stg_id = stg["id"]
        is_stg_passive = is_passive_component(stg.get("type", ""), stg.get("name", ""))

        c0, c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns(col_w)
        c0.markdown(f"**E{i + 1}**")

        # Nombre y PN editable en línea
        stg['name'] = c1.text_input("Nombre", value=stg['name'], key=f"name_{stg_id}", label_visibility="collapsed")
        stg['pn'] = c1.text_input("PN", value=stg.get('pn', 'N/A'), key=f"pn_{stg_id}", label_visibility="collapsed")

        # Reactividad instantánea para pasivas
        if is_stg_passive:
            cur_g = float(stg["gain_db"])
            in_g = c2.number_input("G", value=cur_g, key=f"g_{stg_id}", label_visibility="collapsed")
            if in_g > 0:
                in_g = -abs(in_g)
                warn_passive_gain = True
            stg["gain_db"] = in_g
            stg["nf_db"] = abs(in_g)
            # Valor reactivo forzado en tiempo real
            c3.number_input("NF", value=float(abs(in_g)), disabled=True, key=f"nf_{stg_id}",
                            label_visibility="collapsed")
        else:
            stg['gain_db'] = c2.number_input("G", value=float(stg['gain_db']), key=f"g_{stg_id}",
                                             label_visibility="collapsed")
            stg['nf_db'] = c3.number_input("NF", value=float(stg['nf_db']), min_value=0.0, key=f"nf_{stg_id}",
                                           label_visibility="collapsed")

        # Parámetros de salida e información implícita de entrada
        stg['op1db_dbm'] = c4.number_input("OP1", value=float(stg.get('op1db_dbm', 30.0)), key=f"op1_{stg_id}",
                                           label_visibility="collapsed")
        calc_ip1_val = stg['op1db_dbm'] - stg['gain_db']
        c4.caption(f"IP1: {calc_ip1_val:+.1f}dBm")

        stg['oip3_dbm'] = c5.number_input("OIP3", value=float(stg.get('oip3_dbm', 249.0)), key=f"oip3_{stg_id}",
                                          label_visibility="collapsed")
        calc_iip3_val = stg['oip3_dbm'] - stg['gain_db']
        c5.caption(f"IIP3: {calc_iip3_val:+.1f}dBm")

        stg['oip2_dbm'] = c6.number_input("OIP2", value=float(stg.get('oip2_dbm', 249.0)), key=f"oip2_{stg_id}",
                                          label_visibility="collapsed")
        calc_iip2_val = stg['oip2_dbm'] - stg['gain_db']
        c6.caption(f"IIP2: {calc_iip2_val:+.1f}dBm")

        stg['opmax_dbm'] = c7.number_input("OPmax", value=float(stg.get('opmax_dbm', 249.0)), key=f"opmax_{stg_id}",
                                           label_visibility="collapsed")

        tag_color = "#4FD1C5" if is_stg_passive else "#F6AD55"
        tag_label = "Pasivo" if is_stg_passive else "Activo"
        c8.markdown(f"<span style='font-size:11px;color:{tag_color}'>[{tag_label}]<br>{stg['type']}</span>",
                    unsafe_allow_html=True)

        btn_col1, btn_col2, btn_col3 = c9.columns(3)
        if i > 0:
            if btn_col1.button("⬅️", key=f"up_{stg_id}", help="Mover hacia Antena"):
                st.session_state.stages[i], st.session_state.stages[i - 1] = st.session_state.stages[i - 1], \
                st.session_state.stages[i]
                st.rerun()
        if i < len(st.session_state.stages) - 1:
            if btn_col2.button("➡️", key=f"down_{stg_id}", help="Mover hacia Salida"):
                st.session_state.stages[i], st.session_state.stages[i + 1] = st.session_state.stages[i + 1], \
                st.session_state.stages[i]
                st.rerun()
        if btn_col3.button("❌", key=f"del_{stg_id}", help="Eliminar etapa"):
            st.session_state.stages.pop(i)
            st.rerun()

    if warn_passive_gain:
        st.warning(
            "⚠️ **Aviso de signo:** En componentes pasivas la ganancia representa pérdidas de inserción y se forzó a negativo (-X.X dB).")

    if st.button("🗑️ Vaciar Toda la Cadena"):
        st.session_state.stages = []
        st.rerun()

    if not st.session_state.stages:
        st.info("La cadena está vacía. Añade componentes para calcular.")
        return

    results_df, summary = compute_cascade_v4(
        st.session_state.stages, b_rf_mhz, b_video_mhz, snr_min_db, pin_rf_dbm, temp_kelvin, f_calc_ghz
    )

    st.markdown("---")
    st.subheader(f"📌 Métricas Clave [@ f_calc = {f_calc_ghz:.2f} GHz | T = {temp_kelvin:.1f} K]")

    if any(summary["is_saturated"]):
        sat_names = [results_df.loc[i, "Etapa"] for i, sat in enumerate(summary["is_saturated"]) if sat]
        st.error(
            f"🚨 **¡SATURACIÓN DETECTADA!** Etapas en compresión con Pin = {pin_rf_dbm} dBm: **{', '.join(sat_names)}**.")
    else:
        st.success(f"✅ **Operación Lineal Verificada:** Sin compresión para Pin = {pin_rf_dbm} dBm.")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Frecuencia f_calc", f"{f_calc_ghz:.2f} GHz")
    m2.metric("Temperatura T", f"{temp_kelvin:.1f} K")
    m3.metric("Ganancia Total", f"{summary['total_gain_db']:.2f} dB")
    m4.metric("NF Friis Total", f"{summary['total_nf_db']:.2f} dB")
    m5.metric("I-P1dB Calc Acum", f"{summary['total_ip1db_dbm']:.1f} dBm")

    m6, m7, m8, m9, m10 = st.columns(5)
    m6.metric("O-P1dB Salida", f"{summary['total_op1db_dbm']:.1f} dBm")
    m7.metric("OIP3 Salida", f"{summary['total_oip3_dbm']:.1f} dBm")
    m8.metric("OIP2 Salida", f"{summary['total_oip2_dbm']:.1f} dBm")
    m9.metric("Sensibilidad MDS", f"{summary['mds_rf_dbm']:.1f} dBm")
    m10.metric("Rango Dinámico SFDR", f"{summary['sfdr_db']:.1f} dB")

    st.markdown("---")
    st.subheader("📈 Gráfica de Cascada con Parámetro Seleccionable")

    param_options = {
        "Psig": {"col": "Psig [dBm]", "y_label": "Nivel de Señal de RF (dBm)", "color": "#29B6F6", "unit": "dBm"},
        "NF Friis": {"col": "NF Acum Friis [dB]", "y_label": "Figura de Ruido Acumulada Friis (dB)", "color": "#FF5252",
                     "unit": "dB"},
        "NF Etapa": {"col": "NF Etapa [dB]", "y_label": "Figura de Ruido Nominal de la Etapa (dB)", "color": "#FF7A00",
                     "unit": "dB"},
        "Gain": {"col": "Gain Acum [dB]", "y_label": "Ganancia Acumulada (dB)", "color": "#00E676", "unit": "dB"},
        "OIP2": {"col": "OIP2 Acum [dBm]", "y_label": "Punto de Intercepción OIP2 Acumulado (dBm)", "color": "#E040FB",
                 "unit": "dBm"},
        "OIP3": {"col": "OIP3 Acum [dBm]", "y_label": "Punto de Intercepción OIP3 Acumulado (dBm)", "color": "#AB47BC",
                 "unit": "dBm"},
        "Pnoise": {"col": "Pnoise [dBm]", "y_label": "Piso de Ruido Térmico Integrado (dBm)", "color": "#90A4AE",
                   "unit": "dBm"},
        "SNR": {"col": "SNR [dB]", "y_label": "Relación Señal a Ruido SNR (dB)", "color": "#FFD600", "unit": "dB"},
        "OP1db": {"col": "OP1 Acum [dBm]", "y_label": "Límite de Compresión OP1dB (dBm)", "color": "#FF9800",
                  "unit": "dBm"},
        "PMaxLimited": {"col": "PMaxLimited [dBm]", "y_label": "Potencia Máxima Limitada (dBm)", "color": "#D50000",
                        "unit": "dBm"}
    }

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        selected_param = st.selectbox("Selecciona el parámetro a graficar:", options=list(param_options.keys()),
                                      index=0)
    with col_sel2:
        param_info = param_options[selected_param]
        st.info(f"Visualizando: **{param_info['y_label']}** | @ **{f_calc_ghz:.2f} GHz, {temp_kelvin:.1f} K**")

    stage_names = [f"E{i + 1}: {s['name']}" for i, s in enumerate(st.session_state.stages)]
    y_values = results_df[param_info["col"]].values

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=stage_names, y=y_values, mode="lines+markers+text", name=selected_param,
        text=[f"{v:.1f} {param_info['unit']}" for v in y_values], textposition="top center",
        marker=dict(size=12, color=param_info["color"], line=dict(width=2, color="#FFFFFF")),
        line=dict(color=param_info["color"], width=3)
    ))

    # Trazas de referencia en la gráfica Psig: Límite OP1, Umbral IP1dB de la Etapa y Piso de Ruido
    if selected_param == "Psig":
        fig.add_trace(go.Scatter(
            x=stage_names, y=results_df["OP1 Acum [dBm]"], mode="lines+markers",
            name="Límite OP1dB Salida", line=dict(color="#FF9800", width=2, dash="dash")
        ))
        fig.add_trace(go.Scatter(
            x=stage_names, y=results_df["IP1dB Entrada [dBm]"], mode="lines+markers",
            name="Saturación IP1dB Entrada (Etapa)", line=dict(color="#E53E3E", width=2, dash="dot")
        ))
        fig.add_trace(go.Scatter(
            x=stage_names, y=results_df["Pnoise [dBm]"], mode="lines",
            name="Piso Ruido Pnoise", line=dict(color="#90A4AE", width=2, dash="dot")
        ))

    if selected_param == "NF Friis":
        fig.add_trace(go.Scatter(
            x=stage_names, y=results_df["NF Etapa [dB]"], mode="lines+markers",
            name="NF Nominal Etapa", line=dict(color="#FFB300", width=2, dash="dash")
        ))

    fig.update_layout(
        title=f"Evolución de {param_info['y_label']} en la Cadena [f_calc = {f_calc_ghz:.2f} GHz | T = {temp_kelvin:.1f} K | Pin = {pin_rf_dbm} dBm]",
        xaxis_title="Etapas del Front-End Receiver",
        yaxis_title=param_info['y_label'],
        hovermode="x unified",
        template="plotly_dark",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader(f"📑 Tabla Resumen de Etapas [@ f_calc = {f_calc_ghz:.2f} GHz | T = {temp_kelvin:.1f} K]")
    st.dataframe(results_df, use_container_width=True)

    csv_data = results_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"📥 Exportar Tabla Completa con PNs @ {f_calc_ghz:.2f}GHz & {temp_kelvin:.0f}K (CSV)",
        data=csv_data,
        file_name=f"cascada_fer_{f_calc_ghz:.2f}GHz_{temp_kelvin:.0f}K.csv",
        mime="text/csv"
    )


if __name__ == "__main__":
    main()