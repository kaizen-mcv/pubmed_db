-- ============================================================================
-- Tabla de Especialidades Médicas (SNOMED CT)
-- Fuente SNOMED CT: https://www.hl7.org/fhir/valueset-c80-practice-codes.html
-- Fuente MIR España: https://fse.mscbs.gob.es/fseweb/
-- ============================================================================

-- Eliminar tabla existente
DROP TABLE IF EXISTS snomed_specialties CASCADE;

-- Crear tabla con estructura completa
CREATE TABLE snomed_specialties (
    id SERIAL PRIMARY KEY,
    snomed_code VARCHAR(20) UNIQUE NOT NULL,      -- Código SNOMED CT
    name_en VARCHAR(200) NOT NULL,                 -- Nombre simplificado inglés
    name_snomed VARCHAR(200),                      -- Nombre oficial FHIR (con "qualifier value")
    name_es VARCHAR(200),                          -- Traducción al español
    synonyms TEXT,                                 -- Sinónimos para matching (separados por ;)
    is_mir_spain BOOLEAN DEFAULT FALSE,            -- TRUE si es especialidad MIR española
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked DATE                              -- Última sincronización con API FHIR
);

-- ============================================================================
-- Insertar especialidades SNOMED CT (117 totales, 45 MIR españolas)
-- Las especialidades MIR tienen name_es, synonyms e is_mir_spain=TRUE
-- ============================================================================

INSERT INTO snomed_specialties (snomed_code, name_en, name_snomed, name_es, synonyms, is_mir_spain) VALUES

