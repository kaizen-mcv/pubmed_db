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
('N06.850.520', '394733009', 'Forensic Medicine', 0.85),

-- =====================================================
-- MAPEOS ADICIONALES (Subcategorías específicas)
-- =====================================================

-- Subcategorías de Neoplasms (C04)
('C04.588.149', '394579002', 'Breast Neoplasms (cardiology overlap)', 0.60),
('C04.588.180', '394584008', 'Colorectal Neoplasms (gastro)', 0.80),
('C04.588.274', '418112009', 'Lung Neoplasms (pulmonary)', 0.75),
('C04.588.322', '394803006', 'Hematologic Neoplasms', 0.90),
('C04.588.364', '394612005', 'Kidney Neoplasms (urology)', 0.85),
('C04.588.443', '394612005', 'Urinary Bladder Neoplasms', 0.85),
('C04.588.945', '394612005', 'Urogenital Neoplasms', 0.85),
('C04.588.614', '394594003', 'Ocular Neoplasms', 0.85),
('C04.588.839', '394582007', 'Skin Neoplasms', 0.85),

-- Subcategorías de Nervous System (C10)
('C10.228', '394591006', 'Central Nervous System Diseases', 0.90),
('C10.228.140', '394591006', 'Brain Diseases', 0.95),
('C10.228.140.300', '394591006', 'Cerebrovascular Disorders', 0.90),
('C10.228.662', '394591006', 'Movement Disorders', 0.90),
('C10.574', '394591006', 'Neurodegenerative Diseases', 0.95),
('C10.597', '394591006', 'Neurologic Manifestations', 0.80),
('C10.668', '394591006', 'Neuromuscular Diseases', 0.85),
('C10.720', '394610002', 'Peripheral Nervous System Diseases (surgical)', 0.75),

-- Subcategorías de Cardiovascular (C14)
('C14.280.067', '394579002', 'Arrhythmias, Cardiac', 0.95),
('C14.280.238', '394579002', 'Cardiomyopathies', 0.95),
('C14.280.383', '394579002', 'Heart Defects, Congenital', 0.90),
('C14.280.434', '394579002', 'Heart Failure', 0.95),
('C14.280.484', '394579002', 'Heart Valve Diseases', 0.90),
('C14.280.647', '394579002', 'Myocardial Ischemia', 0.95),
('C14.907.137', '408463005', 'Arterial Occlusive Diseases', 0.90),
('C14.907.253', '408463005', 'Embolism and Thrombosis', 0.85),
('C14.907.940', '408463005', 'Venous Thrombosis', 0.90),

-- Subcategorías de Digestive System (C06)
('C06.130', '394584008', 'Biliary Tract Diseases', 0.90),
('C06.198', '394584008', 'Digestive System Abnormalities', 0.85),
('C06.267', '394584008', 'Esophageal Diseases', 0.95),
('C06.301', '394584008', 'Gastroenteritis', 0.90),
('C06.405', '394584008', 'Gastrointestinal Diseases', 0.95),
('C06.552', '394584008', 'Liver Diseases', 0.95),
('C06.689', '394584008', 'Pancreatic Diseases', 0.90),

-- Subcategorías de Respiratory (C08)
('C08.127', '418112009', 'Bronchial Diseases', 0.95),
('C08.381', '418112009', 'Lung Diseases', 0.95),
('C08.381.495', '418112009', 'Lung Diseases, Interstitial', 0.90),
('C08.381.520', '418112009', 'Lung Diseases, Obstructive', 0.95),
('C08.618', '418112009', 'Respiration Disorders', 0.85),
('C08.730', '418112009', 'Respiratory Tract Infections', 0.85),

-- Subcategorías de Endocrine (C19)
('C19.246', '394583002', 'Diabetes Mellitus', 0.95),
('C19.700', '394583002', 'Thyroid Diseases', 0.95),
('C19.053', '394583002', 'Adrenal Gland Diseases', 0.90),
('C19.391', '394583002', 'Gonadal Disorders', 0.85),

-- Subcategorías de Musculoskeletal (C05)
('C05.116', '394801008', 'Bone Diseases', 0.85),
('C05.550', '394810000', 'Joint Diseases', 0.90),
('C05.651', '394810000', 'Muscular Diseases', 0.85),
('C05.799', '394810000', 'Rheumatic Diseases', 0.95),
('C05.116.198', '394801008', 'Bone Fractures', 0.90),
('C05.550.114', '394810000', 'Arthritis', 0.95),
('C05.550.114.606', '394810000', 'Arthritis, Rheumatoid', 0.95),

