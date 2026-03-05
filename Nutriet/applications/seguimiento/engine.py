# applications/seguimiento/engine.py
"""
Motor de análisis nutricional-corporal para el módulo de seguimiento.

Conecta FormularioNutricionGuardado con MedicionFisica y reutiliza
applications/ai/core/ para todos los cálculos.

Fórmulas usadas:
  - IMC:          peso / (altura_m²)
  - TMB:          Mifflin-St Jeor (el prompt lo exige)
  - TDEE:         TMB × factor de actividad
  - %Grasa:       Deurenberg — (1.20×IMC) + (0.23×edad) − 16.2/5.4
  - Masa magra:   peso × (1 − %grasa/100)

El formulario ya viene validado → edad, sexo, altura, nivel_actividad,
objetivo, peso_objetivo, plazo_meses siempre están presentes.
"""

from datetime import date, timedelta

from applications.ai.core import (
    calcular_imc,
    calcular_grasa_corporal_deurenberg,   # Deurenberg: IMC + edad + sexo
    calcular_tdee,
)
from applications.ai.riesgo.evaluacion import clasificar_imc as _clasif_raw


# ── TMB Mifflin-St Jeor (el prompt lo exige explícitamente) ──────────────────
def _tmb_mifflin(peso_kg: float, altura_cm: float, edad: int, sexo: str) -> float:
    """
    Mifflin-St Jeor 1990:
      Hombre: 10×peso + 6.25×altura − 5×edad + 5
      Mujer:  10×peso + 6.25×altura − 5×edad − 161
    """
    base = 10 * peso_kg + 6.25 * altura_cm - 5 * edad
    return round(base + 5 if sexo.upper() == "M" else base - 161, 2)


# ── Clasificación IMC en español ──────────────────────────────────────────────
_CLASIF_ES = {
    "bajo_peso": "Bajo peso",
    "normal":    "Peso normal",
    "sobrepeso": "Sobrepeso",
    "obesidad":  "Obesidad",
}

def _clasif_es(imc: float) -> str:
    return _CLASIF_ES.get(_clasif_raw(imc), "Desconocido")


# ── Métricas completas para un peso dado (reutilizando ai/core) ───────────────
def _metricas(peso: float, altura_cm: float, edad: int, sexo: str, actividad: str) -> dict:
    imc       = calcular_imc(peso, altura_cm)
    grasa     = max(0.0, calcular_grasa_corporal_deurenberg(imc, edad, sexo))
    masa_magra = round(peso * (1 - grasa / 100), 2)
    tmb       = _tmb_mifflin(peso, altura_cm, edad, sexo)
    tdee      = calcular_tdee(tmb, actividad)
    return {
        "imc":        imc,
        "clasif":     _clasif_es(imc),
        "grasa":      round(grasa, 2),
        "masa_magra": masa_magra,
        "tmb":        tmb,
        "tdee":       tdee,
    }


# ── Ritmo semanal saludable según objetivo ────────────────────────────────────
def _ritmo(objetivo: str) -> tuple[float, float]:
    """(min_kg_sem, max_kg_sem)"""
    obj = objetivo.lower()
    if "reduc" in obj:   return 0.5, 1.0
    if "aument" in obj:  return 0.25, 0.5
    return 0.0, 0.0


