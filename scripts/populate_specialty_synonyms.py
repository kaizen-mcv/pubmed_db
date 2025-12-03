#!/usr/bin/env python3
"""
Script para poblar sinónimos EXCLUSIVOS de especialidades MIR españolas.

Los sinónimos están diseñados para:
1. Ser únicos para cada especialidad (sin solapamiento)
2. Manejar variaciones: mayúsculas, acentos, idioma (EN/ES)
3. Usarse para matching case-insensitive

Uso:
    python populate_specialty_synonyms.py           # Solo mostrar
    python populate_specialty_synonyms.py --apply   # Aplicar a BD
"""

import argparse
import sys
from pathlib import Path

# Añadir path del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import db


# Sinónimos EXCLUSIVOS para las 46 especialidades MIR
# Formato: snomed_code -> lista de sinónimos (separados por ; en BD)
# REGLA: Cada sinónimo debe ser único para UNA sola especialidad
#
# Variaciones incluidas:
# - Inglés y español
# - Con/sin acentos
# - Términos médicos específicos
#
# EVITAR términos ambiguos como:
# - "neuro" (neurología vs neurocirugía vs neurofisiología)
# - "cardio" (cardiología vs cirugía cardiovascular)
# - "onco" (oncología médica vs radioterápica)
# - "pediatr" (pediatría vs cirugía pediátrica vs psiquiatría infantil)

