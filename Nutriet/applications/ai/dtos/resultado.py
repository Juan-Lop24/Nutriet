"""
Contrato de datos de salida de la IA
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List
import json


@dataclass
class ResultadoIA:
    imc: float
    porcentaje_grasa: float
    tmb: float
    tdee: float
    calorias_recomendadas: float

    proteinas_g: int
    grasas_g: int
    carbohidratos_g: int

    clasificacion_imc: str
    nivel_riesgo: str
    objetivo: str

    distribucion_macros_comidas: Dict[str, Dict[str, float]] = field(default_factory=dict)
    ingredientes_excluidos: List[str] = field(default_factory=list)

    def a_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def a_json(self) -> str:
        return json.dumps(self.a_dict(), ensure_ascii=False, indent=2)