# ── Motor principal ───────────────────────────────────────────────────────────
def analizar(formulario, mediciones_qs) -> dict:
    """
    Parámetros
    ----------
    formulario   : FormularioNutricionGuardado (ya validado, todos los campos presentes)
    mediciones_qs: QuerySet de MedicionFisica

    Devuelve el dict JSON completo del formato acordado.
    """
    mediciones = list(mediciones_qs.order_by("fecha"))

    # ── Datos del formulario (siempre presentes, formulario validado) ─────────
    edad      = formulario.edad
    sexo      = formulario.sexo or "M"
    altura    = formulario.altura
    actividad = formulario.nivel_actividad
    objetivo  = formulario.objetivo          # "Reducir" / "Aumentar" / "Mantener"
    peso_meta = float(formulario.peso_objetivo)
    meses     = int(formulario.plazo_meses)
    fecha_ini = formulario.creado_en.date()
    peso_ini  = float(formulario.peso)

    # ── Estado actual ─────────────────────────────────────────────────────────
    if mediciones:
        ultima   = mediciones[-1]
        peso_act = float(ultima.peso)
        fecha_act = ultima.fecha
    else:
        peso_act  = peso_ini
        fecha_act = fecha_ini

    m_act = _metricas(peso_act, altura, edad, sexo, actividad)

    # ── Validar meta y calcular ritmo ─────────────────────────────────────────
    semanas_disp = meses * 4.33
    delta        = abs(peso_act - peso_meta)
    rmin, rmax   = _ritmo(objetivo)
    meta_ajustada_flag = False

    if rmin > 0:
        max_alcanzable = rmax * semanas_disp
        if delta <= max_alcanzable:
            ritmo_rec = round(delta / semanas_disp, 3) if semanas_disp else rmin
            ritmo_rec = max(rmin, min(rmax, ritmo_rec))
        else:
            # Meta irreal → ajustar peso_meta manteniendo los mismos meses
            ritmo_rec = round((rmin + rmax) / 2, 3)
            ajuste = ritmo_rec * semanas_disp
            if "reduc" in objetivo.lower():
                peso_meta = round(peso_act - ajuste, 2)
            else:
                peso_meta = round(peso_act + ajuste, 2)
            meta_ajustada_flag = True

        semanas_rest = round(abs(peso_act - peso_meta) / ritmo_rec, 1) if ritmo_rec else 0
    else:
        ritmo_rec     = 0.0
        semanas_rest  = 0
        meta_ajustada_flag = False

    fecha_cumpl = fecha_act + timedelta(weeks=float(semanas_rest))

    # ── Texto de meta ─────────────────────────────────────────────────────────
    obj_verb = (
        "Reducir" if "reduc" in objetivo.lower() else
        "Aumentar" if "aument" in objetivo.lower() else
        "Mantener"
    )
    meta_original_str = f"{obj_verb} a {formulario.peso_objetivo} kg en {meses} meses"
    meta_ajustada_str = f"{obj_verb} a {peso_meta} kg ({meses} meses)"

    # ── Comentario profesional ────────────────────────────────────────────────
    if "reduc" in objetivo.lower():
        deficit = round(ritmo_rec * 1000)
        comentario = (
            f"Para reducir grasa de forma saludable aplica un déficit de ~{deficit} kcal/día, "
            f"logrando ~{ritmo_rec} kg/semana. Tu TDEE actual es {m_act['tdee']} kcal. "
            f"Apunta a consumir ~{round(m_act['tdee'] - deficit)} kcal/día."
        )
    elif "aument" in objetivo.lower():
        comentario = (
            f"Para ganar masa muscular aplica un superávit de ~300 kcal/día con entrenamiento de fuerza. "
            f"Tu TDEE actual es {m_act['tdee']} kcal. Apunta a ~{round(m_act['tdee'] + 300)} kcal/día."
        )
    else:
        comentario = (
            f"Tu metabolismo está en equilibrio. Consume ~{m_act['tdee']} kcal/día "
            f"para mantener tu peso actual de {peso_act} kg."
        )

    # ── Progreso ──────────────────────────────────────────────────────────────
    total_cambio = abs(peso_ini - peso_meta)
    if total_cambio > 0:
        if "reduc" in objetivo.lower():
            prog_pct = round(max(0, min(100, (peso_ini - peso_act) / (peso_ini - peso_meta) * 100)), 1)
        elif "aument" in objetivo.lower():
            prog_pct = round(max(0, min(100, (peso_act - peso_ini) / (peso_meta - peso_ini) * 100)), 1)
        else:
            prog_pct = 100.0
    else:
        prog_pct = 100.0

    peso_faltante = round(abs(peso_act - peso_meta), 2)

    # ── Arrays para gráficas ──────────────────────────────────────────────────
    def _prog(pw):
        if total_cambio <= 0:
            return 100.0
        if "reduc" in objetivo.lower():
            return round(max(0, min(100, (peso_ini - pw) / (peso_ini - peso_meta) * 100)), 1)
        if "aument" in objetivo.lower():
            return round(max(0, min(100, (pw - peso_ini) / (peso_meta - peso_ini) * 100)), 1)
        return 100.0

    w_time = []; bmi_t = []; bf_t = []; lm_t = []; pp_t = []

    # Punto inicial del formulario (si no coincide con primera medición)
    if not mediciones or mediciones[0].fecha > fecha_ini:
        m0   = _metricas(peso_ini, altura, edad, sexo, actividad)
        f0   = fecha_ini.strftime("%Y-%m-%d")
        w_time.append({"date": f0, "value": peso_ini})
        bmi_t .append({"date": f0, "value": m0["imc"]})
        bf_t  .append({"date": f0, "value": m0["grasa"]})
        lm_t  .append({"date": f0, "value": m0["masa_magra"]})
        pp_t  .append({"date": f0, "value": 0.0})

    for m in mediciones:
        pw  = float(m.peso)
        ms  = _metricas(pw, altura, edad, sexo, actividad)
        fs  = m.fecha.strftime("%Y-%m-%d")
        w_time.append({"date": fs, "value": pw})
        bmi_t .append({"date": fs, "value": ms["imc"]})
        bf_t  .append({"date": fs, "value": ms["grasa"]})
        lm_t  .append({"date": fs, "value": ms["masa_magra"]})
        pp_t  .append({"date": fs, "value": _prog(pw)})

    # Proyección semanal
    semanas_proj = min(int(semanas_rest) + 1, int(semanas_disp) + 1, 52)
    projection = []
    for w in range(1, semanas_proj + 1):
        if "reduc" in objetivo.lower():
            exp = round(max(peso_meta, peso_act - ritmo_rec * w), 2)
        elif "aument" in objetivo.lower():
            exp = round(min(peso_meta, peso_act + ritmo_rec * w), 2)
        else:
            exp = peso_act
        projection.append({"week": w, "expected_weight": exp})

    # ── Alertas ───────────────────────────────────────────────────────────────
    alerts = []
    imc_v   = m_act["imc"]
    grasa_v = m_act["grasa"]

    if imc_v < 18.5:
        alerts.append({"nivel": "warning", "mensaje": "⚠️ IMC bajo — riesgo de desnutrición. Aumenta ingesta calórica."})
    elif imc_v >= 30:
        alerts.append({"nivel": "danger",  "mensaje": "🔴 Obesidad (IMC ≥ 30). Recomendamos consulta con profesional de salud."})
    elif imc_v >= 25:
        alerts.append({"nivel": "warning", "mensaje": "🟡 Sobrepeso (IMC 25–30). Ajusta alimentación y nivel de actividad."})

    lim_grasa = 25 if sexo.upper() == "M" else 32
    if grasa_v > lim_grasa + 10:
        alerts.append({"nivel": "danger", "mensaje": f"🔴 % grasa elevado ({grasa_v}%). Riesgo metabólico alto."})
    elif grasa_v > lim_grasa:
        alerts.append({"nivel": "warning", "mensaje": f"🟡 % grasa ({grasa_v}%) por encima del rango saludable."})

    if not mediciones:
        alerts.append({"nivel": "info", "mensaje": "📊 Aún no tienes mediciones. ¡Agrega la primera hoy!"})
    elif (date.today() - mediciones[-1].fecha).days > 30:
        alerts.append({"nivel": "warning",
                       "mensaje": f"📅 Llevas {(date.today() - mediciones[-1].fecha).days} días sin medir."})

    if meta_ajustada_flag:
        alerts.append({"nivel": "info",
                       "mensaje": f"ℹ️ Tu meta original era irreal para {meses} meses. "
                                  f"La ajustamos a {peso_meta} kg (~{ritmo_rec} kg/semana)."})

    # ── Resultado final ───────────────────────────────────────────────────────
    return {
        "user_summary": {
            "edad":        edad,
            "sexo":        sexo,
            "altura_cm":   altura,
            "actividad":   actividad,
            "objetivo":    objetivo,
            "meses_meta":  meses,
            "fecha_inicio": fecha_ini.strftime("%Y-%m-%d"),
        },
        "calculations_current": {
            "peso_actual":             peso_act,
            "imc_actual":              m_act["imc"],
            "clasificacion_imc":       m_act["clasif"],
            "tmb_actual":              m_act["tmb"],
            "tdee_actual":             m_act["tdee"],
            "porcentaje_grasa_actual": m_act["grasa"],
            "masa_magra_actual":       m_act["masa_magra"],
        },
        "goal_plan": {
            "meta_usuario_original":      meta_original_str,
            "meta_ajustada":              meta_ajustada_str,
            "peso_meta":                  peso_meta,
            "ritmo_semanal_recomendado":  ritmo_rec,
            "fecha_estimada_cumplimiento": fecha_cumpl.strftime("%Y-%m-%d"),
            "comentario_profesional":     comentario,
        },
        "progress": {
            "peso_inicial":               peso_ini,
            "peso_actual":                peso_act,
            "progreso_porcentaje":        prog_pct,
            "peso_faltante_para_meta":    peso_faltante,
            "semanas_estimadas_restantes": semanas_rest,
        },
        "charts": {
            "weight_over_time":           w_time,
            "bmi_over_time":              bmi_t,
            "bodyfat_over_time":          bf_t,
            "leanmass_over_time":         lm_t,
            "progress_percent_over_time": pp_t,
            "projection_weight_weekly":   projection,
        },
        "alerts": alerts,
    }
