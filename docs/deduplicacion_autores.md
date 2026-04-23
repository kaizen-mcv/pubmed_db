# Deduplicación de Autores - Estrategia y Metodología

## Introducción

Este documento describe la estrategia utilizada para identificar autores únicos en la base de datos PubMed, resolviendo el problema de variaciones en nombres y la ausencia de identificadores únicos universales.

---

## Problema

Los datos de autores en PubMed presentan múltiples desafíos:

### Estadísticas de Datos Originales

| Métrica | Valor |
|---------|-------|
| Total registros | 2,086,595 |
| Nombres distintos (COUNT DISTINCT) | 540,354 |
| Combinaciones nombre+afiliación | 1,819,834 |
| Registros con ORCID | 423,806 (20.31%) |
| ORCIDs únicos | 105,616 |
| Afiliaciones únicas | 931,660 |

### Tipos de Variaciones Detectadas

| Tipo | Ejemplo | Frecuencia |
|------|---------|------------|
| Acentos | García vs Garcia | Muy alta |
| Guiones/espacios | García-Pavia vs García Pavia | Alta |
| Iniciales vs completo | J A vs José Alfredo | Alta |
| Abreviaturas de María | Mª, Ma, M, María | Media |
| Orden apellidos | de Luis-Román vs Luis, Daniel de | Media |
| Partículas | de la Torre vs De La Torre | Media |

### Ejemplo Real

Un mismo autor (ORCID 0000-0002-1745-9315) aparece con **19 variantes** diferentes:

```
de Luis, D
de Luis, Daniel
De Luis, Daniel
de Luis, Daniel A
de Luis, Daniel Antonio
de Luis Roman, Daniel
de Luis Román, Daniel
De Luis Román, Daniel
de Luis-Román, Daniel Antonio
Luis, Daniel A De
Luis, Daniel de
...
```

---

## Estrategia de Solución

### Dos Tablas de Resultados

Se crean dos tablas en el schema `sm_result` para diferentes niveles de confianza:

1. **`sm_result.authors_orcid`** - Solo autores con ORCID (100% fiable)
2. **`sm_result.authors_norm`** - Todos los autores por nombre normalizado

### Proceso en 3 Fases

```
FASE 1: ORCID Directo
├── 423,806 registros con ORCID
├── Agrupación por ORCID único
└── Resultado: ~105,616 autores (confianza 100%)

FASE 2: Propagación de ORCID
├── Registros sin ORCID que coinciden en nombre+afiliación
├── Con registros que sí tienen ORCID
└── Resultado: ~58,028 registros adicionales rescatados

FASE 3: Normalización de Nombres
├── Registros restantes sin ORCID
├── Agrupación por nombre normalizado
└── Resultado: ~420,000 autores (confianza 70%)
```

---

## Algoritmo de Normalización

### Función Principal

```python
def normalize_name(name: str) -> str:
    """
    Genera el nombre canónico para comparación.

    Pasos:
    1. Convertir a minúsculas
    2. Eliminar acentos (unidecode)
    3. Normalizar abreviaturas de María
    4. Unificar guiones y espacios
    5. Eliminar puntuación
    6. Normalizar espacios múltiples
    """
    # Lowercase
    name = name.lower()

    # Eliminar acentos
    name = unidecode(name)  # garcía → garcia

    # Normalizar María
    for variant in ['mª', 'ma', 'm.ª', 'm.a', 'mᵃ']:
        name = name.replace(variant, 'maria')

    # Unificar guiones
    name = name.replace('-', ' ')

    # Eliminar puntuación
    name = re.sub(r'[.]', '', name)

    # Normalizar espacios
    return ' '.join(name.split())
```

### Ejemplos de Normalización

| Original | Normalizado |
|----------|-------------|
| García-Pavia, Pablo | garcia pavia, pablo |
| García Pavía, Pablo | garcia pavia, pablo |
| Garcia-Pavia, P | garcia pavia, p |
| Martínez, José Mª | martinez, jose maria |
| de Luis-Román, Daniel | de luis roman, daniel |

---

## Selección del Nombre a Mostrar (display_name)

### Criterios de Preferencia

1. **Con ORCID**: Usar el nombre más completo
   - Priorizar nombres sin iniciales (José > J)
   - Priorizar con acentos (García > Garcia)

2. **Sin ORCID**: Usar el nombre más frecuente

### Algoritmo

