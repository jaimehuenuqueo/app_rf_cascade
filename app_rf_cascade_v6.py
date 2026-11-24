# """
# Simulador Interactivo de Cascada de RF para Front-End Receiver (FER) - Versión 6
# Autor: Jaime | Libro: Fundamentos y Diseño de Sistemas de Guerra Electrónica / ESM
#
# Nuevas características:
# - Nuevas componentes integradas: Módulo Downconverter, UpConverter, Diplexer y Triplexer.
# - Downconverter modelado como etapa activa con ganancia de conversión, NF, IIP3 y rango de potencia de entrada.
# - Parámetros de operación: f_calc (GHz/MHz) y Temperatura T (Kelvin/°C) con recálculo de k*T*B.
# - Trazabilidad en gráficos, tablas y exportables CSV con columnas de Frecuencia y Temperatura.
# - Selector interactivo de parámetro a graficar: Gain, NF, OIP2, OIP3, Psig, Pnoise, SNR, OP1db, PMaxLimited.
# - Desempaquetado correcto de columnas en Streamlit para evitar AttributeError.
# """
#
# import numpy as np
# import pandas as pd
# import plotly.graph_objects as go
# import io
# import qrcode
# from PIL import Image
# import streamlit as st
#
# st.set_page_config(
#     page_title="Simulador FER v4.2 - Jaime",
#     page_icon="📡",
#     layout="wide"
# )
#
# K_BOLTZMANN = 1.380649e-23  # J/K
#
# def generate_qr_code(url: str):
#     """Genera una imagen PIL con el código QR de la URL indicada."""
#     qr = qrcode.QRCode(
#         version=1,
#         error_correction=qrcode.constants.ERROR_CORRECT_M,
#         box_size=10,
#         border=2,
#     )
#     qr.add_data(url)
#     qr.make(fit=True)
#     img = qr.make_image(fill_color="#1A365D", back_color="#FFFFFF")
#     return img
#
# def generate_qr_code_bytes(url: str):
#     """Genera un búfer de bytes PNG listo para Streamlit."""
#     qr = qrcode.QRCode(
#         version=1,
#         error_correction=qrcode.constants.ERROR_CORRECT_M,
#         box_size=8,
#         border=2,
#     )
#     qr.add_data(url)
#     qr.make(fit=True)
#
#     # Generar la imagen y convertirla explícitamente a RGB
#     img = qr.make_image(fill_color="#1A365D", back_color="#FFFFFF").convert("RGB")
#
#     # Guardar en un búfer en memoria en formato PNG
#     buf = io.BytesIO()
#     img.save(buf, format="PNG")
#     buf.seek(0)
#     return buf
#
# def db_to_lin(val_db):
#     return 10.0 ** (val_db / 10.0)
#
#
# def lin_to_db(val_lin):
#     return 10.0 * np.log10(np.maximum(val_lin, 1e-20))
#
#
# def dbm_to_mw(val_dbm):
#     return 10.0 ** (val_dbm / 10.0)
#
#
# def mw_to_dbm(val_mw):
#     return 10.0 * np.log10(np.maximum(val_mw, 1e-20))
#
#
# def compute_noise_power_density_dbm_mhz(temp_kelvin):
#     p_noise_w_per_hz = K_BOLTZMANN * temp_kelvin
#     p_noise_mw_per_hz = p_noise_w_per_hz * 1e3
#     p_noise_dbm_per_hz = 10.0 * np.log10(np.maximum(p_noise_mw_per_hz, 1e-30))
#     return p_noise_dbm_per_hz + 60.0
#
#
# def compute_cascade_v4(stages, b_rf_mhz, b_video_mhz, snr_min_db, pin_rf_dbm, temp_kelvin, f_calc_ghz):
#     if not stages:
#         return pd.DataFrame(), {}
#
#     n = len(stages)
#     cum_gain_db = np.zeros(n)
#     cum_nf_db = np.zeros(n)
#     cum_iip3_dbm = np.zeros(n)
#     cum_oip3_dbm = np.zeros(n)
#     cum_iip2_dbm = np.zeros(n)
#     cum_oip2_dbm = np.zeros(n)
#     cum_ip1db_dbm = np.zeros(n)
#     cum_op1db_dbm = np.zeros(n)
#     sig_level_dbm = np.zeros(n)
#     noise_floor_dbm = np.zeros(n)
#     snr_stage_db = np.zeros(n)
#     pmax_limited_dbm = np.zeros(n)
#     is_saturated = [False] * n
#
#     kt0_dbm_mhz = compute_noise_power_density_dbm_mhz(temp_kelvin)
#
#     g_lin_cum = 1.0
#     f_lin_cum = 0.0
#     inv_iip3_mw = 0.0
#     inv_iip2_mw = 0.0
#     inv_ip1db_mw = 0.0
#     running_pmax_limited = 999.0
#
#     for i, stg in enumerate(stages):
#         g_i_db = float(stg["gain_db"])
#         nf_i_db = float(stg["nf_db"])
#         ip1db_i_dbm = float(stg["ip1db_dbm"])
#         iip3_i_dbm = float(stg.get("iip3_dbm", ip1db_i_dbm + 12.0))
#         iip2_i_dbm = float(stg.get("iip2_dbm", iip3_i_dbm + 20.0))
#         pmax_limit_stage = float(stg.get("pmax_limit_dbm", 999.0))
#
#         g_i_lin = db_to_lin(g_i_db)
#         f_i_lin = db_to_lin(nf_i_db)
#         iip3_i_mw = dbm_to_mw(iip3_i_dbm)
#         iip2_i_mw = dbm_to_mw(iip2_i_dbm)
#         ip1db_i_mw = dbm_to_mw(ip1db_i_dbm)
#
#         if i == 0:
#             g_lin_cum = g_i_lin
#             f_lin_cum = f_i_lin
#             inv_iip3_mw = 1.0 / iip3_i_mw
#             inv_iip2_mw = 1.0 / iip2_i_mw
#             inv_ip1db_mw = 1.0 / ip1db_i_mw
#         else:
#             f_lin_cum += (f_i_lin - 1.0) / g_lin_cum
#             inv_iip3_mw += g_lin_cum / iip3_i_mw
#             inv_iip2_mw += (g_lin_cum ** 2) / iip2_i_mw
#             inv_ip1db_mw += g_lin_cum / ip1db_i_mw
#             g_lin_cum *= g_i_lin
#
#         cum_gain_db[i] = lin_to_db(g_lin_cum)
#         cum_nf_db[i] = lin_to_db(f_lin_cum)
#         cum_iip3_dbm[i] = mw_to_dbm(1.0 / inv_iip3_mw)
#         cum_oip3_dbm[i] = cum_iip3_dbm[i] + cum_gain_db[i]
#         cum_iip2_dbm[i] = mw_to_dbm(1.0 / inv_iip2_mw)
#         cum_oip2_dbm[i] = cum_iip2_dbm[i] + cum_gain_db[i]
#         cum_ip1db_dbm[i] = mw_to_dbm(1.0 / inv_ip1db_mw)
#         cum_op1db_dbm[i] = cum_ip1db_dbm[i] + cum_gain_db[i]
#
#         sig_level_dbm[i] = pin_rf_dbm + cum_gain_db[i]
#         noise_floor_dbm[i] = kt0_dbm_mhz + 10.0 * np.log10(b_rf_mhz) + cum_nf_db[i] + cum_gain_db[i]
#         snr_stage_db[i] = sig_level_dbm[i] - noise_floor_dbm[i]
#
#         if pmax_limit_stage < 900.0:
#             running_pmax_limited = min(running_pmax_limited + g_i_db, pmax_limit_stage)
#         else:
#             running_pmax_limited = running_pmax_limited + g_i_db
#         pmax_limited_dbm[i] = min(running_pmax_limited, cum_op1db_dbm[i])
#
#         # Verificación de saturación incluyendo rango máximo de entrada en Downconverter
#         pin_stage = sig_level_dbm[i] - g_i_db
#         pin_max_stg = float(stg.get("pin_max_dbm", 999.0))
#         if sig_level_dbm[i] >= cum_op1db_dbm[i] or (
#                 pmax_limit_stage < 900.0 and sig_level_dbm[i] >= pmax_limit_stage) or (pin_stage > pin_max_stg):
#             is_saturated[i] = True
#
#     total_nf = cum_nf_db[-1]
#     total_gain = cum_gain_db[-1]
#     total_iip3 = cum_iip3_dbm[-1]
#     total_oip3 = cum_oip3_dbm[-1]
#     total_iip2 = cum_iip2_dbm[-1]
#     total_oip2 = cum_oip2_dbm[-1]
#     total_ip1db = cum_ip1db_dbm[-1]
#     total_op1db = cum_op1db_dbm[-1]
#
#     mds_rf_dbm = kt0_dbm_mhz + 10.0 * np.log10(b_rf_mhz) + total_nf + snr_min_db
#     term_inside = 2.5 * b_video_mhz + 4.0 * np.sqrt(np.maximum(2.0 * b_rf_mhz * b_video_mhz - (b_video_mhz ** 2), 1e-6))
#     tss_video_dbm = kt0_dbm_mhz + total_nf + 10.0 * np.log10(np.maximum(term_inside, 1e-6))
#     sfdr_db = (2.0 / 3.0) * (total_iip3 - (kt0_dbm_mhz + 10.0 * np.log10(b_rf_mhz) + total_nf))
#     idr_db = total_ip1db - mds_rf_dbm
#
#     df_results = pd.DataFrame({
#         "Etapa": [f"{i + 1}. {s['name']}" for i, s in enumerate(stages)],
#         "Tipo": [s["type"] for s in stages],
#         "Frecuencia (GHz)": [f_calc_ghz] * n,
#         "Temp (K)": [temp_kelvin] * n,
#         "G [dB]": [s["gain_db"] for s in stages],
#         "NF [dB]": [s["nf_db"] for s in stages],
#         "P1dB [dBm]": [s["ip1db_dbm"] for s in stages],
#         "IIP3 [dBm]": [s.get("iip3_dbm", s["ip1db_dbm"] + 12.0) for s in stages],
#         "Gain Acum [dB]": np.round(cum_gain_db, 2),
#         "NF Acum [dB]": np.round(cum_nf_db, 2),
#         "OP1dB [dBm]": np.round(cum_op1db_dbm, 2),
#         "OIP3 [dBm]": np.round(cum_oip3_dbm, 2),
#         "OIP2 [dBm]": np.round(cum_oip2_dbm, 2),
#         "Psig [dBm]": np.round(sig_level_dbm, 2),
#         "Pnoise [dBm]": np.round(noise_floor_dbm, 2),
#         "SNR [dB]": np.round(snr_stage_db, 2),
#         "PMaxLimited [dBm]": np.round(pmax_limited_dbm, 2),
#         "Estado": ["⚠️ SATURADO" if sat else "✅ Lineal" for sat in is_saturated]
#     })
#
#     summary = {
#         "f_calc_ghz": f_calc_ghz,
#         "temp_kelvin": temp_kelvin,
#         "total_gain_db": total_gain,
#         "total_nf_db": total_nf,
#         "total_ip1db_dbm": total_ip1db,
#         "total_op1db_dbm": total_op1db,
#         "total_iip3_dbm": total_iip3,
#         "total_oip3_dbm": total_oip3,
#         "total_iip2_dbm": total_iip2,
#         "total_oip2_dbm": total_oip2,
#         "mds_rf_dbm": mds_rf_dbm,
#         "tss_video_dbm": tss_video_dbm,
#         "sfdr_db": sfdr_db,
#         "idr_db": idr_db,
#         "cum_gain_db": cum_gain_db,
#         "cum_nf_db": cum_nf_db,
#         "cum_op1db_dbm": cum_op1db_dbm,
#         "cum_oip3_dbm": cum_oip3_dbm,
#         "cum_oip2_dbm": cum_oip2_dbm,
#         "sig_level_dbm": sig_level_dbm,
#         "noise_floor_dbm": noise_floor_dbm,
#         "snr_stage_db": snr_stage_db,
#         "pmax_limited_dbm": pmax_limited_dbm,
#         "is_saturated": is_saturated,
#     }
#
#     return df_results, summary
#
#
# def render_block_diagram_v4(stages, is_saturated, f_calc_ghz, temp_kelvin):
#     if not stages:
#         return
#
#     cards = []
#     for i, s in enumerate(stages):
#         sat = is_saturated[i] if i < len(is_saturated) else False
#         bg = "#4A1515" if sat else "#1A365D"
#         border = "#E53E3E" if sat else "#3182CE"
#         badge = "⚠️ SATURADO" if sat else "✅ Lineal"
#         bcolor = "#FEB2B2" if sat else "#9AE6B4"
#
#         stype = s["type"]
#         icon = "📡" if "Antena" in stype else ("🔄" if "Downconverter" in stype or "UpConverter" in stype else (
#             "🔀" if "plexer" in stype else ("〰️" if "Cable" in stype else "📦")))
#
#         card_html = (
#             f'<div style="display:inline-block; vertical-align:top; background:{bg}; '
#             f'border:2px solid {border}; border-radius:8px; padding:10px 12px; min-width:145px; '
#             f'text-align:center; box-shadow:0 4px 6px rgba(0,0,0,0.3); margin:0 4px;">'
#             f'<div style="font-size:10px; color:#A0AEC0; font-weight:bold; text-transform:uppercase;">ETAPA {i + 1}</div>'
#             f'<div style="font-size:13px; color:#FFFFFF; font-weight:bold; margin:3px 0;">{icon} {s["name"]}</div>'
#             f'<div style="font-size:10px; color:#CBD5E0; background:rgba(0,0,0,0.25); padding:2px 4px; border-radius:4px; margin-bottom:4px;">{s["type"]}</div>'
#             f'<div style="font-size:11px; color:#90CDF4; font-family:monospace;">G:{s["gain_db"]:+.1f}dB | NF:{s["nf_db"]:.1f}dB</div>'
#             f'<div style="font-size:10px; font-weight:bold; color:{bcolor}; margin-top:4px;">{badge}</div>'
#             f'</div>'
#         )
#         cards.append(card_html)
#
#     arrow_html = '<div style="display:inline-block; vertical-align:middle; color:#63B3ED; font-weight:bold; font-size:16px; margin:0 2px;">▶</div>'
#
#     diagram_html = (
#             '<div style="display:block; overflow-x:auto; white-space:nowrap; padding:15px; '
#             'background:#1A202C; border-radius:10px; border:1px solid #2D3748; margin-bottom:20px;">'
#             + arrow_html.join(cards) +
#             arrow_html +
#             '<div style="display:inline-block; vertical-align:top; background:#2D3748; border:1px solid #4A5568; '
#             'border-radius:8px; padding:10px 14px; min-width:110px; text-align:center;">'
#             '<div style="font-size:10px; color:#A0AEC0; font-weight:bold;">DESTINO</div>'
#             '<div style="font-size:13px; color:#FFFFFF; font-weight:bold; margin-top:3px;">🎯 Salida FER</div>'
#             f'<div style="font-size:10px; color:#90CDF4;">@{f_calc_ghz:.2f}GHz, {temp_kelvin:.1f}K</div>'
#             '</div>'
#             '</div>'
#     )
#     st.markdown(diagram_html, unsafe_allow_html=True)
#
#
# def main():
#     st.title("📡 Simulador de Cascada de RF - Front-End Receiver (FER) V6.0")
#     st.caption("Autor: *Jaime Huenuqueo Salazar* | *Libro: Fundamentos y Diseño de Sistemas de Guerra Electrónica / ESM*")
#
#     st.sidebar.markdown("---")
#     st.sidebar.subheader("📱 Acceso Móvil / Compartir")
#     app_url = "[https://apprfcascade-e2yarkcbf6pohnlcedr5mx.streamlit.app/"
#     qr_buf = generate_qr_code_bytes(app_url)
#     st.sidebar.image(qr_buf, caption="Escanea para abrir el simulador", use_container_width=True)
#     st.sidebar.markdown(f"[🔗 Abrir en el navegador]({app_url})")
#
#     st.sidebar.header("🌐 Cobertura Espectral")
#     col_f1, col_f2 = st.sidebar.columns(2)
#     with col_f1:
#         f_min_ghz = st.number_input("F_min (GHz)", min_value=0.01, max_value=100.0, value=2.0, step=0.5)
#     with col_f2:
#         f_max_ghz = st.number_input("F_max (GHz)", min_value=0.02, max_value=110.0, value=18.0, step=0.5)
#
#     if f_max_ghz <= f_min_ghz:
#         st.sidebar.error("F_max debe ser mayor a F_min")
#         b_rf_mhz = 1000.0
#     else:
#         b_rf_ghz = f_max_ghz - f_min_ghz
#         b_rf_mhz = b_rf_ghz * 1000.0
#         st.sidebar.success(f"**B_RF:** {b_rf_mhz:,.0f} MHz ({b_rf_ghz:.2f} GHz)")
#
#     st.sidebar.markdown("---")
#     st.sidebar.header("⚙️ Parámetros de Operación")
#
#     col_op1, col_op2 = st.sidebar.columns(2)
#     with col_op1:
#         f_calc_ghz = st.number_input("Frecuencia f_calc (GHz)", min_value=float(f_min_ghz), max_value=float(f_max_ghz),
#                                      value=float(min(max(10.0, f_min_ghz), f_max_ghz)), step=0.5, format="%.2f")
#     with col_op2:
#         st.metric("Frecuencia (MHz)", f"{f_calc_ghz * 1000.0:,.0f} MHz")
#
#     col_t1, col_t2 = st.sidebar.columns(2)
#     with col_t1:
#         temp_kelvin = st.number_input("Temperatura T (K)", min_value=1.0, max_value=600.0, value=290.0, step=5.0)
#     with col_t2:
#         st.metric("Temp (°C)", f"{temp_kelvin - 273.15:+.1f} °C")
#
#     kt_val = compute_noise_power_density_dbm_mhz(temp_kelvin)
#     st.sidebar.caption(f"Densidad de ruido térmico k*T: **{kt_val:.2f} dBm/MHz** (a {temp_kelvin:.1f} K)")
#
#     b_video_mhz = st.sidebar.number_input("Ancho Banda Video, B_v (MHz)", min_value=0.1, max_value=200.0, value=10.0,
#                                           step=1.0)
#     snr_min_db = st.sidebar.number_input("SNR mínimo de detección (dB)", min_value=0.0, max_value=30.0, value=12.0,
#                                          step=0.5)
#     pin_rf_dbm = st.sidebar.number_input("Potencia Entrada Pin (dBm)", min_value=-130.0, max_value=30.0, value=-40.0,
#                                          step=5.0)
#
#     # Catálogo ampliado con Downconverter, UpConverter, Diplexer y Triplexer
#     component_templates = {
#         "Módulo Downconverter (Activo)": {"type": "Downconverter", "gain_db": 12.0, "nf_db": 6.5, "ip1db_dbm": -5.0,
#                                           "iip3_dbm": 5.0, "iip2_dbm": 25.0, "pmax_limit": 10.0, "pin_min": -80.0,
#                                           "pin_max": -10.0},
#         "Módulo UpConverter": {"type": "UpConverter", "gain_db": 10.0, "nf_db": 7.0, "ip1db_dbm": -2.0, "iip3_dbm": 8.0,
#                                "iip2_dbm": 28.0, "pmax_limit": 12.0, "pin_min": -70.0, "pin_max": -5.0},
#         "Diplexer (Multiplexor 2 Canales)": {"type": "Diplexer", "gain_db": -1.5, "nf_db": 1.5, "ip1db_dbm": 40.0,
#                                              "iip3_dbm": 55.0, "iip2_dbm": 75.0, "pmax_limit": 40.0, "pin_min": -130.0,
#                                              "pin_max": 30.0},
#         "Triplexer (Multiplexor 3 Canales)": {"type": "Triplexer", "gain_db": -2.2, "nf_db": 2.2, "ip1db_dbm": 40.0,
#                                               "iip3_dbm": 55.0, "iip2_dbm": 75.0, "pmax_limit": 40.0, "pin_min": -130.0,
#                                               "pin_max": 30.0},
#         "Antena ESM (Espiral / Bocina)": {"type": "Antena", "gain_db": 6.0, "nf_db": 0.0, "ip1db_dbm": 50.0,
#                                           "iip3_dbm": 65.0, "iip2_dbm": 85.0, "pmax_limit": 50.0},
#         "Cable Coaxial RF": {"type": "Cable RF", "gain_db": -2.5, "nf_db": 2.5, "ip1db_dbm": 45.0, "iip3_dbm": 60.0,
#                              "iip2_dbm": 80.0, "pmax_limit": 45.0},
#         "Conmutador SPDT": {"type": "Switch SPDT", "gain_db": -1.2, "nf_db": 1.2, "ip1db_dbm": 30.0, "iip3_dbm": 45.0,
#                             "iip2_dbm": 65.0, "pmax_limit": 30.0},
#         "Limitador PIN (Protección)": {"type": "Protección PIN", "gain_db": -1.0, "nf_db": 1.0, "ip1db_dbm": 25.0,
#                                        "iip3_dbm": 40.0, "iip2_dbm": 60.0, "pmax_limit": 15.0},
#         "Amplificador LNA (GaN/GaAs)": {"type": "LNA", "gain_db": 20.0, "nf_db": 2.2, "ip1db_dbm": 0.0,
#                                         "iip3_dbm": 12.0, "iip2_dbm": 32.0, "pmax_limit": 10.0},
#         "Ecualizador de Ganancia": {"type": "Ecualizador", "gain_db": -3.0, "nf_db": 3.0, "ip1db_dbm": 30.0,
#                                     "iip3_dbm": 45.0, "iip2_dbm": 65.0, "pmax_limit": 30.0},
#         "Filtro Preselector": {"type": "Filtro", "gain_db": -2.0, "nf_db": 2.0, "ip1db_dbm": 35.0, "iip3_dbm": 50.0,
#                                "iip2_dbm": 70.0, "pmax_limit": 35.0},
#     }
#
#     st.sidebar.markdown("---")
#     st.sidebar.header("➕ Añadir Etapa")
#     sel_template = st.sidebar.selectbox("Seleccionar Plantilla:", list(component_templates.keys()))
#     t_vals = component_templates[sel_template]
#
#     with st.sidebar.form("add_comp_form", clear_on_submit=True):
#         c_name = st.text_input("Nombre de la Etapa:", value=sel_template)
#         c_type = t_vals["type"]
#         c_gain = st.number_input("Ganancia G (dB):", value=float(t_vals["gain_db"]), step=0.5)
#         c_nf = st.number_input("Figura de Ruido NF (dB):", value=float(t_vals["nf_db"]), min_value=0.0, step=0.5)
#         c_ip1db = st.number_input("I-P1dB (dBm):", value=float(t_vals["ip1db_dbm"]), step=1.0)
#         c_iip3 = st.number_input("IIP3 (dBm):", value=float(t_vals.get("iip3_dbm", 12.0)), step=1.0)
#         c_iip2 = st.number_input("IIP2 (dBm):", value=float(t_vals.get("iip2_dbm", 32.0)), step=1.0)
#         c_pmax = st.number_input("PMaxLimited (dBm):", value=float(t_vals.get("pmax_limit", 20.0)), step=1.0)
#
#         # Parámetros específicos de rango de entrada para Downconverter / UpConverter
#         c_pin_max = st.number_input("Pin Máx Admisible (dBm):", value=float(t_vals.get("pin_max", 999.0)), step=5.0)
#
#         if st.form_submit_button("➕ Insertar Etapa"):
#             if "stages" not in st.session_state:
#                 st.session_state.stages = []
#             st.session_state.stages.append({
#                 "name": c_name, "type": c_type, "gain_db": c_gain, "nf_db": c_nf,
#                 "ip1db_dbm": c_ip1db, "iip3_dbm": c_iip3, "iip2_dbm": c_iip2,
#                 "pmax_limit_dbm": c_pmax, "pin_max_dbm": c_pin_max
#             })
#             st.rerun()
#
#     if "stages" not in st.session_state:
#         st.session_state.stages = [
#             {"name": "Antena Espiral ESM", "type": "Antena", "gain_db": 6.0, "nf_db": 0.0, "ip1db_dbm": 50.0,
#              "iip3_dbm": 65.0, "iip2_dbm": 85.0, "pmax_limit_dbm": 50.0},
#             {"name": "Diplexer Banda Baja/Alta", "type": "Diplexer", "gain_db": -1.5, "nf_db": 1.5, "ip1db_dbm": 40.0,
#              "iip3_dbm": 55.0, "iip2_dbm": 75.0, "pmax_limit_dbm": 40.0},
#             {"name": "Limitador PIN", "type": "Protección PIN", "gain_db": -1.0, "nf_db": 1.0, "ip1db_dbm": 25.0,
#              "iip3_dbm": 40.0, "iip2_dbm": 60.0, "pmax_limit_dbm": 15.0},
#             {"name": "LNA GaN Banda Ancha", "type": "LNA", "gain_db": 20.0, "nf_db": 2.2, "ip1db_dbm": 0.0,
#              "iip3_dbm": 12.0, "iip2_dbm": 32.0, "pmax_limit_dbm": 10.0},
#             {"name": "Filtro Preselector", "type": "Filtro", "gain_db": -2.0, "nf_db": 2.0, "ip1db_dbm": 35.0,
#              "iip3_dbm": 50.0, "iip2_dbm": 70.0, "pmax_limit_dbm": 35.0},
#             {"name": "Módulo Downconverter RF/IF", "type": "Downconverter", "gain_db": 12.0, "nf_db": 6.5,
#              "ip1db_dbm": -5.0, "iip3_dbm": 5.0, "iip2_dbm": 25.0, "pmax_limit_dbm": 10.0, "pin_max_dbm": -10.0},
#         ]
#
#     _, temp_summary = compute_cascade_v4(
#         st.session_state.stages, b_rf_mhz, b_video_mhz, snr_min_db, pin_rf_dbm, temp_kelvin, f_calc_ghz
#     )
#     is_saturated_list = temp_summary.get("is_saturated", [False] * len(st.session_state.stages))
#
#     st.subheader(f"🧩 Diagrama Esquemático de la Cadena [f_calc = {f_calc_ghz:.2f} GHz | T = {temp_kelvin:.1f} K]")
#     render_block_diagram_v4(st.session_state.stages, is_saturated_list, f_calc_ghz, temp_kelvin)
#
#     st.subheader("🔀 Reordenamiento y Configuración de Componentes")
#     col_w = [0.6, 2.2, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.8]
#     h0, h1, h2, h3, h4, h5, h6, h7, h8 = st.columns(col_w)
#     h0.markdown("**#**")
#     h1.markdown("**Nombre / Tipo**")
#     h2.markdown("**G (dB)**")
#     h3.markdown("**NF (dB)**")
#     h4.markdown("**I-P1dB**")
#     h5.markdown("**IIP3**")
#     h6.markdown("**IIP2**")
#     h7.markdown("**PMaxLim**")
#     h8.markdown("**Mover / Quitar**")
#
#     for i in range(len(st.session_state.stages)):
#         stg = st.session_state.stages[i]
#         c0, c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(col_w)
#         c0.markdown(f"**E{i + 1}**")
#         c1.markdown(f"**{stg['name']}**  \n<span style='font-size:11px;color:#888'>{stg['type']}</span>",
#                     unsafe_allow_html=True)
#
#         stg['gain_db'] = c2.number_input("G", value=float(stg['gain_db']), key=f"g_{i}", label_visibility="collapsed")
#         stg['nf_db'] = c3.number_input("NF", value=float(stg['nf_db']), min_value=0.0, key=f"nf_{i}",
#                                        label_visibility="collapsed")
#         stg['ip1db_dbm'] = c4.number_input("P1dB", value=float(stg['ip1db_dbm']), key=f"p1_{i}",
#                                            label_visibility="collapsed")
#         stg['iip3_dbm'] = c5.number_input("IIP3", value=float(stg.get('iip3_dbm', stg['ip1db_dbm'] + 12.0)),
#                                           key=f"ip3_{i}", label_visibility="collapsed")
#         stg['iip2_dbm'] = c6.number_input("IIP2", value=float(stg.get('iip2_dbm', stg['ip1db_dbm'] + 32.0)),
#                                           key=f"ip2_{i}", label_visibility="collapsed")
#         stg['pmax_limit_dbm'] = c7.number_input("PMaxLim", value=float(stg.get('pmax_limit_dbm', 20.0)),
#                                                 key=f"pmax_{i}", label_visibility="collapsed")
#
#         btn_col1, btn_col2, btn_col3 = c8.columns(3)
#         if i > 0:
#             if btn_col1.button("⬅️", key=f"up_{i}", help="Mover hacia Antena"):
#                 st.session_state.stages[i], st.session_state.stages[i - 1] = st.session_state.stages[i - 1], \
#                 st.session_state.stages[i]
#                 st.rerun()
#         if i < len(st.session_state.stages) - 1:
#             if btn_col2.button("➡️", key=f"down_{i}", help="Mover hacia Salida"):
#                 st.session_state.stages[i], st.session_state.stages[i + 1] = st.session_state.stages[i + 1], \
#                 st.session_state.stages[i]
#                 st.rerun()
#         if btn_col3.button("❌", key=f"del_{i}", help="Eliminar etapa"):
#             st.session_state.stages.pop(i)
#             st.rerun()
#
#     if st.button("🗑️ Vaciar Toda la Cadena"):
#         st.session_state.stages = []
#         st.rerun()
#
#     if not st.session_state.stages:
#         st.info("La cadena está vacía. Añade componentes para calcular.")
#         return
#
#     results_df, summary = compute_cascade_v4(
#         st.session_state.stages, b_rf_mhz, b_video_mhz, snr_min_db, pin_rf_dbm, temp_kelvin, f_calc_ghz
#     )
#
#     st.markdown("---")
#     st.subheader(f"📌 Métricas Clave [@ f_calc = {f_calc_ghz:.2f} GHz | T = {temp_kelvin:.1f} K]")
#
#     if any(summary["is_saturated"]):
#         sat_names = [results_df.loc[i, "Etapa"] for i, sat in enumerate(summary["is_saturated"]) if sat]
#         st.error(
#             f"🚨 **¡SATURACIÓN DETECTADA!** Etapas en compresión con Pin = {pin_rf_dbm} dBm: **{', '.join(sat_names)}**.")
#     else:
#         st.success(f"✅ **Operación Lineal Verificada:** Sin compresión para Pin = {pin_rf_dbm} dBm.")
#
#     m1, m2, m3, m4, m5 = st.columns(5)
#     m1.metric("Frecuencia f_calc", f"{f_calc_ghz:.2f} GHz")
#     m2.metric("Temperatura T", f"{temp_kelvin:.1f} K")
#     m3.metric("Ganancia Total", f"{summary['total_gain_db']:.2f} dB")
#     m4.metric("NF Friis Total", f"{summary['total_nf_db']:.2f} dB")
#     m5.metric("I-P1dB Acum", f"{summary['total_ip1db_dbm']:.1f} dBm")
#
#     m6, m7, m8, m9, m10 = st.columns(5)
#     m6.metric("O-P1dB Salida", f"{summary['total_op1db_dbm']:.1f} dBm")
#     m7.metric("OIP3 Salida", f"{summary['total_oip3_dbm']:.1f} dBm")
#     m8.metric("OIP2 Salida", f"{summary['total_oip2_dbm']:.1f} dBm")
#     m9.metric("Sensibilidad MDS", f"{summary['mds_rf_dbm']:.1f} dBm")
#     m10.metric("Rango Dinámico SFDR", f"{summary['sfdr_db']:.1f} dB")
#
#     st.markdown("---")
#     st.subheader("📈 Gráfica de Cascada con Parámetro Seleccionable")
#
#     param_options = {
#         "Gain": {"col": "Gain Acum [dB]", "y_label": "Ganancia Acumulada (dB)", "color": "#00E676", "unit": "dB"},
#         "NF": {"col": "NF Acum [dB]", "y_label": "Figura de Ruido Acumulada Friis (dB)", "color": "#FF5252",
#                "unit": "dB"},
#         "OIP2": {"col": "OIP2 [dBm]", "y_label": "Punto de Intercepción OIP2 (dBm)", "color": "#E040FB", "unit": "dBm"},
#         "OIP3": {"col": "OIP3 [dBm]", "y_label": "Punto de Intercepción OIP3 (dBm)", "color": "#AB47BC", "unit": "dBm"},
#         "Psig": {"col": "Psig [dBm]", "y_label": "Nivel de Señal de RF (dBm)", "color": "#29B6F6", "unit": "dBm"},
#         "Pnoise": {"col": "Pnoise [dBm]", "y_label": "Piso de Ruido Térmico Integrado (dBm)", "color": "#90A4AE",
#                    "unit": "dBm"},
#         "SNR": {"col": "SNR [dB]", "y_label": "Relación Señal a Ruido SNR (dB)", "color": "#FFD600", "unit": "dB"},
#         "OP1db": {"col": "OP1dB [dBm]", "y_label": "Límite de Compresión O-P1dB (dBm)", "color": "#FF9800",
#                   "unit": "dBm"},
#         "PMaxLimited": {"col": "PMaxLimited [dBm]", "y_label": "Potencia Máxima Limitada (dBm)", "color": "#D50000",
#                         "unit": "dBm"}
#     }
#
#     col_sel1, col_sel2 = st.columns(2)
#     with col_sel1:
#         selected_param = st.selectbox("Selecciona el parámetro a graficar:", options=list(param_options.keys()),
#                                       index=0)
#     with col_sel2:
#         param_info = param_options[selected_param]
#         st.info(f"Visualizando: **{param_info['y_label']}** | @ **{f_calc_ghz:.2f} GHz, {temp_kelvin:.1f} K**")
#
#     stage_names = [f"E{i + 1}: {s['name']}" for i, s in enumerate(st.session_state.stages)]
#     y_values = results_df[param_info["col"]].values
#
#     fig = go.Figure()
#     fig.add_trace(go.Scatter(
#         x=stage_names, y=y_values, mode="lines+markers+text", name=selected_param,
#         text=[f"{v:.1f} {param_info['unit']}" for v in y_values], textposition="top center",
#         marker=dict(size=12, color=param_info["color"], line=dict(width=2, color="#FFFFFF")),
#         line=dict(color=param_info["color"], width=3)
#     ))
#
#     if selected_param == "Psig":
#         fig.add_trace(go.Scatter(x=stage_names, y=results_df["OP1dB [dBm]"], mode="lines", name="Límite OP1dB",
#                                  line=dict(color="#FF9800", width=2, dash="dash")))
#         fig.add_trace(go.Scatter(x=stage_names, y=results_df["Pnoise [dBm]"], mode="lines", name="Piso Ruido Pnoise",
#                                  line=dict(color="#90A4AE", width=2, dash="dot")))
#
#     fig.update_layout(
#         title=f"Evolución de {param_info['y_label']} en la Cadena [f_calc = {f_calc_ghz:.2f} GHz | T = {temp_kelvin:.1f} K | Pin = {pin_rf_dbm} dBm]",
#         xaxis_title="Etapas del Front-End Receiver",
#         yaxis_title=param_info['y_label'],
#         hovermode="x unified",
#         template="plotly_dark",
#         height=500,
#         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
#     )
#     st.plotly_chart(fig, use_container_width=True)
#
#     st.markdown("---")
#     st.subheader(f"📑 Tabla Resumen de Etapas [@ f_calc = {f_calc_ghz:.2f} GHz | T = {temp_kelvin:.1f} K]")
#     st.dataframe(results_df, use_container_width=True)
#
#     csv_data = results_df.to_csv(index=False).encode('utf-8')
#     st.download_button(
#         label=f"📥 Exportar Tabla Completa @ {f_calc_ghz:.2f}GHz & {temp_kelvin:.0f}K (CSV)",
#         data=csv_data,
#         file_name=f"cascada_fer_{f_calc_ghz:.2f}GHz_{temp_kelvin:.0f}K.csv",
#         mime="text/csv"
#     )
#
#
# if __name__ == "__main__":
#     main()
"""
Simulador Interactivo de Cascada de RF para Front-End Receiver (FER) - Versión 6.3
Autor: Jaime Huenuqueo Salazar| Libro: Fundamentos y Diseño de Sistemas de Guerra Electrónica / ESM

Correcciones v4.3:
1. Reordenamiento con UUID persistente por etapa: los valores no se pierden ni se cruzan.
2. Ingreso de parámetros de no linealidad referidos a la salida: OP1, OIP3, OIP2 y OPmax (por defecto 249 dBm).
3. Cálculo automático de IIP2, IIP3, IP1 y propagación de Friis.
4. Desglose en tabla y gráfica de NF individual de cada componente y NF Acumulada Friis.
5. Nuevas componentes añadidas: Power Divider 1:2, Power Divider 1:4, SP3T, SP4T y Atenuador.
"""