MIR_SYNONYMS = {
    # === ESPECIALIDADES MÉDICAS ===

    # Alergología
    "408439002": "allergy;allergology;alergologia;allergist;alergologo;allergic;alergico",

    # Anestesiología y Reanimación
    "394577000": "anesthesia;anaesthesia;anestesia;anesthesiology;anaesthesiology;anestesiologia;reanimacion;anesthetist;anaesthetist;anestesiologo",

    # Cardiología (evitar "cardio" por ambigüedad con cirugía cardiovascular)
    "394579002": "cardiology;cardiologia;cardiologist;cardiologo;heart disease;cardiac medicine",

    # Dermatología
    "394582007": "dermatology;dermatologia;dermatologist;dermatologo;skin;cutaneous;piel;cutaneo",

    # Endocrinología y Nutrición
    "394583002": "endocrinology;endocrinologia;endocrinologist;endocrinologo;hormone;hormonal;diabetes;thyroid;tiroides;metabolic;metabolismo",

    # Aparato Digestivo (Gastroenterología)
    "394584008": "gastroenterology;gastroenterologia;gastroenterologist;gastroenterologo;digestive;digestivo;gastrointestinal;gi tract",

    # Obstetricia y Ginecología
    "394585009": "obstetrics;obstetricia;gynecology;gynaecology;ginecologia;obgyn;obstetrician;gynecologist;obstetra;ginecologo;maternal;pregnancy;embarazo",

    # Psiquiatría (adultos)
    "394587001": "psychiatry;psiquiatria;psychiatrist;psiquiatra;mental health;salud mental;psychiatric",

    # Psiquiatría Infantil y de la Adolescencia
    "394588006": "child psychiatry;adolescent psychiatry;psiquiatria infantil;psiquiatria adolescente;child mental health",

    # Nefrología
    "394589003": "nephrology;nefrologia;nephrologist;nefrologo;kidney;renal;riñon;dialysis;dialisis",

    # Neurología (evitar "neuro" por neurocirugía/neurofisiología)
    "394591006": "neurology;neurologia;neurologist;neurologo;neurological;neurologico;brain disease;nervous system disease",

    # Oncología Médica (evitar "onco" por radioterapia)
    "394593009": "medical oncology;oncologia medica;medical oncologist;oncologo medico;chemotherapy;quimioterapia;cancer medicine",

    # Oftalmología
    "394594003": "ophthalmology;oftalmologia;ophthalmologist;oftalmologo;eye;ocular;vision;ojo;ojos;ophthalmic",

    # Anatomía Patológica (Histopatología)
    "394597005": "histopathology;histopatologia;anatomia patologica;pathologist;patologo;biopsy;biopsia;autopsy;autopsia",

    # Farmacología Clínica
    "394600006": "clinical pharmacology;farmacologia clinica;pharmacologist;farmacologo;drug therapy;pharmacotherapy",

    # Medicina Física y Rehabilitación
    "394602003": "rehabilitation;rehabilitacion;physiatry;physiatrist;fisiatra;physical medicine;medicina fisica",

    # Cirugía General y del Aparato Digestivo
    "394609007": "general surgery;cirugia general;general surgeon;cirujano general;abdominal surgery;cirugia abdominal",

    # Neurocirugía (evitar "neuro")
    "394610002": "neurosurgery;neurocirugia;neurosurgeon;neurocirujano;brain surgery;spine surgery;cirugia cerebral;cirugia espinal",

    # Cirugía Plástica, Estética y Reparadora
    "394611003": "plastic surgery;cirugia plastica;plastic surgeon;cirujano plastico;reconstructive surgery;aesthetic surgery;cirugia estetica;cirugia reparadora",

    # Urología
    "394612005": "urology;urologia;urologist;urologo;urinary;urinario;bladder;vejiga;prostate;prostata",

    # Medicina Nuclear
    "394649004": "nuclear medicine;medicina nuclear;nuclear imaging;gammagrafia;pet scan;spect",

    # Medicina Legal y Forense
    "394733009": "forensic medicine;medicina forense;forensic pathology;medicina legal;forensic;forense;medicolegal",

    # Cirugía Ortopédica y Traumatología
    "394801008": "orthopedic surgery;orthopaedic surgery;cirugia ortopedica;traumatology;traumatologia;orthopedist;orthopaedist;traumatologo;bone surgery;fracture;fractura",

    # Hematología y Hemoterapia
    "394803006": "hematology;haematology;hematologia;hematologist;haematologist;hematologo;blood disease;blood disorders;hemotherapy;hemoterapia;coagulation;coagulacion",

    # Neurofisiología Clínica (evitar "neuro")
    "394809005": "neurophysiology;neurofisiologia;neurophysiologist;neurofisiologo;eeg;emg;electroencephalography;electromyography;evoked potentials",

    # Reumatología
    "394810000": "rheumatology;reumatologia;rheumatologist;reumatologo;arthritis;artritis;autoimmune;autoinmune;joint disease",

    # Geriatría
    "394811001": "geriatric medicine;geriatria;geriatrician;geriatra;elderly;anciano;aging;envejecimiento;gerontology",

    # Medicina del Trabajo
    "394821009": "occupational medicine;medicina del trabajo;occupational health;salud laboral;industrial medicine;medicina laboral;workplace health",

    # Radiodiagnóstico (Radiología)
    "394914008": "radiology;radiologia;radiologist;radiologo;x-ray;radiografia;imaging;imagen diagnostica;diagnostic imaging;radiodiagnostico",

    # Análisis Clínicos / Bioquímica Clínica
    "394915009": "clinical pathology;patologia clinica;clinical laboratory;laboratorio clinico;clinical chemistry;bioquimica clinica;analisis clinicos;laboratory medicine",

    # Pediatría y Áreas Específicas
    "394537008": "pediatrics;paediatrics;pediatria;pediatrician;paediatrician;pediatra;child health;salud infantil;children medicine",

    # Cirugía Pediátrica
    "394539006": "pediatric surgery;paediatric surgery;cirugia pediatrica;pediatric surgeon;paediatric surgeon;cirujano pediatrico;child surgery",

    # Microbiología y Parasitología
    "408454008": "clinical microbiology;microbiologia clinica;microbiology;microbiologia;microbiologist;microbiologo;parasitology;parasitologia;bacteriology;bacteriologia;virology;virologia",

    # Angiología y Cirugía Vascular
    "408463005": "vascular surgery;cirugia vascular;vascular surgeon;cirujano vascular;angiology;angiologia;angiologist;angiologo;vein;vena;artery;arteria",

    # Cirugía Oral y Maxilofacial
    "408465003": "oral and maxillofacial surgery;cirugia oral y maxilofacial;maxillofacial surgery;cirugia maxilofacial;oral surgery;cirugia oral;jaw surgery",

    # Cirugía Cardiovascular (evitar "cardio")
    "408466002": "cardiac surgery;cirugia cardiaca;cardiovascular surgery;cirugia cardiovascular;heart surgery;cirugia del corazon;cardiothoracic surgery",

    # Cirugía Torácica
    "408471009": "thoracic surgery;cirugia toracica;chest surgery;cirugia de torax;lung surgery;cirugia pulmonar",

    # Medicina Intensiva
    "408478003": "critical care medicine;medicina intensiva;intensive care;cuidados intensivos;icu;uci;intensivist;intensivista",

    # Inmunología
    "408480009": "clinical immunology;inmunologia clinica;immunology;inmunologia;immunologist;inmunologo;immune;inmune;immunodeficiency;inmunodeficiencia",

    # Medicina Preventiva y Salud Pública
    "409968004": "preventive medicine;medicina preventiva;public health;salud publica;epidemiology;epidemiologia;prevention;prevencion",

    # Neumología
    "418112009": "pulmonary medicine;neumologia;pulmonology;pulmonologist;neumologo;lung;pulmon;respiratory;respiratorio;bronchology",

    # Otorrinolaringología
    "418960008": "otolaryngology;otorrinolaringologia;ent;orl;otorhinolaryngology;ear nose throat;oido nariz garganta;otologist;otologo",

    # Medicina Interna
    "419192003": "internal medicine;medicina interna;internist;internista;general internal medicine;hospitalist",

    # Medicina Familiar y Comunitaria
    "419772000": "family practice;family medicine;medicina familiar;medicina comunitaria;family physician;medico de familia;general practitioner;primary care;atencion primaria",

    # Oncología Radioterápica (evitar "onco")
    "419815003": "radiation oncology;oncologia radioterapica;radiotherapy;radioterapia;radiation therapy;radiation oncologist;radioterapist;radioterapeuta",
}