-- Subcategorías de Kidney/Urinary (C12/C13)
('C12.777.419', '394589003', 'Kidney Diseases', 0.95),
('C12.777.419.403', '394589003', 'Glomerulonephritis', 0.95),
('C12.777.419.570', '394589003', 'Nephrosis', 0.90),
('C12.777.419.780', '394589003', 'Renal Insufficiency', 0.95),

-- Subcategorías de Pediatrics
('C16.614', '394537008', 'Neonatal Diseases', 0.95),
('C16.300', '394580004', 'Genetic Diseases, Inborn', 0.90),

-- Subcategorías de Mental Disorders (F03)
('F03.087', '394587001', 'Anxiety Disorders', 0.90),
('F03.300', '394587001', 'Dissociative Disorders', 0.85),
('F03.550', '394587001', 'Mood Disorders', 0.95),
('F03.550.325', '394587001', 'Depression', 0.95),
('F03.600', '394587001', 'Neurotic Disorders', 0.85),
-- F03.625 ya definido arriba como Child and Adolescent Mental Disorders
('F03.700', '394587001', 'Schizophrenia Spectrum', 0.95),
('F03.875', '394587001', 'Somatoform Disorders', 0.80),
('F03.900', '408468001', 'Substance-Related Disorders', 0.85),

-- =====================================================
-- MAPEOS POR CATEGORÍA MeSH (A = Anatomy - para investigación)
-- =====================================================

('A01.923', '408463005', 'Vascular System anatomy research', 0.60),
('A02', '394801008', 'Musculoskeletal System anatomy', 0.60),
('A03', '394584008', 'Digestive System anatomy', 0.60),
('A04', '418112009', 'Respiratory System anatomy', 0.60),
('A05.360', '394612005', 'Urogenital System anatomy', 0.60),
('A06', '394583002', 'Endocrine System anatomy', 0.60),
('A07', '394579002', 'Cardiovascular System anatomy', 0.60),
('A08', '394591006', 'Nervous System anatomy', 0.65),
('A09', '394594003', 'Sense Organs anatomy', 0.65),
('A10', '394582007', 'Tissues (integumentary)', 0.55),
('A14', '394609007', 'Stomatognathic System anatomy', 0.60),
('A15', '394803006', 'Hemic and Immune Systems anatomy', 0.60),

-- =====================================================
-- MAPEOS POR CATEGORÍA MeSH (D = Chemicals and Drugs)
-- =====================================================

('D27.505.954.248', '394593009', 'Antineoplastic Agents', 0.75),
('D27.505.954.248.025', '394593009', 'Antimetabolites, Antineoplastic', 0.80),
('D27.505.696.277.100', '394579002', 'Antiarrhythmia Agents', 0.75),
('D27.505.696.277.600', '394579002', 'Antihypertensive Agents', 0.75),
('D27.505.696.377', '418112009', 'Bronchodilator Agents', 0.70),
('D27.505.696.560', '394584008', 'Gastrointestinal Agents', 0.75),
('D27.505.519.389', '394583002', 'Hypoglycemic Agents', 0.80),
('D27.505.954.427', '394807007', 'Anti-Infective Agents', 0.70),
('D27.505.954.427.040', '394807007', 'Anti-Bacterial Agents', 0.80),
('D27.505.954.427.080', '394807007', 'Antifungal Agents', 0.75),
('D27.505.954.427.220', '394807007', 'Antiviral Agents', 0.80),
('D27.505.696.663', '394587001', 'Psychotropic Drugs', 0.75),

-- =====================================================
-- MAPEOS POR CATEGORÍA MeSH (B = Organisms - for microbiology)
-- =====================================================

('B01', '408454008', 'Eukaryota (microbiology)', 0.60),
('B02', '408454008', 'Archaea (microbiology)', 0.70),
('B03', '394807007', 'Bacteria (infectious diseases)', 0.75),
('B04', '394807007', 'Viruses (infectious diseases)', 0.75),

-- =====================================================
-- MAPEOS POR CATEGORÍA MeSH (H = Disciplines and Occupations)
-- =====================================================

('H02.403', '394821009', 'Occupational Medicine research', 0.85),
('H02.478', '409968004', 'Preventive Medicine research', 0.80),
('H02.403.720', '408443003', 'Sports Medicine', 0.85);

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

DROP FUNCTION IF EXISTS get_specialties_for_mesh_tree(VARCHAR);

CREATE OR REPLACE FUNCTION get_specialties_for_mesh_tree(tree_number VARCHAR)
RETURNS TABLE (
    snomed_code VARCHAR,
    specialty_name_en VARCHAR,
    specialty_name_snomed VARCHAR,
    specialty_name_es VARCHAR,
    confidence DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.snomed_code,
        ms.name_en::VARCHAR,
        ms.name_snomed::VARCHAR,
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