```python
def select_display_name(name_variants: List[str], counts: Dict[str, int]) -> str:
    """
    Selecciona el nombre preferido para mostrar.
    """
    def score_name(name: str) -> tuple:
        has_full_name = not re.search(r', [A-Z](\s|$)', name)  # No termina en inicial
        has_accents = bool(re.search(r'[áéíóúñüÁÉÍÓÚÑÜ]', name))
        frequency = counts.get(name, 0)
        length = len(name)
        return (has_full_name, has_accents, frequency, length)

    return max(name_variants, key=score_name)
```

---

## Estructura de las Tablas

### Tabla 1: `sm_result.authors_orcid`

**~105,616 registros** - Autores identificados por ORCID.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| sm_author_id | SERIAL PK | ID único |
| author_orcid | VARCHAR(50) UNIQUE | ORCID (identificador) |
| display_name | VARCHAR(500) | Nombre preferido |
| canonical_name | VARCHAR(500) | Nombre normalizado |
| name_variants | TEXT[] | Array de variantes |
| article_count | INTEGER | Número de artículos |
| first_publication | DATE | Primera publicación |
| last_publication | DATE | Última publicación |

### Tabla 2: `sm_result.authors_norm`

**~500,000-525,000 registros** - Todos los autores por nombre normalizado.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| sm_author_id | SERIAL PK | ID único |
| canonical_name | VARCHAR(500) UNIQUE | Nombre normalizado (clave) |
| display_name | VARCHAR(500) | Nombre preferido |
| author_orcid | VARCHAR(50) | ORCID si existe |
| orcid_author_id | INTEGER FK | Referencia a authors_orcid |
| name_variants | TEXT[] | Array de variantes |
| confidence | DECIMAL(3,2) | 1.0=ORCID, 0.7=normalizado |
| article_count | INTEGER | Número de artículos |
| first_publication | DATE | Primera publicación |
| last_publication | DATE | Última publicación |

---

## Relación entre Tablas

```
raw.pubmed_authors (2,086,595 registros)
        │
        ▼
┌───────────────────────────────────────┐
│         PROCESO DE DEDUPLICACIÓN      │
│  (scripts/deduplicacion_autores.py)   │
└───────────────────────────────────────┘
        │
        ├──► sm_result.authors_orcid (105,616)
        │    └── Confianza: 100%
        │
        └──► sm_result.authors_norm (500,000-525,000)
             ├── Con ORCID: Confianza 100%
             └── Sin ORCID: Confianza 70%
```

---

## Uso Recomendado

| Caso de Uso | Tabla | Razón |
|-------------|-------|-------|
| Análisis de alta precisión | `authors_orcid` | 100% fiable |
| Búsqueda por nombre | `authors_norm` | Incluye todos |
| Vincular con ORCID externo | `authors_orcid` | Clave ORCID |
| Estadísticas generales | `authors_norm` | Cobertura completa |
| Machine Learning | `authors_orcid` | Sin ruido |

---

## Cobertura de Especialidades

### Autores con Especialidad Detectada

| Métrica | Valor | % |
|---------|-------|---|
| Con especialidad SNOMED | 144,080 | 26.7% |
| Sin especialidad detectada | 396,274 | 73.3% |
| Total | 540,354 | 100% |

### Top 10 Especialidades

| Especialidad | Autores |
|--------------|---------|
| Urología | 19,071 |
| Neurología | 14,292 |
| Cardiología | 13,262 |
| Medicina Interna | 11,066 |
| Oncología Médica | 8,409 |
| Radiodiagnóstico | 8,204 |
| Aparato Digestivo | 7,734 |
| Dermatología | 7,488 |
| Infectious diseases | 6,604 |
| Psiquiatría | 6,582 |

---

## Limitaciones Conocidas

1. **Homonimia**: Dos personas diferentes con el mismo nombre normalizado se fusionan en `authors_norm` (sin ORCID no hay forma de distinguirlas)

2. **Propagación de ORCID**: Solo funciona con coincidencia exacta de nombre+afiliación

3. **Iniciales**: "García, J" y "García, Juan" no se fusionan automáticamente (podrían ser personas diferentes)

4. **Cobertura ORCID**: Solo 20.31% de registros tienen ORCID

---

## Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `scripts/create_authors_table.sql` | DDL para las tablas |
| `scripts/deduplicacion_autores.py` | Script de población |
| `src/utils/name_normalizer.py` | Funciones de normalización |

---

## Fecha de Creación

Diciembre 2024