def print_synonyms():
    """Muestra los sinónimos que se aplicarán."""
    print("\n" + "=" * 70)
    print("SINÓNIMOS EXCLUSIVOS PARA ESPECIALIDADES MIR (46)")
    print("=" * 70)

    for code, synonyms in sorted(MIR_SYNONYMS.items()):
        synonym_list = synonyms.split(";")
        print(f"\n{code}: ({len(synonym_list)} sinónimos)")
        print(f"  {synonyms[:80]}..." if len(synonyms) > 80 else f"  {synonyms}")

    print("\n" + "=" * 70)
    print(f"Total: {len(MIR_SYNONYMS)} especialidades con sinónimos")
    print("=" * 70 + "\n")


def apply_synonyms():
    """Aplica los sinónimos a la BD."""
    print("\nAplicando sinónimos a la BD...")

    with db.transaction() as cur:
        updated = 0
        for code, synonyms in MIR_SYNONYMS.items():
            cur.execute("""
                UPDATE snomed_specialties
                SET synonyms = %s
                WHERE snomed_code = %s AND is_mir_spain = TRUE
            """, (synonyms, code))

            if cur.rowcount > 0:
                updated += 1

    print(f"\n✓ Sinónimos aplicados a {updated} especialidades MIR")


def verify_exclusivity():
    """Verifica que no hay sinónimos repetidos entre especialidades."""
    print("\nVerificando exclusividad de sinónimos...")

    all_synonyms = {}  # synonym -> list of codes that use it
    issues = []

    for code, synonyms_str in MIR_SYNONYMS.items():
        for synonym in synonyms_str.split(";"):
            synonym = synonym.strip().lower()
            if synonym in all_synonyms:
                all_synonyms[synonym].append(code)
            else:
                all_synonyms[synonym] = [code]

    # Encontrar duplicados
    for synonym, codes in all_synonyms.items():
        if len(codes) > 1:
            issues.append((synonym, codes))

    if issues:
        print("\n⚠️  SINÓNIMOS DUPLICADOS ENCONTRADOS:")
        for synonym, codes in issues:
            print(f"  '{synonym}' usado en: {', '.join(codes)}")
        return False
    else:
        print("✓ Todos los sinónimos son exclusivos")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Pobla sinónimos exclusivos para especialidades MIR"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar sinónimos a la BD (por defecto solo muestra)"
    )

    args = parser.parse_args()

    # Mostrar sinónimos
    print_synonyms()

    # Verificar exclusividad
    is_exclusive = verify_exclusivity()

    if args.apply:
        if is_exclusive:
            apply_synonyms()
        else:
            print("\n❌ No se aplican cambios. Corrige los duplicados primero.")
            sys.exit(1)
    else:
        print("\nUsa --apply para aplicar los sinónimos a la BD")


if __name__ == "__main__":
    main()