-- ============================================================================
-- ESPECIALIDADES MIR ESPAÑA (45)
-- ============================================================================
('408439002', 'Allergy', NULL, 'Alergología', 'allergy;allergology;alergologia;allergist;alergologo;allergic;alergico', TRUE),
('394577000', 'Anesthetics', 'Anaesthetics', 'Anestesiología y Reanimación', 'anesthesia;anaesthesia;anestesia;anesthesiology;anaesthesiology;anestesiologia;reanimacion;anesthetist;anaesthetist;anestesiologo', TRUE),
('394579002', 'Cardiology', 'Cardiology (qualifier value)', 'Cardiología', 'cardiology;cardiologia;cardiologist;cardiologo;heart disease;cardiac medicine', TRUE),
('394803006', 'Clinical hematology', 'Clinical haematology', 'Hematología y Hemoterapia', 'hematology;haematology;hematologia;hematologist;haematologist;hematologo;blood disease;blood disorders;hemotherapy;hemoterapia;coagulation;coagulacion', TRUE),
('408480009', 'Clinical immunology', 'Clinical immunology (qualifier value)', 'Inmunología', 'clinical immunology;inmunologia clinica;immunology;inmunologia;immunologist;inmunologo;immune;inmune;immunodeficiency;inmunodeficiencia', TRUE),
('408454008', 'Clinical microbiology', 'Clinical microbiology (qualifier value)', 'Microbiología y Parasitología', 'clinical microbiology;microbiologia clinica;microbiology;microbiologia;microbiologist;microbiologo;parasitology;parasitologia;bacteriology;bacteriologia;virology;virologia', TRUE),
('394809005', 'Clinical neuro-physiology', 'Clinical neuro-physiology (qualifier value)', 'Neurofisiología Clínica', 'neurophysiology;neurofisiologia;neurophysiologist;neurofisiologo;eeg;emg;electroencephalography;electromyography;evoked potentials', TRUE),
('394600006', 'Clinical pharmacology', 'Clinical pharmacology (qualifier value)', 'Farmacología Clínica', 'clinical pharmacology;farmacologia clinica;pharmacologist;farmacologo;drug therapy;pharmacotherapy', TRUE),
('408478003', 'Critical care medicine', 'Critical care medicine (qualifier value)', 'Medicina Intensiva', 'critical care medicine;medicina intensiva;intensive care;cuidados intensivos;icu;uci;intensivist;intensivista', TRUE),
('394582007', 'Dermatology', 'Dermatology (qualifier value)', 'Dermatología Médico-Quirúrgica y Venereología', 'dermatology;dermatologia;dermatologist;dermatologo;skin;cutaneous;piel;cutaneo', TRUE),
('394583002', 'Endocrinology', 'Endocrinology (qualifier value)', 'Endocrinología y Nutrición', 'endocrinology;endocrinologia;endocrinologist;endocrinologo;hormone;hormonal;diabetes;thyroid;tiroides;metabolic;metabolismo', TRUE),
('419772000', 'Family practice', 'Family practice (qualifier value)', 'Medicina Familiar y Comunitaria', 'family practice;family medicine;medicina familiar;medicina comunitaria;family physician;medico de familia;general practitioner;primary care;atencion primaria', TRUE),
('394584008', 'Gastroenterology', 'Gastroenterology (qualifier value)', 'Aparato Digestivo', 'gastroenterology;gastroenterologia;gastroenterologist;gastroenterologo;digestive;digestivo;gastrointestinal;gi tract', TRUE),
('394915009', 'General pathology', 'General pathology (specialty) (qualifier value)', 'Análisis Clínicos / Bioquímica Clínica', 'clinical pathology;patologia clinica;clinical laboratory;laboratorio clinico;clinical chemistry;bioquimica clinica;analisis clinicos;laboratory medicine', TRUE),
('394811001', 'Geriatric medicine', 'Geriatric medicine (qualifier value)', 'Geriatría', 'geriatric medicine;geriatria;geriatrician;geriatra;elderly;anciano;aging;envejecimiento;gerontology', TRUE),
('394597005', 'Histopathology', 'Histopathology (qualifier value)', 'Anatomía Patológica', 'histopathology;histopatologia;anatomia patologica;pathologist;patologo;biopsy;biopsia;autopsy;autopsia', TRUE),
('419192003', 'Internal medicine', 'Internal medicine (qualifier value)', 'Medicina Interna', 'internal medicine;medicina interna;internist;internista;general internal medicine;hospitalist', TRUE),
('394593009', 'Medical oncology', 'Medical oncology (qualifier value)', 'Oncología Médica', 'medical oncology;oncologia medica;medical oncologist;oncologo medico;chemotherapy;quimioterapia;cancer medicine', TRUE),
('394733009', 'Medical specialty (OTHER)', 'Medical specialty (qualifier value)', 'Medicina Legal y Forense', 'forensic medicine;medicina forense;forensic pathology;medicina legal;forensic;forense;medicolegal', TRUE),
('394589003', 'Nephrology', 'Nephrology (qualifier value)', 'Nefrología', 'nephrology;nefrologia;nephrologist;nefrologo;kidney;renal;riñon;dialysis;dialisis', TRUE),
('394591006', 'Neurology', 'Neurology (qualifier value)', 'Neurología', 'neurology;neurologia;neurologist;neurologo;neurological;neurologico;brain disease;nervous system disease', TRUE),
('394649004', 'Nuclear medicine', 'Nuclear medicine - specialty (qualifier value)', 'Medicina Nuclear', 'nuclear medicine;medicina nuclear;nuclear imaging;gammagrafia;pet scan;spect', TRUE),
('394585009', 'Obstetrics and gynecology', 'Obstetrics and gynaecology', 'Obstetricia y Ginecología', 'obstetrics;obstetricia;gynecology;gynaecology;ginecologia;obgyn;obstetrician;gynecologist;obstetra;ginecologo;maternal;pregnancy;embarazo', TRUE),
('394821009', 'Occupational medicine', 'Occupational medicine (qualifier value)', 'Medicina del Trabajo', 'occupational medicine;medicina del trabajo;occupational health;salud laboral;industrial medicine;medicina laboral;workplace health', TRUE),
('394594003', 'Ophthalmology', 'Ophthalmology (qualifier value)', 'Oftalmología', 'ophthalmology;oftalmologia;ophthalmologist;oftalmologo;eye;ocular;vision;ojo;ojos;ophthalmic', TRUE),
('418960008', 'Otolaryngology', 'Otolaryngology (qualifier value)', 'Otorrinolaringología', 'otolaryngology;otorrinolaringologia;ent;orl;otorhinolaryngology;ear nose throat;oido nariz garganta;otologist;otologo', TRUE),
('394588006', 'Pediatric (Child and adolescent) psychiatry', 'Child and adolescent psychiatry (qualifier value)', 'Psiquiatría Infantil y de la Adolescencia', 'child psychiatry;adolescent psychiatry;psiquiatria infantil;psiquiatria adolescente;child mental health', TRUE),
('394539006', 'Pediatric surgery', 'Paediatric surgery', 'Cirugía Pediátrica', 'pediatric surgery;paediatric surgery;cirugia pediatrica;pediatric surgeon;paediatric surgeon;cirujano pediatrico;child surgery', TRUE),
('394537008', 'Pediatrics', NULL, 'Pediatría y Áreas Específicas', 'pediatrics;paediatrics;pediatria;pediatrician;paediatrician;pediatra;child health;salud infantil;children medicine', TRUE),
('409968004', 'Preventive medicine', 'Preventive medicine (qualifier value)', 'Medicina Preventiva y Salud Pública', 'preventive medicine;medicina preventiva;public health;salud publica;epidemiology;epidemiologia;prevention;prevencion', TRUE),
('394587001', 'Psychiatry', 'Psychiatry (qualifier value)', 'Psiquiatría', 'psychiatry;psiquiatria;psychiatrist;psiquiatra;mental health;salud mental;psychiatric', TRUE),
('418112009', 'Pulmonary medicine', 'Pulmonary medicine (qualifier value)', 'Neumología', 'pulmonary medicine;neumologia;pulmonology;pulmonologist;neumologo;lung;pulmon;respiratory;respiratorio;bronchology', TRUE),
('419815003', 'Radiation oncology', 'Radiation oncology (qualifier value)', 'Oncología Radioterápica', 'radiation oncology;oncologia radioterapica;radiotherapy;radioterapia;radiation therapy;radiation oncologist;radioterapist;radioterapeuta', TRUE),
('394914008', 'Radiology', 'Radiology - specialty (qualifier value)', 'Radiodiagnóstico', 'radiology;radiologia;radiologist;radiologo;x-ray;radiografia;imaging;imagen diagnostica;diagnostic imaging;radiodiagnostico', TRUE),
('394602003', 'Rehabilitation', 'Rehabilitation specialty (qualifier value)', 'Medicina Física y Rehabilitación', 'rehabilitation;rehabilitacion;physiatry;physiatrist;fisiatra;physical medicine;medicina fisica', TRUE),
('394810000', 'Rheumatology', 'Rheumatology (qualifier value)', 'Reumatología', 'rheumatology;reumatologia;rheumatologist;reumatologo;arthritis;artritis;autoimmune;autoinmune;joint disease', TRUE),
('408466002', 'Surgery-Cardiac surgery', 'Cardiac surgery (qualifier value)', 'Cirugía Cardiovascular', 'cardiac surgery;cirugia cardiaca;cardiovascular surgery;cirugia cardiovascular;heart surgery;cirugia del corazon;cardiothoracic surgery', TRUE),
('408471009', 'Surgery-Cardiothoracic transplantation', 'Cardiothoracic transplantation (qualifier value)', 'Cirugía Torácica', 'thoracic surgery;cirugia toracica;chest surgery;cirugia de torax;lung surgery;cirugia pulmonar', TRUE),
('408465003', 'Surgery-Dental-Oral and maxillofacial surgery', 'Oral and maxillofacial surgery (qualifier value)', 'Cirugía Oral y Maxilofacial', 'oral and maxillofacial surgery;cirugia oral y maxilofacial;maxillofacial surgery;cirugia maxilofacial;oral surgery;cirugia oral;jaw surgery', TRUE),
('394609007', 'Surgery-general', 'General surgery (qualifier value)', 'Cirugía General y del Aparato Digestivo', 'general surgery;cirugia general;general surgeon;cirujano general;abdominal surgery;cirugia abdominal', TRUE),
('394610002', 'Surgery-Neurosurgery', 'Neurosurgery (qualifier value)', 'Neurocirugía', 'neurosurgery;neurocirugia;neurosurgeon;neurocirujano;brain surgery;spine surgery;cirugia cerebral;cirugia espinal', TRUE),
('394611003', 'Surgery-Plastic surgery', 'Plastic surgery - speciality', 'Cirugía Plástica, Estética y Reparadora', 'plastic surgery;cirugia plastica;plastic surgeon;cirujano plastico;reconstructive surgery;aesthetic surgery;cirugia estetica;cirugia reparadora', TRUE),
('394801008', 'Surgery-Trauma and orthopedics', 'Trauma & orthopaedics', 'Cirugía Ortopédica y Traumatología', 'orthopedic surgery;orthopaedic surgery;cirugia ortopedica;traumatology;traumatologia;orthopedist;orthopaedist;traumatologo;bone surgery;fracture;fractura', TRUE),
('408463005', 'Surgery-Vascular', 'Vascular surgery (qualifier value)', 'Angiología y Cirugía Vascular', 'vascular surgery;cirugia vascular;vascular surgeon;cirujano vascular;angiology;angiologia;angiologist;angiologo;vein;vena;artery;arteria', TRUE),
('394612005', 'Urology', 'Urology (qualifier value)', 'Urología', 'urology;urologia;urologist;urologo;urinary;urinario;bladder;vejiga;prostate;prostata', TRUE),