import io
import uuid
import qrcode
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Simulador FER v4.3 - Jaime",
    page_icon="📡",
    layout="wide"
)

K_BOLTZMANN = 1.380649e-23  # J/K


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
        nf_i_db = float(stg["nf_db"])

        # El usuario ingresa OP1, OIP3, OIP2 y OPmax
        op1_i_dbm = float(stg.get("op1db_dbm", 30.0))
        oip3_i_dbm = float(stg.get("oip3_dbm", op1_i_dbm + 12.0))
        oip2_i_dbm = float(stg.get("oip2_dbm", oip3_i_dbm + 20.0))
        opmax_stage = float(stg.get("opmax_dbm", 249.0))

        # Cálculo automático de los equivalentes referidos a la entrada
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
            # Fórmula rigurosa de Friis
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
        "Tipo": [s["type"] for s in stages],
        "Frecuencia (GHz)": [f_calc_ghz] * n,
        "Temp (K)": [temp_kelvin] * n,
        "G [dB]": [s["gain_db"] for s in stages],
        "NF Etapa [dB]": [s["nf_db"] for s in stages],
        "OP1 [dBm]": [s.get("op1db_dbm", 30.0) for s in stages],
        "OIP3 [dBm]": [s.get("oip3_dbm", 42.0) for s in stages],
        "OIP2 [dBm]": [s.get("oip2_dbm", 62.0) for s in stages],
        "OPmax [dBm]": [s.get("opmax_dbm", 249.0) for s in stages],
        "Calc IP1 [dBm]": np.round(calc_ip1_list, 2),
        "Calc IIP3 [dBm]": np.round(calc_iip3_list, 2),
        "Calc IIP2 [dBm]": np.round(calc_iip2_list, 2),
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
        icon = "📡" if "Antena" in stype else ("🔄" if "converter" in stype.lower() else (
            "🔀" if "plexer" in stype.lower() or "divider" in stype.lower() or "divisor" in stype.lower() else (
                "〰️" if "cable" in stype.lower() else "📦")))

        card_html = (
            f'<div style="display:inline-block; vertical-align:top; background:{bg}; '
            f'border:2px solid {border}; border-radius:8px; padding:10px 12px; min-width:145px; '
            f'text-align:center; box-shadow:0 4px 6px rgba(0,0,0,0.3); margin:0 4px;">'
            f'<div style="font-size:10px; color:#A0AEC0; font-weight:bold; text-transform:uppercase;">ETAPA {i + 1}</div>'
            f'<div style="font-size:13px; color:#FFFFFF; font-weight:bold; margin:3px 0;">{icon} {s["name"]}</div>'
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
    st.title("📡 Simulador de Cascada de RF - Front-End Receiver (FER) V6.3")
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

    # Catálogo Completo de Componentes con parámetros de Salida y OPmax por defecto 249 dBm
    component_templates = {
        "Power Divider 1:2": {"type": "Divisor 1:2", "gain_db": -3.5, "nf_db": 3.5, "op1db_dbm": 40.0, "oip3_dbm": 55.0,
                              "oip2_dbm": 75.0, "opmax_dbm": 249.0},
        "Power Divider 1:4": {"type": "Divisor 1:4", "gain_db": -7.0, "nf_db": 7.0, "op1db_dbm": 40.0, "oip3_dbm": 55.0,
                              "oip2_dbm": 75.0, "opmax_dbm": 249.0},
        "Conmutador SP3T": {"type": "Switch SP3T", "gain_db": -1.6, "nf_db": 1.6, "op1db_dbm": 28.0, "oip3_dbm": 43.0,
                            "oip2_dbm": 63.0, "opmax_dbm": 249.0},
        "Conmutador SP4T": {"type": "Switch SP4T", "gain_db": -2.0, "nf_db": 2.0, "op1db_dbm": 27.0, "oip3_dbm": 42.0,
                            "oip2_dbm": 62.0, "opmax_dbm": 249.0},
        "Atenuador Fijo/Variable": {"type": "Atenuador", "gain_db": -6.0, "nf_db": 6.0, "op1db_dbm": 35.0,
                                    "oip3_dbm": 50.0, "oip2_dbm": 70.0, "opmax_dbm": 249.0},
        "Módulo Downconverter (Activo)": {"type": "Downconverter", "gain_db": 12.0, "nf_db": 6.5, "op1db_dbm": 7.0,
                                          "oip3_dbm": 17.0, "oip2_dbm": 37.0, "opmax_dbm": 10.0},
        "Módulo UpConverter": {"type": "UpConverter", "gain_db": 10.0, "nf_db": 7.0, "op1db_dbm": 8.0, "oip3_dbm": 18.0,
                               "oip2_dbm": 38.0, "opmax_dbm": 12.0},
        "Diplexer (Multiplexor 2 Vías)": {"type": "Diplexer", "gain_db": -1.5, "nf_db": 1.5, "op1db_dbm": 40.0,
                                          "oip3_dbm": 55.0, "oip2_dbm": 75.0, "opmax_dbm": 249.0},
        "Triplexer (Multiplexor 3 Vías)": {"type": "Triplexer", "gain_db": -2.2, "nf_db": 2.2, "op1db_dbm": 40.0,
                                           "oip3_dbm": 55.0, "oip2_dbm": 75.0, "opmax_dbm": 249.0},
        "Antena ESM (Espiral / Bocina)": {"type": "Antena", "gain_db": 6.0, "nf_db": 0.0, "op1db_dbm": 50.0,
                                          "oip3_dbm": 65.0, "oip2_dbm": 85.0, "opmax_dbm": 249.0},
        "Cable Coaxial RF": {"type": "Cable RF", "gain_db": -2.5, "nf_db": 2.5, "op1db_dbm": 45.0, "oip3_dbm": 60.0,
                             "oip2_dbm": 80.0, "opmax_dbm": 249.0},
        "Conmutador SPDT": {"type": "Switch SPDT", "gain_db": -1.2, "nf_db": 1.2, "op1db_dbm": 30.0, "oip3_dbm": 45.0,
                            "oip2_dbm": 65.0, "opmax_dbm": 249.0},
        "Limitador PIN (Protección)": {"type": "Protección PIN", "gain_db": -1.0, "nf_db": 1.0, "op1db_dbm": 24.0,
                                       "oip3_dbm": 39.0, "oip2_dbm": 59.0, "opmax_dbm": 15.0},
        "Amplificador LNA (GaN/GaAs)": {"type": "LNA", "gain_db": 20.0, "nf_db": 2.2, "op1db_dbm": 20.0,
                                        "oip3_dbm": 32.0, "oip2_dbm": 52.0, "opmax_dbm": 249.0},
        "Ecualizador de Ganancia": {"type": "Ecualizador", "gain_db": -3.0, "nf_db": 3.0, "op1db_dbm": 30.0,
                                    "oip3_dbm": 45.0, "oip2_dbm": 65.0, "opmax_dbm": 249.0},
        "Filtro Preselector": {"type": "Filtro", "gain_db": -2.0, "nf_db": 2.0, "op1db_dbm": 35.0, "oip3_dbm": 50.0,
                               "oip2_dbm": 70.0, "opmax_dbm": 249.0},
    }

    st.sidebar.markdown("---")
    st.sidebar.header("➕ Añadir Etapa")
    sel_template = st.sidebar.selectbox("Seleccionar Plantilla:", list(component_templates.keys()))
    t_vals = component_templates[sel_template]

    with st.sidebar.form("add_comp_form", clear_on_submit=True):
        c_name = st.text_input("Nombre de la Etapa:", value=sel_template)
        c_type = t_vals["type"]
        c_gain = st.number_input("Ganancia G (dB):", value=float(t_vals["gain_db"]), step=0.5)
        c_nf = st.number_input("Figura de Ruido NF (dB):", value=float(t_vals["nf_db"]), min_value=0.0, step=0.5)
        c_op1 = st.number_input("OP1dB de Salida (dBm):", value=float(t_vals["op1db_dbm"]), step=1.0)
        c_oip3 = st.number_input("OIP3 de Salida (dBm):", value=float(t_vals.get("oip3_dbm", c_op1 + 12.0)), step=1.0)
        c_oip2 = st.number_input("OIP2 de Salida (dBm):", value=float(t_vals.get("oip2_dbm", c_oip3 + 20.0)), step=1.0)
        c_opmax = st.number_input("OPmax Límite (dBm):", value=float(t_vals.get("opmax_dbm", 249.0)), step=1.0)

        if st.form_submit_button("➕ Insertar Etapa"):
            if "stages" not in st.session_state:
                st.session_state.stages = []
            st.session_state.stages.append({
                "id": str(uuid.uuid4())[:8],
                "name": c_name, "type": c_type, "gain_db": c_gain, "nf_db": c_nf,
                "op1db_dbm": c_op1, "oip3_dbm": c_oip3, "oip2_dbm": c_oip2,
                "opmax_dbm": c_opmax
            })
            st.rerun()

    # Inicialización por defecto con IDs únicos
    if "stages" not in st.session_state:
        st.session_state.stages = [
            {"id": "s1", "name": "Antena Espiral ESM", "type": "Antena", "gain_db": 6.0, "nf_db": 0.0,
             "op1db_dbm": 50.0, "oip3_dbm": 65.0, "oip2_dbm": 85.0, "opmax_dbm": 249.0},
            {"id": "s2", "name": "Diplexer Banda", "type": "Diplexer", "gain_db": -1.5, "nf_db": 1.5, "op1db_dbm": 40.0,
             "oip3_dbm": 55.0, "oip2_dbm": 75.0, "opmax_dbm": 249.0},
            {"id": "s3", "name": "Limitador PIN", "type": "Protección PIN", "gain_db": -1.0, "nf_db": 1.0,
             "op1db_dbm": 24.0, "oip3_dbm": 39.0, "oip2_dbm": 59.0, "opmax_dbm": 15.0},
            {"id": "s4", "name": "LNA GaN Banda Ancha", "type": "LNA", "gain_db": 20.0, "nf_db": 2.2, "op1db_dbm": 20.0,
             "oip3_dbm": 32.0, "oip2_dbm": 52.0, "opmax_dbm": 249.0},
            {"id": "s5", "name": "Filtro Preselector", "type": "Filtro", "gain_db": -2.0, "nf_db": 2.0,
             "op1db_dbm": 35.0, "oip3_dbm": 50.0, "oip2_dbm": 70.0, "opmax_dbm": 249.0},
            {"id": "s6", "name": "Módulo Downconverter", "type": "Downconverter", "gain_db": 12.0, "nf_db": 6.5,
             "op1db_dbm": 7.0, "oip3_dbm": 17.0, "oip2_dbm": 37.0, "opmax_dbm": 10.0},
        ]
    else:
        # Asegurar que cada etapa tenga ID único
        for s in st.session_state.stages:
            if "id" not in s:
                s["id"] = str(uuid.uuid4())[:8]

    # QR en la barra lateral
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
    st.caption("Los datos ingresados para cada componente se conservan exactamente al utilizar ⬅️ y ➡️.")

    col_w = [0.6, 2.2, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.8]
    h0, h1, h2, h3, h4, h5, h6, h7, h8 = st.columns(col_w)
    h0.markdown("**#**")
    h1.markdown("**Nombre / Tipo**")
    h2.markdown("**G (dB)**")
    h3.markdown("**NF (dB)**")
    h4.markdown("**OP1 (dBm)**")
    h5.markdown("**OIP3 (dBm)**")
    h6.markdown("**OIP2 (dBm)**")
    h7.markdown("**OPmax**")
    h8.markdown("**Mover / Quitar**")

    for i in range(len(st.session_state.stages)):
        stg = st.session_state.stages[i]
        stg_id = stg["id"]
        c0, c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(col_w)
        c0.markdown(f"**E{i + 1}**")
        c1.markdown(f"**{stg['name']}**  \n<span style='font-size:11px;color:#888'>{stg['type']}</span>",
                    unsafe_allow_html=True)

        # Claves de widget vinculadas al ID único persistente
        stg['gain_db'] = c2.number_input("G", value=float(stg['gain_db']), key=f"g_{stg_id}",
                                         label_visibility="collapsed")
        stg['nf_db'] = c3.number_input("NF", value=float(stg['nf_db']), min_value=0.0, key=f"nf_{stg_id}",
                                       label_visibility="collapsed")
        stg['op1db_dbm'] = c4.number_input("OP1", value=float(stg.get('op1db_dbm', 30.0)), key=f"op1_{stg_id}",
                                           label_visibility="collapsed")
        stg['oip3_dbm'] = c5.number_input("OIP3", value=float(stg.get('oip3_dbm', stg.get('op1db_dbm', 30.0) + 12.0)),
                                          key=f"oip3_{stg_id}", label_visibility="collapsed")
        stg['oip2_dbm'] = c6.number_input("OIP2", value=float(stg.get('oip2_dbm', stg.get('oip3_dbm', 42.0) + 20.0)),
                                          key=f"oip2_{stg_id}", label_visibility="collapsed")
        stg['opmax_dbm'] = c7.number_input("OPmax", value=float(stg.get('opmax_dbm', 249.0)), key=f"opmax_{stg_id}",
                                           label_visibility="collapsed")

        btn_col1, btn_col2, btn_col3 = c8.columns(3)
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
        "Gain": {"col": "Gain Acum [dB]", "y_label": "Ganancia Acumulada (dB)", "color": "#00E676", "unit": "dB"},
        "NF Friis": {"col": "NF Acum Friis [dB]", "y_label": "Figura de Ruido Acumulada Friis (dB)", "color": "#FF5252",
                     "unit": "dB"},
        "NF Etapa": {"col": "NF Etapa [dB]", "y_label": "Figura de Ruido Nominal de la Etapa (dB)", "color": "#FF7A00",
                     "unit": "dB"},
        "OIP2": {"col": "OIP2 Acum [dBm]", "y_label": "Punto de Intercepción OIP2 Acumulado (dBm)", "color": "#E040FB",
                 "unit": "dBm"},
        "OIP3": {"col": "OIP3 Acum [dBm]", "y_label": "Punto de Intercepción OIP3 Acumulado (dBm)", "color": "#AB47BC",
                 "unit": "dBm"},
        "Psig": {"col": "Psig [dBm]", "y_label": "Nivel de Señal de RF (dBm)", "color": "#29B6F6", "unit": "dBm"},
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

    # Si se selecciona NF Friis, mostramos también la NF de la etapa como referencia punteada
    if selected_param == "NF Friis":
        fig.add_trace(go.Scatter(
            x=stage_names, y=results_df["NF Etapa [dB]"], mode="lines+markers",
            name="NF Nominal Etapa", line=dict(color="#FFB300", width=2, dash="dash")
        ))

    if selected_param == "Psig":
        fig.add_trace(go.Scatter(x=stage_names, y=results_df["OP1 Acum [dBm]"], mode="lines", name="Límite OP1dB",
                                 line=dict(color="#FF9800", width=2, dash="dash")))
        fig.add_trace(go.Scatter(x=stage_names, y=results_df["Pnoise [dBm]"], mode="lines", name="Piso Ruido Pnoise",
                                 line=dict(color="#90A4AE", width=2, dash="dot")))

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
    st.caption(
        "Muestra los valores de salida ingresados (OP1, OIP3, OIP2, OPmax) junto con los calculados a la entrada (IP1, IIP3, IIP2) y el acumulado Friis.")
    st.dataframe(results_df, use_container_width=True)

    csv_data = results_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"📥 Exportar Tabla Completa @ {f_calc_ghz:.2f}GHz & {temp_kelvin:.0f}K (CSV)",
        data=csv_data,
        file_name=f"cascada_fer_{f_calc_ghz:.2f}GHz_{temp_kelvin:.0f}K.csv",
        mime="text/csv"
    )


if __name__ == "__main__":
    main()