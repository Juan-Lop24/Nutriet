"""
🔗 Adaptadores de servicios

Conecta la lógica IA con aplicaciones externas:
- Convierte ResultadoIA a formatos de la app
- Adapta entrada desde vistas Django
- Serializa para APIs
"""

from typing import Dict, Any, Optional
from applications.ai.dtos import DatosEntrada, ResultadoIA
from applications.nutricion.models import DietaGenerada


class AdaptadorVistas:
    """
    Adapta datos desde vistas Django a DatosEntrada.
    
    Responsable de:
    - Extraer datos de FormularioNutricionGuardado
    - Validar tipos de datos
    - Convertir a DatosEntrada
    """
    
    @staticmethod
    def desde_formulario_django(formulario_guardado) -> DatosEntrada:
        """
        Crea DatosEntrada desde un objeto FormularioNutricionGuardado.
        
        Args:
            formulario_guardado: Instancia de FormularioNutricionGuardado
            
        Returns:
            DatosEntrada validado
        """
        return DatosEntrada(
            peso_kg=float(formulario_guardado.peso),
            altura_cm=float(formulario_guardado.altura),
            edad_anos=int(formulario_guardado.edad),
            sexo=formulario_guardado.sexo.lower(),
            objetivo=formulario_guardado.objetivo.lower(),
            nivel_actividad=formulario_guardado.nivel_actividad.lower(),
            tipo_dieta=formulario_guardado.tipo_dieta.lower() if formulario_guardado.tipo_dieta else "normal",
        )
    
    @staticmethod
    def desde_dict(datos_dict: Dict[str, Any]) -> DatosEntrada:
        """
        Crea DatosEntrada desde un diccionario (API, formulario JSON, etc).
        
        Args:
            datos_dict: Dict con keys: peso_kg, altura_cm, edad_anos, sexo, objetivo, nivel_actividad, tipo_dieta
            
        Returns:
            DatosEntrada validado
        """
        return DatosEntrada(
            peso_kg=float(datos_dict.get("peso_kg", 0)),
            altura_cm=float(datos_dict.get("altura_cm", 0)),
            edad_anos=int(datos_dict.get("edad_anos", 0)),
            sexo=str(datos_dict.get("sexo", "")).lower(),
            objetivo=str(datos_dict.get("objetivo", "mantener")).lower(),
            nivel_actividad=str(datos_dict.get("nivel_actividad", "moderado")).lower(),
            tipo_dieta=str(datos_dict.get("tipo_dieta", "normal")).lower(),
        )