-- ============================================================================
-- ESPECIALIDADES SNOMED CT ADICIONALES (NO MIR España) (72)
-- ============================================================================
('408467006', 'Adult mental illness', 'Adult mental illness - specialty (qualifier value)', NULL, NULL, FALSE),
('394578005', 'Audiological medicine', 'Audiological medicine (qualifier value)', NULL, NULL, FALSE),
('421661004', 'Blood banking and transfusion medicine', 'Blood banking and transfusion medicine (specialty) (qualifier value)', NULL, NULL, FALSE),
('408462000', 'Burns care', 'Burns care (qualifier value)', NULL, NULL, FALSE),
('394804000', 'Clinical cytogenetics and molecular genetics', 'Clinical cytogenetics and molecular genetics (qualifier value)', NULL, NULL, FALSE),
('394580004', 'Clinical genetics', 'Clinical genetics (qualifier value)', NULL, NULL, FALSE),
('394592004', 'Clinical oncology', 'Clinical oncology (qualifier value)', NULL, NULL, FALSE),
('394601005', 'Clinical physiology', 'Clinical physiology (qualifier value)', NULL, NULL, FALSE),
('394581000', 'Community medicine', 'Community medicine (qualifier value)', NULL, NULL, FALSE),
('394812008', 'Dental medicine specialties', 'Dental medicine specialties (qualifier value)', NULL, NULL, FALSE),
('408444009', 'Dental-General dental practice', 'General dental practice (qualifier value)', NULL, NULL, FALSE),
('408475000', 'Diabetic medicine', 'Diabetic medicine (qualifier value)', NULL, NULL, FALSE),
('410005002', 'Dive medicine', 'Dive medicine (qualifier value)', NULL, NULL, FALSE),
('408443003', 'General medical practice', 'General medical practice (qualifier value)', NULL, NULL, FALSE),
('394802001', 'General medicine', 'General medicine (qualifier value)', NULL, NULL, FALSE),
('394814009', 'General practice', 'General practice (specialty) (qualifier value)', NULL, NULL, FALSE),
('394808002', 'Genito-urinary medicine', 'Genitourinary medicine (qualifier value)', NULL, NULL, FALSE),
('408446006', 'Gynecological oncology', 'Gynaecological oncology', NULL, NULL, FALSE),
('394586005', 'Gynecology', 'Gynaecology', NULL, NULL, FALSE),
('394916005', 'Hematopathology', 'Haematology (specialty)', NULL, NULL, FALSE),
('408472002', 'Hepatology', 'Hepatology (qualifier value)', NULL, NULL, FALSE),
('394598000', 'Immunopathology', 'Immunopathology (qualifier value)', NULL, NULL, FALSE),
('394807007', 'Infectious diseases', 'Infectious disease specialty (qualifier value)', NULL, NULL, FALSE),
('408468001', 'Learning disability', 'Learning disability - specialty (qualifier value)', NULL, NULL, FALSE),
('394813003', 'Medical ophthalmology', 'Medical ophthalmology (qualifier value)', NULL, NULL, FALSE),
('410001006', 'Military medicine', 'Military medicine (qualifier value)', NULL, NULL, FALSE),
('394599008', 'Neuropathology', 'Neuropathology (qualifier value)', NULL, NULL, FALSE),
('408470005', 'Obstetrics', 'Obstetrics (qualifier value)', NULL, NULL, FALSE),
('422191005', 'Ophthalmic surgery', 'Ophthalmic surgery (qualifier value)', NULL, NULL, FALSE),
('416304004', 'Osteopathic manipulative medicine', 'Osteopathic manipulative medicine (qualifier value)', NULL, NULL, FALSE),
('394882004', 'Pain management', 'Pain management (specialty) (qualifier value)', NULL, NULL, FALSE),
('394806003', 'Palliative medicine', 'Palliative medicine (qualifier value)', NULL, NULL, FALSE),
('408459003', 'Pediatric cardiology', 'Paediatric cardiology', NULL, NULL, FALSE),
('394607009', 'Pediatric dentistry', 'Paediatric dentistry', NULL, NULL, FALSE),
('419610006', 'Pediatric endocrinology', 'Pediatric endocrinology', NULL, NULL, FALSE),
('418058008', 'Pediatric gastroenterology', 'Pediatric gastroenterology', NULL, NULL, FALSE),
('420208008', 'Pediatric genetics', 'Pediatric genetics', NULL, NULL, FALSE),
('418652005', 'Pediatric hematology', 'Pediatric hematology (qualifier value)', NULL, NULL, FALSE),
('418535003', 'Pediatric immunology', 'Pediatric immunology (qualifier value)', NULL, NULL, FALSE),
('418862001', 'Pediatric infectious diseases', 'Pediatric infectious diseases (qualifier value)', NULL, NULL, FALSE),
('419365004', 'Pediatric nephrology', 'Pediatric nephrology (qualifier value)', NULL, NULL, FALSE),
('418002000', 'Pediatric oncology', 'Pediatric oncology (qualifier value)', NULL, NULL, FALSE),
('419983000', 'Pediatric ophthalmology', 'Pediatric ophthalmology', NULL, NULL, FALSE),
('419170002', 'Pediatric pulmonology', 'Pediatric pulmonology (qualifier value)', NULL, NULL, FALSE),
('419472004', 'Pediatric rheumatology', 'Pediatric rheumatology', NULL, NULL, FALSE),
('420112009', 'Pediatric surgery-bone marrow transplantation', 'Pediatric bone marrow transplantation (qualifier value)', NULL, NULL, FALSE),
('394913002', 'Psychotherapy', 'Psychotherapy (specialty) (qualifier value)', NULL, NULL, FALSE),
('408440000', 'Public health medicine', 'Public health medicine (qualifier value)', NULL, NULL, FALSE),
('408455009', 'Radiology-Interventional radiology', 'Interventional radiology - specialty (qualifier value)', NULL, NULL, FALSE),
('408447002', 'Respite care', 'Respite care - specialty (qualifier value)', NULL, NULL, FALSE),
('408450004', 'Sleep studies', 'Sleep studies - specialty (qualifier value)', NULL, NULL, FALSE),
('408476004', 'Surgery-Bone and marrow transplantation', 'Bone and marrow transplantation (qualifier value)', NULL, NULL, FALSE),
('408469009', 'Surgery-Breast surgery', 'Breast surgery (qualifier value)', NULL, NULL, FALSE),
('408464004', 'Surgery-Colorectal surgery', 'Colorectal surgery (qualifier value)', NULL, NULL, FALSE),
('408441001', 'Surgery-Dental-Endodontics', 'Endodontics - specialty (qualifier value)', NULL, NULL, FALSE),
('394605001', 'Surgery-Dental-Oral surgery', 'Oral surgery (qualifier value)', NULL, NULL, FALSE),
('394608004', 'Surgery-Dental-Orthodontics', 'Orthodontics (qualifier value)', NULL, NULL, FALSE),
('408461007', 'Surgery-Dental-Periodontal surgery', 'Periodontics (qualifier value)', NULL, NULL, FALSE),
('408460008', 'Surgery-Dental-Prosthetic dentistry (Prosthodontics)', 'Prosthodontics (qualifier value)', NULL, NULL, FALSE),
('394606000', 'Surgery-Dentistry-Restorative dentistry', 'Restorative dentistry (qualifier value)', NULL, NULL, FALSE),
('408449004', 'Surgery-Dentistry--surgical', 'Surgical dentistry (qualifier value)', NULL, NULL, FALSE),
('418018006', 'Surgery-Dermatologic surgery', 'Dermatologic surgery (qualifier value)', NULL, NULL, FALSE),
('394604002', 'Surgery-Ear, nose and throat surgery', 'Ear, nose and throat surgery (qualifier value)', NULL, NULL, FALSE),
('408474001', 'Surgery-Hepatobiliary and pancreatic surgery', 'Hepatobiliary and pancreatic surgery (qualifier value)', NULL, NULL, FALSE),
('408477008', 'Surgery-Transplantation surgery', 'Transplantation surgery (qualifier value)', NULL, NULL, FALSE),
('419321007', 'Surgical oncology', 'Surgical oncology (qualifier value)', NULL, NULL, FALSE),
('394732004', 'Surgical specialty (OTHER)', 'Surgical specialties', NULL, NULL, FALSE),
('394576009', 'Surgical-Accident & emergency', 'Accident & emergency (qualifier value)', NULL, NULL, FALSE),
('394590007', 'Thoracic medicine', 'Thoracic medicine (qualifier value)', NULL, NULL, FALSE),
('409967009', 'Toxicology', 'Toxicology (qualifier value)', NULL, NULL, FALSE),
('408448007', 'Tropical medicine', 'Tropical medicine (qualifier value)', NULL, NULL, FALSE),
('419043006', 'Urological oncology', 'Urological oncology (qualifier value)', NULL, NULL, FALSE);

-- ============================================================================
-- Índices
-- ============================================================================
CREATE INDEX idx_snomed_specialties_snomed ON snomed_specialties(snomed_code);
CREATE INDEX idx_snomed_specialties_mir ON snomed_specialties(is_mir_spain);

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON TABLE snomed_specialties IS 'Especialidades médicas SNOMED CT / HL7 FHIR';
COMMENT ON COLUMN snomed_specialties.snomed_code IS 'Código SNOMED CT único';
COMMENT ON COLUMN snomed_specialties.name_en IS 'Nombre simplificado en inglés';
COMMENT ON COLUMN snomed_specialties.name_snomed IS 'Nombre oficial FHIR (con qualifier value)';
COMMENT ON COLUMN snomed_specialties.name_es IS 'Traducción al español';
COMMENT ON COLUMN snomed_specialties.synonyms IS 'Sinónimos para matching, separados por punto y coma';
COMMENT ON COLUMN snomed_specialties.is_mir_spain IS 'TRUE si es especialidad MIR española';
COMMENT ON COLUMN snomed_specialties.last_checked IS 'Última sincronización con API FHIR';
