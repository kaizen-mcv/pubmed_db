-- Tabla de mapeo MeSH Tree Number → SNOMED CT Specialty
-- Permite clasificar artículos por especialidad médica basándose en sus términos MeSH
-- Fuente: Mapeo manual basado en categorías MeSH (https://meshb.nlm.nih.gov/treeView)

-- Eliminar tabla existente
DROP TABLE IF EXISTS mesh_to_snomed CASCADE;

-- Crear tabla de mapeo
CREATE TABLE mesh_to_snomed (
    id SERIAL PRIMARY KEY,
    mesh_tree_prefix VARCHAR(20) NOT NULL,           -- Prefijo del tree number (ej: "C14", "C14.280")
    snomed_code VARCHAR(20) NOT NULL REFERENCES snomed_specialties(snomed_code),
    description VARCHAR(200),                         -- Descripción de la categoría MeSH
    confidence DECIMAL(3,2) DEFAULT 0.90,            -- Confianza del mapeo (0.00-1.00)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(mesh_tree_prefix, snomed_code)
);

-- =====================================================
-- MAPEOS POR CATEGORÍA MeSH (C = Diseases)
-- =====================================================

INSERT INTO mesh_to_snomed (mesh_tree_prefix, snomed_code, description, confidence) VALUES
-- C01: Bacterial Infections and Mycoses → Infectious diseases / Microbiology
('C01', '394807007', 'Bacterial Infections and Mycoses', 0.85),
('C01', '408454008', 'Bacterial Infections and Mycoses', 0.80),

-- C02: Virus Diseases → Infectious diseases
('C02', '394807007', 'Virus Diseases', 0.85),

-- C03: Parasitic Diseases → Infectious diseases / Microbiology
('C03', '394807007', 'Parasitic Diseases', 0.85),
('C03', '408454008', 'Parasitic Diseases', 0.75),

-- C04: Neoplasms → Medical oncology
('C04', '394593009', 'Neoplasms', 0.90),
('C04', '419815003', 'Neoplasms (radiation therapy)', 0.70),

-- C05: Musculoskeletal Diseases → Rheumatology / Trauma and orthopedics
('C05', '394810000', 'Musculoskeletal Diseases', 0.85),
('C05', '394801008', 'Musculoskeletal Diseases (surgical)', 0.75),

-- C06: Digestive System Diseases → Gastroenterology
('C06', '394584008', 'Digestive System Diseases', 0.90),

-- C07: Stomatognathic Diseases → Oral and maxillofacial surgery
('C07', '408465003', 'Stomatognathic Diseases', 0.85),

-- C08: Respiratory Tract Diseases → Pulmonary medicine
('C08', '418112009', 'Respiratory Tract Diseases', 0.90),

-- C09: Otorhinolaryngologic Diseases → Otolaryngology
('C09', '418960008', 'Otorhinolaryngologic Diseases', 0.95),

-- C10: Nervous System Diseases → Neurology / Neurosurgery
('C10', '394591006', 'Nervous System Diseases', 0.90),
('C10', '394610002', 'Nervous System Diseases (surgical)', 0.70),

-- C11: Eye Diseases → Ophthalmology
('C11', '394594003', 'Eye Diseases', 0.95),

-- C12: Male Urogenital Diseases → Urology
('C12', '394612005', 'Male Urogenital Diseases', 0.90),

-- C13: Female Urogenital Diseases and Pregnancy Complications → Obstetrics and gynecology
('C13', '394585009', 'Female Urogenital Diseases and Pregnancy Complications', 0.90),

-- C14: Cardiovascular Diseases → Cardiology / Cardiac surgery / Vascular surgery
('C14', '394579002', 'Cardiovascular Diseases', 0.90),
('C14.280', '394579002', 'Heart Diseases', 0.95),
('C14.907', '408463005', 'Vascular Diseases', 0.85),
('C14.280', '408466002', 'Heart Diseases (surgical)', 0.70),

-- C15: Hemic and Lymphatic Diseases → Clinical hematology
('C15', '394803006', 'Hemic and Lymphatic Diseases', 0.90),

-- C16: Congenital, Hereditary, and Neonatal Diseases → Pediatrics / Clinical genetics
('C16', '394537008', 'Congenital, Hereditary, and Neonatal Diseases', 0.80),
('C16', '394580004', 'Congenital, Hereditary, and Neonatal Diseases (genetics)', 0.75),

-- C17: Skin and Connective Tissue Diseases → Dermatology / Rheumatology
('C17.800', '394582007', 'Skin Diseases', 0.95),
('C17.300', '394810000', 'Connective Tissue Diseases', 0.85),

-- C18: Nutritional and Metabolic Diseases → Endocrinology
('C18', '394583002', 'Nutritional and Metabolic Diseases', 0.85),

-- C19: Endocrine System Diseases → Endocrinology
('C19', '394583002', 'Endocrine System Diseases', 0.95),

-- C20: Immune System Diseases → Clinical immunology / Allergy
('C20', '408480009', 'Immune System Diseases', 0.85),
('C20.543', '408439002', 'Hypersensitivity (Allergy)', 0.90),

-- C21: Disorders of Environmental Origin → Occupational medicine
('C21', '394821009', 'Disorders of Environmental Origin', 0.70),

-- C22: Animal Diseases (generally not mapped to human specialties)

-- C23: Pathological Conditions, Signs and Symptoms → General pathology
('C23', '394915009', 'Pathological Conditions, Signs and Symptoms', 0.70),
('C23', '394597005', 'Pathological Conditions (histopathology)', 0.70),

-- C24: Occupational Diseases → Occupational medicine
('C24', '394821009', 'Occupational Diseases', 0.90),

-- C25: Chemically-Induced Disorders → Toxicology / Clinical pharmacology
('C25', '409967009', 'Chemically-Induced Disorders', 0.80),
('C25', '394600006', 'Chemically-Induced Disorders (pharmacology)', 0.75),

-- C26: Wounds and Injuries → Trauma and orthopedics / Surgery
('C26', '394801008', 'Wounds and Injuries', 0.85),
('C26', '394609007', 'Wounds and Injuries (general surgery)', 0.75),

-- =====================================================
-- MAPEOS POR CATEGORÍA MeSH (F = Psychiatry and Psychology)
-- =====================================================

-- F03: Mental Disorders → Psychiatry
('F03', '394587001', 'Mental Disorders', 0.90),
('F03.625', '394588006', 'Child and Adolescent Mental Disorders', 0.90),

-- =====================================================
-- MAPEOS POR CATEGORÍA MeSH (E = Analytical, Diagnostic and Therapeutic Techniques)
-- =====================================================

-- E01.370.350: Diagnostic Imaging → Radiology
('E01.370.350', '394914008', 'Diagnostic Imaging', 0.85),

-- E01.370.350.700: Radiography → Radiology
('E01.370.350.700', '394914008', 'Radiography', 0.90),

-- E01.370.350.600: Nuclear Medicine Imaging → Nuclear medicine
('E01.370.350.600', '394649004', 'Nuclear Medicine Imaging', 0.95),

-- E02.319: Interventional radiology
('E02.319', '408455009', 'Endovascular Procedures', 0.85),

-- E02.760: Physical Therapy → Rehabilitation
('E02.760', '394602003', 'Physical Therapy Modalities', 0.85),

-- E04: Surgical Procedures → Surgery-general
('E04', '394609007', 'Surgical Procedures, Operative', 0.80),

-- E04.100.814: Neurosurgical Procedures → Neurosurgery
('E04.100.814', '394610002', 'Neurosurgical Procedures', 0.95),

-- E04.210: Digestive System Surgical Procedures → General surgery
('E04.210', '394609007', 'Digestive System Surgical Procedures', 0.90),

-- E04.502: Obstetric Surgical Procedures → Obstetrics and gynecology
('E04.502', '394585009', 'Obstetric Surgical Procedures', 0.90),

-- E04.525: Ophthalmologic Surgical Procedures → Ophthalmology
('E04.525', '394594003', 'Ophthalmologic Surgical Procedures', 0.95),

-- E04.540: Orthopedic Procedures → Trauma and orthopedics
('E04.540', '394801008', 'Orthopedic Procedures', 0.95),

-- E04.580: Plastic Surgery → Plastic surgery
('E04.580', '394611003', 'Plastic Surgery Procedures', 0.95),

-- E04.650: Thoracic Surgical Procedures → Cardiothoracic surgery
('E04.650', '408471009', 'Thoracic Surgical Procedures', 0.85),
('E04.650', '408466002', 'Thoracic Surgical Procedures (cardiac)', 0.80),

-- E04.680: Urologic Surgical Procedures → Urology
('E04.680', '394612005', 'Urologic Surgical Procedures', 0.95),

-- E04.928: Vascular Surgical Procedures → Vascular surgery
('E04.928', '408463005', 'Vascular Surgical Procedures', 0.95),

-- =====================================================
-- MAPEOS POR CATEGORÍA MeSH (G = Phenomena and Processes)
-- =====================================================

-- G09: Circulatory and Respiratory Physiological Phenomena
('G09.330', '394579002', 'Cardiovascular Physiological Phenomena', 0.70),
('G09.772', '418112009', 'Respiratory Physiological Phenomena', 0.70),

-- =====================================================
-- MAPEOS POR CATEGORÍA MeSH (N = Health Care)
-- =====================================================

-- N02.421.143: Critical Care → Critical care medicine
('N02.421.143', '408478003', 'Critical Care', 0.95),

-- N02.421.585: Palliative Care → Palliative medicine
('N02.421.585', '394806003', 'Palliative Care', 0.90),

-- N02.421.726: Preventive Health Services → Preventive medicine
('N02.421.726', '409968004', 'Preventive Health Services', 0.85),

-- N02.421.784: Rehabilitation → Rehabilitation medicine
('N02.421.784', '394602003', 'Rehabilitation', 0.90),

-- N06.850.520: Forensic Medicine → Medical specialty (OTHER) - Medicina Legal
('N06.850.520', '394733009', 'Forensic Medicine', 0.85);

-- =====================================================
-- ÍNDICES
-- =====================================================

CREATE INDEX idx_mesh_to_snomed_prefix ON mesh_to_snomed(mesh_tree_prefix);
CREATE INDEX idx_mesh_to_snomed_snomed ON mesh_to_snomed(snomed_code);

-- Índice para búsquedas por prefijo (LIKE 'C14%')
CREATE INDEX idx_mesh_to_snomed_prefix_pattern ON mesh_to_snomed(mesh_tree_prefix varchar_pattern_ops);

-- =====================================================
-- COMENTARIOS DE DOCUMENTACIÓN
-- =====================================================

COMMENT ON TABLE mesh_to_snomed IS 'Mapeo de prefijos MeSH Tree Number a códigos SNOMED CT de especialidades médicas';
COMMENT ON COLUMN mesh_to_snomed.mesh_tree_prefix IS 'Prefijo del tree number MeSH (ej: C14, C14.280). Un artículo con MeSH tree C14.280.647 matchea con C14.280 y C14';
COMMENT ON COLUMN mesh_to_snomed.snomed_code IS 'Código SNOMED CT de la especialidad médica';
COMMENT ON COLUMN mesh_to_snomed.description IS 'Descripción de la categoría MeSH';
COMMENT ON COLUMN mesh_to_snomed.confidence IS 'Nivel de confianza del mapeo (0.00-1.00). Mapeos directos ~0.90, mapeos secundarios ~0.70';

-- =====================================================
-- FUNCIÓN AUXILIAR: Encontrar especialidades para un tree number
-- =====================================================

CREATE OR REPLACE FUNCTION get_specialties_for_mesh_tree(tree_number VARCHAR)
RETURNS TABLE (
    snomed_code VARCHAR,
    specialty_name_en VARCHAR,
    specialty_name_es VARCHAR,
    confidence DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.snomed_code,
        ms.name_en::VARCHAR,
        ms.name_es::VARCHAR,
        m.confidence
    FROM mesh_to_snomed m
    JOIN snomed_specialties ms ON m.snomed_code = ms.snomed_code
    WHERE tree_number LIKE m.mesh_tree_prefix || '%'
    ORDER BY LENGTH(m.mesh_tree_prefix) DESC, m.confidence DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_specialties_for_mesh_tree IS 'Dado un tree number MeSH, retorna las especialidades SNOMED CT asociadas ordenadas por especificidad y confianza';

-- =====================================================
-- EJEMPLO DE USO
-- =====================================================

-- Ejemplo: Encontrar especialidades para un artículo con MeSH "Heart Failure" (tree: C14.280.434)
-- SELECT * FROM get_specialties_for_mesh_tree('C14.280.434');
-- Resultado: Cardiology (C14.280 match), Cardiology (C14 match)

-- Ejemplo: Clasificar un artículo con múltiples MeSH terms
-- WITH article_mesh AS (
--     SELECT unnest(string_to_array('C14.280.434;C08.381', ';')) as tree_num
-- )
-- SELECT DISTINCT ON (snomed_code) *
-- FROM article_mesh, get_specialties_for_mesh_tree(tree_num)
-- ORDER BY snomed_code, confidence DESC;