class AdaptadorRecetas:
    """
    Adapta ResultadoIA al formato de recetas y comidas.
    
    Convierte macros recomendadas a:
    - Sugerencias de recetas
    - Formatos de plan de comidas
    - Integración con base de recetas
    """
    
    @staticmethod
    def a_formato_comidas(resultado: ResultadoIA, distribucion: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Convierte resultado a formato de plan de comidas.
        
        Args:
            resultado: ResultadoIA del procesador
            distribucion: Distribución por comidas (opcional)
            
        Returns:
            Dict con plan de comidas formateado
        """
        return {
            "resumen": {
                "calorias_recomendadas": resultado.calorias_recomendadas,
                "proteinas_g": resultado.proteinas_g,
                "grasas_g": resultado.grasas_g,
                "carbohidratos_g": resultado.carbohidratos_g,
                "tipo_dieta": resultado.tipo_dieta,
                "objetivo": resultado.objetivo,
            },
            "distribucion_comidas": distribucion or {},
            "metodos_coccion_recomendados": AdaptadorRecetas._sugerir_metodos(resultado.tipo_dieta),
        }
    
    @staticmethod
    def _sugerir_metodos(tipo_dieta: str) -> list:
        """Sugiere métodos de cocción según tipo de dieta."""
        sugerencias = {
            "normal": ["hervir", "asar", "saltear"],
            "vegetariano": ["asar", "hornear", "saltear"],
            "vegano": ["vapor", "saltear", "hornear"],
            "keto": ["asar", "saltear", "horno"],
        }
        return sugerencias.get(tipo_dieta.lower(), ["hervir", "asar"])


class AdaptadorJSON:
    """
    Serializa ResultadoIA a JSON para APIs.
    """
    
    @staticmethod
    def a_json(resultado: ResultadoIA) -> Dict[str, Any]:
        """
        Convierte ResultadoIA a diccionario JSON-serializable.
        
        Args:
            resultado: ResultadoIA del procesador
            
        Returns:
            Dict listo para JSON
        """
        return resultado.a_dict()


class AdaptadorDieta:
    """
    Adapta el resultado para integración con DietaGenerada.
    """
    
    @staticmethod
    def guardar_en_modelo(resultado: ResultadoIA, usuario) -> 'DietaGenerada':
        """
        Convierte ResultadoIA a instancia de DietaGenerada para guardar.
        
        Args:
            resultado: ResultadoIA del procesador
            usuario: Usuario propietario de la dieta
            
        Returns:
            Instancia de DietaGenerada (sin guardar)
        """
        
        
        dieta = DietaGenerada(
            usuario=usuario,
            tipo_dieta=resultado.tipo_dieta,
            calorias=int(resultado.calorias_recomendadas),
            proteinas=round(resultado.proteinas_g, 1),
            grasas=round(resultado.grasas_g, 1),
            carbohidratos=round(resultado.carbohidratos_g, 1),
            imc=round(resultado.imc, 2),
            porcentaje_grasa=round(resultado.porcentaje_grasa, 1),
            clasificacion_imc=resultado.clasificacion_imc,
            nivel_riesgo=resultado.nivel_riesgo,
        )
        
        return dieta


class CanalResultado:
    """
    Enruta el resultado a diferentes destinos según necesidad.
    
    ✅ JSON API
    ✅ Template HTML
    ✅ Base de datos
    ✅ Archivo descargable
    """
    
    @staticmethod
    def a_vista_template(resultado: ResultadoIA) -> Dict[str, Any]:
        """Formatea para renderizar en template HTML."""
        return {
            "metricas": {
                "imc": f"{resultado.imc:.1f}",
                "grasa": f"{resultado.porcentaje_grasa:.1f}%",
                "tmb": f"{resultado.tmb:.0f} kcal",
                "tdee": f"{resultado.tdee:.0f} kcal",
            },
            "recomendaciones": {
                "calorias": f"{resultado.calorias_recomendadas:.0f} kcal",
                "proteinas": f"{resultado.proteinas_g:.0f}g",
                "grasas": f"{resultado.grasas_g:.0f}g",
                "carbohidratos": f"{resultado.carbohidratos_g:.0f}g",
            },
            "clasificacion": resultado.clasificacion_imc,
            "riesgo": resultado.nivel_riesgo,
        }
    
    @staticmethod
    def a_descargable_csv(resultado: ResultadoIA) -> str:
        """Formatea para descargar como CSV."""
        lineas = [
            "Métrica,Valor",
            f"IMC,{resultado.imc:.1f}",
            f"Porcentaje Grasa,{resultado.porcentaje_grasa:.1f}%",
            f"TMB,{resultado.tmb:.0f} kcal",
            f"TDEE,{resultado.tdee:.0f} kcal",
            f"Calorias Recomendadas,{resultado.calorias_recomendadas:.0f} kcal",
            f"Proteínas,{resultado.proteinas_g:.0f}g",
            f"Grasas,{resultado.grasas_g:.0f}g",
            f"Carbohidratos,{resultado.carbohidratos_g:.0f}g",
            f"Clasificación IMC,{resultado.clasificacion_imc}",
            f"Nivel Riesgo,{resultado.nivel_riesgo}",
        ]
        return "\n".join(lineas)
